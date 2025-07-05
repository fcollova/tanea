"""
Trafilatura Crawler - Orchestratore principale
Coordina link discovery, content extraction e storage
"""

import asyncio
import yaml
import os
from typing import List, Dict, Optional, Any
from datetime import datetime

from .link_discoverer import LinkDiscoverer
from .content_extractor import ContentExtractor
from ..storage.database_manager import DatabaseManager
from ..config import get_crawler_config
from ..log import get_news_logger

logger = get_news_logger(__name__)

class TrafilaturaCrawler:
    """Crawler principale che orchestra discovery, extraction e storage"""
    
    def __init__(self, environment: str = None):
        self.environment = environment or 'dev'
        self.config = get_crawler_config()
        
        # Componenti crawler
        self.link_discoverer = None
        self.content_extractor = None
        self.db_manager = None
        
        # Carica configurazione siti
        self.sites_config = self._load_sites_config()
        
        # Stats crawling
        self.crawl_stats = {
            'sites_processed': 0,
            'links_discovered': 0,
            'links_crawled': 0,
            'articles_extracted': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
    
    def _load_sites_config(self) -> Dict[str, Any]:
        """Carica configurazione siti da web_scraping.yaml"""
        try:
            config_path = os.path.join(
                os.path.dirname(__file__), '..', '..', 'config', 'web_scraping.yaml'
            )
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info(f"Configurazione siti caricata: {len(config.get('sites', {}))} siti")
                return config
                
        except Exception as e:
            logger.error(f"Errore caricamento configurazione siti: {e}")
            return {'sites': {}}
    
    async def __aenter__(self):
        """Context manager entry - inizializza componenti"""
        # Inizializza componenti
        self.link_discoverer = LinkDiscoverer()
        self.content_extractor = ContentExtractor()
        self.db_manager = DatabaseManager(self.environment)
        
        # Inizializza connessioni
        await self.link_discoverer.__aenter__()
        await self.content_extractor.__aenter__()
        await self.db_manager.initialize()
        
        logger.info("TrafilaturaCrawler inizializzato")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - chiudi connessioni"""
        if self.link_discoverer:
            await self.link_discoverer.__aexit__(exc_type, exc_val, exc_tb)
        
        if self.content_extractor:
            await self.content_extractor.__aexit__(exc_type, exc_val, exc_tb)
        
        if self.db_manager:
            await self.db_manager.close()
        
        logger.info("TrafilaturaCrawler disconnesso")
    
    # ========================================================================
    # CRAWLING PRINCIPALE
    # ========================================================================
    
    async def crawl_all_sites(self, site_names: List[str] = None, 
                            domain_filter: str = None) -> Dict[str, Any]:
        """
        Crawla tutti i siti configurati
        
        Args:
            site_names: Lista nomi siti specifici (None = tutti)
            domain_filter: Filtra solo siti per questo dominio
            
        Returns:
            dict: Statistiche crawling
        """
        self.crawl_stats['start_time'] = datetime.now()
        logger.info("Inizio crawling completo tutti i siti")
        
        sites_to_crawl = self._get_sites_to_crawl(site_names, domain_filter)
        
        for site_name, site_config in sites_to_crawl.items():
            try:
                logger.info(f"Crawling sito: {site_name}")
                await self._crawl_single_site(site_name, site_config)
                self.crawl_stats['sites_processed'] += 1
                
            except Exception as e:
                logger.error(f"Errore crawling sito {site_name}: {e}")
                self.crawl_stats['errors'] += 1
                continue
        
        self.crawl_stats['end_time'] = datetime.now()
        duration = (self.crawl_stats['end_time'] - self.crawl_stats['start_time']).total_seconds()
        
        logger.info(f"Crawling completato in {duration:.1f}s: {self.crawl_stats}")
        return self.crawl_stats
    
    async def _crawl_single_site(self, site_name: str, site_config: Dict[str, Any]):
        """Crawla un singolo sito: discovery + extraction + storage"""
        try:
            # 1. Assicura che il sito sia nel database
            site_db = await self._ensure_site_in_database(site_name, site_config)
            
            # 2. Link Discovery
            discovered_links = await self.link_discoverer.discover_site_links(site_config)
            if not discovered_links:
                logger.warning(f"Nessun link scoperto per {site_name}")
                return
            
            # 3. Salva link scoperti nel database
            added_count = await self.db_manager.link_db.add_discovered_links(
                links=discovered_links,
                site_id=site_db.id,
                parent_url=site_config['base_url']
            )
            self.crawl_stats['links_discovered'] += added_count
            
            # 4. Recupera link da crawlare (nuovi + alcuni vecchi)
            links_to_crawl = await self.db_manager.link_db.get_links_to_crawl(
                site_id=site_db.id,
                limit=self.config.get('max_articles_per_site', 20)
            )
            
            if not links_to_crawl:
                logger.info(f"Nessun link da crawlare per {site_name}")
                return
            
            # 5. Content Extraction
            await self._crawl_links_batch(links_to_crawl, site_config)
            
            logger.info(f"Sito {site_name} completato: {len(links_to_crawl)} link processati")
            
        except Exception as e:
            logger.error(f"Errore crawling sito {site_name}: {e}")
            raise
    
    async def _crawl_links_batch(self, links_to_crawl: List, site_config: Dict[str, Any]):
        """Crawla batch di link con extraction e storage"""
        try:
            # Determina dominio dal mapping
            domain = self._determine_domain_for_site(site_config)
            
            # Process link in piccoli batch per non sovraccaricare
            batch_size = min(5, self.config.get('max_concurrent', 3))
            
            for i in range(0, len(links_to_crawl), batch_size):
                batch = links_to_crawl[i:i + batch_size]
                await self._process_links_batch(batch, domain)
                
                # Piccola pausa tra batch
                await asyncio.sleep(1.0)
            
        except Exception as e:
            logger.error(f"Errore processing batch link: {e}")
            raise
    
    async def _process_links_batch(self, batch_links: List, domain: str):
        """Processa un piccolo batch di link"""
        tasks = []
        
        for link_record in batch_links:
            task = self._process_single_link(link_record, domain)
            tasks.append(task)
        
        # Esegui estrazione concorrente limitata
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Errore processing link {batch_links[i].url}: {result}")
                self.crawl_stats['errors'] += 1
    
    async def _process_single_link(self, link_record, domain: str):
        """Processa un singolo link: extraction + storage"""
        try:
            # 1. Marca link come in crawling
            await self.db_manager.link_db.mark_link_crawling(link_record.id)
            
            # 2. Estrai contenuto
            article_data = await self.content_extractor.extract_article(
                url=link_record.url,
                domain=domain
            )
            
            if not article_data:
                await self.db_manager.link_db.mark_link_crawled(
                    link_record.id,
                    success=False,
                    error_message="Estrazione contenuto fallita"
                )
                return
            
            # 3. Salva articolo (PostgreSQL + Weaviate)
            success = await self.db_manager.process_crawled_article(
                link_id=link_record.id,
                article_data=article_data
            )
            
            if success:
                self.crawl_stats['articles_extracted'] += 1
                logger.debug(f"Articolo salvato: {article_data['title'][:50]}...")
            
            self.crawl_stats['links_crawled'] += 1
            
        except Exception as e:
            logger.error(f"Errore processing link {link_record.url}: {e}")
            try:
                await self.db_manager.link_db.mark_link_crawled(
                    link_record.id,
                    success=False,
                    error_message=str(e)
                )
            except:
                pass
            raise
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def _get_sites_to_crawl(self, site_names: List[str] = None, 
                           domain_filter: str = None) -> Dict[str, Dict]:
        """Determina quali siti crawlare"""
        all_sites = self.sites_config.get('sites', {})
        
        # Filtra per nomi specifici
        if site_names:
            sites = {name: config for name, config in all_sites.items() 
                    if name in site_names}
        else:
            sites = all_sites.copy()
        
        # Filtra per dominio se specificato
        if domain_filter:
            domain_mapping = self.sites_config.get('domain_mapping', {})
            domain_sites = domain_mapping.get(domain_filter.lower(), [])
            sites = {name: config for name, config in sites.items() 
                    if name in domain_sites}
        
        # Filtra solo siti attivi
        active_sites = {name: config for name, config in sites.items() 
                       if config.get('active', True)}
        
        logger.info(f"Siti da crawlare: {list(active_sites.keys())}")
        return active_sites
    
    async def _ensure_site_in_database(self, site_name: str, site_config: Dict[str, Any]):
        """Assicura che il sito sia presente nel database PostgreSQL"""
        existing_site = await self.db_manager.link_db.get_site_by_name(site_name)
        
        if not existing_site:
            site = await self.db_manager.link_db.create_site(
                name=site_name,
                base_url=site_config['base_url'],
                config=site_config
            )
            logger.info(f"Sito {site_name} aggiunto al database")
            return site
        else:
            # Aggiorna configurazione se necessario
            await self.db_manager.link_db.update_site_config(
                existing_site.id, 
                site_config
            )
            return existing_site
    
    def _determine_domain_for_site(self, site_config: Dict[str, Any]) -> str:
        """Determina dominio appropriato per il sito"""
        # Cerca nel mapping dominio
        domain_mapping = self.sites_config.get('domain_mapping', {})
        site_name = site_config.get('name', '').lower()
        
        for domain, sites in domain_mapping.items():
            if any(site_name in s.lower() for s in sites):
                return domain
        
        # Fallback basato sul nome sito
        site_name_lower = site_name.lower()
        if any(term in site_name_lower for term in ['gazzetta', 'sport', 'calcio']):
            return 'calcio'
        elif any(term in site_name_lower for term in ['tech', 'tecnologia']):
            return 'tecnologia'
        elif any(term in site_name_lower for term in ['sole', 'economia', 'finanza']):
            return 'finanza'
        else:
            return 'general'
    
    # ========================================================================
    # MODALITÀ SPECIFICHE
    # ========================================================================
    
    async def crawl_domain(self, domain: str, max_articles: int = 50) -> Dict[str, Any]:
        """Crawla solo siti di un dominio specifico"""
        logger.info(f"Crawling dominio: {domain}")
        return await self.crawl_all_sites(domain_filter=domain)
    
    async def crawl_site(self, site_name: str) -> Dict[str, Any]:
        """Crawla un singolo sito specifico"""
        logger.info(f"Crawling sito singolo: {site_name}")
        return await self.crawl_all_sites(site_names=[site_name])
    
    async def refresh_recent_content(self, hours_old: int = 24) -> Dict[str, Any]:
        """Re-crawla contenuti recenti per aggiornamenti"""
        logger.info(f"Refresh contenuti ultimi {hours_old} ore")
        
        # Implementazione semplificata - in futuro si potrebbe 
        # recuperare link crawlati di recente e ri-processarli
        return await self.crawl_all_sites()
    
    def get_crawl_statistics(self) -> Dict[str, Any]:
        """Statistiche complete crawling"""
        stats = self.crawl_stats.copy()
        
        # Aggiungi statistiche componenti
        if self.link_discoverer:
            stats['discovery'] = self.link_discoverer.get_discovery_stats()
        
        if self.content_extractor:
            stats['extraction'] = self.content_extractor.get_extraction_stats()
        
        return stats