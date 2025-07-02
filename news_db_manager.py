import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import logging
import schedule
import time

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_weaviate import WeaviateVectorStore
from langchain.schema import Document

from vector_db_manager import VectorDBManager
from news_sources import NewsQuery, NewsSourceManager, create_default_news_manager
from config import get_config, get_news_config, get_scheduler_config, setup_logging

# Configura logging dalla configurazione
setup_logging()
logger = logging.getLogger(__name__)

class NewsVectorDB:
    """
    Classe principale per gestire il Vector DB delle notizie
    """
    
    def __init__(self, environment: str = None):
        # Ottieni configurazioni
        self.config = get_config(environment)
        
        # Inizializza i componenti
        self._init_vector_db_manager()
        self._init_text_splitter()
        self._init_news_sources()
        self._init_vector_store()
        
        # Cache per evitare duplicati
        self.processed_urls = set()
    
    def close(self):
        """Chiude le connessioni per evitare memory leaks"""
        try:
            if hasattr(self, 'weaviate_client') and self.weaviate_client:
                self.weaviate_client.close()
                logger.info("Connessione Weaviate chiusa")
        except Exception as e:
            logger.error(f"Errore nella chiusura delle connessioni: {e}")
    
    def __enter__(self):
        """Support for context manager"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup when exiting context manager"""
        self.close()
        
    def _init_vector_db_manager(self):
        """Inizializza il gestore del vector database"""
        # Passa l'environment al VectorDBManager per coerenza
        environment = getattr(self.config, 'environment', None)
        self.vector_db_manager = VectorDBManager(environment)
        
        self.weaviate_client, self.embeddings = self.vector_db_manager.initialize_all()
    
    def _init_text_splitter(self):
        """Inizializza il text splitter"""
        news_config = get_news_config()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=news_config['chunk_size'],
            chunk_overlap=news_config['chunk_overlap'],
            length_function=len,
        )
    
    def _init_news_sources(self):
        """Inizializza il gestore delle fonti di notizie"""
        self.news_manager = create_default_news_manager()
        available_sources = self.news_manager.get_available_sources()
        logger.info(f"Fonti di notizie disponibili: {available_sources}")
    
    def _init_vector_store(self):
        """Inizializza il vector store"""
        self.vector_store = WeaviateVectorStore(
            client=self.weaviate_client,
            index_name=self.vector_db_manager.index_name,
            text_key="content",
            embedding=self.embeddings,
        )
        logger.info("Vector store inizializzato")
    
    
    def _generate_content_hash(self, content: str) -> str:
        """Genera un hash del contenuto per evitare duplicati"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def search_news(self, domain: str, keywords: List[str], max_results: int = 10, 
                   language: str = "it", time_range: str = "1d") -> List[Dict[str, Any]]:
        """Cerca notizie utilizzando le fonti configurate"""
        try:
            # Crea query per il news manager
            query = NewsQuery(
                keywords=keywords,
                domain=domain,
                max_results=max_results,
                language=language,
                time_range=time_range
            )
            
            logger.info(f"Ricerca notizie: {query.keywords} nel dominio {query.domain}")
            
            # Esegui la ricerca usando la migliore fonte disponibile
            articles = self.news_manager.search_best_source(query)
            
            # Converte gli articoli in formato compatibile
            search_results = []
            for article in articles:
                result = {
                    'title': article.title,
                    'content': article.content,
                    'url': article.url,
                    'score': article.score or 0.0,
                    'raw_content': article.raw_content or '',
                    'source': article.source
                }
                search_results.append(result)
            
            # Processa i risultati
            processed_results = []
            for result in search_results:
                if isinstance(result, dict):
                    processed_result = {
                        "title": result.get("title", ""),
                        "content": result.get("content", ""),
                        "url": result.get("url", ""),
                        "source": result.get("source", ""),
                        "published_date": result.get("published_date", datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")),
                        "domain": domain,
                        "keywords": keywords
                    }
                    processed_results.append(processed_result)
            
            logger.info(f"Trovati {len(processed_results)} articoli")
            return processed_results
            
        except Exception as e:
            logger.error(f"Errore nella ricerca delle notizie: {e}")
            return []
    
    def add_articles_to_vectordb(self, articles: List[Dict[str, Any]]) -> int:
        """Aggiunge articoli al vector database"""
        added_count = 0
        
        for article in articles:
            try:
                # Controlla se l'articolo è già stato processato
                content_hash = self._generate_content_hash(article["content"])
                if content_hash in self.processed_urls:
                    logger.info(f"Articolo già processato: {article['title']}")
                    continue
                
                # Dividi il contenuto in chunks
                text_chunks = self.text_splitter.split_text(article["content"])
                
                # Crea documenti per ogni chunk
                documents = []
                for i, chunk in enumerate(text_chunks):
                    metadata = {
                        "title": article["title"],
                        "url": article["url"],
                        "domain": article["domain"],
                        "published_date": article["published_date"],
                        "keywords": article["keywords"],
                        "source": article["source"],
                        "content_hash": content_hash,
                        "chunk_index": i
                    }
                    
                    doc = Document(
                        page_content=chunk,
                        metadata=metadata
                    )
                    documents.append(doc)
                
                # Aggiungi al vector store
                if documents:
                    self.vector_store.add_documents(documents)
                    self.processed_urls.add(content_hash)
                    added_count += 1
                    logger.info(f"Aggiunto articolo: {article['title']}")
                
            except Exception as e:
                logger.error(f"Errore nell'aggiunta dell'articolo {article.get('title', 'Unknown')}: {e}")
                continue
        
        logger.info(f"Aggiunti {added_count} nuovi articoli al database")
        return added_count
    
    def add_news_to_db(self, domain: str, keywords: List[str], max_results: int = 10,
                      language: str = "it", time_range: str = "1d") -> int:
        """Aggiunge notizie al vector database"""
        try:
            # Cerca notizie
            search_results = self.search_news(domain, keywords, max_results, language, time_range)
            
            # Aggiungi al database
            return self.add_articles_to_vectordb(search_results)
            
        except Exception as e:
            logger.error(f"Errore nell'aggiunta delle notizie al database: {e}")
            return 0
    
    def update_football_news(self) -> int:
        """Aggiorna le notizie di calcio Serie A"""
        logger.info("Aggiornamento notizie calcio Serie A...")
        return self.add_news_to_db(
            domain="calcio Serie A",
            keywords=["Inter", "Milan", "Juventus", "Napoli", "Roma", "Lazio", "Atalanta", "Fiorentina"],
            max_results=20,
            language="it",
            time_range="1d"
        )
    
    def search_relevant_context(self, question: str, k: int = 5) -> List[Document]:
        """Cerca il contesto più rilevante per una domanda"""
        try:
            # Usa il retriever per trovare documenti rilevanti
            retriever = self.vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": k}
            )
            
            relevant_docs = retriever.get_relevant_documents(question)
            logger.info(f"Trovati {len(relevant_docs)} documenti rilevanti per la domanda")
            
            return relevant_docs
            
        except Exception as e:
            logger.error(f"Errore nella ricerca del contesto: {e}")
            return []
    
    def get_context_for_question(self, question: str, max_context_length: int = 4000) -> str:
        """Ottiene il contesto formattato per una domanda"""
        relevant_docs = self.search_relevant_context(question)
        
        context_parts = []
        current_length = 0
        
        for doc in relevant_docs:
            # Crea una stringa formattata per il documento
            doc_context = f"""
