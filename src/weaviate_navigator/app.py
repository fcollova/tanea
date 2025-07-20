"""
🔍 Weaviate Navigator - Dashboard Streamlit
Dashboard interattiva per esplorare il database vettoriale Weaviate
"""

import streamlit as st
import sys
import os
from pathlib import Path

# Aggiungi il path src al sistema
src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))

# Imports
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# Import utilities locali
from weaviate_navigator.utils.weaviate_client import WeaviateExplorer
from weaviate_navigator.utils.data_processing import DataProcessor
from weaviate_navigator.components.metrics import show_metrics_cards
from weaviate_navigator.components.charts import create_domain_pie, create_timeline_chart, create_sources_bar

# Configurazione pagina
st.set_page_config(
    page_title="🔍 Weaviate Navigator",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Dashboard per esplorare il database vettoriale Weaviate"
    }
)

# CSS personalizzato
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
    }
    .content-preview {
        border: 1px solid #dee2e6;
        border-radius: 0.25rem;
        padding: 1rem;
        background-color: #f8f9fa;
        margin: 0.5rem 0;
    }
    .article-container {
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        background-color: #f8f9fa;
        margin: 0.5rem 0;
    }
    .content-area {
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        line-height: 1.4;
    }
    .article-title {
        color: #1f77b4;
        border-bottom: 2px solid #e9ecef;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }
    .sidebar-info {
        background-color: #e8f4fd;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .status-connected {
        color: #28a745;
        font-weight: bold;
    }
    .status-disconnected {
        color: #dc3545;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_weaviate_client():
    """Inizializza client Weaviate con cache"""
    return WeaviateExplorer(url="http://localhost:8080")

@st.cache_data(ttl=300)  # Cache per 5 minuti
def load_articles_data(_explorer, limit=1000):
    """Carica dati articoli con cache"""
    return _explorer.get_all_articles(limit=limit)

@st.cache_data(ttl=300)
def get_schema_info(_explorer):
    """Ottiene info schema con cache"""
    return _explorer.get_schema_info()

def main():
    """Main dashboard application"""
    
    # Header principale
    st.markdown('<h1 class="main-header">🔍 Weaviate Navigator Dashboard</h1>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("## 🔧 Controlli")
        
        # Auto-refresh toggle
        auto_refresh = st.checkbox("🔄 Auto-refresh (30s)", value=False)
        
        # Manual refresh button
        if st.button("🔄 Aggiorna Dati", type="primary"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        
        # Connessione status
        st.markdown("## 📡 Connessione")
        
        try:
            explorer = init_weaviate_client()
            if explorer.client and explorer.client.is_ready():
                st.markdown('<p class="status-connected">✅ Weaviate Connesso</p>', unsafe_allow_html=True)
                st.text(f"URL: {explorer.url}")
                
                # Info schema
                schema_info = get_schema_info(explorer)
                if schema_info:
                    st.markdown("### 📊 Database Info")
                    for cls in schema_info.get('classes', []):
                        count = schema_info.get(f'{cls}_count', 0)
                        st.text(f"{cls}: {count:,} oggetti")
            else:
                st.markdown('<p class="status-disconnected">❌ Weaviate Disconnesso</p>', unsafe_allow_html=True)
                st.error("Verifica che Weaviate sia avviato su localhost:8080")
                return
                
        except Exception as e:
            st.markdown('<p class="status-disconnected">❌ Errore Connessione</p>', unsafe_allow_html=True)
            st.error(f"Errore: {str(e)}")
            return
    
    # Main content
    col1, col2 = st.columns([3, 1])
    
    with col2:
        # Controlli filtri
        st.markdown("### 🔧 Filtri")
        
        # Limite articoli
        article_limit = st.selectbox(
            "📊 Numero articoli da caricare:",
            options=[100, 500, 1000, 2000],
            index=2,
            help="Più articoli = più tempo di caricamento"
        )
    
    with col1:
        # Caricamento dati
        with st.spinner("🔄 Caricamento dati..."):
            df = load_articles_data(explorer, limit=article_limit)
        
        if df is None or len(df) == 0:
            st.warning("📭 Nessun articolo trovato nel database")
            st.info("💡 Verifica che ci siano dati caricati in Weaviate")
            return
        
        # Data processor
        processor = DataProcessor(df)
        
        # Metriche principali
        st.markdown("## 📊 Statistiche Generali")
        show_metrics_cards(df)
        
        # Visualizzazioni principali
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("### 🏷️ Distribuzione Domini")
            fig_domain = create_domain_pie(df)
            if fig_domain:
                st.plotly_chart(fig_domain, use_container_width=True)
        
        with col_right:
            st.markdown("### 📰 Top 10 Fonti")
            fig_sources = create_sources_bar(df)
            if fig_sources:
                st.plotly_chart(fig_sources, use_container_width=True)
        
        # Timeline se abbiamo le date
        if 'date' in df.columns:
            st.markdown("### 📅 Timeline Pubblicazioni")
            fig_timeline = create_timeline_chart(df)
            if fig_timeline:
                st.plotly_chart(fig_timeline, use_container_width=True)
        
        # Tabella articoli recenti
        st.markdown("### 📄 Articoli Recenti")
        
        # Selezione colonne da mostrare
        available_columns = ['title', 'domain', 'source', 'date', 'quality_score', 'url']
        display_columns = [col for col in available_columns if col in df.columns]
        
        # Filtri per la tabella
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        
        with col_filter1:
            selected_domains = st.multiselect(
                "🏷️ Filtra Domini:",
                options=df['domain'].unique(),
                default=df['domain'].unique()[:3] if len(df['domain'].unique()) > 3 else df['domain'].unique()
            )
        
        with col_filter2:
            selected_sources = st.multiselect(
                "📰 Filtra Fonti:",
                options=df['source'].unique(),
                default=df['source'].unique()[:5] if len(df['source'].unique()) > 5 else df['source'].unique()
            )
        
        with col_filter3:
            max_rows = st.number_input(
                "📊 Max righe:",
                min_value=10,
                max_value=500,
                value=50,
                step=10
            )
        
        # Applica filtri
        filtered_df = df[
            (df['domain'].isin(selected_domains)) &
            (df['source'].isin(selected_sources))
        ].head(max_rows)
        
        if len(filtered_df) > 0:
            # Mostra articoli in formato compatto con contenuto a fianco
            st.markdown("### 📄 Articoli con Contenuto")
            
            for idx, row in filtered_df.head(20).iterrows():  # Mostra solo prime 20 per performance
                # Container per ogni articolo
                with st.container():
                    # Titolo dell'articolo
                    st.markdown(f'<div class="article-title">📰 {row.get("title", "Titolo non disponibile")}</div>', 
                              unsafe_allow_html=True)
                    
                    # Layout a due colonne: info a sinistra, contenuto a destra
                    col_info, col_content = st.columns([1, 2])
                    
                    with col_info:
                        st.markdown("**📊 Informazioni:**")
                        info_text = f"""
                        - **Dominio:** {row.get('domain', 'N/A')}
                        - **Fonte:** {row.get('source', 'N/A')}
                        """
                        if 'date' in row and pd.notna(row['date']):
                            info_text += f"- **Data:** {row['date']}\n"
                        if 'quality_score' in row and pd.notna(row['quality_score']):
                            info_text += f"- **Quality:** {row['quality_score']:.2f}\n"
                        
                        st.markdown(info_text)
                        
                        # Link alla fonte
                        if 'url' in row and row['url']:
                            st.markdown(f"🔗 [Fonte originale]({row['url']})")
                    
                    with col_content:
                        st.markdown("**📄 Contenuto:**")
                        content = row.get('content', '')
                        
                        if content and str(content).strip():
                            # Mostra contenuto in text area scrollabile
                            st.text_area(
                                f"Contenuto articolo ({len(str(content))} caratteri):",
                                value=str(content),
                                height=200,
                                key=f"content_display_{idx}",
                                disabled=True,
                                label_visibility="collapsed"
                            )
                        else:
                            st.warning("⚠️ Contenuto non disponibile")
                            st.info("Il contenuto potrebbe non essere stato estratto correttamente.")
                    
                    # Separatore tra articoli
                    st.markdown("---")
            
            # Tabella completa per export
            st.markdown("### 📊 Tabella Completa (per Export)")
            st.dataframe(
                filtered_df[display_columns],
                use_container_width=True,
                height=300
            )
            
            # Export controls
            col_export1, col_export2 = st.columns(2)
            
            with col_export1:
                if st.button("📄 Export CSV"):
                    csv = filtered_df.to_csv(index=False)
                    st.download_button(
                        label="⬇️ Scarica CSV",
                        data=csv,
                        file_name=f"weaviate_articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            
            with col_export2:
                if st.button("📋 Export JSON"):
                    json_data = filtered_df.to_json(orient='records', date_format='iso')
                    st.download_button(
                        label="⬇️ Scarica JSON",
                        data=json_data,
                        file_name=f"weaviate_articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
        else:
            st.warning("📭 Nessun articolo corrisponde ai filtri selezionati")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        🔍 Weaviate Navigator Dashboard | 
        Ultimo aggiornamento: {} | 
        Articoli caricati: {:,}
    </div>
    """.format(
        datetime.now().strftime("%H:%M:%S"),
        len(df) if df is not None else 0
    ), unsafe_allow_html=True)
    
    # Auto-refresh logic
    if auto_refresh:
        time.sleep(30)
        st.rerun()

if __name__ == "__main__":
    main()