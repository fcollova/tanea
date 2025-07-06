"""
Weaviate Client Utilities per Jupyter Dashboard
"""

import weaviate
from weaviate.exceptions import WeaviateException
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
    
    def connect(self) -> bool:
        """Connette a Weaviate"""
        try:
            self.client = weaviate.Client(url=self.url)
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
            schema = self.client.schema.get()
            classes = [cls['class'] for cls in schema.get('classes', [])]
            
            info = {
                'classes': classes,
                'schema': schema
            }
            
            # Conta oggetti per classe
            for class_name in classes:
                try:
                    result = self.client.query.aggregate(class_name).with_meta_count().do()
                    count = result['data']['Aggregate'][class_name][0]['meta']['count']
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
            result = self.client.query.get(
                self.index_name,
                ['title', 'content', 'domain', 'source', 'published_date', 
                 'url', 'author', 'quality_score', 'keywords']
            ).with_limit(limit).do()
            
            articles = result['data']['Get'][self.index_name]
            
            if not articles:
                return None
            
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
            query_builder = self.client.query.get(
                self.index_name,
                ['title', 'content', 'domain', 'source', 'published_date', 
                 'url', 'quality_score']
            ).with_near_text({
                'concepts': [query]
            }).with_limit(limit).with_additional(['distance'])
            
            # Aggiungi filtro dominio se specificato
            if domain_filter:
                where_filter = {
                    "path": ["domain"],
                    "operator": "ContainsAny",
                    "valueText": domain_filter
                }
                query_builder = query_builder.with_where(where_filter)
            
            result = query_builder.do()
            articles = result['data']['Get'][self.index_name]
            
            if not articles:
                return None
            
            df = pd.DataFrame(articles)
            
            # Calcola similarità
            df['similarity'] = [1 - float(item['_additional']['distance']) for item in articles]
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
            where_filter = {
                "path": ["domain"],
                "operator": "Equal",
                "valueText": domain
            }
            
            result = self.client.query.get(
                self.index_name,
                ['title', 'content', 'domain', 'source', 'published_date', 
                 'url', 'quality_score']
            ).with_where(where_filter).with_limit(limit).do()
            
            articles = result['data']['Get'][self.index_name]
            
            if not articles:
                return None
            
            return pd.DataFrame(articles)
            
        except Exception as e:
            print(f"❌ Errore recupero articoli per dominio {domain}: {e}")
            return None
    
    def get_recent_articles(self, days: int = 7, limit: int = 100) -> Optional[pd.DataFrame]:
        """Recupera articoli recenti"""
        if not self.client:
            return None
        
        try:
            from datetime import datetime, timedelta
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            where_filter = {
                "path": ["published_date"],
                "operator": "GreaterThan",
                "valueDate": cutoff_date
            }
            
            result = self.client.query.get(
                self.index_name,
                ['title', 'content', 'domain', 'source', 'published_date', 
                 'url', 'quality_score']
            ).with_where(where_filter).with_limit(limit).do()
            
            articles = result['data']['Get'][self.index_name]
            
            if not articles:
                return None
            
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