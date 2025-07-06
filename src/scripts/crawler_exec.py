#!/usr/bin/env python3
"""
Modulo separato per eseguire il crawler Trafilatura
Gestisce discovery e crawling dei link configurati in web_scraping.yaml
"""

import argparse
import asyncio
import sys
import os
from typing import List, Optional
from datetime import datetime

# Aggiungi src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.crawler.trafilatura_crawler import TrafilaturaCrawler
from core.crawler.trafilatura_link_discoverer import TrafilaturaLinkDiscoverer
from core.crawler.content_extractor import ContentExtractor
from core.storage.database_manager import DatabaseManager
from core.domain_manager import DomainManager
from core.config import get_config, get_web_crawling_config
from core.log import get_scripts_logger

# Setup logging
logger = get_scripts_logger(__name__)

class CrawlerExecutor:
    """Executor per operazioni di crawling con logica domini attivi"""
    
    def __init__(self):
        self.config = get_config()
        self.crawling_config = get_web_crawling_config()
        self.domain_manager = DomainManager()
        self.crawler = None
        
        logger.info("CrawlerExecutor inizializzato con configurazione unificata (config.* + web_crawling.yaml)")
    
    async def initialize(self):
        """Inizializza il crawler"""
        self.crawler = TrafilaturaCrawler()
        # Inizializza manualmente i componenti del crawler
        await self.crawler.__aenter__()
        logger.info("Crawler inizializzato")
    
    async def cleanup(self):
        """Cleanup risorse"""
        if self.crawler:
            await self.crawler.__aexit__(None, None, None)
            logger.info("Crawler disconnesso")
    
    def get_active_domains_from_crawling_config(self) -> List[str]:
        """Ottieni domini attivi usando solo core domain management"""
        active_domains = []
        crawling_sites = self.crawling_config.get('crawling_sites', {})
        
        for domain_key in crawling_sites.keys():
            # Verifica solo che dominio sia attivo in domains.yaml tramite core modules
            if (self.domain_manager.domain_exists(domain_key) and 
                self.domain_manager.is_domain_active(domain_key)):
                active_domains.append(domain_key)
                logger.debug(f"Dominio attivo per crawling: {domain_key}")
            else:
                logger.debug(f"Dominio inattivo in domains.yaml: {domain_key}")
        
        return active_domains
    
    def get_active_sites_for_domain(self, domain: str) -> List[str]:
        """Ottieni siti attivi per un dominio specifico"""
        crawling_sites = self.crawling_config.get('crawling_sites', {})
        domain_config = crawling_sites.get(domain, {})
        sites_config = domain_config.get('sites', {})
        
        active_sites = []
        for site_key, site_config in sites_config.items():
            if site_config.get('active', False):
                active_sites.append(site_key)
        
        return active_sites
    
    async def discover_links(self, sites: Optional[List[str]] = None, 
                           domains: Optional[List[str]] = None) -> dict:
        """
        Discovery dei link da web_crawling.yaml con logica domini attivi
        
        Args:
            sites: Lista siti specifici da crawlare
            domains: Lista domini specifici da filtrare
        """
        logger.info(f"Inizio discovery link - Siti: {sites}, Domini: {domains}")
        
        if not self.crawler:
            await self.initialize()
        
        results = {
            'total_sites_processed': 0,
            'total_links_discovered': 0,
            'domains_processed': [],
            'sites_results': {},
            'errors': []
        }
        
        # Determina domini target
        if domains:
            # Valida domini specificati
            target_domains = []
            for domain in domains:
                if domain in self.get_active_domains_from_crawling_config():
                    target_domains.append(domain)
                else:
                    logger.warning(f"Dominio non disponibile per crawling: {domain}")
        else:
            # Usa tutti i domini attivi
            target_domains = self.get_active_domains_from_crawling_config()
        
        if not target_domains:
            logger.error("Nessun dominio attivo disponibile per crawling")
            return results
        
        logger.info(f"Domini target per crawling: {target_domains}")
        
        # Discovery per ogni dominio attivo
        for domain in target_domains:
            try:
                logger.info(f"Processing domain: {domain}")
                
                # Ottieni siti attivi per questo dominio
                domain_sites = self.get_active_sites_for_domain(domain)
                
                # Filtra per siti specifici se richiesto
                if sites:
                    domain_sites = [s for s in domain_sites if s in sites]
                
                if not domain_sites:
                    logger.warning(f"Nessun sito attivo per dominio {domain}")
                    continue
                
                logger.info(f"Siti attivi per {domain}: {domain_sites}")
                
                domain_links = 0
                # Discovery per ogni sito del dominio
                for site_key in domain_sites:
                    try:
                        site_result = await self._discover_site_links(domain, site_key)
                        
                        results['sites_results'][f"{domain}_{site_key}"] = site_result
                        results['total_sites_processed'] += 1
                        domain_links += site_result.get('links_discovered', 0)
                        
                        logger.info(f"Sito {site_key}: {site_result.get('links_discovered', 0)} link scoperti")
                        
                    except Exception as e:
                        error_msg = f"Errore discovery sito {site_key} in dominio {domain}: {e}"
                        logger.error(error_msg)
                        results['errors'].append(error_msg)
                
                results['total_links_discovered'] += domain_links
                results['domains_processed'].append(domain)
                logger.info(f"Dominio {domain} completato: {domain_links} link totali")
                
            except Exception as e:
                error_msg = f"Errore processing dominio {domain}: {e}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
        
        logger.info(f"Discovery completata: {results['total_links_discovered']} link da {len(results['domains_processed'])} domini")
        return results
    
    async def _discover_site_links(self, domain: str, site_key: str) -> dict:
        """Discovery link per un sito specifico utilizzando web_crawling.yaml"""
        crawling_sites = self.crawling_config.get('crawling_sites', {})
        domain_config = crawling_sites.get(domain, {})
        site_config = domain_config.get('sites', {}).get(site_key, {})
        
        if not site_config.get('active', False):
            return {'links_discovered': 0, 'error': 'Site not active'}
        
        # Ottieni discovery pages per il sito
        discovery_pages = site_config.get('discovery_pages', {})
        active_pages = {k: v for k, v in discovery_pages.items() if v.get('active', False)}
        
        total_links = 0
        page_results = {}
        
        for page_key, page_config in active_pages.items():
            try:
                # Simula discovery (qui dovrebbe chiamare il vero crawler)
                page_url = page_config.get('url', '')
                max_links = page_config.get('max_links', 10)
                
                # TODO: Chiamare il vero link discoverer
                # Per ora ritorna un mock
                page_links = min(max_links, 5)  # Mock
                
                page_results[page_key] = {
                    'url': page_url,
                    'links_found': page_links,
                    'max_links': max_links
                }
                
                total_links += page_links
                logger.debug(f"Page {page_key}: {page_links} link scoperti")
                
            except Exception as e:
                logger.error(f"Errore discovery page {page_key}: {e}")
                page_results[page_key] = {'error': str(e)}
        
        return {
            'site': site_key,
            'domain': domain,
            'links_discovered': total_links,
            'pages_processed': len(active_pages),
            'page_details': page_results
        }
    
    async def crawl_links(self, sites: Optional[List[str]] = None,
                         domains: Optional[List[str]] = None,
                         max_links: int = 50) -> dict:
        """
        Crawling completo: discovery + extraction + storage
        
        Args:
            sites: Lista siti specifici
            domains: Lista domini specifici  
            max_links: Limite massimo link per sito
        """
        logger.info(f"Inizio crawling completo - Siti: {sites}, Domini: {domains}, Max: {max_links}")
        
        if not self.crawler:
            await self.initialize()
        
        results = {
            'start_time': datetime.now(),
            'sites_processed': 0,
            'links_discovered': 0,
            'links_crawled': 0,
            'articles_extracted': 0,
            'errors': 0,
            'sites_details': {}
        }
        
        # Valida domini se specificati
        target_domains = None
        if domains:
            target_domains = []
            for domain in domains:
                if self.domain_manager.domain_exists(domain) and self.domain_manager.is_domain_active(domain):
                    target_domains.append(domain)
                else:
                    logger.warning(f"Dominio invalido o inattivo: {domain}")
            
            if not target_domains:
                logger.error("Nessun dominio valido per il crawling")
                return results
        
        # Esegui crawling
        if target_domains:
            # Crawling per domini specifici
            for domain in target_domains:
                try:
                    domain_stats = await self.crawler.crawl_domain(domain, max_links_per_site=max_links)
                    
                    results['sites_processed'] += domain_stats.get('sites_processed', 0)
                    results['links_discovered'] += domain_stats.get('links_discovered', 0)
                    results['links_crawled'] += domain_stats.get('links_crawled', 0)
                    results['articles_extracted'] += domain_stats.get('articles_extracted', 0)
                    results['errors'] += domain_stats.get('errors', 0)
                    
                    results['sites_details'][f"domain_{domain}"] = domain_stats
                    
                    logger.info(f"Dominio {domain}: {domain_stats.get('articles_extracted', 0)} articoli estratti")
                    
                except Exception as e:
                    logger.error(f"Errore crawling dominio {domain}: {e}")
                    results['errors'] += 1
        
        elif sites:
            # Crawling per siti specifici
            for site in sites:
                try:
                    site_stats = await self.crawler.crawl_single_site(site, max_links=max_links)
                    
                    results['sites_processed'] += 1
                    results['links_discovered'] += site_stats.get('links_discovered', 0)
                    results['links_crawled'] += site_stats.get('links_crawled', 0)
                    results['articles_extracted'] += site_stats.get('articles_extracted', 0)
                    
                    results['sites_details'][site] = site_stats
                    
                    logger.info(f"Sito {site}: {site_stats.get('articles_extracted', 0)} articoli estratti")
                    
                except Exception as e:
                    logger.error(f"Errore crawling sito {site}: {e}")
                    results['errors'] += 1
        
        else:
            # Crawling completo tutti i siti
            try:
                all_stats = await self.crawler.crawl_all_sites(max_links_per_site=max_links)
                results.update(all_stats)
                
            except Exception as e:
                logger.error(f"Errore crawling completo: {e}")
                results['errors'] += 1
        
        results['end_time'] = datetime.now()
        results['duration'] = (results['end_time'] - results['start_time']).total_seconds()
        
        logger.info(f"Crawling completato in {results['duration']:.1f}s: {results['articles_extracted']} articoli")
        return results
    
    def show_configuration(self):
        """Mostra configurazione corrente da config.* + web_crawling.yaml + domains.yaml"""
        print("\n📋 Configurazione Crawler (config.* + web_crawling.yaml + domains.yaml)")
        print("=" * 75)
        
        # Domini configurati nel sistema
        all_domains = self.domain_manager.get_domain_list(active_only=False)
        active_domains_system = self.domain_manager.get_domain_list(active_only=True)
        
        # Domini configurati per crawling
        crawling_domains = self.get_active_domains_from_crawling_config()
        
        print(f"\n📂 Domini Sistema ({len(all_domains)} totali, {len(active_domains_system)} attivi, {len(crawling_domains)} crawling):")
        
        for domain in all_domains:
            # Status nel sistema
            system_active = domain in active_domains_system
            crawling_active = domain in crawling_domains
            
            if system_active and crawling_active:
                status = "🟢 ATTIVO CRAWLING"
            elif system_active:
                status = "🟡 ATTIVO SISTEMA"
            else:
                status = "🔴 INATTIVO"
            
            domain_config = self.domain_manager.get_domain(domain)
            keywords = domain_config.keywords[:3] if domain_config else []
            print(f"  • {domain:12} - {status} - Keywords: {keywords}")
        
        # Configurazione crawling per domini
        crawling_sites = self.crawling_config.get('crawling_sites', {})
        print(f"\n🌐 Configurazione Crawling ({len(crawling_sites)} domini):")
        
        for domain_key, domain_config in crawling_sites.items():
            # Status del dominio viene solo da domains.yaml tramite core modules
            domain_active_in_system = (self.domain_manager.domain_exists(domain_key) and 
                                     self.domain_manager.is_domain_active(domain_key))
            priority = domain_config.get('priority', 'N/A')
            max_articles = domain_config.get('max_articles_per_domain', 'N/A')
            
            status = "🟢" if domain_active_in_system else "🔴"
            print(f"\n  {status} {domain_key} (Priorità: {priority}, Max articoli: {max_articles})")
            
            # Siti per questo dominio
            sites = domain_config.get('sites', {})
            for site_key, site_config in sites.items():
                site_active = site_config.get('active', False)
                site_priority = site_config.get('priority', 'N/A')
                site_status = "🟢" if site_active else "🔴"
                
                discovery_pages = site_config.get('discovery_pages', {})
                active_pages = sum(1 for p in discovery_pages.values() if p.get('active', False))
                
                print(f"    {site_status} {site_key:15} - Priorità: {site_priority}, Pages: {active_pages}/{len(discovery_pages)}")
        
        # Configurazione da files config.*
        print(f"\n⚙️  Configurazione Base (config.*):")
        print(f"  • Rate limit delay: {self.crawling_config.get('rate_limit_delay', 'N/A')}s")
        print(f"  • Max links per site: {self.crawling_config.get('max_links_per_site', 'N/A')}")
        print(f"  • Max concurrent requests: {self.crawling_config.get('max_concurrent_requests', 'N/A')}")
        print(f"  • Min quality score: {self.crawling_config.get('min_quality_score', 'N/A')}")
        print(f"  • Respect robots.txt: {self.crawling_config.get('respect_robots_txt', 'N/A')}")
        print(f"  • Extract metadata: {self.crawling_config.get('extract_metadata', 'N/A')}")
        
        # Configurazione generale YAML
        general_config = self.crawling_config.get('general', {})
        if general_config:
            print(f"\n⚙️  Configurazione YAML:")
            print(f"  • Timeout: {general_config.get('timeout', 'N/A')}s")
            print(f"  • Max retries: {general_config.get('max_retries', 'N/A')}")
            print(f"  • Max content length: {general_config.get('max_content_length', 'N/A')}")
        
        # Mapping domini
        domain_mapping = self.crawling_config.get('domain_mapping', {})
        if domain_mapping:
            print(f"\n🗺️  Mapping Domini → Siti:")
            for domain, mapping in domain_mapping.items():
                # Status del dominio solo da domains.yaml
                active = (self.domain_manager.domain_exists(domain) and 
                         self.domain_manager.is_domain_active(domain))
                sites = mapping.get('sites', [])
                keywords = mapping.get('crawling_keywords', [])
                status = "🟢" if active else "🔴"
                print(f"  {status} {domain}: {len(sites)} siti - {sites}")
                if keywords:
                    print(f"     Keywords crawling: {keywords[:3]}..." if len(keywords) > 3 else f"     Keywords crawling: {keywords}")
    
    def show_available_sites(self):
        """Mostra siti disponibili da web_crawling.yaml"""
        crawling_sites = self.crawling_config.get('crawling_sites', {})
        
        total_sites = 0
        active_sites = 0
        
        print(f"\n🌐 Siti Crawling Disponibili:")
        
        for domain_key, domain_config in crawling_sites.items():
            # Status del dominio solo da domains.yaml
            domain_active = (self.domain_manager.domain_exists(domain_key) and 
                           self.domain_manager.is_domain_active(domain_key))
            domain_status = "🟢" if domain_active else "🔴"
            
            print(f"\n{domain_status} Dominio: {domain_key}")
            
            sites = domain_config.get('sites', {})
            for site_key, site_config in sites.items():
                site_active = site_config.get('active', False)
                site_name = site_config.get('name', site_key)
                base_url = site_config.get('base_url', 'N/A')
                priority = site_config.get('priority', 'N/A')
                
                site_status = "🟢" if site_active else "🔴"
                
                # Conta discovery pages attive
                discovery_pages = site_config.get('discovery_pages', {})
                active_pages = sum(1 for p in discovery_pages.values() if p.get('active', False))
                
                print(f"  {site_status} {site_key:15} - {site_name}")
                print(f"     URL: {base_url}")
                print(f"     Priorità: {priority}, Pages attive: {active_pages}/{len(discovery_pages)}")
                
                # Mostra dettagli discovery pages se verbose
                if discovery_pages:
                    print(f"     Discovery Pages:")
                    for page_key, page_config in discovery_pages.items():
                        page_active = page_config.get('active', False)
                        page_url = page_config.get('url', 'N/A')[:50] + "..."
                        max_links = page_config.get('max_links', 0)
                        page_status = "🟢" if page_active else "🔴"
                        print(f"       {page_status} {page_key}: {page_url} (max: {max_links})")
                
                total_sites += 1
                if site_active:
                    active_sites += 1
        
        print(f"\n📊 Riepilogo: {active_sites}/{total_sites} siti attivi per crawling")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Crawler Executor - Modulo autonomo per crawling Trafilatura',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi di utilizzo:
  python crawler_exec.py --config                         # Mostra configurazione completa
  python crawler_exec.py --sites                          # Mostra siti disponibili per crawling
  python crawler_exec.py --discover                       # Discovery tutti i domini attivi
  python crawler_exec.py --discover --domain calcio       # Discovery solo dominio calcio
  python crawler_exec.py --discover --site gazzetta       # Discovery solo sito gazzetta
  python crawler_exec.py --crawl                          # Crawling completo domini attivi
  python crawler_exec.py --crawl --domain calcio          # Crawling dominio calcio
  python crawler_exec.py --crawl --site gazzetta          # Crawling sito specifico
  python crawler_exec.py --crawl --max-links 20           # Limite 20 link per sito
  
