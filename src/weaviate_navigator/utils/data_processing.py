"""
Utilities per processing e trasformazione dati
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import re
from collections import Counter

class DataProcessor:
    """Classe per processare e analizzare dati Weaviate"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self._prepare_data()
    
    def _prepare_data(self):
        """Prepara e pulisce i dati"""
        
        # Converti date se disponibili
        if 'published_date' in self.df.columns:
            self.df['published_date'] = pd.to_datetime(self.df['published_date'], errors='coerce')
            self.df['date'] = self.df['published_date'].dt.date
            self.df['year'] = self.df['published_date'].dt.year
            self.df['month'] = self.df['published_date'].dt.month
            self.df['day'] = self.df['published_date'].dt.day
            self.df['hour'] = self.df['published_date'].dt.hour
            self.df['weekday'] = self.df['published_date'].dt.day_name()
        
        # Pulisci quality score
        if 'quality_score' in self.df.columns:
            self.df['quality_score'] = pd.to_numeric(self.df['quality_score'], errors='coerce')
        
        # Pulisci titoli
        if 'title' in self.df.columns:
            self.df['title_length'] = self.df['title'].str.len()
            self.df['title_words'] = self.df['title'].str.split().str.len()
        
        # Pulisci contenuto
        if 'content' in self.df.columns:
            self.df['content_length'] = self.df['content'].str.len()
            self.df['content_words'] = self.df['content'].str.split().str.len()
        
        # Pulisci keywords
        if 'keywords' in self.df.columns:
            self.df['keywords_count'] = self.df['keywords'].apply(
                lambda x: len(x) if isinstance(x, list) else 0
            )
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Ottiene statistiche riassuntive"""
        
        stats = {
            'total_articles': len(self.df),
            'unique_domains': self.df['domain'].nunique() if 'domain' in self.df.columns else 0,
            'unique_sources': self.df['source'].nunique() if 'source' in self.df.columns else 0,
        }
        
        # Statistiche temporali
        if 'date' in self.df.columns:
            stats['date_range'] = {
                'start': self.df['date'].min(),
                'end': self.df['date'].max(),
                'days_covered': self.df['date'].nunique()
            }
            
            # Articoli per periodo
            today = datetime.now().date()
            stats['articles_today'] = len(self.df[self.df['date'] == today])
            stats['articles_week'] = len(self.df[self.df['date'] >= today - timedelta(days=7)])
            stats['articles_month'] = len(self.df[self.df['date'] >= today - timedelta(days=30)])
        
        # Statistiche quality
        if 'quality_score' in self.df.columns and not self.df['quality_score'].isna().all():
            qs_stats = self.df['quality_score'].describe()
            stats['quality_stats'] = {
                'mean': qs_stats['mean'],
                'median': qs_stats['50%'],
                'std': qs_stats['std'],
                'min': qs_stats['min'],
                'max': qs_stats['max']
            }
        
        # Top entities
        if 'domain' in self.df.columns:
            stats['top_domains'] = self.df['domain'].value_counts().head(5).to_dict()
        
        if 'source' in self.df.columns:
            stats['top_sources'] = self.df['source'].value_counts().head(5).to_dict()
        
        return stats
    
    def filter_by_domain(self, domains: List[str]) -> 'DataProcessor':
        """Filtra per domini"""
        filtered_df = self.df[self.df['domain'].isin(domains)]
        return DataProcessor(filtered_df)
    
    def filter_by_source(self, sources: List[str]) -> 'DataProcessor':
        """Filtra per fonti"""
        filtered_df = self.df[self.df['source'].isin(sources)]
        return DataProcessor(filtered_df)
    
    def filter_by_date_range(self, start_date: datetime, end_date: datetime) -> 'DataProcessor':
        """Filtra per range di date"""
        if 'date' not in self.df.columns:
            return self
        
        start_date = start_date.date() if isinstance(start_date, datetime) else start_date
        end_date = end_date.date() if isinstance(end_date, datetime) else end_date
        
        filtered_df = self.df[
            (self.df['date'] >= start_date) & 
            (self.df['date'] <= end_date)
        ]
        return DataProcessor(filtered_df)
    
    def filter_by_quality(self, min_quality: float, max_quality: float = 1.0) -> 'DataProcessor':
        """Filtra per quality score"""
        if 'quality_score' not in self.df.columns:
            return self
        
        filtered_df = self.df[
            (self.df['quality_score'] >= min_quality) & 
            (self.df['quality_score'] <= max_quality)
        ]
        return DataProcessor(filtered_df)
    
    def get_daily_counts(self) -> pd.DataFrame:
        """Ottiene conteggi giornalieri"""
        if 'date' not in self.df.columns:
            return pd.DataFrame()
        
        daily_counts = self.df.groupby('date').agg({
            'title': 'count',
            'domain': 'nunique',
            'source': 'nunique',
            'quality_score': 'mean' if 'quality_score' in self.df.columns else 'count'
        }).reset_index()
        
        daily_counts.columns = ['date', 'articles', 'unique_domains', 'unique_sources', 'avg_quality']
        return daily_counts
    
    def get_domain_breakdown(self) -> pd.DataFrame:
        """Ottiene breakdown per dominio"""
        if 'domain' not in self.df.columns:
            return pd.DataFrame()
        
        domain_stats = self.df.groupby('domain').agg({
            'title': 'count',
            'source': 'nunique',
            'quality_score': 'mean' if 'quality_score' in self.df.columns else 'count',
            'content_length': 'mean' if 'content_length' in self.df.columns else 'count'
        }).round(3)
        
        domain_stats.columns = ['articles', 'unique_sources', 'avg_quality', 'avg_content_length']
        
        # Aggiungi percentuali
        domain_stats['percentage'] = (domain_stats['articles'] / domain_stats['articles'].sum() * 100).round(1)
        
        return domain_stats.sort_values('articles', ascending=False)
    
    def get_source_breakdown(self) -> pd.DataFrame:
        """Ottiene breakdown per fonte"""
        if 'source' not in self.df.columns:
            return pd.DataFrame()
        
        source_stats = self.df.groupby('source').agg({
            'title': 'count',
            'domain': 'nunique',
            'quality_score': 'mean' if 'quality_score' in self.df.columns else 'count'
        }).round(3)
        
        source_stats.columns = ['articles', 'unique_domains', 'avg_quality']
        
        # Aggiungi percentuali
        source_stats['percentage'] = (source_stats['articles'] / source_stats['articles'].sum() * 100).round(1)
        
        return source_stats.sort_values('articles', ascending=False)
    
    def extract_keywords_from_content(self, top_n: int = 50) -> List[tuple]:
        """Estrae keywords dal contenuto"""
        if 'content' not in self.df.columns:
            return []
        
        # Combina tutto il contenuto
        all_content = ' '.join(self.df['content'].dropna().astype(str))
        
        # Pulizia testo
        all_content = re.sub(r'[^\w\s]', ' ', all_content.lower())
        words = all_content.split()
        
        # Rimuovi stopwords italiane
        stopwords = {
            'il', 'la', 'di', 'che', 'e', 'è', 'un', 'una', 'per', 'con', 'non', 'su', 'del', 'della',
            'dei', 'delle', 'da', 'in', 'a', 'al', 'alla', 'dai', 'dalle', 'dal', 'dalla', 'le', 'i',
            'gli', 'lo', 'li', 'si', 'mi', 'ti', 'ci', 'vi', 'se', 'ma', 'anche', 'come', 'più',
            'dopo', 'molto', 'bene', 'dove', 'solo', 'prima', 'stata', 'stato', 'ogni', 'tra',
            'nel', 'nella', 'nelle', 'nei', 'questo', 'questa', 'questi', 'queste', 'suo', 'sua',
            'suoi', 'sue', 'ha', 'hanno', 'aveva', 'erano', 'essere', 'anni', 'anno', 'oggi'
        }
        
        # Filtra parole
        filtered_words = [word for word in words if len(word) > 3 and word not in stopwords]
        
        # Conta occorrenze
        word_counts = Counter(filtered_words)
        
        return word_counts.most_common(top_n)
    
    def get_publication_patterns(self) -> Dict[str, Any]:
        """Analizza pattern di pubblicazione"""
        if 'published_date' not in self.df.columns:
            return {}
        
        patterns = {}
        
        # Pattern orari
        if 'hour' in self.df.columns:
            hourly_counts = self.df['hour'].value_counts().sort_index()
            patterns['hourly_distribution'] = hourly_counts.to_dict()
            patterns['peak_hour'] = hourly_counts.idxmax()
        
        # Pattern giorni settimana
        if 'weekday' in self.df.columns:
            weekday_counts = self.df['weekday'].value_counts()
            patterns['weekday_distribution'] = weekday_counts.to_dict()
            patterns['most_active_day'] = weekday_counts.idxmax()
        
        # Pattern mensili
        if 'month' in self.df.columns:
            monthly_counts = self.df['month'].value_counts().sort_index()
            patterns['monthly_distribution'] = monthly_counts.to_dict()
        
        return patterns
    
    def detect_anomalies(self, column: str = 'title', method: str = 'zscore', threshold: float = 3.0) -> pd.DataFrame:
        """Rileva anomalie nei dati"""
        if column not in self.df.columns:
            return pd.DataFrame()
        
        if method == 'zscore':
            # Z-score per valori numerici
            if self.df[column].dtype in ['int64', 'float64']:
                z_scores = np.abs((self.df[column] - self.df[column].mean()) / self.df[column].std())
                anomalies = self.df[z_scores > threshold]
                return anomalies
        
        elif method == 'length':
            # Anomalie per lunghezza testo
            if column in ['title', 'content']:
                lengths = self.df[column].str.len()
                mean_length = lengths.mean()
                std_length = lengths.std()
                
                threshold_min = mean_length - threshold * std_length
                threshold_max = mean_length + threshold * std_length
                
                anomalies = self.df[
                    (lengths < threshold_min) | (lengths > threshold_max)
                ]
                return anomalies
        
        return pd.DataFrame()
    
    def export_summary_report(self) -> Dict[str, Any]:
        """Genera report riassuntivo completo"""
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary_stats': self.get_summary_stats(),
            'domain_breakdown': self.get_domain_breakdown().to_dict(),
            'source_breakdown': self.get_source_breakdown().head(10).to_dict(),
            'publication_patterns': self.get_publication_patterns(),
            'top_keywords': self.extract_keywords_from_content(20)
        }
        
        return report