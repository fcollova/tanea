#!/usr/bin/env python3
# ============================================================================
# load_news.py
"""
Modulo per caricare notizie nel News Vector DB
Evita duplicazioni e gestisce il caricamento incrementale
"""

import logging
from datetime import datetime
from news_db_manager import NewsVectorDB
from news_sources import NewsQuery
from config import get_config, get_news_config, setup_logging

# Configura logging dal sistema di configurazione
setup_logging()
logger = logging.getLogger(__name__)

class NewsLoader:
    """Caricatore di notizie con controllo duplicati"""
    
    def __init__(self):
        self.news_db = NewsVectorDB()
        self.config = get_config()
        
        # Crea configurazioni domini dai file config
        self.news_domains = self._create_news_domains()
    
    def _create_news_domains(self):
        """Crea configurazioni domini dai file config"""
        domains_config = self.config.get_section('domains')
        news_config = get_news_config()
        
        domains = []
        
        # Crea domini dalle configurazioni
        if 'calcio_keywords' in domains_config:
            calcio_config = NewsQuery(
                domain="calcio",
                keywords=self.config.get('domains', 'calcio_keywords', [], list),
                max_results=self.config.get('domains', 'calcio_max_results', 25, int),
                time_range=news_config['default_time_range'],
                language=news_config['default_language']
            )
            domains.append(calcio_config)
        
        return domains
    
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
            
            # Cerca nuove notizie
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

def main():
    """Funzione principale per caricare notizie"""
    print("📰 News Loader - Caricamento notizie incrementale")
    print("=" * 60)
    
    # Usa il context manager per gestire le connessioni automaticamente
    with NewsLoader() as loader:
        try:
            # Mostra statistiche iniziali
            print("\n📊 Statistiche database (prima del caricamento):")
            stats_before = loader.get_database_stats()
            if "error" not in stats_before:
                print(f"  • Totale articoli: {stats_before['total_articles']}")
                for domain, count in stats_before.get('by_domain', {}).items():
                    print(f"  • {domain}: {count} articoli")
            else:
                print(f"  • Errore: {stats_before['error']}")
            
            print("\n🔄 Avvio caricamento notizie...")
            
            # Carica notizie evitando duplicati
            result = loader.load_news_incremental()
            
            print(f"\n✅ Caricamento completato!")
            print(f"  • Nuovi articoli: {result['new_articles']}")
            print(f"  • Duplicati saltati: {result['skipped_duplicates']}")
            print(f"  • Totale processati: {result['total_processed']}")
            
            # Mostra statistiche finali
            print("\n📊 Statistiche database (dopo il caricamento):")
            stats_after = loader.get_database_stats()
            if "error" not in stats_after:
                print(f"  • Totale articoli: {stats_after['total_articles']}")
                for domain, count in stats_after.get('by_domain', {}).items():
                    print(f"  • {domain}: {count} articoli")
            
            print(f"\n🎯 Il database è ora pronto per le ricerche!")
            
        except Exception as e:
            logger.error(f"Errore durante il caricamento: {e}")
            print(f"\n❌ Errore: {e}")
    
    # Le connessioni vengono chiuse automaticamente qui

if __name__ == "__main__":
    main()