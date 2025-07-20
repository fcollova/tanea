"""
Trafilatura Crawler - Orchestratore principale
Coordina link discovery, content extraction e storage
"""

import asyncio
import yaml
import os
from typing import List, Dict, Optional, Any
from datetime import datetime

from .trafilatura_link_discoverer import TrafilaturaLinkDiscoverer
from .content_extractor import ContentExtractor
from .rate_limiter import AdvancedRateLimiter
from core.storage.database_manager import DatabaseManager
from core.config import get_crawler_config
from core.domain_manager import DomainManager
from core.log import get_news_logger

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
        self.rate_limiter = AdvancedRateLimiter()
        self.domain_manager = DomainManager()
        
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
        """Carica configurazione siti da web_crawling.yaml"""
        try:
            config_path = os.path.join(
                os.path.dirname(__file__), '..', 'config', 'web_crawling.yaml'
            )
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                # Estrai siti dalla struttura crawling_sites
                crawling_sites = config.get('crawling_sites', {})
                all_sites = {}
                
                # Converti struttura dominio->siti in siti flat
                for domain, domain_config in crawling_sites.items():
                    sites = domain_config.get('sites', {})
                    for site_key, site_config in sites.items():
                        # Aggiungi informazioni sul dominio al sito
                        site_config_copy = site_config.copy()
                        site_config_copy['domain'] = domain
                        all_sites[site_key] = site_config_copy
                
                # Aggiungi mapping domini per compatibilità
                config['sites'] = all_sites
                logger.info(f"Configurazione siti caricata: {len(all_sites)} siti da {len(crawling_sites)} domini")
                
                # Validation: almeno un sito deve essere configurato
                if not all_sites:
                    raise ValueError("Nessun sito configurato in web_crawling.yaml - verificare la configurazione")
                
                return config
                
        except FileNotFoundError as e:
            logger.error(f"❌ File configurazione non trovato: {config_path}")
            logger.error(f"   Assicurati che web_crawling.yaml sia presente in /src/config/")
            raise FileNotFoundError(f"File configurazione mancante: {config_path}") from e
        except yaml.YAMLError as e:
            logger.error(f"❌ Errore parsing YAML in {config_path}: {e}")
            raise ValueError(f"File YAML malformato: {config_path}") from e
        except Exception as e:
            logger.error(f"❌ Errore caricamento configurazione siti: {e}")
            logger.error(f"   Path tentato: {config_path}")
            raise RuntimeError(f"Errore configurazione crawler: {e}") from e
    
    async def __aenter__(self):
        """Context manager entry - inizializza componenti"""
        # Inizializza componenti
        self.link_discoverer = TrafilaturaLinkDiscoverer()
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
                            domain_filter: str = None, max_links_per_site: int = None) -> Dict[str, Any]:
        """
        Crawla tutti i siti configurati
        
        Args:
            site_names: Lista nomi siti specifici (None = tutti)
            domain_filter: Filtra solo siti per questo dominio
            max_links_per_site: Limite massimo link per sito (sovrascrive config)
            
        Returns:
            dict: Statistiche crawling
        """
        self.crawl_stats['start_time'] = datetime.now()
        logger.info("Inizio crawling completo tutti i siti")
        
        # Aggiorna temporaneamente la configurazione se max_links_per_site è specificato
        original_config = None
        if max_links_per_site is not None:
            original_config = self.config.get('max_articles_per_site', 20)
            self.config['max_articles_per_site'] = max_links_per_site
        
        try:
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
        
        finally:
            # Ripristina configurazione originale
            if original_config is not None:
                self.config['max_articles_per_site'] = original_config
    
    async def _crawl_single_site(self, site_name: str, site_config: Dict[str, Any]):
        """Crawla un singolo sito: discovery + extraction + storage"""
        try:
            # 0. Verifica dominio PRIMA di iniziare qualsiasi operazione
            try:
                domain = self._determine_domain_for_site(site_config)
                logger.info(f"Sito {site_name} assegnato al dominio: {domain}")
            except ValueError as domain_error:
                logger.error(f"❌ SKIP sito {site_name}: {domain_error}")
                self.crawl_stats['errors'] += 1
                return  # Skip questo sito invece di crashare tutto il crawling
            
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
            max_links = self.config.get('max_articles_per_site', 20)
            links_to_crawl = await self.db_manager.link_db.get_links_to_crawl(
                site_id=site_db.id,
                limit=max_links
            )
            
            logger.info(f"Sito {site_name}: richiesti max {max_links} link, ottenuti {len(links_to_crawl)} link da crawlare")
            
            # Log dei link da crawlare
            for i, link in enumerate(links_to_crawl, 1):
                logger.info(f"  ToCrawl[{i}]: {link.url}")
                logger.debug(f"    Status: {link.status}, ID: {link.id}")
            
            if not links_to_crawl:
                logger.warning(f"Nessun link da crawlare per {site_name} - verifica stato link nel database")
                return
            
            # 5. Content Extraction (usa il dominio già verificato)
            await self._crawl_links_batch(links_to_crawl, domain)
            
            logger.info(f"Sito {site_name} completato: {len(links_to_crawl)} link processati")
            
        except Exception as e:
            logger.error(f"Errore crawling sito {site_name}: {e}")
            raise
    
    async def _crawl_links_batch(self, links_to_crawl: List, domain: str):
        """Crawla batch di link con extraction e storage"""
        try:
            logger.info(f"Inizio processing {len(links_to_crawl)} link per dominio: {domain}")
            
            # Process link in piccoli batch per non sovraccaricare
            batch_size = min(5, self.config.get('max_concurrent', 3))
            logger.info(f"Batch size configurato: {batch_size}")
            
            for i in range(0, len(links_to_crawl), batch_size):
                batch = links_to_crawl[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}: {len(batch)} link")
                await self._process_links_batch(batch, domain)
                
                # Piccola pausa tra batch
                await asyncio.sleep(1.0)
            
        except Exception as e:
            logger.error(f"Errore processing batch link: {e}")
            raise
    
    async def _process_links_batch(self, batch_links: List, domain: str):
        """Processa un piccolo batch di link"""
        logger.info(f"_process_links_batch chiamato con {len(batch_links)} link")
        tasks = []
        
        for link_record in batch_links:
            logger.info(f"Creando task per link: {link_record.url}")
            task = self._process_single_link(link_record, domain)
            tasks.append(task)
        
        logger.info(f"Eseguendo {len(tasks)} task concorrenti")
        # Esegui estrazione concorrente limitata
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info(f"Task completati, processing {len(results)} risultati")
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Errore processing link {batch_links[i].url}: {result}")
                self.crawl_stats['errors'] += 1
            else:
                logger.info(f"Link {batch_links[i].url} processato con successo")
    
    async def _process_single_link(self, link_record, domain: str):
        """Processa un singolo link: extraction + storage"""
        try:
            logger.info(f"Inizio processing link: {link_record.url}")
            
            # 1. Marca link come in crawling
            await self.db_manager.link_db.mark_link_crawling(link_record.id)
            logger.info(f"Link marcato come in crawling: {link_record.id}")
            
            # 2. Ottieni keywords del dominio per filtraggio
            domain_keywords = []
            if domain and self.domain_manager:
                domain_config = self.domain_manager.get_domain(domain)
                if domain_config:
                    domain_keywords = domain_config.keywords
                    logger.debug(f"Keywords dominio {domain}: {len(domain_keywords)} keywords")
                else:
                    logger.warning(f"Configurazione dominio {domain} non trovata")
            
            # 3. Estrai contenuto con filtraggio keywords
            logger.info(f"Inizio estrazione contenuto per: {link_record.url}")
            article_data = await self.content_extractor.extract_article(
                url=link_record.url,
                domain=domain,
                keywords=domain_keywords
            )
            logger.info(f"Estrazione completata, risultato: {bool(article_data)}")
            
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
                logger.info(f"Articolo salvato: {article_data['title'][:50]}...")
            
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
            # Filtra siti per dominio usando il campo 'domain' aggiunto durante il load
            sites = {name: config for name, config in sites.items() 
                    if config.get('domain') == domain_filter.lower()}
        
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
        # METODO 1: Usa il campo 'domain' dalla nuova struttura web_crawling.yaml
        if 'domain' in site_config:
            domain = site_config['domain']
            logger.debug(f"Dominio dal config: {domain}")
            
            # Verifica che il dominio sia configurato e attivo in domains.yaml
            if not self.domain_manager.domain_exists(domain, active_only=True):
                site_name = site_config.get('name', 'Unknown')
                if self.domain_manager.domain_exists(domain, active_only=False):
                    logger.error(f"❌ ERRORE: Dominio '{domain}' per sito '{site_name}' esiste ma NON È ATTIVO in domains.yaml")
                else:
                    logger.error(f"❌ ERRORE: Dominio '{domain}' per sito '{site_name}' NON ESISTE in domains.yaml")
                
                logger.error(f"❌ Domini attivi disponibili: {self.domain_manager.get_domain_list(active_only=True)}")
                raise ValueError(
                    f"Dominio '{domain}' per sito '{site_name}' non valido o non attivo. "
                    f"Verifica domains.yaml e assicurati che il dominio sia attivo."
                )
            
            return domain
        
        # METODO 2: Cerca nel mapping dominio (per compatibilità)
        domain_mapping = self.sites_config.get('domain_mapping', {})
        site_name = site_config.get('name', '').lower()
        
        for domain, mapping_data in domain_mapping.items():
            sites = mapping_data.get('sites', []) if isinstance(mapping_data, dict) else []
            if any(site_name in s.lower() for s in sites):
                logger.debug(f"Dominio dal mapping: {domain}")
                # Verifica che il dominio sia attivo in domains.yaml
                if not self.domain_manager.is_domain_active(domain):
                    logger.warning(f"Dominio '{domain}' trovato nel mapping ma NON ATTIVO in domains.yaml per sito {site_config.get('name', 'Unknown')}")
                    # Continua la ricerca invece di usare dominio inattivo
                    continue
                return domain
        
        # METODO 3: Fallback basato sul nome sito (deprecato)
        site_name_lower = site_name.lower()
        if any(term in site_name_lower for term in ['gazzetta', 'sport', 'calcio', 'tuttomercato']):
            logger.warning(f"Dominio da fallback per {site_config.get('name', 'Unknown')}: calcio - AGGIORNA LA CONFIGURAZIONE!")
            return 'calcio'
        elif any(term in site_name_lower for term in ['tech', 'tecnologia']):
            logger.warning(f"Dominio da fallback per {site_config.get('name', 'Unknown')}: tecnologia - AGGIORNA LA CONFIGURAZIONE!")
            return 'tecnologia'
        elif any(term in site_name_lower for term in ['sole', 'economia', 'finanza']):
            logger.warning(f"Dominio da fallback per {site_config.get('name', 'Unknown')}: finanza - AGGIORNA LA CONFIGURAZIONE!")
            return 'finanza'
        else:
            # ERRORE: Nessun dominio configurato
            site_name = site_config.get('name', 'Unknown')
            base_url = site_config.get('base_url', 'Unknown')
            logger.error(f"❌ ERRORE CONFIGURAZIONE: Nessun dominio trovato per sito '{site_name}' ({base_url})")
            logger.error(f"❌ Soluzioni possibili:")
            logger.error(f"   1. Aggiungi campo 'domain' nella configurazione del sito in web_crawling.yaml")
            logger.error(f"   2. Aggiungi il sito nel domain_mapping in web_crawling.yaml")
            logger.error(f"   3. Verifica che il sito sia sotto il dominio corretto nella struttura YAML")
            logger.error(f"❌ Domini disponibili: {list(self.domain_manager.get_all_domains().keys())}")
            
            # Lancia eccezione invece di ritornare "general"
            raise ValueError(
                f"Dominio non configurato per sito '{site_name}' ({base_url}). "
                f"Aggiorna web_crawling.yaml per assegnare il sito a un dominio valido."
            )
    
    # ========================================================================
    # MODALITÀ SPECIFICHE
    # ========================================================================
    
    async def crawl_domain(self, domain: str, max_articles: int = 50, max_links_per_site: int = None) -> Dict[str, Any]:
        """Crawla solo siti di un dominio specifico"""
        logger.info(f"Crawling dominio: {domain}")
        # Se max_links_per_site è specificato, aggiorna temporaneamente la configurazione
        if max_links_per_site is not None:
            original_config = self.config.get('max_articles_per_site', 20)
            self.config['max_articles_per_site'] = max_links_per_site
            try:
                result = await self.crawl_all_sites(domain_filter=domain)
            finally:
                self.config['max_articles_per_site'] = original_config
            return result
        else:
            return await self.crawl_all_sites(domain_filter=domain)
    
    async def crawl_site(self, site_name: str) -> Dict[str, Any]:
        """Crawla un singolo sito specifico"""
        logger.info(f"Crawling sito singolo: {site_name}")
        return await self.crawl_all_sites(site_names=[site_name])
    
    async def crawl_single_site(self, site_name: str, max_links: int = None) -> Dict[str, Any]:
        """Alias per crawl_site con parametro max_links per compatibilità"""
        return await self.crawl_all_sites(site_names=[site_name], max_links_per_site=max_links)
    
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
        
        # Aggiungi statistiche rate limiting
        stats['rate_limiting'] = self.rate_limiter.get_domain_stats()
        
        return stats