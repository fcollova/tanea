#!/usr/bin/env python3
"""
Modulo separato per caricare news nel database Weaviate tramite Trafilatura
Si integra con il sistema esistente mantenendo coerenza con domini e configurazioni
"""

import argparse
import asyncio
import sys
import os
from typing import List, Dict, Optional, Any
from datetime import datetime

# Aggiungi src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.news_db_manager_v2 import NewsVectorDBV2
from core.news_source_trafilatura_v2 import TrafilaturaSourceV2
from core.domain_manager import DomainManager
from core.storage.database_manager import DatabaseManager
from core.storage.vector_collections import VectorCollections
from core.config import get_config, get_news_config
from core.log import get_scripts_logger

# Setup logging
logger = get_scripts_logger(__name__)

class NewsLoader:
    """Loader per news tramite Trafilatura con integrazione database Weaviate"""
    
    def __init__(self):
        self.config = get_config()
        self.news_config = get_news_config()
        self.domain_manager = DomainManager()
        
        # Componenti principali
        self.news_db = None
        self.trafilatura_source = None
        self.db_manager = None
        
        logger.info("NewsLoader inizializzato")
    
    async def initialize(self):
        """Inizializza componenti"""
        self.news_db = NewsVectorDBV2()
        self.trafilatura_source = TrafilaturaSourceV2()
        self.db_manager = DatabaseManager()
        
        await self.db_manager.connect()
        logger.info("Componenti NewsLoader inizializzati")
    
    async def cleanup(self):
        """Cleanup risorse"""
        if self.db_manager:
            await self.db_manager.disconnect()
        if self.news_db:
            await self.news_db.disconnect()
        logger.info("NewsLoader disconnesso")
    
    async def load_domain_news(self, domain: str, max_results: int = 50,
                              time_range: str = "1d", force_update: bool = False) -> Dict[str, Any]:
        """
        Carica news per un dominio specifico
        
        Args:
            domain: Nome dominio (deve essere in domains.yaml)
            max_results: Numero massimo risultati per query
            time_range: Range temporale (1d, 1w, 1m)
            force_update: Forza aggiornamento anche se recente
        """
        logger.info(f"Caricamento news dominio: {domain}")
        
        # Valida dominio
        if not self.domain_manager.validate_domain(domain):
            raise ValueError(f"Dominio non configurato: {domain}")
        
        if not self.domain_manager.is_domain_active(domain):
            logger.warning(f"Dominio inattivo: {domain}")
            return {'error': f"Dominio {domain} non attivo"}
        
        if not self.news_db:
            await self.initialize()
        
        # Ottieni configurazione dominio
        domain_config = self.domain_manager.get_domain(domain)
        keywords = domain_config.keywords if domain_config else [domain]
        
        logger.info(f"Keywords per {domain}: {keywords}")
        
        results = {
            'domain': domain,
            'domain_name': domain_config.name if domain_config else domain,
            'keywords_used': keywords,
            'max_results': max_results,
            'time_range': time_range,
            'start_time': datetime.now()
        }
        
        try:
            # Usa news_db_manager_v2 per aggiornamento dominio
            update_result = await self.news_db.update_domain(
                domain,
                max_results=max_results,
                force_update=force_update
            )
            
            results.update(update_result)
            results['success'] = True
            
            logger.info(f"Dominio {domain} aggiornato: {update_result.get('crawl_stats', {})}")
            
        except Exception as e:
            logger.error(f"Errore caricamento dominio {domain}: {e}")
            results['error'] = str(e)
            results['success'] = False
        
        results['end_time'] = datetime.now()
        results['duration'] = (results['end_time'] - results['start_time']).total_seconds()
        
        return results
    
    async def load_multiple_domains(self, domains: List[str], max_results: int = 50,
                                   time_range: str = "1d") -> Dict[str, Any]:
        """
        Carica news per multipli domini
        
        Args:
            domains: Lista domini da aggiornare
            max_results: Numero massimo risultati per dominio
            time_range: Range temporale
        """
        logger.info(f"Caricamento multipli domini: {domains}")
        
        if not self.news_db:
            await self.initialize()
        
        results = {
            'domains_processed': [],
            'domains_failed': [],
            'total_articles': 0,
            'total_errors': 0,
            'start_time': datetime.now(),
            'details': {}
        }
        
        for domain in domains:
            try:
                domain_result = await self.load_domain_news(
                    domain, max_results, time_range
                )
                
                if domain_result.get('success'):
                    results['domains_processed'].append(domain)
                    crawl_stats = domain_result.get('crawl_stats', {})
                    results['total_articles'] += crawl_stats.get('articles_extracted', 0)
                else:
                    results['domains_failed'].append(domain)
                    results['total_errors'] += 1
                
                results['details'][domain] = domain_result
                
            except Exception as e:
                logger.error(f"Errore dominio {domain}: {e}")
                results['domains_failed'].append(domain)
                results['total_errors'] += 1
                results['details'][domain] = {'error': str(e)}
        
        results['end_time'] = datetime.now()
        results['duration'] = (results['end_time'] - results['start_time']).total_seconds()
        
        logger.info(f"Caricamento completato: {len(results['domains_processed'])} domini, "
                   f"{results['total_articles']} articoli")
        
        return results
    
    async def search_existing_news(self, domain: str, keywords: List[str],
                                  max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Cerca news esistenti nel database
        
        Args:
            domain: Dominio di ricerca
            keywords: Keywords di ricerca
            max_results: Numero massimo risultati
        """
        logger.info(f"Ricerca news esistenti - Dominio: {domain}, Keywords: {keywords}")
        
        if not self.news_db:
            await self.initialize()
        
        try:
            # Usa il metodo di ricerca del news_db_manager_v2
            articles = await self.news_db.search_news(
                domain=domain,
                keywords=keywords,
                max_results=max_results
            )
            
            logger.info(f"Trovati {len(articles)} articoli per {domain}")
            return articles
            
        except Exception as e:
            logger.error(f"Errore ricerca: {e}")
            return []
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Ottieni statistiche database"""
        logger.info("Recupero statistiche database")
        
        if not self.db_manager:
            await self.initialize()
        
        try:
            stats = await self.db_manager.get_system_stats()
            return stats
            
        except Exception as e:
            logger.error(f"Errore statistiche: {e}")
            return {'error': str(e)}
    
    async def cleanup_old_articles(self, days_old: int = 30) -> Dict[str, Any]:
        """
        Pulizia articoli vecchi
        
        Args:
            days_old: Giorni di vecchiaia per la pulizia
        """
        logger.info(f"Pulizia articoli più vecchi di {days_old} giorni")
        
        if not self.db_manager:
            await self.initialize()
        
        try:
            # Pulizia PostgreSQL
            pg_result = await self.db_manager.link_database.cleanup_obsolete_links(days_old)
            
            # Pulizia Weaviate
            weaviate_result = self.db_manager.vector_collections.cleanup_old_articles(days_old)
            
            result = {
                'days_old': days_old,
                'postgresql_cleaned': pg_result,
                'weaviate_cleaned': weaviate_result,
                'success': True
            }
            
            logger.info(f"Pulizia completata: PostgreSQL={pg_result}, Weaviate={weaviate_result}")
            return result
            
        except Exception as e:
            logger.error(f"Errore pulizia: {e}")
            return {'error': str(e), 'success': False}
    
    def show_domains_configuration(self):
        """Mostra configurazione domini da domains.yaml"""
        print("\n📂 Configurazione Domini (domains.yaml)")
        print("=" * 60)
        
        all_domains = self.domain_manager.get_domain_list(active_only=False)
        active_domains = self.domain_manager.get_domain_list(active_only=True)
        
        print(f"Domini totali: {len(all_domains)} | Domini attivi: {len(active_domains)}")
        
        for domain_id in all_domains:
            domain_config = self.domain_manager.get_domain(domain_id)
            status = "🟢 ATTIVO" if domain_id in active_domains else "🔴 INATTIVO"
            
            print(f"\n• {domain_id} - {status}")
            if domain_config:
                print(f"  Nome: {domain_config.name}")
                print(f"  Keywords: {domain_config.keywords}")
                priority = getattr(domain_config, 'priority', 'N/A')
                print(f"  Priorità: {priority}")
                
                # Max results per ambiente
                environment = getattr(self.config, 'environment', 'dev')
                max_results = self.domain_manager.get_max_results(domain_id, environment)
                print(f"  Max results ({environment}): {max_results}")
    
    def show_news_configuration(self):
        """Mostra configurazione news"""
        print("\n📰 Configurazione News")
        print("=" * 40)
        
        print(f"Lingua default: {self.news_config.get('default_language', 'N/A')}")
        print(f"Time range default: {self.news_config.get('default_time_range', 'N/A')}")
        print(f"Max results default: {self.news_config.get('default_max_results', 'N/A')}")
        
        # Configurazione Trafilatura
        if hasattr(self, 'trafilatura_source') and self.trafilatura_source:
            print(f"\n🕷️ Trafilatura Source:")
            print(f"  Disponibile: {self.trafilatura_source.is_available()}")
            print(f"  Priorità: {self.trafilatura_source.priority}")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='News Loader - Caricamento news tramite Trafilatura nel DB Weaviate',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi di utilizzo:
  python news_loader.py --config                          # Mostra configurazione
  python news_loader.py --stats                           # Statistiche database
  python news_loader.py --domain calcio                   # Carica dominio calcio
  python news_loader.py --domain calcio --max-results 30  # Limita risultati
  python news_loader.py --domains calcio tecnologia       # Multipli domini
  python news_loader.py --search calcio "Serie A" "Inter" # Cerca news esistenti
  python news_loader.py --cleanup 7                       # Pulisci articoli >7 giorni
        """
    )
    
    # Operazioni principali
    operation_group = parser.add_mutually_exclusive_group(required=True)
    operation_group.add_argument(
        '--config', action='store_true',
        help='Mostra configurazione domini e news'
    )
    operation_group.add_argument(
        '--stats', action='store_true',
        help='Mostra statistiche database'
    )
    operation_group.add_argument(
        '--domain', metavar='DOMAIN',
        help='Carica news per dominio specifico'
    )
    operation_group.add_argument(
        '--domains', nargs='+', metavar='DOMAIN',
        help='Carica news per multipli domini'
    )
    operation_group.add_argument(
        '--search', nargs='+', metavar='KEYWORD',
        help='Cerca news esistenti (primo arg = dominio, resto = keywords)'
    )
    operation_group.add_argument(
        '--cleanup', type=int, metavar='DAYS',
        help='Pulisci articoli più vecchi di N giorni'
    )
    
    # Parametri caricamento
    parser.add_argument(
        '--max-results', type=int, default=50, metavar='N',
        help='Numero massimo risultati per dominio (default: 50)'
    )
    parser.add_argument(
        '--time-range', choices=['1d', '1w', '1m'], default='1d',
        help='Range temporale news (default: 1d)'
    )
    parser.add_argument(
        '--force', action='store_true',
        help='Forza aggiornamento anche se recente'
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
    
    print("📰 News Loader - Trafilatura → Weaviate")
    print("=" * 60)
    
    loader = NewsLoader()
    
    try:
        if args.config:
            loader.show_domains_configuration()
            loader.show_news_configuration()
            
        elif args.stats:
            print("\n📊 Statistiche Database...")
            stats = await loader.get_database_stats()
            
            if 'error' in stats:
                print(f"❌ Errore: {stats['error']}")
            else:
                print(f"\n📈 Statistiche Sistema:")
                pg_stats = stats.get('postgresql', {})
                weaviate_stats = stats.get('weaviate', {})
                
                print(f"PostgreSQL:")
                print(f"  • Link nuovi: {pg_stats.get('new', 0)}")
                print(f"  • Link crawlati: {pg_stats.get('crawled', 0)}")
                print(f"  • Articoli estratti: {pg_stats.get('articles_extracted', 0)}")
                
                print(f"Weaviate:")
                print(f"  • Articoli totali: {weaviate_stats.get('total_articles', 0)}")
                print(f"  • Collezione: {weaviate_stats.get('collection_name', 'N/A')}")
                
        elif args.domain:
            print(f"\n📄 Caricamento dominio: {args.domain}")
            result = await loader.load_domain_news(
                args.domain,
                max_results=args.max_results,
                time_range=args.time_range,
                force_update=args.force
            )
            
            if result.get('success'):
                crawl_stats = result.get('crawl_stats', {})
                print(f"\n✅ Caricamento completato:")
                print(f"  • Durata: {result.get('duration', 0):.1f}s")
                print(f"  • Siti processati: {crawl_stats.get('sites_processed', 0)}")
                print(f"  • Link scoperti: {crawl_stats.get('links_discovered', 0)}")
                print(f"  • Articoli estratti: {crawl_stats.get('articles_extracted', 0)}")
            else:
                print(f"❌ Errore: {result.get('error', 'Errore sconosciuto')}")
                
        elif args.domains:
            print(f"\n📄 Caricamento domini: {args.domains}")
            result = await loader.load_multiple_domains(
                args.domains,
                max_results=args.max_results,
                time_range=args.time_range
            )
            
            print(f"\n📊 Risultati:")
            print(f"  • Durata: {result.get('duration', 0):.1f}s")
            print(f"  • Domini processati: {len(result['domains_processed'])}")
            print(f"  • Domini falliti: {len(result['domains_failed'])}")
            print(f"  • Articoli totali: {result['total_articles']}")
            
            if args.verbose and result.get('details'):
                print(f"\n📋 Dettaglio per dominio:")
                for domain, details in result['details'].items():
                    if 'error' in details:
                        print(f"  ❌ {domain}: {details['error']}")
                    else:
                        crawl_stats = details.get('crawl_stats', {})
                        print(f"  ✅ {domain}: {crawl_stats.get('articles_extracted', 0)} articoli")
                        
        elif args.search:
            if len(args.search) < 2:
                print("❌ Ricerca richiede almeno dominio + keyword")
                return
            
            domain = args.search[0]
            keywords = args.search[1:]
            
            print(f"\n🔍 Ricerca nel dominio '{domain}' con keywords: {keywords}")
            articles = await loader.search_existing_news(domain, keywords, args.max_results)
            
            print(f"\n📋 Risultati ({len(articles)}):")
            for i, article in enumerate(articles[:10]):  # Mostra max 10
                title = article.get('title', 'N/A')[:60]
                source = article.get('source', 'N/A')
                print(f"  {i+1:2}. {title}... [{source}]")
                
        elif args.cleanup is not None:
            print(f"\n🧹 Pulizia articoli più vecchi di {args.cleanup} giorni...")
            result = await loader.cleanup_old_articles(args.cleanup)
            
            if result.get('success'):
                print(f"✅ Pulizia completata:")
                print(f"  • PostgreSQL: {result['postgresql_cleaned']} record")
                print(f"  • Weaviate: {result['weaviate_cleaned']} articoli")
            else:
                print(f"❌ Errore pulizia: {result.get('error', 'Errore sconosciuto')}")
            
    except KeyboardInterrupt:
        print("\n⚠️  Operazione interrotta")
    except Exception as e:
        logger.error(f"Errore esecuzione: {e}")
        print(f"\n❌ Errore: {e}")
    finally:
        await loader.cleanup()

if __name__ == "__main__":
    asyncio.run(main())