Titolo: {doc.metadata.get('title', 'N/A')}
Fonte: {doc.metadata.get('source', 'N/A')}
Data: {doc.metadata.get('published_date', 'N/A')}
Contenuto: {doc.page_content}
---
"""
            
            if current_length + len(doc_context) > max_context_length:
                break
            
            context_parts.append(doc_context)
            current_length += len(doc_context)
        
        return "\n".join(context_parts)
    
    def cleanup_old_articles(self, days_old: int = 30):
        """Rimuove articoli più vecchi di X giorni"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            # Query per trovare articoli vecchi
            query = {
                "where": {
                    "path": ["published_date"],
                    "operator": "LessThan",
                    "valueDate": cutoff_date.isoformat()
                }
            }
            
            # Elimina gli articoli vecchi
            result = self.weaviate_client.batch.delete_objects(
                class_name=self.index_name,
                where=query["where"]
            )
            
            logger.info(f"Eliminati articoli più vecchi di {days_old} giorni")
            
        except Exception as e:
            logger.error(f"Errore nella pulizia degli articoli vecchi: {e}")
    
    def schedule_daily_updates(self):
        """Programma aggiornamenti giornalieri"""
        scheduler_config = get_scheduler_config()
        
        schedule.every().day.at(scheduler_config['update_time']).do(self.update_football_news)
        logger.info(f"Aggiornamenti giornalieri programmati alle {scheduler_config['update_time']}")
        
        # Programma anche la pulizia settimanale
        cleanup_day = getattr(schedule.every(), scheduler_config['cleanup_day'])
        cleanup_day.at(scheduler_config['cleanup_time']).do(self.cleanup_old_articles, scheduler_config['cleanup_days_old'])
        logger.info(f"Pulizia settimanale programmata per {scheduler_config['cleanup_day']} alle {scheduler_config['cleanup_time']}")
    
    def run_scheduler(self):
        """Esegue lo scheduler in background"""
        scheduler_config = get_scheduler_config()
        logger.info("Avvio dello scheduler...")
        while True:
            schedule.run_pending()
            time.sleep(scheduler_config['check_interval'])

# Esempio di utilizzo
def main():
    """Esempio di utilizzo del modulo"""
    
    # Inizializza il sistema
    with NewsVectorDB() as news_db:
        # Aggiornamento manuale notizie calcio
        added = news_db.update_football_news()
        print(f"Aggiunti {added} articoli al database")
        
        # Esempio di ricerca contesto per una domanda
        question = "Quali sono le ultime novità dell'Inter?"
        context = news_db.get_context_for_question(question)
        print(f"Contesto per la domanda '{question}':")
        print(context)
        
        # Programma aggiornamenti automatici
        news_db.schedule_daily_updates()
        
        # Avvia lo scheduler (blocca il thread principale)
        # news_db.run_scheduler()

if __name__ == "__main__":
    main()