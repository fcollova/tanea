"""
Rate Limiter e Robots.txt Parser per crawling rispettoso
Implementa back-off exponential, rate limiting per-dominio e rispetto robots.txt
"""

import asyncio
import time
import aiohttp
import io
from typing import Dict, Optional, Set, List
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..config import get_crawler_config
from ..log import get_news_logger

logger = get_news_logger(__name__)

@dataclass
class RateLimit:
    """Configurazione rate limiting per dominio"""
    requests_per_second: float = 0.5  # Default: 1 request ogni 2 secondi
    max_concurrent: int = 2
    back_off_factor: float = 2.0
    max_back_off: float = 300.0  # 5 minuti max
    
class DomainRateLimiter:
    """Rate limiter per-dominio con back-off exponential"""
    
    def __init__(self, requests_per_second: float = 0.5, max_concurrent: int = 2):
        self.requests_per_second = requests_per_second
        self.max_concurrent = max_concurrent
        self.last_request_time = 0.0
        self.request_history = deque(maxlen=100)  # Ultimi 100 requests
        self.current_delay = 1.0 / requests_per_second
        self.back_off_factor = 2.0
        self.max_back_off = 300.0
        self.concurrent_requests = 0
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
    async def acquire(self) -> None:
        """Acquisisce il permesso per fare una richiesta"""
        await self.semaphore.acquire()
        self.concurrent_requests += 1
        
        # Calcola delay necessario
        now = time.time()
        min_delay = 1.0 / self.requests_per_second
        time_since_last = now - self.last_request_time
        
        if time_since_last < min_delay:
            delay = min_delay - time_since_last
            logger.debug(f"Rate limiting: attesa {delay:.2f}s")
            await asyncio.sleep(delay)
        
        self.last_request_time = time.time()
        self.request_history.append(self.last_request_time)
        
    def release(self, success: bool = True) -> None:
        """Rilascia il permesso e aggiorna back-off"""
        self.concurrent_requests -= 1
        self.semaphore.release()
        
        if success:
            # Reset graduale del delay in caso di successo
            self.current_delay = max(
                1.0 / self.requests_per_second,
                self.current_delay * 0.9
            )
        else:
            # Aumenta delay in caso di errore (exponential back-off)
            self.current_delay = min(
                self.current_delay * self.back_off_factor,
                self.max_back_off
            )
            logger.warning(f"Back-off attivato: delay aumentato a {self.current_delay:.2f}s")
            
    def get_stats(self) -> Dict:
        """Statistiche rate limiting"""
        now = time.time()
        recent_requests = len([t for t in self.request_history if now - t < 60])
        
        return {
            'requests_last_minute': recent_requests,
            'current_delay': self.current_delay,
            'concurrent_requests': self.concurrent_requests,
            'requests_per_second': self.requests_per_second
        }

