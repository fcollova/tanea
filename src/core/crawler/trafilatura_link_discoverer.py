"""
Trafilatura Link Discoverer - Crawler moderno basato su Trafilatura Spider
Utilizza run_spider di Trafilatura per discovery automatico dei link
"""

import asyncio
from typing import List, Dict, Set, Optional, Any
from urllib.parse import urljoin, urlparse

try:
    from trafilatura import fetch_url, extract
    from trafilatura.sitemaps import sitemap_search
    from trafilatura.spider import focused_crawler
    from bs4 import BeautifulSoup
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False
    BeautifulSoup = None

from ..config import get_config, get_web_crawling_config
from ..domain_manager import DomainManager
from ..log import get_news_logger

logger = get_news_logger(__name__)

class TrafilaturaLinkDiscoverer:
    """Link Discoverer moderno che usa Trafilatura Spider per crawling automatico"""
    
    def __init__(self):
        self.config = get_config()
        self.crawling_config = get_web_crawling_config()
        self.domain_manager = DomainManager()
        
        # Parametri spider da configurazione
        self.spider_max_depth = self.crawling_config.get('spider_max_depth', 2)
        self.spider_max_pages = self.crawling_config.get('spider_max_pages', 50)
        self.spider_max_known_urls = self.crawling_config.get('spider_max_known_urls', 150)
        self.spider_language = self.crawling_config.get('spider_language', 'it')
        self.rate_limit_delay = self.crawling_config.get('rate_limit_delay', 2.0)
        
        # Cache per evitare duplicati nella sessione
        self.discovered_urls = set()
        
        logger.info(f"Trafilatura Focused Crawler configurato: max_depth={self.spider_max_depth}, max_pages={self.spider_max_pages}, max_known={self.spider_max_known_urls}, language={self.spider_language}")
    
    async def __aenter__(self):
        """Context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        pass
    
    async def discover_site_links(self, site_config: Dict) -> List[str]:
        """
        Scopre link usando Trafilatura Spider
        
        Args:
            site_config: Configurazione sito da web_crawling.yaml
            
        Returns:
            list: Lista URL articoli scoperti
        """
        if not site_config.get('active', True):
            logger.debug(f"Sito {site_config.get('name')} disattivato, skip discovery")
            return []
        
        if not TRAFILATURA_AVAILABLE:
            logger.error("Trafilatura non disponibile, impossibile utilizzare spider")
            return []
        
        site_name = site_config.get('name', 'Unknown')
        base_url = site_config.get('base_url')
        domain = site_config.get('domain', 'general')
        
        if not base_url:
            logger.error(f"Nessun base_url configurato per {site_name}")
            return []
        
        logger.info(f"Inizio spider crawling per sito: {site_name} ({base_url})")
        
        try:
            # STRATEGIA 1: Trafilatura Spider (principale)
            spider_links = await self._discover_with_spider(base_url, site_name, domain)
            
            if spider_links:
                logger.info(f"Spider: {len(spider_links)} link scoperti per {site_name}")
                for i, link in enumerate(spider_links[:5], 1):  # Primi 5 link
                    logger.info(f"  Spider[{i}]: {link}")
                if len(spider_links) > 5:
                    logger.info(f"  Spider[...]: +{len(spider_links)-5} altri link")
                return spider_links
            
            # STRATEGIA 2: Sitemap Discovery (fallback)
            sitemap_links = await self._discover_with_sitemap(base_url, site_name, domain)
            
            if sitemap_links:
                logger.info(f"Sitemap: {len(sitemap_links)} link scoperti per {site_name}")
                for i, link in enumerate(sitemap_links, 1):
                    is_article = self._is_article_url(link)
                    logger.info(f"  Sitemap[{i}]: {link} {'(ARTICOLO)' if is_article else '(CATEGORIA)'}")
                
                # Verifica se sono pagine categoria o articoli reali
                article_count = sum(1 for link in sitemap_links if self._is_article_url(link))
                if article_count > 0:
                    logger.info(f"Sitemap contiene {article_count} articoli reali")
                    return sitemap_links
                else:
                    logger.info(f"Sitemap contiene solo pagine categoria, provo estrazione articoli")
                    # Continua alla strategia successiva
            
            # STRATEGIA 3: BeautifulSoup per estrazione articoli da pagine categoria
            category_links = await self._extract_articles_from_categories(base_url, site_name, domain)
            
            if category_links:
                logger.info(f"Categoria extraction: {len(category_links)} link articoli scoperti per {site_name}")
                for i, link in enumerate(category_links[:10], 1):  # Primi 10 link
                    logger.info(f"  Categoria[{i}]: {link}")
                if len(category_links) > 10:
                    logger.info(f"  Categoria[...]: +{len(category_links)-10} altri link")
                return category_links
            
            # STRATEGIA 4: BeautifulSoup Fallback (ultimo resort)
            fallback_links = await self._discover_with_beautifulsoup(base_url, site_name, domain)
            
            logger.info(f"Fallback: {len(fallback_links)} link scoperti per {site_name}")
            for i, link in enumerate(fallback_links[:5], 1):  # Primi 5 link
                logger.info(f"  Fallback[{i}]: {link}")
            if len(fallback_links) > 5:
                logger.info(f"  Fallback[...]: +{len(fallback_links)-5} altri link")
            return fallback_links
            
        except Exception as e:
            logger.error(f"Errore discovery per {site_name}: {e}")
            return []
    
    async def _discover_with_spider(self, base_url: str, site_name: str, domain: str) -> List[str]:
        """Usa Trafilatura Spider per discovery automatico"""
        try:
            # Esegui spider in thread separato per non bloccare async
            loop = asyncio.get_event_loop()
            
            logger.debug(f"Avvio focused_crawler per {base_url} (max_pages={self.spider_max_pages})")
            
            # Run spider in executor per evitare blocking
            spider_results = await loop.run_in_executor(
                None,
                self._run_spider_sync,
                base_url
            )
            
            if not spider_results:
                logger.warning(f"Spider non ha trovato URL per {site_name}")
                return []
            
            logger.debug(f"Spider raw results: {len(spider_results)} URL trovati")
            
            # Filtra e processa i risultati
            filtered_links = self._filter_spider_results(spider_results, domain, base_url)
            
            return filtered_links
            
        except Exception as e:
            logger.error(f"Errore spider per {base_url}: {e}")
            return []
    
    def _run_spider_sync(self, base_url: str) -> List[str]:
        """Esegue focused crawler in modo sincrono"""
        try:
            # Usa focused_crawler con parametri supportati (max_depth non è supportato)
            results = focused_crawler(
                homepage=base_url,
                max_seen_urls=self.spider_max_pages,      # URL da visitare
                max_known_urls=self.spider_max_known_urls, # URL totali mantenuti
                lang=self.spider_language
            )
            
            # Converte il risultato in lista se necessario
            if hasattr(results, '__iter__') and not isinstance(results, str):
                return list(results)
            else:
                return [results] if results else []
                
        except Exception as e:
            logger.error(f"Errore esecuzione focused_crawler: {e}")
            return []
    
    def _filter_spider_results(self, spider_results: List[str], domain: str, base_url: str) -> List[str]:
        """Filtra risultati spider per rilevanza dominio"""
        try:
            # Ottieni keywords del dominio
            domain_keywords = []
            if domain:
                domain_config = self.domain_manager.get_domain(domain)
                if domain_config:
                    domain_keywords = [kw.lower() for kw in domain_config.keywords]
            
            filtered_links = []
            base_domain = urlparse(base_url).netloc
            
            for url in spider_results:
                if not url or not isinstance(url, str):
                    continue
                
                # Normalizza URL
                normalized_url = self._normalize_url(url, base_url)
                if not normalized_url:
                    continue
                
                # Verifica che sia dello stesso dominio
                url_domain = urlparse(normalized_url).netloc
                if url_domain != base_domain:
                    continue
                
                # Verifica rilevanza per il dominio
                if self._is_relevant_for_domain(normalized_url, domain_keywords):
                    if normalized_url not in self.discovered_urls:
                        filtered_links.append(normalized_url)
                        self.discovered_urls.add(normalized_url)
            
            logger.debug(f"Filtrati {len(filtered_links)} link rilevanti da {len(spider_results)} totali")
            return filtered_links
            
        except Exception as e:
            logger.error(f"Errore filtro spider results: {e}")
            return []
    
    async def _discover_with_sitemap(self, base_url: str, site_name: str, domain: str) -> List[str]:
        """Fallback con sitemap discovery"""
        try:
            loop = asyncio.get_event_loop()
            
            # Esegui sitemap search in executor
            sitemap_urls = await loop.run_in_executor(
                None,
                self._run_sitemap_search,
                base_url
            )
            
            if not sitemap_urls:
                return []
            
            # Filtra per rilevanza dominio
            domain_keywords = []
            if domain:
                domain_config = self.domain_manager.get_domain(domain)
                if domain_config:
                    domain_keywords = [kw.lower() for kw in domain_config.keywords]
            
            filtered_links = []
            for url in sitemap_urls[:self.spider_max_pages]:  # Limita come spider
                if self._is_relevant_for_domain(url, domain_keywords):
                    if url not in self.discovered_urls:
                        filtered_links.append(url)
                        self.discovered_urls.add(url)
            
            return filtered_links
            
        except Exception as e:
            logger.error(f"Errore sitemap discovery per {base_url}: {e}")
            return []
    
    def _run_sitemap_search(self, base_url: str) -> List[str]:
        """Esegue sitemap search in modo sincrono"""
        try:
            sitemap_urls = sitemap_search(base_url)
            return list(sitemap_urls) if sitemap_urls else []
        except Exception as e:
            logger.error(f"Errore sitemap search: {e}")
            return []
    
    async def _discover_with_beautifulsoup(self, base_url: str, site_name: str, domain: str) -> List[str]:
        """Ultimo fallback con BeautifulSoup per estrazione link basilare"""
        try:
            if not BeautifulSoup:
                return []
            
            # Scarica pagina principale
            loop = asyncio.get_event_loop()
            html = await loop.run_in_executor(None, fetch_url, base_url)
            
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Trova tutti i link
            all_links = []
            for a_tag in soup.find_all('a', href=True):
                href = a_tag.get('href')
                if href:
                    normalized = self._normalize_url(href, base_url)
                    if normalized:
                        all_links.append(normalized)
            
            # Filtra per rilevanza dominio
            domain_keywords = []
            if domain:
                domain_config = self.domain_manager.get_domain(domain)
                if domain_config:
                    domain_keywords = [kw.lower() for kw in domain_config.keywords]
            
            filtered_links = []
            for url in all_links[:self.spider_max_pages]:  # Limita
                if self._is_relevant_for_domain(url, domain_keywords):
                    if url not in self.discovered_urls:
                        filtered_links.append(url)
                        self.discovered_urls.add(url)
            
            return filtered_links
            
        except Exception as e:
            logger.error(f"Errore BeautifulSoup fallback per {base_url}: {e}")
            return []
    
    async def _extract_articles_from_categories(self, base_url: str, site_name: str, domain: str) -> List[str]:
        """Estrae link articoli dalle pagine categoria conosciute"""
        try:
            category_pages = [
                f"{base_url}/l-angolo-di-calcio2000",
                f"{base_url}/l-intervista",
                f"{base_url}/la-legge-del-gol",
                f"{base_url}/serie-a",
                f"{base_url}/calciomercato"
            ]
            
            article_links = []
            loop = asyncio.get_event_loop()
            
            for category_url in category_pages:
                try:
                    logger.debug(f"Estrazione articoli da categoria: {category_url}")
                    
                    # Scarica pagina categoria
                    html = await loop.run_in_executor(None, fetch_url, category_url)
                    if not html:
                        continue
                    
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Estrai link articoli usando diversi selettori
                    selectors = [
                        'a[href*="/l-angolo-di-calcio2000/"][href*="-2"]',  # Link angolo calcio con ID
                        'a[href*="/l-intervista/"][href*="-2"]',           # Link interviste con ID  
                        'a[href*="/la-legge-del-gol/"][href*="-2"]',       # Link legge del gol con ID
                        'a[href*="/serie-a/"][href*="-2"]',                # Link serie A con ID
                        'a[href*="/calciomercato/"][href*="-2"]',          # Link calciomercato con ID
                        'a.titolo-notizia',                                # Classe titolo notizia
                        'h2 a', 'h3 a',                                   # Link in titoli
                        '.lista-notizie a',                                # Link in lista notizie  
                        '.notizia a'                                       # Link generici notizie
                    ]
                    
                    for selector in selectors:
                        links = soup.select(selector)
                        for link in links:
                            href = link.get('href')
                            if href:
                                normalized = self._normalize_url(href, base_url)
                                if normalized and self._is_article_url(normalized):
                                    article_links.append(normalized)
                    
                    # Limite per categoria
                    if len(article_links) >= self.spider_max_pages // 2:
                        break
                        
                except Exception as e:
                    logger.debug(f"Errore estrazione da {category_url}: {e}")
                    continue
            
            # Rimuovi duplicati e filtra per rilevanza dominio
            unique_links = list(dict.fromkeys(article_links))  # Mantiene ordine
            
            domain_keywords = []
            if domain:
                domain_config = self.domain_manager.get_domain(domain)
                if domain_config:
                    domain_keywords = [kw.lower() for kw in domain_config.keywords]
            
            filtered_links = []
            for url in unique_links[:self.spider_max_pages]:
                if self._is_relevant_for_domain(url, domain_keywords):
                    if url not in self.discovered_urls:
                        filtered_links.append(url)
                        self.discovered_urls.add(url)
            
            return filtered_links
            
        except Exception as e:
            logger.error(f"Errore estrazione articoli da categorie: {e}")
            return []
    
    def _is_article_url(self, url: str) -> bool:
        """Determina se URL sembra essere un articolo specifico"""
        url_lower = url.lower()
        
        # Patter positivi per articoli
        article_patterns = [
            r'-\d{7}$',           # URL che finiscono con -7cifre (ID articolo)
            r'-\d{6,8}$',         # URL che finiscono con -6-8cifre  
            r'/\d{4}/\d{2}/',     # URL con pattern data /2024/07/
            r'/articolo/',         # URL contenenti /articolo/
            r'/notizie/',          # URL contenenti /notizie/
        ]
        
        # Pattern negativi per escludere pagine categoria/indice  
        negative_patterns = [
            r'/$',                # URL che finiscono con /
            r'/page/',           # Paginazione
            r'/category/',       # Categorie
            r'/tag/',            # Tag
            r'/archivio/',       # Archivi
        ]
        
        # Controlla pattern negativi
        import re
        for pattern in negative_patterns:
            if re.search(pattern, url_lower):
                return False
        
        # Controlla pattern positivi
        for pattern in article_patterns:
            if re.search(pattern, url_lower):
                return True
        
        # Se URL ha struttura profonda (molti /) probabile articolo
        path_parts = url.split('/')[3:]  # Rimuovi schema e dominio
        if len(path_parts) >= 2 and len(path_parts[-1]) > 10:
            return True
            
        return False

    def _normalize_url(self, url: str, base_url: str) -> Optional[str]:
        """Normalizza URL relativo in assoluto"""
        if not url:
            return None
        
        try:
            # Rimuovi anchors
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
    
    def _is_relevant_for_domain(self, url: str, domain_keywords: List[str]) -> bool:
        """Determina se URL è rilevante per il dominio"""
        url_lower = url.lower()
        
        # Filtri negativi
        negative_patterns = [
            '/tag/', '/tags/', '/category/', '/author/', '/search/', '/page/',
            '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mp3',
            '/fotogallery/', '/gallery/', '/video/', '/live/', '/diretta/',
            '/privacy', '/cookie', '/login', '/register', '/contact',
            'facebook.com', 'twitter.com', 'instagram.com'
        ]
        
        if any(pattern in url_lower for pattern in negative_patterns):
            return False
        
        # Filtri positivi
        positive_score = 0
        
        # Pattern URL positivi
        article_patterns = ['/news/', '/notizie/', '/articolo/', '/article/', '/sport/', '/calcio/']
        if any(pattern in url_lower for pattern in article_patterns):
            positive_score += 3
        
        # Keywords del dominio
        keyword_matches = sum(1 for kw in domain_keywords if kw in url_lower)
        positive_score += keyword_matches * 2
        
        # URL strutturato (probabile articolo)
        if len(url.split('/')) >= 5:
            positive_score += 1
        
        # Contiene numeri (date, ID)
        if any(char.isdigit() for char in url):
            positive_score += 1
        
        # Decide in base al punteggio
        return positive_score >= 2
    
    def get_discovery_stats(self) -> Dict[str, int]:
        """Statistiche discovery sessione corrente"""
        return {
            'total_discovered': len(self.discovered_urls),
            'spider_max_depth': self.spider_max_depth,
            'spider_max_pages': self.spider_max_pages
        }