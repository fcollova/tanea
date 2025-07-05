"""
Vector Collections Manager - Weaviate per ricerca semantica
Gestisce articoli estratti e ricerca semantica
"""

import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from langchain_weaviate import WeaviateVectorStore
from langchain.schema import Document

from ..vector_db_manager import VectorDBManager
from ..config import get_weaviate_config
from ..log import get_news_logger

logger = get_news_logger(__name__)

class VectorCollections:
    """Gestore collezioni Weaviate per ricerca semantica"""
    
    def __init__(self, environment: str = None):
        self.weaviate_config = get_weaviate_config()
        self.environment = environment or 'dev'
        
        # Inizializza vector DB manager
        self.vector_db_manager = VectorDBManager(environment)
        self.weaviate_client = None
        self.embeddings = None
        
        # Collezioni specifiche
        self.articles_collection_name = f"NewsArticles_{self.environment.upper()}"
        self.links_metadata_collection_name = f"LinksMetadata_{self.environment.upper()}"
        
        self._initialized = False
    
    def initialize(self):
        """Inizializza connessioni Weaviate"""
        if not self._initialized:
            self.weaviate_client, self.embeddings = self.vector_db_manager.initialize_all()
            self._ensure_collections_exist()
            self._initialized = True
            logger.info(f"VectorCollections inizializzato per ambiente: {self.environment}")
    
    def _ensure_collections_exist(self):
        """Assicura che le collezioni esistano"""
        try:
            # Verifica se le collezioni esistono, altrimenti le crea
            collections = self.weaviate_client.collections.list_all()
            # In Weaviate v4, collections.list_all() restituisce un dict con 'collections'
            if isinstance(collections, dict) and 'collections' in collections:
                existing_names = [col['name'] for col in collections['collections']]
            else:
                # Fallback se la struttura è diversa
                existing_names = [str(col) for col in collections] if collections else []
            
            if self.articles_collection_name not in existing_names:
                self._create_articles_collection()
            
            if self.links_metadata_collection_name not in existing_names:
                self._create_links_metadata_collection()
                
        except Exception as e:
            logger.error(f"Errore nella verifica/creazione collezioni: {e}")
    
    def _create_articles_collection(self):
        """Crea collezione per articoli"""
        try:
            collection_config = {
                "class": self.articles_collection_name,
                "description": "Articoli estratti con contenuto per ricerca semantica",
                "vectorizer": "none",  # Usiamo i nostri embeddings
                "properties": [
                    {
                        "name": "title",
                        "dataType": ["text"],
                        "description": "Titolo articolo"
                    },
                    {
                        "name": "content", 
                        "dataType": ["text"],
                        "description": "Contenuto completo articolo"
                    },
                    {
                        "name": "url",
                        "dataType": ["text"],
                        "description": "URL articolo originale"
                    },
                    {
                        "name": "source",
                        "dataType": ["text"],
                        "description": "Fonte dell'articolo"
                    },
                    {
                        "name": "domain",
                        "dataType": ["text"],
                        "description": "Dominio di appartenenza"
                    },
                    {
                        "name": "published_date",
                        "dataType": ["date"],
                        "description": "Data pubblicazione"
                    },
                    {
                        "name": "extracted_date",
                        "dataType": ["date"],
                        "description": "Data estrazione"
                    },
                    {
                        "name": "author",
                        "dataType": ["text"],
                        "description": "Autore articolo"
                    },
                    {
                        "name": "quality_score",
                        "dataType": ["number"],
                        "description": "Score qualità contenuto"
                    },
                    {
                        "name": "content_length",
                        "dataType": ["int"],
                        "description": "Lunghezza contenuto"
                    },
                    {
                        "name": "keywords",
                        "dataType": ["text[]"],
                        "description": "Keywords trovate"
                    },
                    {
                        "name": "link_id",
                        "dataType": ["text"],
                        "description": "ID link in PostgreSQL"
                    }
                ]
            }
            
            # Usa l'API v4 di Weaviate
            self.weaviate_client.collections.create_from_dict(collection_config)
            logger.info(f"Collezione {self.articles_collection_name} creata")
            
        except Exception as e:
            logger.error(f"Errore creazione collezione articoli: {e}")
    
    def _create_links_metadata_collection(self):
        """Crea collezione per metadati link (opzionale per analytics)"""
        try:
            collection_config = {
                "class": self.links_metadata_collection_name,
                "description": "Metadati link per analytics",
                "vectorizer": "none",
                "properties": [
                    {
                        "name": "url",
                        "dataType": ["text"],
                        "description": "URL del link"
                    },
                    {
                        "name": "site_name",
                        "dataType": ["text"],
                        "description": "Nome sito"
                    },
                    {
                        "name": "crawl_success_rate",
                        "dataType": ["number"],
                        "description": "Tasso successo crawling"
                    },
                    {
                        "name": "avg_quality_score",
                        "dataType": ["number"],
                        "description": "Score qualità medio"
                    },
                    {
                        "name": "last_crawled",
                        "dataType": ["date"],
                        "description": "Ultimo crawling"
                    }
                ]
            }
            
            self.weaviate_client.collections.create_from_dict(collection_config)
            logger.info(f"Collezione {self.links_metadata_collection_name} creata")
            
        except Exception as e:
            logger.error(f"Errore creazione collezione metadati: {e}")
    
    # ========================================================================
    # GESTIONE ARTICOLI
    # ========================================================================
    
    def store_article(self, article_data: Dict[str, Any], link_id: str) -> Optional[str]:
        """Salva articolo in Weaviate"""
        if not self._initialized:
            self.initialize()
        
        try:
            # Prepara oggetto per Weaviate
            weaviate_obj = {
                "title": article_data.get("title", ""),
                "content": article_data.get("content", ""),
                "url": article_data.get("url", ""),
                "source": article_data.get("source", ""),
                "domain": article_data.get("domain", "general"),
                "published_date": self._format_date(article_data.get("published_date")),
                "extracted_date": datetime.now().isoformat(),
                "author": article_data.get("author", ""),
                "quality_score": article_data.get("quality_score", 0.0),
                "content_length": len(article_data.get("content", "")),
                "keywords": article_data.get("keywords", []),
                "link_id": link_id
            }
            
            # Genera embedding per il contenuto
            text_for_embedding = f"{article_data.get('title', '')} {article_data.get('content', '')}"
            
            # Usa WeaviateVectorStore per consistency
            collection = self.weaviate_client.collections.get(self.articles_collection_name)
            
            # Inserisci con embedding
            result = collection.data.insert(
                properties=weaviate_obj,
                vector=self.embeddings.embed_query(text_for_embedding)
            )
            
            logger.info(f"Articolo salvato in Weaviate: {article_data.get('title', 'No title')[:50]}...")
            return str(result.uuid)
            
        except Exception as e:
            logger.error(f"Errore salvataggio articolo in Weaviate: {e}")
            return None
    
    def _format_date(self, date_obj: Any) -> str:
        """Formatta data per Weaviate"""
        if date_obj is None:
            return datetime.now().isoformat()
        
        if isinstance(date_obj, str):
            return date_obj
        
        if isinstance(date_obj, datetime):
            return date_obj.isoformat()
        
        return datetime.now().isoformat()
    
    def search_articles(self, query: str, domain: str = None, limit: int = 10,
                       min_quality: float = 0.0) -> List[Dict[str, Any]]:
        """Ricerca semantica articoli"""
        if not self._initialized:
            self.initialize()
        
        try:
            collection = self.weaviate_client.collections.get(self.articles_collection_name)
            
            # Costruisci filtri
            where_filter = None
            if domain or min_quality > 0:
                conditions = []
                if domain:
                    conditions.append({
                        "path": "domain",
                        "operator": "Equal",
                        "valueText": domain
                    })
                if min_quality > 0:
                    conditions.append({
                        "path": "quality_score",
                        "operator": "GreaterThanEqual", 
                        "valueNumber": min_quality
                    })
                
                where_filter = {
                    "operator": "And",
                    "operands": conditions
                } if len(conditions) > 1 else conditions[0]
            
            # Esegui ricerca near_text con API v4
            try:
                if where_filter:
                    # Metodo con filtro - prova diversi approcci API v4
                    results = collection.query.near_text(
                        query=query,
                        limit=limit,
                        return_metadata=["score", "distance"]
                    ).where(where_filter)
                else:
                    results = collection.query.near_text(
                        query=query,
                        limit=limit,
                        return_metadata=["score", "distance"]
                    )
            except Exception as near_text_error:
                logger.warning(f"Errore con filtri near_text: {near_text_error}")
                # Fallback senza filtri
                results = collection.query.near_text(
                    query=query,
                    limit=limit,
                    return_metadata=["score", "distance"]
                )
            
            # Converte risultati
            articles = []
            for item in results.objects:
                article = {
                    "id": str(item.uuid),
                    "title": item.properties.get("title", ""),
                    "content": item.properties.get("content", ""),
                    "url": item.properties.get("url", ""),
                    "source": item.properties.get("source", ""),
                    "domain": item.properties.get("domain", ""),
                    "published_date": item.properties.get("published_date"),
                    "author": item.properties.get("author", ""),
                    "quality_score": item.properties.get("quality_score", 0.0),
                    "keywords": item.properties.get("keywords", []),
                    "link_id": item.properties.get("link_id", ""),
                    "score": item.metadata.score if hasattr(item.metadata, 'score') else 0.0
                }
                articles.append(article)
            
            logger.info(f"Trovati {len(articles)} articoli per query: {query[:50]}...")
            return articles
            
        except Exception as e:
            logger.error(f"Errore ricerca articoli: {e}")
            return []
    
    def get_articles_by_domain(self, domain: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Recupera articoli per dominio"""
        if not self._initialized:
            self.initialize()
        
        try:
            collection = self.weaviate_client.collections.get(self.articles_collection_name)
            
            results = collection.query.fetch_objects(
                where={
                    "path": "domain",
                    "operator": "Equal",
                    "valueText": domain
                },
                limit=limit,
                sort={
                    "path": "published_date",
                    "order": "desc"
                }
            )
            
            articles = []
            for item in results.objects:
                article = {
                    "id": str(item.uuid),
                    "title": item.properties.get("title", ""),
                    "content": item.properties.get("content", ""),
                    "url": item.properties.get("url", ""),
                    "source": item.properties.get("source", ""),
                    "published_date": item.properties.get("published_date"),
                    "author": item.properties.get("author", ""),
                    "quality_score": item.properties.get("quality_score", 0.0),
                    "link_id": item.properties.get("link_id", "")
                }
                articles.append(article)
            
            return articles
            
        except Exception as e:
            logger.error(f"Errore recupero articoli per dominio {domain}: {e}")
            return []
    
    def delete_article(self, weaviate_id: str) -> bool:
        """Elimina articolo da Weaviate"""
        if not self._initialized:
            self.initialize()
        
        try:
            collection = self.weaviate_client.collections.get(self.articles_collection_name)
            collection.data.delete_by_id(weaviate_id)
            
            logger.info(f"Articolo {weaviate_id} eliminato da Weaviate")
            return True
            
        except Exception as e:
            logger.error(f"Errore eliminazione articolo {weaviate_id}: {e}")
            return False
    
    def cleanup_old_articles(self, days_old: int = 90) -> int:
        """Elimina articoli troppo vecchi"""
        if not self._initialized:
            self.initialize()
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            collection = self.weaviate_client.collections.get(self.articles_collection_name)
            
            # Elimina articoli vecchi
            result = collection.data.delete_many(
                where={
                    "path": "extracted_date",
                    "operator": "LessThan",
                    "valueDate": cutoff_date.isoformat()
                }
            )
            
            deleted_count = result.deleted_count if hasattr(result, 'deleted_count') else 0
            logger.info(f"Eliminati {deleted_count} articoli più vecchi di {days_old} giorni")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Errore cleanup articoli vecchi: {e}")
            return 0
    
    # ========================================================================
    # STATISTICHE E ANALYTICS
    # ========================================================================
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Statistiche collezioni"""
        if not self._initialized:
            self.initialize()
        
        try:
            collection = self.weaviate_client.collections.get(self.articles_collection_name)
            
            # Count totale usando la nuova API v4
            total_result = collection.aggregate.over_all(total_count=True)
            total_articles = total_result.total_count if hasattr(total_result, 'total_count') else 0
            
            # Statistiche per dominio usando la nuova API v4
            try:
                domain_result = collection.aggregate.over_all(
                    group_by="domain",
                    total_count=True
                )
                domain_stats = domain_result
            except Exception as domain_error:
                logger.warning(f"Impossibile ottenere statistiche dominio: {domain_error}")
                domain_stats = []
            
            return {
                "total_articles": total_articles,
                "domain_stats": domain_stats,
                "collection_name": self.articles_collection_name
            }
            
        except Exception as e:
            logger.error(f"Errore statistiche collezione: {e}")
            return {}
    
    def close(self):
        """Chiudi connessioni"""
        if self.weaviate_client:
            try:
                self.weaviate_client.close()
                logger.info("Connessioni Weaviate chiuse")
            except Exception as e:
                logger.error(f"Errore chiusura Weaviate: {e}")