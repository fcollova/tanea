# ============================================================================
# example_usage.py
"""
Esempio di utilizzo del News Vector DB
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Aggiungi il percorso del modulo src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.news_db_manager import NewsVectorDB
from core.news_sources import NewsQuery
from core.config import get_config, get_weaviate_config, get_search_config, get_news_config, setup_logging
from core.domain_manager import DomainManager

# Configura logging dal sistema di configurazione
setup_logging()
from core.log import get_scripts_logger
logger = get_scripts_logger(__name__)

class NewsQASystem:
    """Sistema di Q&A basato sulle notizie"""
    
    def __init__(self):
        self.news_db = NewsVectorDB()
        self.config = get_config()
        
        # Inizializza domain manager
        self.domain_manager = DomainManager()
        
        # Crea configurazioni domini dal domain manager
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
            # Usa Weaviate v4 API per le statistiche
            collection = self.news_db.weaviate_client.collections.get(self.news_db.vector_db_manager.index_name)
            
            # Recupera tutti i documenti per analizzare i domini
            response = collection.query.fetch_objects(
                return_properties=["domain"],
                limit=10000
            )
            
            stats = {}
            for obj in response.objects:
                domain = obj.properties.get("domain", "Unknown")
                stats[domain] = stats.get(domain, 0) + 1
            
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