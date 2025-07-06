"""
📈 Analytics - Analisi statistiche e visualizzazioni avanzate
"""

import streamlit as st
import sys
from pathlib import Path

# Aggiungi path
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from wordcloud import WordCloud
import matplotlib.pyplot as plt

from weaviate_navigator.utils.weaviate_client import WeaviateExplorer
from weaviate_navigator.utils.data_processing import DataProcessor
from weaviate_navigator.components.charts import (
    create_domain_timeline_heatmap,
    create_hourly_heatmap,
    create_sunburst_domains_sources,
    create_quality_histogram,
    create_combined_metrics_chart
)
from weaviate_navigator.components.metrics import (
    show_domain_breakdown,
    show_recent_activity,
    show_source_stats
)

# Configurazione pagina
st.set_page_config(
    page_title="📈 Analytics - Weaviate Navigator",
    page_icon="📈",
    layout="wide"
)

@st.cache_resource
def init_explorer():
    return WeaviateExplorer(url="http://localhost:8080")

@st.cache_data(ttl=300)
def load_analytics_data(_explorer, limit=2000):
    return _explorer.get_all_articles(limit=limit)

@st.cache_data(ttl=600)
def generate_wordcloud(texts, domain_name):
    """Genera word cloud per un dominio"""
    if not texts:
        return None
    
    # Combina testi
    combined_text = ' '.join(texts)
    
    # Stopwords italiane
    stopwords = {
        'il', 'la', 'di', 'che', 'e', 'è', 'un', 'una', 'per', 'con', 'non', 'su', 'del', 'della',
        'dei', 'delle', 'da', 'in', 'a', 'al', 'alla', 'dai', 'dalle', 'dal', 'dalla', 'le', 'i',
        'gli', 'lo', 'li', 'si', 'mi', 'ti', 'ci', 'vi', 'se', 'ma', 'anche', 'come', 'più',
        'dopo', 'molto', 'bene', 'dove', 'solo', 'prima', 'stata', 'stato', 'ogni', 'tra',
        'nel', 'nella', 'nelle', 'nei', 'questo', 'questa', 'questi', 'queste', 'suo', 'sua',
        'sono', 'anni', 'anno', 'oggi', 'ieri', 'ora', 'poi', 'già', 'ancora', 'sempre'
    }
    
    try:
        wordcloud = WordCloud(
            width=800,
            height=400,
            background_color='white',
            max_words=100,
            stopwords=stopwords,
            colormap='viridis',
            relative_scaling=0.5,
            random_state=42
        ).generate(combined_text)
        
        return wordcloud
    except:
        return None

