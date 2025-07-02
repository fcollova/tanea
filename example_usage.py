# ============================================================================
# example_usage.py
"""
Esempio di utilizzo del News Vector DB
"""

import asyncio
import logging
from datetime import datetime
from news_db_manager import NewsVectorDB
from news_sources import NewsQuery
from config import get_config, get_weaviate_config, get_search_config, get_news_config, setup_logging

# Configura logging dal sistema di configurazione
setup_logging()
logger = logging.getLogger(__name__)

class NewsQASystem:
    """Sistema di Q&A basato sulle notizie"""
    
    def __init__(self):
        self.news_db = NewsVectorDB()
        self.config = get_config()
        
        # Crea configurazioni domini dai file config
        self.news_domains = self._create_news_domains()
    
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
    
    def _create_news_domains(self):
        """Crea configurazioni domini dai file config"""
        domains_config = self.config.get_section('domains')
        news_config = get_news_config()
        
        domains = []
        
        # Solo calcio per ora, seguendo il pattern della configurazione originale
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
    
    def initial_setup(self):
        """Setup iniziale del database"""
        logger.info("Esecuzione setup iniziale...")
        
        # Carica notizie calcio (metodo semplificato)
        total_articles = self.news_db.update_football_news()
        logger.info(f"Setup completato. Caricati {total_articles} articoli.")
        
        return total_articles
    
    def ask_question(self, question: str) -> dict:
        """Pone una domanda e ottiene una risposta con contesto"""
        logger.info(f"Processando domanda: {question}")
        
        # Ottieni il contesto rilevante
        context = self.news_db.get_context_for_question(
            question, 
            max_context_length=4000  # Default value
        )
        
        # Ottieni i documenti rilevanti per metadati aggiuntivi
        relevant_docs = self.news_db.search_relevant_context(
            question, 
            k=5  # Default value
        )
        
        # Estrai le fonti
        sources = []
        for doc in relevant_docs:
            source_info = {
                "title": doc.metadata.get("title", "N/A"),
                "url": doc.metadata.get("url", "N/A"),
                "source": doc.metadata.get("source", "N/A"),
                "published_date": doc.metadata.get("published_date", "N/A"),
                "domain": doc.metadata.get("domain", "N/A")
            }
            if source_info not in sources:
                sources.append(source_info)
        
        return {
            "question": question,
            "context": context,
            "sources": sources,
            "timestamp": datetime.now().isoformat(),
            "num_sources": len(sources)
        }
    
    def get_domain_statistics(self) -> dict:
        """Ottieni statistiche sui domini nel database"""
        try:
            # Query per ottenere statistiche per dominio
            # Usa il nome index dalla configurazione
            weaviate_config = get_weaviate_config()
            index_name = weaviate_config['index_name']
            
            query = f"""
            {{
              Aggregate {{
                {index_name}(groupBy: ["domain"]) {{
                  groupedBy {{
                    value
                  }}
                  meta {{
                    count
                  }}
                }}
              }}
            }}
            """
            
            result = self.news_db.weaviate_client.graphql_raw_query(query)
            stats = {}
            
            if result and "data" in result:
                groups = result["data"]["Aggregate"][index_name]
                for group in groups:
                    domain = group["groupedBy"]["value"]
                    count = group["meta"]["count"]
                    stats[domain] = count
            
            return stats
            
        except Exception as e:
            logger.error(f"Errore nel recupero delle statistiche: {e}")
            return {}
    
    def start_automated_updates(self):
        """Avvia gli aggiornamenti automatici"""
        logger.info("Avvio aggiornamenti automatici...")
        
        # Programma gli aggiornamenti
        self.news_db.schedule_daily_updates()
        
        # Esegui lo scheduler
        self.news_db.run_scheduler()

# Funzioni di utilità
def demo_questions():
    """Lista di domande di esempio per test"""
    return [
        "Chi ha vinto l'ultima partita di Serie A?",
        "Quali sono i risultati dell'ultima giornata di campionato?",
        "Come sta andando la Juventus in Serie A?",
        "Ci sono novità sul calciomercato?",
        "Chi è in testa alla classifica di Serie A?",
        "Quali sono le ultime notizie sull'Inter?",
        "Come sta giocando il Milan questa stagione?",
        "Ci sono infortuni importanti in Serie A?"
    ]

def main():
    """Funzione principale di esempio"""
    print("🚀 News Vector DB System - Sistema Q&A")
    print("=" * 50)
    print("💡 Per caricare notizie, usa: python load_news.py")
    print("🔍 Questo script esegue solo ricerche e test Q&A")
    print("=" * 50)
    
    # Usa il context manager per gestire le connessioni automaticamente
    with NewsQASystem() as qa_system:
        # Setup iniziale rimosso - usa load_news.py per caricare notizie
        # qa_system.initial_setup()
        
        # Mostra statistiche
        stats = qa_system.get_domain_statistics()
        if stats:
            print("\n📊 Statistiche database:")
            for domain, count in stats.items():
                print(f"  • {domain}: {count} articoli")
        
        print("\n" + "=" * 50)
        print("🔍 Test con domande di esempio:")
        print("=" * 50)
        
        # Test con alcune domande di esempio
        demo_qs = demo_questions()
        
        for i, question in enumerate(demo_qs[:3], 1):  # Solo le prime 3 per demo
            print(f"\n{i}. {question}")
            print("-" * 60)
            
            result = qa_system.ask_question(question)
            
            print(f"📰 Fonti trovate: {result['num_sources']}")
            
            if result['sources']:
                print("\n🔗 Principali fonti:")
                for j, source in enumerate(result['sources'][:3], 1):
                    print(f"  {j}. {source['title']}")
                    print(f"     Fonte: {source['source']} | Data: {source['published_date']}")
            
            # Mostra un estratto del contesto
            context_preview = result['context'][:300] + "..." if len(result['context']) > 300 else result['context']
            print(f"\n📝 Contesto (anteprima):\n{context_preview}")
            print("\n" + "=" * 50)
        
        print("\n✅ Demo Q&A completata!")
        print("\n📝 Comandi utili:")
        print("  • Caricare notizie: python load_news.py")
        print("  • Test Q&A: python example_usage.py")
        print("  • Avviare sistema: ./start.sh")
    
    # Le connessioni vengono chiuse automaticamente qui

if __name__ == "__main__":
    main()