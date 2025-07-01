import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import logging
import schedule
import time

import weaviate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_weaviate import WeaviateVectorStore
from langchain.schema import Document
from langchain.tools import TavilySearchResults
from langchain.retrievers.web_research import WebResearchRetriever
from langchain.llms import OpenAI
from langchain.utilities import GoogleSearchAPIWrapper

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class NewsConfig:
    """Configurazione per il recupero delle notizie"""
    domain: str
    keywords: List[str]
    max_results: int = 10
    language: str = "it"
    time_range: str = "1d"  # 1d, 1w, 1m
    sources: Optional[List[str]] = None

class NewsVectorDB:
    """
    Classe principale per gestire il Vector DB delle notizie
    """
    
    def __init__(
        self,
        weaviate_url: str = "http://localhost:8080",
        weaviate_api_key: Optional[str] = None,
        tavily_api_key: Optional[str] = None,
        index_name: str = "NewsArticles",
        embedding_model: str = "intfloat/multilingual-e5-base"
    ):
        self.weaviate_url = weaviate_url
        self.weaviate_api_key = weaviate_api_key
        self.tavily_api_key = tavily_api_key
        self.index_name = index_name
        self.embedding_model = embedding_model
        
        # Inizializza i componenti
        self._init_weaviate_client()
        self._init_embeddings()
        self._init_text_splitter()
        self._init_search_tools()
        self._init_vector_store()
        
        # Cache per evitare duplicati
        self.processed_urls = set()
        
    def _init_weaviate_client(self):
        """Inizializza il client Weaviate"""
        try:
            auth_config = None
            if self.weaviate_api_key:
                auth_config = weaviate.auth.AuthApiKey(api_key=self.weaviate_api_key)
            
            self.weaviate_client = weaviate.connect_to_local(
                auth_credentials=auth_config
            )
            
            # Crea lo schema se non esiste
            self._create_schema()
            logger.info("Client Weaviate inizializzato con successo")
            
        except Exception as e:
            logger.error(f"Errore nell'inizializzazione di Weaviate: {e}")
            raise
    
    def _init_embeddings(self):
        """Inizializza il modello di embedding"""
        logger.info("Inizializzazione FastEmbed con modello BERTino italiano")
        
        try:
            # Importa le classi necessarie per il modello custom
            from fastembed import TextEmbedding
            from fastembed.common.model_description import PoolingType, ModelSource
            
            # Aggiunge il modello BERTino custom
            TextEmbedding.add_custom_model(
                model="nickprock/multi-sentence-BERTino",
                pooling=PoolingType.MEAN,
                normalization=True,
                sources=ModelSource(hf="nickprock/multi-sentence-BERTino"),
                dim=768,
                model_file="onnx/model_qint8_avx512_vnni.onnx",
            )
            
            self.embeddings = FastEmbedEmbeddings(
                model_name="nickprock/multi-sentence-BERTino",
                max_length=512,
                cache_dir="./fastembed_cache"
            )
            logger.info("FastEmbed BERTino inizializzato con successo")
            
        except Exception as e:
            logger.error(f"Errore nell'inizializzazione di BERTino: {e}")
            logger.info("Tentativo con modello di fallback...")
            
            # Fallback a modello supportato
            self.embeddings = FastEmbedEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                max_length=512,
                cache_dir="./fastembed_cache"
            )
            logger.info("Modello di fallback inizializzato")
    
    def _init_text_splitter(self):
        """Inizializza il text splitter"""
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
    
    def _init_search_tools(self):
        """Inizializza gli strumenti di ricerca"""
        if not self.tavily_api_key:
            raise ValueError("Tavily API key è richiesta per la ricerca web")
        
        os.environ["TAVILY_API_KEY"] = self.tavily_api_key
        self.tavily_search = TavilySearchResults(
            max_results=10,
            search_depth="advanced",
            include_answer=True,
            include_raw_content=True
        )
        logger.info("Strumenti di ricerca inizializzati")
    
    def _init_vector_store(self):
        """Inizializza il vector store"""
        self.vector_store = WeaviateVectorStore(
            client=self.weaviate_client,
            index_name=self.index_name,
            text_key="content",
            embedding=self.embeddings,
        )
        logger.info("Vector store inizializzato")
    
    def _create_schema(self):
        """Crea lo schema Weaviate se non esiste"""
        try:
            # Controlla se la collezione esiste già
            if self.weaviate_client.collections.exists(self.index_name):
                logger.info(f"Collezione {self.index_name} già esistente")
                return
            
            # Crea la collezione con il nuovo schema v4
            self.weaviate_client.collections.create(
                name=self.index_name,
                description="Articoli di notizie per dominio specifico",
                vectorizer_config=weaviate.classes.config.Configure.Vectorizer.none(),
                properties=[
                    weaviate.classes.config.Property(
                        name="content",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Contenuto dell'articolo"
                    ),
                    weaviate.classes.config.Property(
                        name="title",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Titolo dell'articolo"
                    ),
                    weaviate.classes.config.Property(
                        name="url",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="URL dell'articolo"
                    ),
                    weaviate.classes.config.Property(
                        name="domain",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Dominio di appartenenza"
                    ),
                    weaviate.classes.config.Property(
                        name="published_date",
                        data_type=weaviate.classes.config.DataType.DATE,
                        description="Data di pubblicazione"
                    ),
                    weaviate.classes.config.Property(
                        name="keywords",
                        data_type=weaviate.classes.config.DataType.TEXT_ARRAY,
                        description="Parole chiave associate"
                    ),
                    weaviate.classes.config.Property(
                        name="source",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Fonte dell'articolo"
                    ),
                    weaviate.classes.config.Property(
                        name="content_hash",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Hash per deduplicazione"
                    )
                ]
            )
            logger.info(f"Collezione {self.index_name} creata")
                
        except Exception as e:
            logger.error(f"Errore nella creazione dello schema: {e}")
            raise
    
    def _generate_content_hash(self, content: str) -> str:
        """Genera un hash del contenuto per evitare duplicati"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def search_news(self, config: NewsConfig) -> List[Dict[str, Any]]:
        """Cerca notizie utilizzando Tavily"""
        try:
            # Costruisci la query di ricerca
            query_parts = []
            
            # Aggiungi il dominio
            if config.domain:
                query_parts.append(f'"{config.domain}"')
            
            # Aggiungi le keywords
            if config.keywords:
                keywords_str = " OR ".join([f'"{kw}"' for kw in config.keywords])
                query_parts.append(f"({keywords_str})")
            
            # Aggiungi filtri temporali
            if config.time_range:
                query_parts.append(f"after:{config.time_range}")
            
            query = " ".join(query_parts)
            logger.info(f"Ricerca con query: {query}")
            
            # Esegui la ricerca
            search_results = self.tavily_search.run(query)
            
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
                        "domain": config.domain,
                        "keywords": config.keywords
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
    
    def update_daily_news(self, configs: List[NewsConfig]):
        """Aggiorna il database con le notizie giornaliere"""
        logger.info("Inizio aggiornamento giornaliero delle notizie")
        
        total_added = 0
        for config in configs:
            logger.info(f"Processando dominio: {config.domain}")
            
            # Cerca nuove notizie
            articles = self.search_news(config)
            
            # Aggiungi al database
            added = self.add_articles_to_vectordb(articles)
            total_added += added
        
        logger.info(f"Aggiornamento completato. Totale articoli aggiunti: {total_added}")
        return total_added
    
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
    
    def schedule_daily_updates(self, configs: List[NewsConfig], update_time: str = "09:00"):
        """Programma aggiornamenti giornalieri"""
        schedule.every().day.at(update_time).do(self.update_daily_news, configs)
        logger.info(f"Aggiornamenti giornalieri programmati alle {update_time}")
        
        # Programma anche la pulizia settimanale
        schedule.every().sunday.at("02:00").do(self.cleanup_old_articles, 30)
        logger.info("Pulizia settimanale programmata per domenica alle 02:00")
    
    def run_scheduler(self):
        """Esegue lo scheduler in background"""
        logger.info("Avvio dello scheduler...")
        while True:
            schedule.run_pending()
            time.sleep(60)  # Controlla ogni minuto

# Esempio di utilizzo
def main():
    """Esempio di utilizzo del modulo"""
    
    # Configurazione
    config_tech = NewsConfig(
        domain="tecnologia",
        keywords=["intelligenza artificiale", "AI", "machine learning", "tecnologia"],
        max_results=15,
        time_range="1d"
    )
    
    config_finance = NewsConfig(
        domain="finanza",
        keywords=["borsa", "investimenti", "economia", "mercati finanziari"],
        max_results=10,
        time_range="1d"
    )
    
    # Inizializza il sistema
    news_db = NewsVectorDB(
        weaviate_url="http://localhost:8080",
        tavily_api_key="your-tavily-key"
    )
    
    # Aggiornamento manuale
    news_db.update_daily_news([config_tech, config_finance])
    
    # Esempio di ricerca contesto per una domanda
    question = "Quali sono le ultime novità nell'intelligenza artificiale?"
    context = news_db.get_context_for_question(question)
    print(f"Contesto per la domanda '{question}':")
    print(context)
    
    # Programma aggiornamenti automatici
    news_db.schedule_daily_updates([config_tech, config_finance], "08:00")
    
    # Avvia lo scheduler (blocca il thread principale)
    # news_db.run_scheduler()

if __name__ == "__main__":
    main()