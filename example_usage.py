# ============================================================================
# example_usage.py
"""
Esempio di utilizzo del News Vector DB
"""

import asyncio
import logging
from datetime import datetime
from news_vector_db import NewsVectorDB
from config import NEWS_DOMAINS, VECTOR_DB_CONFIG, WEAVIATE_URL, TAVILY_API_KEY, EMBEDDING_MODEL

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NewsQASystem:
    """Sistema di Q&A basato sulle notizie"""
    
    def __init__(self):
        self.news_db = NewsVectorDB(
            weaviate_url=WEAVIATE_URL,
            tavily_api_key=TAVILY_API_KEY,
            index_name=VECTOR_DB_CONFIG["index_name"],
            embedding_model=EMBEDDING_MODEL
        )
    
    def initial_setup(self):
        """Setup iniziale del database"""
        logger.info("Esecuzione setup iniziale...")
        
        # Carica notizie per tutti i domini configurati
        total_articles = self.news_db.update_daily_news(NEWS_DOMAINS)
        logger.info(f"Setup completato. Caricati {total_articles} articoli.")
        
        return total_articles
    
    def ask_question(self, question: str) -> dict:
        """Pone una domanda e ottiene una risposta con contesto"""
        logger.info(f"Processando domanda: {question}")
        
        # Ottieni il contesto rilevante
        context = self.news_db.get_context_for_question(
            question, 
            max_context_length=VECTOR_DB_CONFIG["max_context_length"]
        )
        
        # Ottieni i documenti rilevanti per metadati aggiuntivi
        relevant_docs = self.news_db.search_relevant_context(
            question, 
            k=VECTOR_DB_CONFIG["similarity_search_k"]
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
            query = """
            {
              Aggregate {
                NewsArticles_IT(groupBy: ["domain"]) {
                  groupedBy {
                    value
                  }
                  meta {
                    count
                  }
                }
              }
            }
            """
            
            result = self.news_db.weaviate_client.query.raw(query)
            stats = {}
            
            if result and "data" in result:
                groups = result["data"]["Aggregate"]["NewsArticles_IT"]
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
        self.news_db.schedule_daily_updates(
            NEWS_DOMAINS, 
            VECTOR_DB_CONFIG["update_time"]
        )
        
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
    
    # Inizializza il sistema
    qa_system = NewsQASystem()
    
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

if __name__ == "__main__":
    main()