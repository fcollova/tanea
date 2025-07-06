"""
Componenti per grafici Plotly in Streamlit
"""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_domain_pie(df: pd.DataFrame, title: str = "Distribuzione Articoli per Dominio"):
    """Crea grafico a torta per domini"""
    
    if 'domain' not in df.columns:
        return None
    
    domain_counts = df['domain'].value_counts()
    
    fig = px.pie(
        values=domain_counts.values,
        names=domain_counts.index,
        title=title,
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>Articoli: %{value}<br>Percentuale: %{percent}<extra></extra>'
    )
    
    fig.update_layout(
        showlegend=True,
        height=400,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    return fig

def create_timeline_chart(df: pd.DataFrame, title: str = "Articoli Pubblicati nel Tempo"):
    """Crea timeline degli articoli"""
    
    if 'date' not in df.columns:
        return None
    
    # Raggruppa per data
    daily_counts = df.groupby('date').size().reset_index()
    daily_counts.columns = ['date', 'count']
    
    fig = px.line(
        daily_counts,
        x='date',
        y='count',
        title=title,
        markers=True
    )
    
    fig.update_traces(
        line_color='#1f77b4',
        marker_color='#ff7f0e',
        marker_size=6
    )
    
    fig.update_layout(
        xaxis_title="Data",
        yaxis_title="Numero Articoli",
        hovermode='x unified',
        height=400,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    return fig

def create_sources_bar(df: pd.DataFrame, top_n: int = 10, title: str = "Top Fonti per Numero Articoli"):
    """Crea grafico a barre delle top fonti"""
    
    if 'source' not in df.columns:
        return None
    
    source_counts = df['source'].value_counts().head(top_n)
    
    fig = px.bar(
        x=source_counts.values,
        y=source_counts.index,
        orientation='h',
        title=title,
        color=source_counts.values,
        color_continuous_scale='viridis'
    )
    
    fig.update_layout(
        xaxis_title="Numero Articoli",
        yaxis_title="Fonte",
        coloraxis_showscale=False,
        height=400,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    return fig

def create_quality_histogram(df: pd.DataFrame, title: str = "Distribuzione Quality Score"):
    """Crea istogramma quality score"""
    
    if 'quality_score' not in df.columns or df['quality_score'].isna().all():
        return None
    
    fig = px.histogram(
        df,
        x='quality_score',
        title=title,
        nbins=20,
        color_discrete_sequence=['#9467bd']
    )
    
    # Aggiungi linea media
    mean_score = df['quality_score'].mean()
    fig.add_vline(
        x=mean_score,
        line_dash="dash",
        line_color="#d62728",
        annotation_text=f"Media: {mean_score:.3f}"
    )
    
    fig.update_layout(
        xaxis_title="Quality Score",
        yaxis_title="Frequenza",
        height=400,
        margin=dict(t=50, b=50, l=50, r=50),
        bargap=0.1
    )
    
    return fig

def create_domain_timeline_heatmap(df: pd.DataFrame, title: str = "Heatmap Domini nel Tempo"):
    """Crea heatmap domini x tempo"""
    
    if 'date' not in df.columns or 'domain' not in df.columns:
        return None
    
    # Crea pivot table
    pivot_data = df.groupby(['date', 'domain']).size().unstack(fill_value=0)
    
    fig = px.imshow(
        pivot_data.T,
        title=title,
        color_continuous_scale='Blues',
        aspect="auto"
    )
    
    fig.update_layout(
        xaxis_title="Data",
        yaxis_title="Dominio",
        height=500,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    return fig

def create_hourly_heatmap(df: pd.DataFrame, title: str = "Heatmap Pubblicazioni per Ora"):
    """Crea heatmap ore x giorni settimana"""
    
    if 'published_date' not in df.columns:
        return None
    
    # Prepara dati
    df_time = df.copy()
    df_time['published_date'] = pd.to_datetime(df_time['published_date'], errors='coerce')
    df_time = df_time.dropna(subset=['published_date'])
    
    if len(df_time) == 0:
        return None
    
    df_time['hour'] = df_time['published_date'].dt.hour
    df_time['weekday'] = df_time['published_date'].dt.day_name()
    
    # Ordina giorni settimana
    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    df_time['weekday'] = pd.Categorical(df_time['weekday'], categories=weekday_order, ordered=True)
    
    # Crea pivot
    heatmap_data = df_time.groupby(['weekday', 'hour']).size().unstack(fill_value=0)
    
    fig = px.imshow(
        heatmap_data,
        title=title,
        color_continuous_scale='Reds',
        aspect="auto"
    )
    
    fig.update_layout(
        xaxis_title="Ora del Giorno",
        yaxis_title="Giorno della Settimana",
        height=400,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    return fig

def create_sunburst_domains_sources(df: pd.DataFrame, title: str = "Gerarchia Domini → Fonti"):
    """Crea grafico sunburst domini → fonti"""
    
    if 'domain' not in df.columns or 'source' not in df.columns:
        return None
    
    # Conta combinazioni
    domain_source = df.groupby(['domain', 'source']).size().reset_index()
    domain_source.columns = ['domain', 'source', 'count']
    
    # Prepara dati per sunburst
    labels = []
    parents = []
    values = []
    
    # Aggiungi domini (livello 1)
    for domain in domain_source['domain'].unique():
        labels.append(domain)
        parents.append("")
        values.append(domain_source[domain_source['domain'] == domain]['count'].sum())
    
    # Aggiungi fonti (livello 2)
    for _, row in domain_source.iterrows():
        labels.append(f"{row['source']}")
        parents.append(row['domain'])
        values.append(row['count'])
    
    fig = go.Figure(go.Sunburst(
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        hovertemplate='<b>%{label}</b><br>Articoli: %{value}<extra></extra>'
    ))
    
    fig.update_layout(
        title=title,
        height=500,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    return fig

def create_similarity_distribution(similarities, title: str = "Distribuzione Similarity Score"):
    """Crea istogramma similarity scores"""
    
    if not similarities:
        return None
    
    fig = px.histogram(
        x=similarities,
        title=title,
        nbins=20,
        color_discrete_sequence=['#2ca02c']
    )
    
    # Aggiungi statistiche
    mean_sim = np.mean(similarities)
    fig.add_vline(
        x=mean_sim,
        line_dash="dash",
        line_color="#d62728",
        annotation_text=f"Media: {mean_sim:.3f}"
    )
    
    fig.update_layout(
        xaxis_title="Similarity Score",
        yaxis_title="Frequenza",
        height=400,
        margin=dict(t=50, b=50, l=50, r=50),
        bargap=0.1
    )
    
    return fig

def create_combined_metrics_chart(df: pd.DataFrame):
    """Crea grafico combinato con multiple metriche"""
    
    if 'date' not in df.columns:
        return None
    
    # Prepara dati giornalieri
    daily_data = df.groupby('date').agg({
        'title': 'count',
        'domain': 'nunique',
        'source': 'nunique',
        'quality_score': 'mean' if 'quality_score' in df.columns else 'count'
    }).reset_index()
    
    # Crea subplot
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Articoli per Giorno', 'Domini Unici per Giorno', 
                       'Fonti Uniche per Giorno', 'Quality Score Medio'),
        vertical_spacing=0.1
    )
    
    # Articoli per giorno
    fig.add_trace(
        go.Scatter(x=daily_data['date'], y=daily_data['title'], mode='lines+markers', name='Articoli'),
        row=1, col=1
    )
    
    # Domini unici
    fig.add_trace(
        go.Scatter(x=daily_data['date'], y=daily_data['domain'], mode='lines+markers', name='Domini'),
        row=1, col=2
    )
    
    # Fonti uniche
    fig.add_trace(
        go.Scatter(x=daily_data['date'], y=daily_data['source'], mode='lines+markers', name='Fonti'),
        row=2, col=1
    )
    
    # Quality score
    if 'quality_score' in df.columns:
        fig.add_trace(
            go.Scatter(x=daily_data['date'], y=daily_data['quality_score'], mode='lines+markers', name='Quality'),
            row=2, col=2
        )
    
    fig.update_layout(
        height=600,
        showlegend=False,
        title_text="Dashboard Metriche Complete"
    )
    
    return fig