class RobotsTxtParser:
    """Parser per robots.txt con caching"""
    
    def __init__(self):
        self.robots_cache: Dict[str, RobotFileParser] = {}
        self.cache_expiry: Dict[str, datetime] = {}
        self.cache_duration = timedelta(hours=24)  # Cache 24 ore
        self.user_agent = get_crawler_config().get('user_agent', 'TaneaBot/1.0')
        self._downloading: Set[str] = set()  # Domini in download per evitare duplicati
        self._download_lock = asyncio.Lock()  # Lock per operazioni di download
        
    async def can_fetch(self, url: str) -> bool:
        """Verifica se possiamo crawlare l'URL secondo robots.txt"""
        try:
            parsed_url = urlparse(url)
            domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Controlla cache
            if domain in self.robots_cache:
                if datetime.now() < self.cache_expiry[domain]:
                    rp = self.robots_cache[domain]
                    can_fetch = rp.can_fetch(self.user_agent, url)
                    logger.debug(f"Robots.txt cache HIT: {domain} -> {can_fetch}")
                    return can_fetch
                else:
                    # Cache scaduta
                    logger.debug(f"Robots.txt cache EXPIRED per {domain}")
                    del self.robots_cache[domain]
                    del self.cache_expiry[domain]
            
            # Use lock per evitare download concorrenti dello stesso dominio
            async with self._download_lock:
                # Ricontrolla cache dopo aver acquisito il lock
                if domain in self.robots_cache:
                    if datetime.now() < self.cache_expiry[domain]:
                        rp = self.robots_cache[domain]
                        can_fetch = rp.can_fetch(self.user_agent, url)
                        logger.debug(f"Robots.txt cache HIT (dopo lock): {domain} -> {can_fetch}")
                        return can_fetch
                
                # Controlla se qualcun altro sta già scaricando lo stesso dominio
                if domain in self._downloading:
                    logger.debug(f"Robots.txt già in download per {domain}, assumo permesso temporaneo")
                    return True
                
                # Scarica e parsa robots.txt solo se non in cache
                logger.debug(f"Robots.txt cache MISS per {domain}, scarico...")
                self._downloading.add(domain)
            
            try:
                robots_url = urljoin(domain, '/robots.txt')
                rp = await self._fetch_robots_txt(robots_url)
            finally:
                async with self._download_lock:
                    self._downloading.discard(domain)
            
            if rp:
                self.robots_cache[domain] = rp
                self.cache_expiry[domain] = datetime.now() + self.cache_duration
                can_fetch = rp.can_fetch(self.user_agent, url)
                logger.info(f"Robots.txt DOWNLOADED: {domain} -> permette {url}: {can_fetch}")
                return can_fetch
            else:
                # Se non riusciamo a scaricare robots.txt, cache un risultato positivo temporaneo
                logger.warning(f"Impossibile scaricare robots.txt per {domain}, assumo permesso per 1 ora")
                
                # Cache un parser vuoto che permette tutto per 1 ora
                empty_rp = RobotFileParser()
                empty_rp.set_url(urljoin(domain, '/robots.txt'))
                
                self.robots_cache[domain] = empty_rp
                self.cache_expiry[domain] = datetime.now() + timedelta(hours=1)  # Cache più breve
                return True
                
        except Exception as e:
            logger.error(f"Errore parsing robots.txt per {url}: {e}")
            return True  # In caso di errore, assumiamo permesso
            
    async def _fetch_robots_txt(self, robots_url: str) -> Optional[RobotFileParser]:
        """Scarica e parsa robots.txt"""
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'text/plain',
                'Connection': 'close'
            }
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(robots_url, headers=headers) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        rp = RobotFileParser()
                        rp.set_url(robots_url)
                        
                        # Compatibilità per diverse versioni di Python
                        try:
                            if hasattr(rp, 'set_content'):
                                rp.set_content(content)
                            elif hasattr(rp, 'readfp'):
                                # Fallback per versioni più vecchie
                                rp.readfp(io.StringIO(content))
                            else:
                                # Metodo alternativo: usa il parser manuale
                                rp = self._parse_robots_content(robots_url, content)
                        except Exception as attr_e:
                            logger.debug(f"Metodo standard fallito per RobotFileParser: {attr_e}, uso parser manuale")
                            # Usa parser manuale in caso di problemi
                            rp = self._parse_robots_content(robots_url, content)
                        
                        logger.info(f"Robots.txt scaricato e parsato da {robots_url} ({len(content)} caratteri)")
                        return rp
                    else:
                        logger.debug(f"Robots.txt non trovato: {robots_url} (status: {response.status})")
                        return None
                        
        except asyncio.TimeoutError:
            logger.warning(f"Timeout scaricamento robots.txt da {robots_url}")
            return None
        except Exception as e:
            logger.debug(f"Errore download robots.txt da {robots_url}: {e}")
            return None
    
    def _parse_robots_content(self, robots_url: str, content: str) -> RobotFileParser:
        """Parser manuale per robots.txt quando i metodi standard non funzionano"""
        try:
            # Crea un RobotFileParser e usa il metodo parse() se disponibile
            rp = RobotFileParser()
            rp.set_url(robots_url)
            
            # Prova a scrivere il contenuto in un file temporaneo e far leggere da lì
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
                tmp_file.write(content)
                tmp_file_path = tmp_file.name
            
            try:
                # Imposta l'URL al file temporaneo
                rp.set_url(f"file://{tmp_file_path}")
                rp.read()
                # Ripristina l'URL originale
                rp.set_url(robots_url)
                logger.debug(f"Robots.txt parsato via file temporaneo: {robots_url}")
                return rp
            finally:
                # Pulisci il file temporaneo
                import os
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass
                    
        except Exception as e:
            logger.debug(f"Parser manuale fallito per {robots_url}: {e}")
            # Ritorna un parser vuoto che permette tutto
            empty_rp = RobotFileParser()
            empty_rp.set_url(robots_url)
            return empty_rp
            
    def get_sitemap_urls(self, domain: str) -> List[str]:
        """Estrae URL sitemap da robots.txt"""
        if domain in self.robots_cache:
            rp = self.robots_cache[domain]
            if hasattr(rp, 'site_maps'):
                return list(rp.site_maps())
        return []