def main():
    st.title("📈 Analytics - Analisi Statistiche Avanzate")
    
    # Inizializza explorer
    try:
        explorer = init_explorer()
        if not explorer.client or not explorer.client.is_ready():
            st.error("❌ Connessione a Weaviate fallita. Verifica che sia avviato su localhost:8080")
            return
    except Exception as e:
        st.error(f"❌ Errore connessione: {e}")
        return
    
    # Sidebar controlli
    with st.sidebar:
        st.markdown("## ⚙️ Controlli Analytics")
        
        # Limite dati
        data_limit = st.selectbox(
            "📊 Articoli da analizzare:",
            options=[500, 1000, 2000, 5000],
            index=1,
            help="Più dati = analisi più accurate ma più lente"
        )
        
        # Refresh data
        if st.button("🔄 Aggiorna Dati", type="primary"):
            st.cache_data.clear()
            st.rerun()
        
        # Period analysis
        st.markdown("### 📅 Analisi Periodo")
        analysis_period = st.selectbox(
            "Periodo di analisi:",
            options=[7, 14, 30, 60, 90],
            index=2,
            format_func=lambda x: f"Ultimi {x} giorni"
        )
    
    # Carica dati
    with st.spinner("🔄 Caricamento dati per analytics..."):
        df = load_analytics_data(explorer, limit=data_limit)
    
    if df is None or len(df) == 0:
        st.warning("📭 Nessun dato disponibile per l'analisi")
        return
    
    # Crea processor
    processor = DataProcessor(df)
    
    # Statistiche generali
    st.markdown("## 📊 Panoramica Generale")
    
    summary_stats = processor.get_summary_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "📰 Totale Articoli",
            f"{summary_stats['total_articles']:,}"
        )
    
    with col2:
        st.metric(
            "🏷️ Domini Unici",
            summary_stats['unique_domains']
        )
    
    with col3:
        st.metric(
            "📰 Fonti Uniche",
            summary_stats['unique_sources']
        )
    
    with col4:
        if 'quality_stats' in summary_stats:
            st.metric(
                "⭐ Quality Medio",
                f"{summary_stats['quality_stats']['mean']:.3f}"
            )
        else:
            if 'articles_today' in summary_stats:
                st.metric(
                    "📅 Oggi",
                    summary_stats['articles_today']
                )
    
    # Analisi temporali
    if 'date' in df.columns:
        st.markdown("## 📅 Analisi Temporali")
        
        # Filtra per periodo selezionato
        cutoff_date = datetime.now().date() - timedelta(days=analysis_period)
        recent_df = df[df['date'] >= cutoff_date] if 'date' in df.columns else df
        
        col_time1, col_time2 = st.columns(2)
        
        with col_time1:
            # Heatmap domini nel tempo
            st.markdown("### 🔥 Heatmap Domini nel Tempo")
            fig_heatmap = create_domain_timeline_heatmap(recent_df)
            if fig_heatmap:
                st.plotly_chart(fig_heatmap, use_container_width=True)
            else:
                st.info("Dati insufficienti per heatmap domini")
        
        with col_time2:
            # Pattern orari
            st.markdown("### 🕐 Pattern Pubblicazioni per Ora")
            fig_hourly = create_hourly_heatmap(recent_df)
            if fig_hourly:
                st.plotly_chart(fig_hourly, use_container_width=True)
            else:
                st.info("Dati insufficienti per pattern orari")
        
        # Attività recente
        st.markdown("### 📈 Attività Recente")
        show_recent_activity(recent_df, days=analysis_period)
    
    # Analisi domini e fonti
    st.markdown("## 🏷️ Analisi Domini e Fonti")
    
    col_domain, col_source = st.columns(2)
    
    with col_domain:
        st.markdown("### 📊 Breakdown Domini")
        show_domain_breakdown(df)
    
    with col_source:
        st.markdown("### 📰 Statistiche Fonti")
        show_source_stats(df, top_n=10)
    
    # Sunburst chart
    st.markdown("### 🌅 Relazione Domini → Fonti")
    fig_sunburst = create_sunburst_domains_sources(df)
    if fig_sunburst:
        st.plotly_chart(fig_sunburst, use_container_width=True)
    else:
        st.info("Dati insufficienti per grafico sunburst")
    
    # Quality Analysis
    if 'quality_score' in df.columns and not df['quality_score'].isna().all():
        st.markdown("## ⭐ Analisi Quality Score")
        
        col_qual1, col_qual2 = st.columns(2)
        
        with col_qual1:
            # Istogramma quality
            fig_quality = create_quality_histogram(df)
            if fig_quality:
                st.plotly_chart(fig_quality, use_container_width=True)
        
        with col_qual2:
            # Statistiche quality per dominio
            st.markdown("### 📊 Quality per Dominio")
            quality_by_domain = df.groupby('domain')['quality_score'].agg(['mean', 'std', 'count']).round(3)
            quality_by_domain.columns = ['Media', 'Deviazione', 'Count']
            quality_by_domain = quality_by_domain.sort_values('Media', ascending=False)
            st.dataframe(quality_by_domain, use_container_width=True)
    
    # Word Clouds
    st.markdown("## ☁️ Word Clouds per Dominio")
    
    # Selettore dominio per word cloud
    available_domains = df['domain'].unique()
    selected_domain = st.selectbox(
        "🏷️ Seleziona dominio per word cloud:",
        options=available_domains,
        help="Genera word cloud dai titoli degli articoli del dominio selezionato"
    )
    
    if selected_domain:
        domain_articles = df[df['domain'] == selected_domain]
        
        if len(domain_articles) > 0:
            # Usa titoli per word cloud
            titles = domain_articles['title'].dropna().tolist()
            
            if titles:
                with st.spinner(f"Generazione word cloud per {selected_domain}..."):
                    wordcloud = generate_wordcloud(titles, selected_domain)
                
                if wordcloud:
                    fig, ax = plt.subplots(figsize=(12, 6))
                    ax.imshow(wordcloud, interpolation='bilinear')
                    ax.axis('off')
                    ax.set_title(f'Word Cloud - {selected_domain}', fontsize=16, fontweight='bold')
                    st.pyplot(fig)
                    plt.close()
                else:
                    st.error("Impossibile generare word cloud")
            else:
                st.warning(f"Nessun titolo disponibile per {selected_domain}")
        else:
            st.warning(f"Nessun articolo trovato per {selected_domain}")
    
    # Advanced Analytics
    st.markdown("## 🔬 Analisi Avanzate")
    
    # Pattern di pubblicazione
    patterns = processor.get_publication_patterns()
    
    if patterns:
        col_pattern1, col_pattern2 = st.columns(2)
        
        with col_pattern1:
            st.markdown("### 🕐 Pattern Orari")
            if 'peak_hour' in patterns:
                st.metric("Ora di picco", f"{patterns['peak_hour']}:00")
            
            if 'hourly_distribution' in patterns:
                hourly_df = pd.DataFrame.from_dict(
                    patterns['hourly_distribution'], 
                    orient='index', 
                    columns=['Articoli']
                )
                st.bar_chart(hourly_df)
        
        with col_pattern2:
            st.markdown("### 📅 Pattern Settimanali")
            if 'most_active_day' in patterns:
                st.metric("Giorno più attivo", patterns['most_active_day'])
            
            if 'weekday_distribution' in patterns:
                weekday_df = pd.DataFrame.from_dict(
                    patterns['weekday_distribution'], 
                    orient='index', 
                    columns=['Articoli']
                )
                st.bar_chart(weekday_df)
    
    # Keywords Analysis
    st.markdown("### 🔤 Top Keywords")
    
    with st.spinner("Estrazione keywords..."):
        top_keywords = processor.extract_keywords_from_content(top_n=30)
    
    if top_keywords:
        # Mostra top keywords
        keywords_df = pd.DataFrame(top_keywords, columns=['Keyword', 'Frequenza'])
        
        col_kw1, col_kw2 = st.columns(2)
        
        with col_kw1:
            st.dataframe(keywords_df.head(15), use_container_width=True)
        
        with col_kw2:
            # Grafico keywords
            st.bar_chart(keywords_df.head(10).set_index('Keyword'))
    else:
        st.info("Nessuna keyword estratta")
    
    # Dashboard combinato
    st.markdown("## 📊 Dashboard Combinato")
    fig_combined = create_combined_metrics_chart(df)
    if fig_combined:
        st.plotly_chart(fig_combined, use_container_width=True)
    
    # Export report
    st.markdown("## 💾 Export Report")
    
    col_export1, col_export2 = st.columns(2)
    
    with col_export1:
        if st.button("📊 Genera Report Completo"):
            with st.spinner("Generazione report..."):
                report = processor.export_summary_report()
                
                report_json = pd.Series(report).to_json(indent=2)
                st.download_button(
                    label="⬇️ Scarica Report JSON",
                    data=report_json,
                    file_name=f"weaviate_analytics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
    
    with col_export2:
        if st.button("📈 Export Dati Analytics"):
            # Esporta dati processati
            export_data = {
                'summary': processor.get_summary_stats(),
                'domain_breakdown': processor.get_domain_breakdown().to_dict(),
                'source_breakdown': processor.get_source_breakdown().to_dict(),
                'daily_counts': processor.get_daily_counts().to_dict()
            }
            
            export_json = pd.Series(export_data).to_json(indent=2)
            st.download_button(
                label="⬇️ Scarica Dati CSV",
                data=df.to_csv(index=False),
                file_name=f"weaviate_analytics_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    # Footer
    st.markdown("---")
    st.info(f"""
    📊 **Analytics Summary**: Analizzati {len(df):,} articoli da {summary_stats['unique_sources']} fonti 
    in {summary_stats['unique_domains']} domini | 
    Ultimo aggiornamento: {datetime.now().strftime('%H:%M:%S')}
    """)

if __name__ == "__main__":
    main()