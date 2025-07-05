"""
Link Discoverer - Scoperta nuovi link dalle pagine dei siti
"""

import asyncio
import aiohttp
import time
from typing import List, Dict, Set, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False

from ..config import get_crawler_config
from ..log import get_news_logger

logger = get_news_logger(__name__)

class LinkDiscoverer:
    """Scopre nuovi link articoli dalle pagine categoria dei siti"""
    
    def __init__(self):
        self.config = get_crawler_config()
        self.session = None
        self.rate_limit_delay = self.config['rate_limit']
        self.timeout = self.config['timeout']
        self.max_retries = self.config['max_retries']
        
        # Cache per evitare duplicati nella sessione
        self.discovered_urls = set()
        
        # Headers realistici per evitare bot detection
        self.headers = {
            'User-Agent': self.config['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    async def __aenter__(self):
        """Context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers=self.headers
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            await self.session.close()
    
    async def discover_site_links(self, site_config: Dict) -> List[str]:
        """
        Scopre link articoli da tutte le categorie di un sito
        
        Args:
            site_config: Configurazione sito da web_scraping.yaml
            
        Returns:
            list: Lista URL articoli scoperti
        """
        if not site_config.get('active', True):
            logger.debug(f"Sito {site_config.get('name')} disattivato, skip discovery")
            return []
        
        site_name = site_config.get('name', 'Unknown')
        logger.info(f"Inizio discovery link per sito: {site_name}")
        
        all_links = []
        categories = site_config.get('categories', {})
        
        for category_name, category_config in categories.items():
            try:
                category_url = category_config.get('url') if isinstance(category_config, dict) else category_config
                if not category_url:
                    continue
                
                logger.debug(f"Discovery categoria {category_name}: {category_url}")
                
                # Rate limiting
                await asyncio.sleep(self.rate_limit_delay)
                
                # Scopri link dalla categoria
                category_links = await self._discover_category_links(
                    category_url, 
                    site_config, 
                    category_config
                )
                
                all_links.extend(category_links)
                logger.debug(f"Categoria {category_name}: {len(category_links)} link trovati")
                
            except Exception as e:
                logger.error(f"Errore discovery categoria {category_name}: {e}")
                continue
        
        # Rimuovi duplicati mantenendo ordine
        unique_links = []
        seen = set()
        for link in all_links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)
        
        logger.info(f"Sito {site_name}: {len(unique_links)} link unici scoperti")
        return unique_links
    
    async def _discover_category_links(self, category_url: str, site_config: Dict, 
                                     category_config: Dict) -> List[str]:
        """Scopre link da una singola pagina categoria"""
        try:
            # Scarica pagina categoria
            html = await self._fetch_page(category_url)
            if not html:
                return []
            
            # Usa trafilatura se disponibile per link discovery
            if TRAFILATURA_AVAILABLE:
                trafilatura_links = self._extract_links_trafilatura(html, site_config['base_url'])
                if trafilatura_links:
                    return trafilatura_links
            
            # Fallback a selettori CSS
            return self._extract_links_selectors(html, site_config, category_config)
            
        except Exception as e:
            logger.error(f"Errore discovery da {category_url}: {e}")
            return []
    
    async def _fetch_page(self, url: str, retry_count: int = 0) -> Optional[str]:
        """Scarica pagina con retry logic"""
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                elif response.status == 429:  # Rate limited
                    if retry_count < self.max_retries:
                        wait_time = self.rate_limit_delay * (2 ** retry_count)
                        logger.warning(f"Rate limited su {url}, attendo {wait_time}s")
                        await asyncio.sleep(wait_time)
                        return await self._fetch_page(url, retry_count + 1)
                else:
                    logger.warning(f"HTTP {response.status} per {url}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout per {url}")
            return None
        except Exception as e:
            logger.error(f"Errore fetch {url}: {e}")
            return None
    
    def _extract_links_trafilatura(self, html: str, base_url: str) -> List[str]:
        """Estrae link usando trafilatura (più intelligente)"""
        try:
            # Usa trafilatura per estrarre tutti i link
            links = trafilatura.extract_links(html)
            
            if not links:
                return []
            
            # Filtra e normalizza link
            article_links = []
            for link in links:
                normalized_link = self._normalize_url(link, base_url)
                if normalized_link and self._is_likely_article(normalized_link):
                    article_links.append(normalized_link)
            
            return article_links[:50]  # Limita per performance
            
        except Exception as e:
            logger.debug(f"Errore trafilatura link extraction: {e}")
            return []
    
    def _extract_links_selectors(self, html: str, site_config: Dict, 
                               category_config: Dict) -> List[str]:
        """Fallback con selettori CSS"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            base_url = site_config['base_url']
            
            # Prova selettori specifici categoria
            links = []
            if isinstance(category_config, dict) and 'selectors' in category_config:
                selectors = category_config['selectors']
                link_selector = selectors.get('article_links')
                if link_selector:
                    elements = soup.select(link_selector)
                    links = [elem.get('href') for elem in elements if elem.get('href')]
            
            # Fallback a selettori generici
            if not links:
                generic_selectors = [
                    'a[href*="/article"]', 'a[href*="/news"]', 'a[href*="/articolo"]',
                    'a[href*="/sport"]', 'a[href*="/calcio"]', 'a[href*="/notizie"]',
                    '.article-title a', '.news-title a', '.headline a',
                    'h1 a', 'h2 a', 'h3 a'
                ]
                
                for selector in generic_selectors:
                    elements = soup.select(selector)
                    if elements:
                        links = [elem.get('href') for elem in elements if elem.get('href')]
                        break
            
            # Normalizza URL
            normalized_links = []
            for link in links:
                normalized = self._normalize_url(link, base_url)
                if normalized and self._is_likely_article(normalized):
                    normalized_links.append(normalized)
            
            return normalized_links[:30]  # Limita per performance
            
        except Exception as e:
            logger.error(f"Errore selettori CSS: {e}")
            return []
    
    def _normalize_url(self, url: str, base_url: str) -> Optional[str]:
        """Normalizza URL relativo in assoluto"""
        if not url:
            return None
        
        try:
            # Rimuovi anchors e query parameters troppo complessi
            if '#' in url:
                url = url.split('#')[0]
            
            # Converti in URL assoluto
            if url.startswith('/'):
                url = urljoin(base_url, url)
            elif not url.startswith('http'):
                url = urljoin(base_url, url)
            
            # Valida URL
            parsed = urlparse(url)
            if parsed.scheme in ('http', 'https') and parsed.netloc:
                return url
            
            return None
            
        except Exception:
            return None
    
    def _is_likely_article(self, url: str) -> bool:
        """Determina se URL è probabilmente un articolo"""
        url_lower = url.lower()
        
        # Pattern positivi (articoli)
        positive_patterns = [
            '/articolo', '/article', '/news', '/notizie', '/sport', '/calcio',
            '/cronaca', '/politica', '/economia', '/tecnologia', '/salute'
        ]
        
        # Pattern negativi (navigazione)
        negative_patterns = [
            '/tag/', '/category/', '/author/', '/search/', '/page/',
            '?', '/rss', '/feed', '/sitemap', '/home', '/contact', 
            '/about', '/privacy', '/cookie', '/login', '/register',
            '.pdf', '.jpg', '.png', '.gif', '.mp4', '.mp3'
        ]
        
        # Check pattern positivi
        has_positive = any(pattern in url_lower for pattern in positive_patterns)
        
        # Check pattern negativi
        has_negative = any(pattern in url_lower for pattern in negative_patterns)
        
        # Se ha pattern positivi e non negativi, è probabilmente un articolo
        if has_positive and not has_negative:
            return True
        
        # Se non ha pattern negativi ed è sufficientemente specifico
        if not has_negative and len(url.split('/')) >= 4:
            return True
        
        return False
    
    def get_discovery_stats(self) -> Dict[str, int]:
        """Statistiche discovery sessione corrente"""
        return {
            'total_discovered': len(self.discovered_urls),
            'session_urls': len(self.discovered_urls)
        }