class AdvancedRateLimiter:
    """Rate limiter avanzato con supporto robots.txt e rate limiting per-dominio"""
    
    def __init__(self):
        self.config = get_crawler_config()
        self.domain_limiters: Dict[str, DomainRateLimiter] = {}
        self.robots_parser = RobotsTxtParser()
        
        # Configurazione default
        self.default_rate_limit = RateLimit(
            requests_per_second=1.0 / self.config.get('rate_limit', 2.0),
            max_concurrent=self.config.get('max_concurrent', 3)
        )
        
        # Configurazioni specifiche per dominio
        self.domain_configs = {
            'tuttomercatoweb.com': RateLimit(
                requests_per_second=0.3,  # 1 request ogni 3.3 secondi 
                max_concurrent=2
            ),
            'gazzetta.it': RateLimit(
                requests_per_second=0.5,  # 1 request ogni 2 secondi
                max_concurrent=2
            )
        }
        
        logger.info("Advanced Rate Limiter inizializzato")
        
    def _get_domain_limiter(self, url: str) -> DomainRateLimiter:
        """Ottiene il rate limiter per il dominio dell'URL"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        if domain not in self.domain_limiters:
            # Configurazione specifica per dominio o default
            config = self.domain_configs.get(domain, self.default_rate_limit)
            
            self.domain_limiters[domain] = DomainRateLimiter(
                requests_per_second=config.requests_per_second,
                max_concurrent=config.max_concurrent
            )
            
            logger.info(f"Rate limiter creato per {domain}: {config.requests_per_second} req/s")
            
        return self.domain_limiters[domain]
        
    async def can_crawl(self, url: str) -> bool:
        """Verifica se possiamo crawlare l'URL (robots.txt check)"""
        return await self.robots_parser.can_fetch(url)
        
    async def acquire_for_url(self, url: str) -> bool:
        """Acquisisce permesso per crawlare URL specifico"""
        # 1. Controlla robots.txt
        if not await self.can_crawl(url):
            logger.warning(f"URL bloccato da robots.txt: {url}")
            return False
            
        # 2. Applica rate limiting per-dominio
        limiter = self._get_domain_limiter(url)
        await limiter.acquire()
        
        logger.debug(f"Rate limiting: permesso acquisito per {url}")
        return True
        
    def release_for_url(self, url: str, success: bool = True) -> None:
        """Rilascia permesso per URL"""
        limiter = self._get_domain_limiter(url)
        limiter.release(success)
        
        if not success:
            logger.warning(f"Request fallita per {url}, back-off attivato")
            
    def get_domain_stats(self) -> Dict[str, Dict]:
        """Statistiche rate limiting per tutti i domini"""
        stats = {}
        for domain, limiter in self.domain_limiters.items():
            stats[domain] = limiter.get_stats()
        return stats
        
    def get_sitemap_urls(self, domain: str) -> List[str]:
        """Ottiene URL sitemap da robots.txt"""
        return self.robots_parser.get_sitemap_urls(domain)