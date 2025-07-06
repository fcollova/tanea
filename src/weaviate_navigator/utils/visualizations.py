"""
Utilities per visualizzazioni Plotly e Matplotlib
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import seaborn as sns
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from collections import Counter
import re
from typing import List, Dict, Optional, Any

class NewsVisualizer:
    """Classe per creare visualizzazioni dei dati news"""
    
    def __init__(self):
        # Palette colori personalizzata
        self.colors = {
            'primary': '#1f77b4',
            'secondary': '#ff7f0e', 
            'success': '#2ca02c',
            'warning': '#d62728',
            'info': '#9467bd',
            'light': '#8c564b'
        }
        
        # Template Plotly personalizzato
        self.plotly_template = "plotly_white"
    
    def domain_distribution_pie(self, df: pd.DataFrame, title: str = "Distribuzione Articoli per Dominio") -> go.Figure:
        """Grafico a torta per distribuzione domini"""
        domain_counts = df['domain'].value_counts()
        
        fig = px.pie(
            values=domain_counts.values,
            names=domain_counts.index,
            title=title,
            color_discrete_sequence=px.colors.qualitative.Set3,
            template=self.plotly_template
        )
        
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>Articoli: %{value}<br>Percentuale: %{percent}<extra></extra>'
        )
        
        return fig
    
    def articles_timeline(self, df: pd.DataFrame, title: str = "Articoli nel Tempo") -> go.Figure:
        """Timeline degli articoli pubblicati"""
        if 'date' not in df.columns:
            return None
        
        daily_counts = df.groupby('date').size().reset_index()
        daily_counts.columns = ['date', 'count']
        
        fig = px.line(
            daily_counts,
            x='date',
            y='count',
            title=title,
            markers=True,
            template=self.plotly_template
        )
        
        fig.update_traces(
            line_color=self.colors['primary'],
            marker_color=self.colors['secondary']
        )
        
        fig.update_layout(
            xaxis_title="Data",
            yaxis_title="Numero Articoli",
            hovermode='x unified'
        )
        
        return fig
    
    def top_sources_bar(self, df: pd.DataFrame, top_n: int = 10, 
                       title: str = "Top Fonti per Numero Articoli") -> go.Figure:
        """Grafico a barre delle top fonti"""
        source_counts = df['source'].value_counts().head(top_n)
        
        fig = px.bar(
            x=source_counts.values,
            y=source_counts.index,
            orientation='h',
            title=title,
            color=source_counts.values,
            color_continuous_scale='viridis',
            template=self.plotly_template
        )
        
        fig.update_layout(
            xaxis_title="Numero Articoli",
            yaxis_title="Fonte",
            coloraxis_showscale=False
        )
        
        return fig
    
    def quality_score_histogram(self, df: pd.DataFrame, 
                               title: str = "Distribuzione Quality Score") -> go.Figure:
        """Istogramma quality score"""
        if 'quality_score' not in df.columns or df['quality_score'].isna().all():
            return None
        
        fig = px.histogram(
            df,
            x='quality_score',
            title=title,
            nbins=20,
            color_discrete_sequence=[self.colors['info']],
            template=self.plotly_template
        )
        
        fig.update_layout(
            xaxis_title="Quality Score",
            yaxis_title="Frequenza",
            bargap=0.1
        )
        
        # Aggiungi statistiche
        mean_score = df['quality_score'].mean()
        fig.add_vline(
            x=mean_score,
            line_dash="dash",
            line_color=self.colors['warning'],
            annotation_text=f"Media: {mean_score:.3f}"
        )
        
        return fig
    
    def domain_timeline_heatmap(self, df: pd.DataFrame, 
                               title: str = "Heatmap Articoli per Dominio nel Tempo") -> go.Figure:
        """Heatmap domini x tempo"""
        if 'date' not in df.columns:
            return None
        
        # Crea pivot table
        pivot_data = df.groupby(['date', 'domain']).size().unstack(fill_value=0)
        
        fig = px.imshow(
            pivot_data.T,
            title=title,
            color_continuous_scale='Blues',
            template=self.plotly_template,
            aspect="auto"
        )
        
        fig.update_layout(
            xaxis_title="Data",
            yaxis_title="Dominio"
        )
        
        return fig
    
    def sources_per_domain_sunburst(self, df: pd.DataFrame, 
                                   title: str = "Fonti per Dominio (Sunburst)") -> go.Figure:
        """Grafico sunburst domini -> fonti"""
        # Conta combinazioni dominio-fonte
        domain_source = df.groupby(['domain', 'source']).size().reset_index()
        domain_source.columns = ['domain', 'source', 'count']
        
        fig = go.Figure(go.Sunburst(
            labels=list(domain_source['domain']) + list(domain_source['source']),
            parents=[''] * len(domain_source['domain'].unique()) + list(domain_source['domain']),
            values=[domain_source[domain_source['domain']==d]['count'].sum() 
                   for d in domain_source['domain'].unique()] + list(domain_source['count']),
            branchvalues="total"
        ))
        
        fig.update_layout(
            title=title,
            template=self.plotly_template
        )
        
        return fig
    
    def create_wordcloud(self, texts: List[str], title: str = "Word Cloud", 
                        max_words: int = 100) -> plt.Figure:
        """Crea word cloud da lista di testi"""
        # Combina tutti i testi
        all_text = ' '.join(texts)
        
        # Pulizia testo
        all_text = re.sub(r'[^\w\s]', ' ', all_text.lower())
        all_text = re.sub(r'\s+', ' ', all_text)
        
        # Parole comuni da escludere (italiano)
        stopwords = {
            'il', 'la', 'di', 'che', 'e', 'è', 'un', 'una', 'per', 'con', 'non', 'su', 'del', 'della',
            'dei', 'delle', 'da', 'in', 'a', 'al', 'alla', 'dai', 'dalle', 'dal', 'dalla', 'le', 'i',
            'gli', 'lo', 'li', 'si', 'mi', 'ti', 'ci', 'vi', 'se', 'ma', 'anche', 'come', 'più',
            'dopo', 'molto', 'bene', 'dove', 'solo', 'prima', 'stata', 'stato', 'ogni', 'tra',
            'nel', 'nella', 'nelle', 'nei', 'questo', 'questa', 'questi', 'queste', 'suo', 'sua',
            'suoi', 'sue', 'ha', 'hanno', 'aveva', 'erano', 'essere', 'stata', 'stato', 'anni', 'anno'
        }
        
        # Genera word cloud
        wordcloud = WordCloud(
            width=800,
            height=400,
            background_color='white',
            max_words=max_words,
            stopwords=stopwords,
            colormap='viridis',
            relative_scaling=0.5,
            random_state=42
        ).generate(all_text)
        
        # Crea figura matplotlib
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        ax.set_title(title, fontsize=16, fontweight='bold')
        
        return fig
    
    def similarity_distribution(self, similarities: List[float], 
                               title: str = "Distribuzione Similarity Score") -> go.Figure:
        """Istogramma dei punteggi di similarità"""
        fig = px.histogram(
            x=similarities,
            title=title,
            nbins=20,
            color_discrete_sequence=[self.colors['success']],
            template=self.plotly_template
        )
        
        fig.update_layout(
            xaxis_title="Similarity Score",
            yaxis_title="Frequenza",
            bargap=0.1
        )
        
        # Aggiungi statistiche
        mean_sim = np.mean(similarities)
        fig.add_vline(
            x=mean_sim,
            line_dash="dash",
            line_color=self.colors['warning'],
            annotation_text=f"Media: {mean_sim:.3f}"
        )
        
        return fig
    
    def articles_per_hour_heatmap(self, df: pd.DataFrame,
                                 title: str = "Heatmap Articoli per Ora del Giorno") -> go.Figure:
        """Heatmap articoli per ora e giorno della settimana"""
        if 'published_date' not in df.columns:
            return None
        
        # Estrai ora e giorno della settimana
        df_time = df.copy()
        df_time['hour'] = pd.to_datetime(df_time['published_date']).dt.hour
        df_time['weekday'] = pd.to_datetime(df_time['published_date']).dt.day_name()
        
        # Ordina giorni della settimana
        weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        df_time['weekday'] = pd.Categorical(df_time['weekday'], categories=weekday_order, ordered=True)
        
        # Crea pivot
        heatmap_data = df_time.groupby(['weekday', 'hour']).size().unstack(fill_value=0)
        
        fig = px.imshow(
            heatmap_data,
            title=title,
            color_continuous_scale='Reds',
            template=self.plotly_template,
            aspect="auto"
        )
        
        fig.update_layout(
            xaxis_title="Ora del Giorno",
            yaxis_title="Giorno della Settimana"
        )
        
        return fig
    
    def create_dashboard_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Crea riassunto statistico per dashboard"""
        summary = {}
        
        # Statistiche base
        summary['total_articles'] = len(df)
        summary['unique_domains'] = df['domain'].nunique()
        summary['unique_sources'] = df['source'].nunique()
        
        # Date range
        if 'date' in df.columns:
            summary['date_range'] = {
                'start': df['date'].min(),
                'end': df['date'].max(),
                'days_covered': df['date'].nunique()
            }
        
        # Quality score stats
        if 'quality_score' in df.columns and not df['quality_score'].isna().all():
            qs_stats = df['quality_score'].describe()
            summary['quality_stats'] = {
                'mean': qs_stats['mean'],
                'median': qs_stats['50%'],
                'std': qs_stats['std']
            }
        
        # Top domains e sources
        summary['top_domains'] = df['domain'].value_counts().head(5).to_dict()
        summary['top_sources'] = df['source'].value_counts().head(5).to_dict()
        
        return summary