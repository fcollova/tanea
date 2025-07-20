"""
Weaviate Client Utilities per Jupyter Dashboard
"""

import weaviate
from weaviate.exceptions import WeaviateBaseError
import pandas as pd
from typing import Dict, List, Optional, Any
import json
import logging

logger = logging.getLogger(__name__)

class WeaviateExplorer:
    """Client Weaviate per esplorare e analizzare dati con supporto Bertino"""
    
    def __init__(self, url: str = "http://weaviate:8080", index_name: str = "NewsArticles_DEV"):
        self.url = url
        self.index_name = index_name
        self.client = None
        self.embeddings = None
        self.connect()
        self._init_bertino_embeddings()
    
    def close(self):
        """Chiude la connessione a Weaviate"""
        if self.client:
            self.client.close()
            self.client = None
    
    def _init_bertino_embeddings(self):
        """Inizializza il modello Bertino per embedding usando stessa configurazione del crawler"""
        try:
            from fastembed import TextEmbedding
            from fastembed.common.model_description import PoolingType, ModelSource
            from langchain_community.embeddings import FastEmbedEmbeddings
            
            logger.info("🤖 Inizializzazione modello Bertino per ricerca semantica...")
            
            # Usa la stessa configurazione del crawler per evitare download duplicati
            try:
                from core.config import Config
                from pathlib import Path
                
                config = Config()
                embedding_config = config.get_embedding_config()
                custom_model = embedding_config['custom_model']
                max_length = embedding_config['max_length']
                
                # Converti cache_dir in path assoluto per evitare cache duplicate
                cache_dir_raw = embedding_config['cache_dir']
                if cache_dir_raw.startswith('./'):
                    # Path relativo: risolvi dalla root del progetto
                    project_root = Path(__file__).parent.parent.parent.parent  # Torna alla root tanea/
                    cache_dir = str(project_root / cache_dir_raw[2:])  # Rimuovi './'
                else:
                    cache_dir = cache_dir_raw
                    
                logger.info(f"📁 Cache dir assoluta: {cache_dir}")
                
            except Exception as config_error:
                # Fallback alla configurazione manuale se config non disponibile
                logger.warning(f"⚠️ Config crawler non disponibile: {config_error}")
                custom_model = "nickprock/multi-sentence-BERTino"
                max_length = 512
                
                # Fallback anche per cache dir assoluta
                from pathlib import Path
                project_root = Path(__file__).parent.parent.parent.parent
                cache_dir = str(project_root / "fastembed_cache")
                logger.info(f"📁 Cache dir fallback assoluta: {cache_dir}")
            
            # Registra il modello custom Bertino (evita errore se già registrato)
            try:
                TextEmbedding.add_custom_model(
                    model=custom_model,
                    pooling=PoolingType.MEAN,
                    normalization=True,
                    sources=ModelSource(hf=custom_model),
                    dim=768,  # Dimensioni vettore Bertino
                    model_file="onnx/model_qint8_avx512_vnni.onnx",
                )
            except Exception as reg_error:
                # Modello già registrato, continua senza errore
                if "already registered" in str(reg_error):
                    logger.info("🔄 Modello Bertino già registrato, riutilizzo esistente")
                else:
                    raise reg_error
            
            # Inizializza FastEmbedEmbeddings wrapper
            self.embeddings = FastEmbedEmbeddings(
                model_name=custom_model,
                max_length=max_length,
                cache_dir=cache_dir
            )
            
            logger.info("✅ Modello Bertino inizializzato con successo")
            
        except Exception as e:
            logger.warning(f"⚠️ Errore inizializzazione Bertino: {e}")
            logger.info("🔄 Fallback a ricerca BM25 textuale")
            self.embeddings = None
    
    def connect(self) -> bool:
        """Connette a Weaviate"""
        try:
            # Extract host from URL
            host = self.url.replace("http://", "").replace("https://", "").split(":")[0]
            port = 8080
            if ":" in self.url.replace("http://", "").replace("https://", ""):
                port = int(self.url.replace("http://", "").replace("https://", "").split(":")[1])
            
            self.client = weaviate.connect_to_local(host=host, port=port)
            if self.client.is_ready():
                print(f"✅ Connesso a Weaviate: {self.url}")
                return True
            else:
                print(f"❌ Weaviate non ready: {self.url}")
                return False
        except Exception as e:
            print(f"❌ Errore connessione Weaviate: {e}")
            self.client = None
            return False
    
    def get_schema_info(self) -> Dict[str, Any]:
        """Ottiene informazioni sullo schema"""
        if not self.client:
            return {}
        
        try:
            # In v4, use collections to get schema info
            collections = self.client.collections.list_all()
            classes = [name for name in collections.keys()]
            
            info = {
                'classes': classes,
                'schema': collections
            }
            
            # Conta oggetti per classe
            for class_name in classes:
                try:
                    collection = self.client.collections.get(class_name)
                    aggregate = collection.aggregate.over_all(total_count=True)
                    count = aggregate.total_count
                    info[f'{class_name}_count'] = count
                except:
                    info[f'{class_name}_count'] = 0
            
            return info
            
        except Exception as e:
            print(f"❌ Errore recupero schema: {e}")
            return {}
    
    def get_all_articles(self, limit: int = 1000) -> Optional[pd.DataFrame]:
        """Recupera tutti gli articoli come DataFrame"""
        if not self.client:
            return None
        
        try:
            collection = self.client.collections.get(self.index_name)
            
            # Query all objects with specified properties
            response = collection.query.fetch_objects(
                return_properties=['title', 'content', 'domain', 'source', 'published_date', 
                                 'url', 'author', 'quality_score', 'keywords'],
                limit=limit
            )
            
            if not response.objects:
                return None
            
            # Convert objects to list of dictionaries
            articles = []
            for obj in response.objects:
                article = dict(obj.properties)
                articles.append(article)
            
            df = pd.DataFrame(articles)
            
            # Pulizia dati
            if 'published_date' in df.columns:
                df['published_date'] = pd.to_datetime(df['published_date'], errors='coerce')
                df['date'] = df['published_date'].dt.date
            
            if 'quality_score' in df.columns:
                df['quality_score'] = pd.to_numeric(df['quality_score'], errors='coerce')
            
            if 'keywords' in df.columns:
                # Converte liste keywords in stringhe
                df['keywords_str'] = df['keywords'].apply(
                    lambda x: ', '.join(x) if isinstance(x, list) else str(x) if x else ''
                )
            
            return df
            
        except Exception as e:
            print(f"❌ Errore recupero articoli: {e}")
            return None
    
    def semantic_search(self, query: str, limit: int = 10, 
                       domain_filter: Optional[List[str]] = None) -> Optional[pd.DataFrame]:
        """Ricerca semantica usando modello Bertino per vettorizzare la query"""
        if not self.client:
            return None
        
        try:
            import weaviate.classes as wvc
            
            collection = self.client.collections.get(self.index_name)
            
            # Build where filter if domain filter is specified  
            # NOTA: Per ora disabilitiamo i filtri domini perché l'API v4 ha problemi
            # Useremo solo ricerche non filtrate per evitare errori
            where_filter = None
            if domain_filter and len(domain_filter) > 0:
                # Log del tentativo di filtro ma non applicare per evitare errori API
                logger.info(f"🏷️ Filtro domini richiesto: {domain_filter} (temporaneamente disabilitato)")
                # where_filter = wvc.query.Filter.by_property("domain").equal(domain_filter[0])
                where_filter = None  # Forza nessun filtro per ora
            
            # Try semantic search with Bertino embeddings
            if self.embeddings:
                try:
                    logger.info(f"🔍 Ricerca semantica con Bertino per: '{query}'")
                    
                    # Vettorizza la query con Bertino (stesso modello del crawler)
                    query_vector = self.embeddings.embed_query(query)
                    
                    # Esegui ricerca near_vector senza filtri (per ora)
                    response = collection.query.near_vector(
                        near_vector=query_vector,
                        limit=limit,
                        return_properties=['title', 'content', 'domain', 'source', 'published_date', 
                                         'url', 'quality_score'],
                        return_metadata=wvc.query.MetadataQuery(distance=True)
                    )
                    
                    if response.objects:
                        # Convert objects to list of dictionaries
                        articles = []
                        for obj in response.objects:
                            article = dict(obj.properties)
                            # Calcola similarità da distanza coseno
                            article['similarity'] = 1 - obj.metadata.distance
                            articles.append(article)
                        
                        df = pd.DataFrame(articles)
                        
                        # Arrotonda similarità
                        df['similarity'] = df['similarity'].round(3)
                        
                        # Ordina per similarità
                        df = df.sort_values('similarity', ascending=False)
                        
                        logger.info(f"✅ Trovati {len(df)} risultati semantici")
                        return df
                        
                except Exception as semantic_error:
                    logger.warning(f"⚠️ Errore ricerca semantica Bertino: {semantic_error}")
                    logger.info("🔄 Fallback a ricerca BM25...")
            else:
                logger.info("🔄 Bertino non disponibile, usando ricerca BM25...")
                
            # Fallback to BM25 text search senza filtri
            response = collection.query.bm25(
                query=query,
                limit=limit,
                return_properties=['title', 'content', 'domain', 'source', 'published_date', 
                                 'url', 'quality_score'],
                return_metadata=wvc.query.MetadataQuery(score=True)
            )
            
            if not response.objects:
                return None
            
            # Convert objects to list of dictionaries
            articles = []
            for obj in response.objects:
                article = dict(obj.properties)
                # For BM25, use score instead of distance
                article['similarity'] = obj.metadata.score if hasattr(obj.metadata, 'score') else 0.5
                articles.append(article)
            
            df = pd.DataFrame(articles)
            
            # Arrotonda similarità
            df['similarity'] = df['similarity'].round(3)
            
            # Ordina per similarità (BM25 score è già in ordine decrescente)
            df = df.sort_values('similarity', ascending=False)
            
            logger.info(f"✅ Trovati {len(df)} risultati BM25")
            return df
            
        except Exception as e:
            logger.error(f"❌ Errore ricerca: {e}")
            return None
    
    def get_articles_by_domain(self, domain: str, limit: int = 100) -> Optional[pd.DataFrame]:
        """Recupera articoli per un dominio specifico"""
        if not self.client:
            return None
        
        try:
            import weaviate.classes as wvc
            
            collection = self.client.collections.get(self.index_name)
            
            where_filter = wvc.query.Filter.by_property("domain").equal(domain)
            
            response = collection.query.fetch_objects(
                return_properties=['title', 'content', 'domain', 'source', 'published_date', 
                                 'url', 'quality_score'],
                where=where_filter,
                limit=limit
            )
            
            if not response.objects:
                return None
            
            # Convert objects to list of dictionaries
            articles = []
            for obj in response.objects:
                article = dict(obj.properties)
                articles.append(article)
            
            return pd.DataFrame(articles)
            
        except Exception as e:
            print(f"❌ Errore recupero articoli per dominio {domain}: {e}")
            return None
    
    def get_recent_articles(self, days: int = 7, limit: int = 100) -> Optional[pd.DataFrame]:
        """Recupera articoli recenti"""
        if not self.client:
            return None
        
        try:
            import weaviate.classes as wvc
            from datetime import datetime, timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            collection = self.client.collections.get(self.index_name)
            
            where_filter = wvc.query.Filter.by_property("published_date").greater_than(cutoff_date)
            
            response = collection.query.fetch_objects(
                return_properties=['title', 'content', 'domain', 'source', 'published_date', 
                                 'url', 'quality_score'],
                where=where_filter,
                limit=limit
            )
            
            if not response.objects:
                return None
            
            # Convert objects to list of dictionaries
            articles = []
            for obj in response.objects:
                article = dict(obj.properties)
                articles.append(article)
            
            df = pd.DataFrame(articles)
            df['published_date'] = pd.to_datetime(df['published_date'])
            df = df.sort_values('published_date', ascending=False)
            
            return df
            
        except Exception as e:
            print(f"❌ Errore recupero articoli recenti: {e}")
            return None
    
    def export_to_json(self, df: pd.DataFrame, filename: str) -> bool:
        """Esporta DataFrame in JSON"""
        try:
            df.to_json(filename, orient='records', date_format='iso', indent=2)
            print(f"✅ Esportato {len(df)} record in {filename}")
            return True
        except Exception as e:
            print(f"❌ Errore export JSON: {e}")
            return False
    
    def export_to_csv(self, df: pd.DataFrame, filename: str) -> bool:
        """Esporta DataFrame in CSV"""
        try:
            df.to_csv(filename, index=False)
            print(f"✅ Esportato {len(df)} righe in {filename}")
            return True
        except Exception as e:
            print(f"❌ Errore export CSV: {e}")
            return False