Configurazione:
  Il crawler usa config.dev.conf + web_crawling.yaml + domains.yaml
  Domini attivi devono essere abilitati in TUTTI i file di configurazione
        """
    )
    
    # Operazioni principali
    operation_group = parser.add_mutually_exclusive_group(required=True)
    operation_group.add_argument(
        '--config', action='store_true',
        help='Mostra configurazione domini e siti'
    )
    operation_group.add_argument(
        '--sites', action='store_true', 
        help='Mostra siti disponibili'
    )
    operation_group.add_argument(
        '--discover', action='store_true',
        help='Discovery link (senza extraction)'
    )
    operation_group.add_argument(
        '--crawl', action='store_true',
        help='Crawling completo (discovery + extraction + storage)'
    )
    
    # Filtri
    parser.add_argument(
        '--domain', nargs='+', metavar='DOMAIN',
        help='Filtra per domini specifici (es: calcio tecnologia)'
    )
    parser.add_argument(
        '--site', nargs='+', metavar='SITE', 
        help='Filtra per siti specifici (es: gazzetta ansa)'
    )
    
    # Parametri crawling
    parser.add_argument(
        '--max-links', type=int, default=50, metavar='N',
        help='Numero massimo link per sito (default: 50)'
    )
    
    # Opzioni output
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Output dettagliato'
    )
    parser.add_argument(
        '--quiet', '-q', action='store_true', 
        help='Output minimo'
    )
    
    return parser.parse_args()

async def main():
    """Funzione principale"""
    args = parse_arguments()
    
    # Setup logging level
    if args.verbose:
        logger.setLevel('DEBUG')
    elif args.quiet:
        logger.setLevel('ERROR')
    
    print("🕷️ Crawler Executor - Trafilatura")
    print("=" * 60)
    
    executor = CrawlerExecutor()
    
    try:
        if args.config:
            executor.show_configuration()
            
        elif args.sites:
            executor.show_available_sites()
            
        elif args.discover:
            print(f"\n🔍 Discovery link...")
            if args.domain:
                print(f"Filtro domini: {args.domain}")
            if args.site:
                print(f"Filtro siti: {args.site}")
            
            results = await executor.discover_links(
                sites=args.site,
                domains=args.domain
            )
            
            print(f"\n📊 Risultati Discovery:")
            print(f"  • Siti processati: {results['total_sites_processed']}")
            print(f"  • Link scoperti: {results['total_links_discovered']}")
            
            if results['errors']:
                print(f"  • Errori: {len(results['errors'])}")
                for error in results['errors']:
                    print(f"    - {error}")
            
            if args.verbose and results['sites_results']:
                print(f"\n📋 Dettaglio per sito:")
                for site, result in results['sites_results'].items():
                    print(f"  • {site}: {result.get('links_discovered', 0)} link")
                    
        elif args.crawl:
            print(f"\n🕷️ Crawling completo...")
            if args.domain:
                print(f"Filtro domini: {args.domain}")
            if args.site:
                print(f"Filtro siti: {args.site}")
            print(f"Max links per sito: {args.max_links}")
            
            results = await executor.crawl_links(
                sites=args.site,
                domains=args.domain,
                max_links=args.max_links
            )
            
            print(f"\n📊 Risultati Crawling:")
            print(f"  • Durata: {results.get('duration', 0):.1f}s")
            print(f"  • Siti processati: {results['sites_processed']}")
            print(f"  • Link scoperti: {results['links_discovered']}")
            print(f"  • Link crawlati: {results['links_crawled']}")
            print(f"  • Articoli estratti: {results['articles_extracted']}")
            print(f"  • Errori: {results['errors']}")
            
            if args.verbose and results.get('sites_details'):
                print(f"\n📋 Dettaglio per sito:")
                for site, details in results['sites_details'].items():
                    print(f"  • {site}:")
                    print(f"    - Link: {details.get('links_discovered', 0)}")
                    print(f"    - Articoli: {details.get('articles_extracted', 0)}")
            
    except KeyboardInterrupt:
        print("\n⚠️  Operazione interrotta")
    except Exception as e:
        logger.error(f"Errore esecuzione: {e}")
        print(f"\n❌ Errore: {e}")
    finally:
        await executor.cleanup()

if __name__ == "__main__":
    asyncio.run(main())