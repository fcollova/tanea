"""
Componenti per visualizzare metriche in Streamlit
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

def show_metrics_cards(df: pd.DataFrame):
    """Mostra cards con metriche principali"""
    
    # Calcola metriche
    total_articles = len(df)
    unique_domains = df['domain'].nunique()
    unique_sources = df['source'].nunique()
    
    # Calcola articoli oggi se abbiamo le date
    articles_today = 0
    if 'date' in df.columns:
        today = datetime.now().date()
        articles_today = len(df[df['date'] == today])
    
    # Quality score medio se disponibile
    avg_quality = None
    if 'quality_score' in df.columns and not df['quality_score'].isna().all():
        avg_quality = df['quality_score'].mean()
    
    # Layout a colonne
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📰 Totale Articoli",
            value=f"{total_articles:,}",
            delta=f"+{articles_today}" if articles_today > 0 else None,
            help="Numero totale di articoli nel database"
        )
    
    with col2:
        st.metric(
            label="🏷️ Domini",
            value=unique_domains,
            help="Numero di domini unici"
        )
    
    with col3:
        st.metric(
            label="📰 Fonti",
            value=unique_sources,
            help="Numero di fonti uniche"
        )
    
    with col4:
        if avg_quality is not None:
            st.metric(
                label="⭐ Quality Score",
                value=f"{avg_quality:.3f}",
                help="Punteggio qualità medio degli articoli"
            )
        else:
            st.metric(
                label="📅 Oggi",
                value=articles_today,
                help="Articoli pubblicati oggi"
            )

def show_domain_breakdown(df: pd.DataFrame):
    """Mostra breakdown per dominio"""
    
    st.markdown("#### 🏷️ Breakdown per Dominio")
    
    domain_stats = df.groupby('domain').agg({
        'title': 'count',
        'source': 'nunique',
        'quality_score': 'mean' if 'quality_score' in df.columns else 'count'
    }).round(3)
    
    domain_stats.columns = ['Articoli', 'Fonti Uniche', 'Quality Medio']
    
    # Aggiungi percentuali
    domain_stats['%'] = (domain_stats['Articoli'] / domain_stats['Articoli'].sum() * 100).round(1)
    
    # Ordina per numero articoli
    domain_stats = domain_stats.sort_values('Articoli', ascending=False)
    
    st.dataframe(
        domain_stats,
        use_container_width=True
    )

def show_recent_activity(df: pd.DataFrame, days: int = 7):
    """Mostra attività recente"""
    
    if 'date' not in df.columns:
        return
    
    st.markdown(f"#### 📅 Attività Ultimi {days} Giorni")
    
    # Filtra ultimi giorni
    cutoff_date = datetime.now().date() - timedelta(days=days)
    recent_df = df[df['date'] >= cutoff_date]
    
    if len(recent_df) == 0:
        st.info(f"📭 Nessun articolo negli ultimi {days} giorni")
        return
    
    # Raggruppa per data
    daily_counts = recent_df.groupby('date').size().reset_index()
    daily_counts.columns = ['Data', 'Articoli']
    
    # Mostra tabella
    st.dataframe(
        daily_counts.sort_values('Data', ascending=False),
        use_container_width=True,
        height=200
    )
    
    # Statistiche quick
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "📊 Totale Periodo",
            len(recent_df)
        )
    
    with col2:
        avg_daily = len(recent_df) / days
        st.metric(
            "📈 Media Giornaliera",
            f"{avg_daily:.1f}"
        )
    
    with col3:
        max_daily = daily_counts['Articoli'].max()
        st.metric(
            "🎯 Picco Giornaliero",
            max_daily
        )

def show_source_stats(df: pd.DataFrame, top_n: int = 10):
    """Mostra statistiche per fonte"""
    
    st.markdown(f"#### 📰 Top {top_n} Fonti")
    
    source_stats = df.groupby('source').agg({
        'title': 'count',
        'domain': 'nunique'
    })
    
    source_stats.columns = ['Articoli', 'Domini']
    source_stats = source_stats.sort_values('Articoli', ascending=False).head(top_n)
    
    # Aggiungi percentuali
    source_stats['%'] = (source_stats['Articoli'] / len(df) * 100).round(1)
    
    st.dataframe(
        source_stats,
        use_container_width=True
    )