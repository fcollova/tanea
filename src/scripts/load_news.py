#!/usr/bin/env python3
# ============================================================================
# load_news.py
"""
Modulo per caricare notizie nel News Vector DB
Evita duplicazioni e gestisce il caricamento incrementale
Supporta caricamento da fonti specifiche tramite command line
"""

import argparse
import sys
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional

# Aggiungi il percorso del modulo src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.news_db_manager import NewsVectorDB
from core.news_sources import NewsQuery, NewsSourceManager, create_default_news_manager
from core.config import get_config, get_news_config, setup_logging
from core.domain_manager import DomainManager

# Configura logging dal sistema di configurazione
setup_logging()
from core.log import get_scripts_logger
logger = get_scripts_logger(__name__)

class NewsLoader:
    """Caricatore di notizie con controllo duplicati"""
    
    def __init__(self, sources_filter: Optional[List[str]] = None):
        self.news_db = NewsVectorDB()
        self.config = get_config()
        self.sources_filter = sources_filter  # Filtra fonti specifiche
        
        # Inizializza domain manager
        self.domain_manager = DomainManager()
        
        # Crea configurazioni domini dal domain manager
        self.news_domains = self._create_news_domains()
        
        # Inizializza gestore fonti per caricamenti specifici
        self.news_manager = create_default_news_manager()
        
        # Filtra fonti se specificato
        if sources_filter:
            self._filter_sources(sources_filter)
    
    def _create_news_domains(self):
        """Crea configurazioni domini dal domain manager"""
        news_config = get_news_config()
        environment = getattr(self.config, 'environment', 'dev')
        
        domains = []
        
        # Crea configurazione per ogni dominio attivo dal domain manager
        for domain_id in self.domain_manager.get_domain_list(active_only=True):
            domain_config_obj = self.domain_manager.get_domain(domain_id)
            if domain_config_obj and domain_config_obj.active:
                domain_config = NewsQuery(
                    domain=domain_id,
                    keywords=domain_config_obj.keywords,
                    max_results=self.domain_manager.get_max_results(domain_id, environment),
                    time_range=news_config['default_time_range'],
                    language=news_config['default_language']
                )
                domains.append(domain_config)
                logger.info(f"Configurato dominio attivo: {domain_config_obj.name} ({domain_id})")
        
        return domains
    
    def _filter_sources(self, allowed_sources: List[str]):
        """Filtra il news manager per usare solo le fonti specificate"""
        available_sources = list(self.news_manager.sources.keys())
        
        for source_name in available_sources:
            if source_name not in allowed_sources:
                self.news_manager.remove_source(source_name)
                logger.info(f"Fonte {source_name} rimossa dal caricamento")
        
        remaining = self.news_manager.get_available_sources()
        logger.info(f"Fonti attive per il caricamento: {remaining}")
    
    def get_available_sources(self) -> List[str]:
        """Ottieni lista delle fonti disponibili"""
        return self.news_manager.get_available_sources()
    
    def get_source_stats(self) -> Dict[str, Dict]:
        """Ottieni statistiche delle fonti"""
        return self.news_manager.get_source_stats()
    
    def get_existing_hashes(self):
        """Recupera gli hash dei contenuti già presenti nel database"""
        try:
            # Query per ottenere tutti gli hash esistenti
            collection = self.news_db.weaviate_client.collections.get(self.news_db.vector_db_manager.index_name)
            
            # Cerca tutti i documenti e prendi solo gli hash
            response = collection.query.fetch_objects(
                return_properties=["content_hash"],
                limit=10000  # Limite alto per prendere tutti gli articoli
            )
            
            existing_hashes = set()
            for obj in response.objects:
                if obj.properties.get("content_hash"):
                    existing_hashes.add(obj.properties["content_hash"])
            
            logger.info(f"Trovati {len(existing_hashes)} articoli esistenti nel database")
            return existing_hashes
            
        except Exception as e:
            logger.error(f"Errore nel recupero degli hash esistenti: {e}")
            return set()
    
    def load_news_incremental(self, domains=None):
        """Carica notizie evitando duplicati"""
        if domains is None:
            domains = self.news_domains
        
        logger.info(f"Inizio caricamento incrementale per {len(domains)} domini")
        
        # Recupera hash esistenti
        existing_hashes = self.get_existing_hashes()
        
        total_new_articles = 0
        total_skipped = 0
        
        for domain_config in domains:
            logger.info(f"Processando dominio: {domain_config.domain}")
            
            # Cerca nuove notizie usando il gestore fonti configurato
            if hasattr(self, 'news_manager'):
                # Usa il gestore fonti filtrato
                articles = self._search_with_filtered_sources(
                    domain_config.domain,
                    domain_config.keywords,
                    domain_config.max_results,
                    domain_config.language,
                    domain_config.time_range
                )
            else:
                # Fallback al metodo originale
                articles = self.news_db.search_news(
                    domain_config.domain,
                    domain_config.keywords,
                    domain_config.max_results,
                    domain_config.language,
                    domain_config.time_range
                )
            logger.info(f"Trovati {len(articles)} articoli da {domain_config.domain}")
            
            # Filtra articoli già esistenti
            new_articles = []
            for article in articles:
                content_hash = self.news_db._generate_content_hash(article["content"])
                
                if content_hash not in existing_hashes:
                    new_articles.append(article)
                    existing_hashes.add(content_hash)  # Aggiungi per evitare duplicati in questa sessione
                else:
                    total_skipped += 1
                    logger.debug(f"Articolo già esistente saltato: {article.get('title', 'N/A')[:50]}...")
            
            # Carica solo articoli nuovi
            if new_articles:
                added = self.news_db.add_articles_to_vectordb(new_articles)
                total_new_articles += added
                logger.info(f"Aggiunti {added} nuovi articoli per {domain_config.domain}")
            else:
                logger.info(f"Nessun nuovo articolo per {domain_config.domain}")
        
        logger.info(f"Caricamento completato:")
        logger.info(f"  • Nuovi articoli aggiunti: {total_new_articles}")
        logger.info(f"  • Articoli duplicati saltati: {total_skipped}")
        
        return {
            "new_articles": total_new_articles,
            "skipped_duplicates": total_skipped,
            "total_processed": total_new_articles + total_skipped
        }
    
    def _search_with_filtered_sources(self, domain: str, keywords: List[str], 
                                    max_results: int = 10, language: str = "it", 
                                    time_range: str = "1d") -> List[Dict]:
        """Cerca notizie usando solo le fonti filtrate"""
        query = NewsQuery(
            keywords=keywords,
            domain=domain,
            max_results=max_results,
            language=language,
            time_range=time_range
        )
        
        # Usa il gestore fonti filtrato
        articles = self.news_manager.search_hybrid(query)
        
        # Converte nel formato richiesto dal resto del sistema
        search_results = []
        for article in articles:
            # Assicurati che source sia sempre valorizzato
            source_value = article.source
            if not source_value or (isinstance(source_value, str) and source_value.strip() == ""):
                source_value = "Unknown Source"
                logger.warning(f"Articolo senza fonte rilevata: {article.title[:50] if article.title else 'No title'}... - Impostata come 'Unknown Source'")
            
            result = {
                'title': article.title or '',
                'content': article.content or '',
                'url': article.url or '',
                'source': source_value,
                'published_date': article.published_date.isoformat() if article.published_date else datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                'domain': domain,
                'keywords': keywords
            }
            search_results.append(result)
        
        return search_results
    
    def get_database_stats(self):
        """Ottieni statistiche del database"""
        try:
            collection = self.news_db.weaviate_client.collections.get(self.news_db.vector_db_manager.index_name)
            
            # Conta totale
            total = collection.aggregate.over_all(total_count=True).total_count
            
            # Conta per dominio
            domain_stats = {}
            response = collection.query.fetch_objects(
                return_properties=["domain"],
                limit=10000
            )
            
            for obj in response.objects:
                domain = obj.properties.get("domain", "Unknown")
                domain_stats[domain] = domain_stats.get(domain, 0) + 1
            
            return {
                "total_articles": total,
                "by_domain": domain_stats,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Errore nel recupero delle statistiche: {e}")
            return {"error": str(e)}
    
    def cleanup_old_articles(self, days_old=30):
        """Rimuove articoli più vecchi di X giorni"""
        logger.info(f"Rimozione articoli più vecchi di {days_old} giorni...")
        try:
            self.news_db.cleanup_old_articles(days_old)
            logger.info("Pulizia completata")
        except Exception as e:
            logger.error(f"Errore durante la pulizia: {e}")
    
    def load_from_specific_sources(self, sources: List[str], domains: Optional[List[NewsQuery]] = None) -> Dict:
        """Carica notizie solo da fonti specifiche"""
        logger.info(f"Caricamento da fonti specifiche: {sources}")
        
        # Filtra il news manager
        self._filter_sources(sources)
        
        # Esegui il caricamento normale
        return self.load_news_incremental(domains)
    
    def load_rss_only(self, domains: Optional[List[NewsQuery]] = None) -> Dict:
        """Carica notizie solo da feed RSS"""
        return self.load_from_specific_sources(['rss'], domains)
    
    def load_newsapi_only(self, domains: Optional[List[NewsQuery]] = None) -> Dict:
        """Carica notizie solo da NewsAPI"""
        return self.load_from_specific_sources(['newsapi'], domains)
    
    def load_scraping_only(self, domains: Optional[List[NewsQuery]] = None) -> Dict:
        """Carica notizie solo da web scraping"""
        return self.load_from_specific_sources(['scraping'], domains)
    
    def load_tavily_only(self, domains: Optional[List[NewsQuery]] = None) -> Dict:
        """Carica notizie solo da Tavily"""
        return self.load_from_specific_sources(['tavily'], domains)
    
    def test_sources(self) -> Dict[str, Dict]:
        """Testa tutte le fonti disponibili"""
        logger.info("Test delle fonti di notizie...")
        
        test_query = NewsQuery(
            keywords=["calcio", "Serie A"],
            domain="calcio",
            max_results=3,
            language="it",
            time_range="1d"
        )
        
        results = self.news_manager.search_all_sources(test_query)
        
        test_results = {}
        for source_name, articles in results.items():
            test_results[source_name] = {
                "available": len(articles) > 0,
                "articles_found": len(articles),
                "sample_titles": [art.title for art in articles[:2]] if articles else []
            }
        
        return test_results
    
    def close(self):
        """Chiude le connessioni per evitare memory leaks"""
        if hasattr(self, 'news_db'):
            self.news_db.close()
    
    def __enter__(self):
        """Support for context manager"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup when exiting context manager"""
        self.close()

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='News Loader - Carica notizie nel Vector Database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi di utilizzo:
  python load_news.py                          # Carica da tutte le fonti
  python load_news.py --rss                    # Solo feed RSS
  python load_news.py --newsapi                # Solo NewsAPI
  python load_news.py --scraping               # Solo web scraping
  python load_news.py --tavily                 # Solo Tavily
  python load_news.py --sources rss newsapi    # RSS + NewsAPI
  python load_news.py --test                   # Test tutte le fonti
  python load_news.py --stats                  # Solo statistiche
  python load_news.py --cleanup 7              # Pulisci articoli >7 giorni
        """
    )
    
    # Opzioni per fonti specifiche
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        '--rss', action='store_true',
        help='Carica solo da feed RSS'
    )
    source_group.add_argument(
        '--newsapi', action='store_true',
        help='Carica solo da NewsAPI'
    )
    source_group.add_argument(
        '--scraping', action='store_true',
        help='Carica solo da web scraping'
    )
    source_group.add_argument(
        '--tavily', action='store_true',
        help='Carica solo da Tavily'
    )
    source_group.add_argument(
        '--sources', nargs='+', 
        choices=['rss', 'newsapi', 'scraping', 'tavily'],
        help='Carica da fonti specifiche (multiple)'
    )
    
    # Operazioni speciali
    special_group = parser.add_mutually_exclusive_group()
    special_group.add_argument(
        '--test', action='store_true',
        help='Testa tutte le fonti senza caricare'
    )
    special_group.add_argument(
        '--stats', action='store_true',
        help='Mostra solo statistiche database'
    )
    special_group.add_argument(
        '--cleanup', type=int, metavar='DAYS',
        help='Rimuovi articoli più vecchi di N giorni'
    )
    
    # Opzioni generali
    parser.add_argument(
        '--max-results', type=int, default=25,
        help='Numero massimo articoli per dominio (default: 25)'
    )
    parser.add_argument(
        '--time-range', choices=['1d', '1w', '1m'], default='1d',
        help='Range temporale notizie (default: 1d)'
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Output verbose'
    )
    parser.add_argument(
        '--quiet', '-q', action='store_true',
        help='Output minimo'
    )
    
    return parser.parse_args()

def show_database_stats(loader: NewsLoader):
    """Mostra statistiche del database"""
    print("\n📊 Statistiche Database:")
    print("-" * 40)
    
    stats = loader.get_database_stats()
    if "error" in stats:
        print(f"❌ Errore: {stats['error']}")
        return
    
    print(f"📈 Totale articoli: {stats['total_articles']}")
    print(f"📅 Ultimo aggiornamento: {stats.get('last_updated', 'N/A')}")
    
    if stats.get('by_domain'):
        print("\n🏷️  Per dominio:")
        for domain, count in sorted(stats['by_domain'].items()):
            print(f"  • {domain}: {count} articoli")

def show_source_stats(loader: NewsLoader):
    """Mostra statistiche delle fonti"""
    print("\n🔗 Stato Fonti:")
    print("-" * 40)
    
    source_stats = loader.get_source_stats()
    for name, stats in source_stats.items():
        status = "🟢" if stats['available'] else "🔴"
        print(f"{status} {name}:")
        print(f"  • Disponibile: {'Sì' if stats['available'] else 'No'}")
        print(f"  • Priorità: {stats['priority']}")
        print(f"  • Affidabilità: {stats['reliability']:.1%}")
        print(f"  • Richieste: {stats['success_count']} ✅ / {stats['error_count']} ❌")
        if stats['last_request']:
            print(f"  • Ultima richiesta: {stats['last_request']}")
        print()

def test_all_sources(loader: NewsLoader):
    """Testa tutte le fonti disponibili"""
    print("\n🧪 Test Fonti di Notizie:")
    print("-" * 40)
    
    test_results = loader.test_sources()
    
    for source_name, result in test_results.items():
        status = "🟢" if result['available'] else "🔴"
        print(f"{status} {source_name}:")
        print(f"  • Funzionante: {'Sì' if result['available'] else 'No'}")
        print(f"  • Articoli trovati: {result['articles_found']}")
        
        if result['sample_titles']:
            print("  • Esempi:")
            for title in result['sample_titles']:
                print(f"    - {title[:60]}...")
        print()

def run_loading_operation(loader: NewsLoader, args):
    """Esegue l'operazione di caricamento specificata"""
    print("\n🔄 Avvio caricamento notizie...")
    
    # Determina il metodo di caricamento
    if args.rss:
        result = loader.load_rss_only()
        method = "RSS"
    elif args.newsapi:
        result = loader.load_newsapi_only()
        method = "NewsAPI"
    elif args.scraping:
        result = loader.load_scraping_only()
        method = "Web Scraping"
    elif args.tavily:
        result = loader.load_tavily_only()
        method = "Tavily"
    elif args.sources:
        result = loader.load_from_specific_sources(args.sources)
        method = f"Fonti: {', '.join(args.sources)}"
    else:
        result = loader.load_news_incremental()
        method = "Tutte le fonti"
    
    # Mostra risultati
    print(f"\n✅ Caricamento completato ({method})!")
    print(f"  • Nuovi articoli: {result['new_articles']}")
    print(f"  • Duplicati saltati: {result['skipped_duplicates']}")
    print(f"  • Totale processati: {result['total_processed']}")
    
    return result

def main():
    """Funzione principale con supporto command line"""
    args = parse_arguments()
    
    # Configura logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    
    print("📰 News Loader - Sistema di caricamento notizie")
    print("=" * 60)
    
    # Determina fonti da usare
    sources_filter = None
    if args.sources:
        sources_filter = args.sources
    elif args.rss:
        sources_filter = ['rss']
    elif args.newsapi:
        sources_filter = ['newsapi']
    elif args.scraping:
        sources_filter = ['scraping']
    elif args.tavily:
        sources_filter = ['tavily']
    
    # Usa il context manager
    with NewsLoader(sources_filter) as loader:
        try:
            # Operazioni speciali
            if args.stats:
                show_database_stats(loader)
                show_source_stats(loader)
                return
            
            if args.test:
                show_source_stats(loader)
                test_all_sources(loader)
                return
            
            if args.cleanup is not None:
                print(f"\n🧹 Pulizia articoli più vecchi di {args.cleanup} giorni...")
                loader.cleanup_old_articles(args.cleanup)
                print("✅ Pulizia completata")
                return
            
            # Mostra statistiche iniziali (se non quiet)
            if not args.quiet:
                show_database_stats(loader)
                show_source_stats(loader)
            
            # Esegui caricamento
            result = run_loading_operation(loader, args)
            
            # Mostra statistiche finali
            if not args.quiet:
                show_database_stats(loader)
            
            print(f"\n🎯 Il database è ora pronto per le ricerche!")
            
        except KeyboardInterrupt:
            print("\n⚠️  Operazione interrotta dall'utente")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Errore durante l'operazione: {e}")
            print(f"\n❌ Errore: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()