"""
🔍 Explorer - Ricerca semantica e filtri avanzati
"""

import streamlit as st
import sys
from pathlib import Path

# Aggiungi path
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))

import pandas as pd
from datetime import datetime, timedelta
import time

from weaviate_navigator.utils.weaviate_client import WeaviateExplorer
from weaviate_navigator.utils.data_processing import DataProcessor
from weaviate_navigator.components.charts import create_similarity_distribution

# Configurazione pagina
st.set_page_config(
    page_title="🔍 Explorer - Weaviate Navigator",
    page_icon="🔍",
    layout="wide"
)

# CSS
st.markdown("""
<style>
    .search-box {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #007bff;
        margin-bottom: 2rem;
    }
    .result-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .similarity-score {
        background-color: #28a745;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.875rem;
        font-weight: bold;
    }
    .similarity-medium {
        background-color: #ffc107;
        color: #212529;
    }
    .similarity-low {
        background-color: #6c757d;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_explorer():
    return WeaviateExplorer(url="http://localhost:8080")

@st.cache_data(ttl=300)
def perform_semantic_search(_explorer, query, limit, domain_filter=None):
    return _explorer.semantic_search(query, limit=limit, domain_filter=domain_filter)

@st.cache_data(ttl=300)
def load_articles_for_filtering(_explorer, limit=1000):
    """Carica articoli per filtri SENZA contenuto per performance cache"""
    df = _explorer.get_all_articles(limit=limit)
    
    if df is not None:
        # Rimuovi completamente la colonna content per evitare problemi cache
        # La useremo solo per la ricerca semantica, non per i filtri
        df = df.copy()
        if 'content' in df.columns:
            df = df.drop('content', axis=1)
        
    return df

def get_similarity_class(score):
    if score >= 0.8:
        return "similarity-score"
    elif score >= 0.6:
        return "similarity-score similarity-medium"
    else:
        return "similarity-score similarity-low"

def main():
    st.title("🔍 Explorer - Ricerca e Filtri Avanzati")
    
    # Inizializza explorer
    try:
        explorer = init_explorer()
        if not explorer.client or not explorer.client.is_ready():
            st.error("❌ Connessione a Weaviate fallita. Verifica che sia avviato su localhost:8080")
            return
    except Exception as e:
        st.error(f"❌ Errore connessione: {e}")
        return
    
    # Sidebar con filtri
    with st.sidebar:
        st.markdown("## 🔧 Filtri di Ricerca")
        
        # Carica dati per filtri con gestione errori robusta
        try:
            with st.spinner("Caricamento filtri..."):
                df_all = load_articles_for_filtering(explorer, limit=1000)
        except Exception as e:
            st.error(f"❌ Errore caricamento filtri: {e}")
            df_all = None
        
        if df_all is not None:
            # Filtro domini
            available_domains = df_all['domain'].unique()
            selected_domains = st.multiselect(
                "🏷️ Filtra per Domini:",
                options=available_domains,
                default=available_domains,
                help="Seleziona i domini in cui cercare"
            )
            
            # Filtro date con gestione errori
            try:
                if 'date' in df_all.columns and not df_all['date'].isna().all():
                    st.markdown("### 📅 Periodo")
                    min_date = df_all['date'].min()
                    max_date = df_all['date'].max()
                    
                    # Verifica che le date siano valide
                    if pd.notna(min_date) and pd.notna(max_date):
                        date_range = st.date_input(
                            "Seleziona periodo:",
                            value=(min_date, max_date),
                            min_value=min_date,
                            max_value=max_date
                        )
                    else:
                        date_range = None
                        st.info("📅 Date non disponibili per il filtro")
                else:
                    date_range = None
            except Exception as e:
                st.warning(f"⚠️ Problema con filtro date: {e}")
                date_range = None
            
            # Filtro quality score
            if 'quality_score' in df_all.columns and not df_all['quality_score'].isna().all():
                quality_min = float(df_all['quality_score'].min())
                quality_max = float(df_all['quality_score'].max())
                
                # Solo mostra slider se i valori sono diversi
                if quality_min < quality_max:
                    st.markdown("### ⭐ Quality Score")
                    min_quality = st.slider(
                        "Quality minimo:",
                        min_value=quality_min,
                        max_value=quality_max,
                        value=quality_min,
                        step=0.1
                    )
                else:
                    min_quality = quality_min
            else:
                min_quality = None
        else:
            selected_domains = None
            date_range = None
            min_quality = None
            st.warning("Impossibile caricare filtri")
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Search box senza HTML custom che può causare problemi
        st.markdown("### 🔍 Ricerca Semantica")
        
        # Input ricerca
        col_search, col_limit, col_button = st.columns([3, 1, 1])
        
        with col_search:
            search_query = st.text_input(
                "Inserisci la tua query:",
                value="juventus milan inter calcio",
                placeholder="Es: calcio serie a, tecnologia AI, economia italiana...",
                help="La ricerca semantica trova articoli correlati al significato della query"
            )
        
        with col_limit:
            search_limit = st.selectbox(
                "Risultati:",
                options=[5, 10, 20, 50],
                index=1
            )
        
        with col_button:
            st.markdown("<br>", unsafe_allow_html=True)  # Spacing
            search_clicked = st.button("🔍 Cerca", type="primary", use_container_width=True)
        
        st.markdown("---")  # Separatore semplice invece del div
        
        # Esegui ricerca
        if search_clicked or search_query:
            if not search_query.strip():
                st.warning("⚠️ Inserisci una query di ricerca")
            else:
                with st.spinner("🔄 Ricerca in corso..."):
                    # Applica filtri domini
                    domain_filter = selected_domains if selected_domains else None
                    
                    # Esegui ricerca semantica
                    results = perform_semantic_search(
                        explorer, 
                        search_query.strip(), 
                        search_limit,
                        domain_filter=domain_filter
                    )
                
                if results is not None and len(results) > 0:
                    # Applica altri filtri se necessario
                    filtered_results = results.copy()
                    
                    # Filtro date
                    if date_range and len(date_range) == 2 and 'date' in filtered_results.columns:
                        start_date, end_date = date_range
                        filtered_results['date'] = pd.to_datetime(filtered_results['published_date']).dt.date
                        filtered_results = filtered_results[
                            (filtered_results['date'] >= start_date) & 
                            (filtered_results['date'] <= end_date)
                        ]
                    
                    # Filtro quality
                    if min_quality is not None and 'quality_score' in filtered_results.columns:
                        filtered_results = filtered_results[
                            filtered_results['quality_score'] >= min_quality
                        ]
                    
                    st.markdown(f"### 📊 Risultati ({len(filtered_results)} trovati)")
                    
                    if len(filtered_results) == 0:
                        st.warning("📭 Nessun risultato trovato con i filtri applicati")
                    else:
                        # Mostra risultati
                        for idx, row in filtered_results.iterrows():
                            with st.container():
                                st.markdown('<div class="result-card">', unsafe_allow_html=True)
                                
                                # Header con titolo e similarity
                                col_title, col_similarity = st.columns([4, 1])
                                
                                with col_title:
                                    st.markdown(f"**{row['title']}**")
                                
                                with col_similarity:
                                    similarity_class = get_similarity_class(row['similarity'])
                                    st.markdown(f'<span class="{similarity_class}">{row["similarity"]:.3f}</span>', 
                                              unsafe_allow_html=True)
                                
                                # Metadata
                                col_meta1, col_meta2, col_meta3 = st.columns(3)
                                
                                with col_meta1:
                                    st.text(f"🏷️ {row['domain']}")
                                
                                with col_meta2:
                                    st.text(f"📰 {row['source']}")
                                
                                with col_meta3:
                                    if 'published_date' in row:
                                        pub_date = pd.to_datetime(row['published_date']).strftime("%d/%m/%Y")
                                        st.text(f"📅 {pub_date}")
                                
                                # Contenuto con espansione dinamica della stessa casella
                                if 'content' in row and row['content']:
                                    full_content = str(row['content'])
                                    is_expanded = st.session_state.get(f'content_expanded_{idx}', False)
                                    
                                    # Determina contenuto e altezza in base allo stato
                                    if is_expanded:
                                        display_content = full_content
                                        text_height = min(max(len(full_content) // 80, 200), 600)  # Altezza dinamica
                                        label_text = f"Contenuto completo ({len(full_content)} caratteri):"
                                    else:
                                        display_content = full_content[:300] + "..." if len(full_content) > 300 else full_content
                                        text_height = 100
                                        label_text = "Anteprima contenuto:"
                                    
                                    col_content, col_button = st.columns([4, 1])
                                    
                                    with col_content:
                                        st.text_area(
                                            label_text,
                                            display_content,
                                            height=text_height,
                                            key=f"content_display_{idx}_{is_expanded}",  # Key diversa per forzare re-render
                                            disabled=True
                                        )
                                    
                                    with col_button:
                                        if len(full_content) > 300:
                                            if not is_expanded:
                                                # Usa session_state direttamente invece di callback per evitare bug closure
                                                if st.button("📖 Espandi", key=f"expand_{idx}", use_container_width=True):
                                                    st.session_state[f'content_expanded_{idx}'] = True
                                                    st.rerun()
                                            else:
                                                if st.button("📄 Comprimi", key=f"collapse_{idx}", use_container_width=True):
                                                    st.session_state[f'content_expanded_{idx}'] = False
                                                    st.rerun()
                                                
                                            # Mostra info lunghezza quando espanso
                                            if is_expanded:
                                                st.caption(f"📊 {len(full_content)} caratteri")
                                        else:
                                            st.caption("📄 Contenuto breve")
                                
                                # Link
                                if 'url' in row and row['url']:
                                    st.markdown(f"🔗 [Leggi articolo completo]({row['url']})")
                                
                                st.markdown('</div>', unsafe_allow_html=True)
                                st.markdown("---")
                else:
                    st.info(f"📭 Nessun risultato trovato per la query: '{search_query}'")
    
    with col2:
        st.markdown("### 📈 Statistiche Ricerca")
        
        # Info query corrente
        if search_query:
            st.info(f"**Query:** {search_query}")
            st.info(f"**Risultati richiesti:** {search_limit}")
            
            if selected_domains:
                st.info(f"**Domini filtrati:** {len(selected_domains)}")
        
        # Suggerimenti query
        st.markdown("### 💡 Suggerimenti Query")
        
        suggestions = [
            "🏆 juventus milan inter serie a",
            "🤖 intelligenza artificiale tecnologia",
            "📈 economia italiana borsa mercati",
            "🏥 covid salute pandemia",
            "🌍 ambiente clima sostenibilità",
            "🇪🇺 europa politica internazionale"
        ]
        
        for suggestion in suggestions:
            if st.button(suggestion, key=f"sug_{suggestion}", use_container_width=True):
                # Ricarica pagina con nuova query
                st.experimental_set_query_params(query=suggestion.split(' ', 1)[1])
                st.rerun()
        
        # Statistiche similarity se abbiamo risultati
        if 'results' in locals() and results is not None and len(results) > 0:
            st.markdown("### 📊 Distribuzione Similarity")
            similarities = results['similarity'].tolist()
            
            avg_sim = sum(similarities) / len(similarities)
            max_sim = max(similarities)
            min_sim = min(similarities)
            
            st.metric("Media", f"{avg_sim:.3f}")
            st.metric("Massimo", f"{max_sim:.3f}")
            st.metric("Minimo", f"{min_sim:.3f}")
            
            # Grafico distribuzione
            fig_sim = create_similarity_distribution(similarities)
            if fig_sim:
                st.plotly_chart(fig_sim, use_container_width=True)
    
    # Footer con tips
    st.markdown("---")
    st.markdown("""
    ### 💡 Tips per la Ricerca Semantica
    
    - **Usa concetti correlati**: invece di "calcio" prova "football serie a juventus"
    - **Combina termini**: "tecnologia AI machine learning" trova più contenuti correlati
    - **Usa sinonimi**: "economia finanza mercati borsa" amplia i risultati
    - **Sii specifico**: "covid vaccini pfizer" è meglio di solo "virus"
    - **La similarity** indica quanto il risultato è correlato alla tua query (>0.8 = molto correlato)
    """)

if __name__ == "__main__":
    main()