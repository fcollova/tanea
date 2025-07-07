"""
Weaviate Client Utilities per Jupyter Dashboard
"""

import weaviate
from weaviate.exceptions import WeaviateBaseError
import pandas as pd
from typing import Dict, List, Optional, Any
import json

class WeaviateExplorer:
    """Client Weaviate per esplorare e analizzare dati"""
    
    def __init__(self, url: str = "http://weaviate:8080", index_name: str = "NewsArticles_DEV"):
        self.url = url
        self.index_name = index_name
        self.client = None
        self.connect()
    
    def close(self):
        """Chiude la connessione a Weaviate"""
        if self.client:
            self.client.close()
            self.client = None
    
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
        """Ricerca semantica negli articoli"""
        if not self.client:
            return None
        
        try:
            import weaviate.classes as wvc
            
            collection = self.client.collections.get(self.index_name)
            
            # Build the query
            where_filter = None
            if domain_filter:
                where_filter = wvc.query.Filter.by_property("domain").contains_any(domain_filter)
            
            response = collection.query.near_text(
                query=query,
                limit=limit,
                return_properties=['title', 'content', 'domain', 'source', 'published_date', 
                                 'url', 'quality_score'],
                return_metadata=wvc.query.MetadataQuery(distance=True),
                where=where_filter
            )
            
            if not response.objects:
                return None
            
            # Convert objects to list of dictionaries
            articles = []
            for obj in response.objects:
                article = dict(obj.properties)
                article['similarity'] = 1 - obj.metadata.distance
                articles.append(article)
            
            df = pd.DataFrame(articles)
            
            # Arrotonda similarità
            df['similarity'] = df['similarity'].round(3)
            
            # Ordina per similarità
            df = df.sort_values('similarity', ascending=False)
            
            return df
            
        except Exception as e:
            print(f"❌ Errore ricerca semantica: {e}")
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