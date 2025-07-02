import streamlit as st
import weaviate
import json
import pandas as pd
from typing import Dict, List, Any
import plotly.express as px
import plotly.graph_objects as go
from config import get_weaviate_config

# Configurazione della pagina
st.set_page_config(
    page_title="Weaviate Explorer",
    page_icon="🔍",
    layout="wide"
)

# Funzioni di utilità
@st.cache_resource
def connect_to_weaviate(url: str, api_key: str = None):
    """Connessione a Weaviate v4 con caching"""
    try:
        auth_config = None
        if api_key:
            auth_config = weaviate.auth.AuthApiKey(api_key=api_key)
        
        # Per localhost usa connect_to_local, altrimenti connect_to_wcs
        if "localhost" in url or "127.0.0.1" in url:
            client = weaviate.connect_to_local(
                host=url.replace("http://", "").replace("https://", "").split(":")[0],
                port=int(url.split(":")[-1]) if ":" in url.replace("http://", "").replace("https://", "") else 8080,
                auth_credentials=auth_config
            )
        else:
            client = weaviate.connect_to_wcs(
                cluster_url=url,
                auth_credentials=auth_config
            )
        
        # Verifica connessione
        if client.is_ready():
            return client
        else:
            st.error("Client Weaviate non è pronto")
            return None
            
    except Exception as e:
        st.error(f"Errore di connessione a Weaviate: {e}")
        return None

def get_schema(client):
    """Ottiene lo schema del database"""
    try:
        collections = client.collections.list_all()
        schema = {'classes': []}
        
        for collection_name in collections.keys():
            try:
                # Ottieni la collezione per accedere alla configurazione completa
                collection = client.collections.get(collection_name)
                config = collection.config.get()
                
                class_info = {
                    'class': collection_name,
                    'description': getattr(config, 'description', ''),
                    'vectorizer': str(getattr(config, 'vectorizer', '')),
                    'properties': []
                }
                
                # Ottieni proprietà dalla configurazione
                if hasattr(config, 'properties') and config.properties:
                    for prop_name, prop_config in config.properties.items():
                        prop_info = {
                            'name': prop_name,
                            'dataType': [str(prop_config.data_type)] if hasattr(prop_config, 'data_type') else ['text'],
                            'description': getattr(prop_config, 'description', ''),
                            'indexFilterable': getattr(prop_config, 'index_filterable', True)
                        }
                        class_info['properties'].append(prop_info)
                
                schema['classes'].append(class_info)
                
            except Exception as collection_error:
                # Se non riusciamo a ottenere i dettagli della collezione, aggiungi info base
                st.warning(f"Impossibile ottenere dettagli per la collezione {collection_name}: {collection_error}")
                class_info = {
                    'class': collection_name,
                    'description': 'N/A',
                    'vectorizer': 'N/A',
                    'properties': []
                }
                schema['classes'].append(class_info)
        
        return schema
    except Exception as e:
        st.error(f"Errore nel recupero dello schema: {e}")
        return None

def get_class_objects(client, class_name: str, limit: int = 50):
    """Recupera oggetti da una classe specifica"""
    try:
        collection = client.collections.get(class_name)
        response = collection.query.fetch_objects(limit=limit)
        return response
    except Exception as e:
        st.error(f"Errore nel recupero degli oggetti: {e}")
        return None

def search_objects(client, class_name: str, query: str, limit: int = 10):
    """Ricerca per similarità"""
    try:
        collection = client.collections.get(class_name)
        response = collection.query.near_text(
            query=query,
            limit=limit,
            return_metadata=['certainty', 'distance']
        )
        return response
    except Exception as e:
        st.error(f"Errore nella ricerca: {e}")
        return None

def execute_graphql_query(client, query: str):
    """Esegue una query GraphQL personalizzata"""
    try:
        result = client.graphql_raw_query(query)
        return result
    except Exception as e:
        st.error(f"Errore nell'esecuzione della query: {e}")
        return None

# Header dell'applicazione
st.title("🔍 Weaviate Database Explorer")
st.markdown("---")

# Sidebar per la configurazione
st.sidebar.header("⚙️ Configurazione")

# Carica configurazione Weaviate
weaviate_config = get_weaviate_config()

# Input per l'URL di Weaviate con valore da config
weaviate_url = st.sidebar.text_input(
    "URL Weaviate", 
    value=weaviate_config['url'],
    help="URL del tuo instance Weaviate locale"
)

# Input per API Key (opzionale)
weaviate_api_key = st.sidebar.text_input(
    "API Key (opzionale)",
    value=weaviate_config.get('api_key', ''),
    type="password",
    help="API Key per istanze Weaviate remote"
)

# Connessione a Weaviate
if st.sidebar.button("🔌 Connetti"):
    st.session_state.client = connect_to_weaviate(weaviate_url, weaviate_api_key)

# Verifica se c'è una connessione attiva
if 'client' not in st.session_state:
    st.session_state.client = connect_to_weaviate(weaviate_url, weaviate_api_key)

client = st.session_state.client

if client is None:
    st.error("❌ Impossibile connettersi a Weaviate. Verifica che il container sia in esecuzione.")
    st.info("💡 Assicurati che Weaviate sia accessibile all'URL specificato")
    st.stop()

# Verifica dello stato della connessione
try:
    if client.is_ready():
        st.sidebar.success("✅ Connesso a Weaviate")
    else:
        st.sidebar.error("❌ Weaviate non è pronto")
        st.stop()
except:
    st.sidebar.error("❌ Errore di connessione")
    st.stop()

# Tab principali
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Overview", 
    "🗂️ Classi & Schema", 
    "🔍 Esplora Oggetti", 
    "🔎 Ricerca", 
    "⚡ Query GraphQL"
])

# Tab 1: Overview
with tab1:
    st.header("📊 Panoramica del Database")
    
    # Recupera lo schema
    schema = get_schema(client)
    
    if schema:
        classes = schema.get('classes', [])
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Numero di Classi", len(classes))
        
        # Conta oggetti per classe
        class_counts = {}
        total_objects = 0
        
        for cls in classes:
            class_name = cls['class']
            try:
                # Usa la nuova API per contare gli oggetti
                collection = client.collections.get(class_name)
                count = collection.aggregate.over_all(total_count=True).total_count
                class_counts[class_name] = count
                total_objects += count
            except:
                class_counts[class_name] = 0
        
        with col2:
            st.metric("Totale Oggetti", total_objects)
        
        with col3:
            avg_objects = total_objects / len(classes) if classes else 0
            st.metric("Media Oggetti/Classe", f"{avg_objects:.1f}")
        
        # Grafico distribuzione oggetti per classe
        if class_counts:
            fig = px.bar(
                x=list(class_counts.keys()), 
                y=list(class_counts.values()),
                title="Distribuzione Oggetti per Classe",
                labels={'x': 'Classe', 'y': 'Numero Oggetti'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Tabella riassuntiva
        st.subheader("📋 Riassunto Classi")
        class_data = []
        for cls in classes:
            class_name = cls['class']
            properties = len(cls.get('properties', []))
            count = class_counts.get(class_name, 0)
            class_data.append({
                'Classe': class_name,
                'Proprietà': properties,
                'Oggetti': count,
                'Descrizione': cls.get('description', 'N/A')
            })
        
        df = pd.DataFrame(class_data)
        st.dataframe(df, use_container_width=True)

# Tab 2: Classi & Schema
with tab2:
    st.header("🗂️ Schema e Classi")
    
    if schema:
        classes = schema.get('classes', [])
        
        # Selezione classe
        if classes:
            selected_class = st.selectbox(
                "Seleziona una classe da esplorare:",
                [cls['class'] for cls in classes]
            )
            
            # Trova la classe selezionata
            class_info = next((cls for cls in classes if cls['class'] == selected_class), None)
            
            if class_info:
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.subheader(f"📝 Informazioni Classe: {selected_class}")
                    st.write(f"**Descrizione:** {class_info.get('description', 'N/A')}")
                    st.write(f"**Vectorizer:** {class_info.get('vectorizer', 'N/A')}")
                    
                    # Moduli configurati
                    modules = class_info.get('moduleConfig', {})
                    if modules:
                        st.write("**Moduli configurati:**")
                        st.json(modules)
                
                with col2:
                    st.subheader("🏷️ Proprietà")
                    properties = class_info.get('properties', [])
                    
                    if properties:
                        prop_data = []
                        for prop in properties:
                            prop_data.append({
                                'Nome': prop.get('name', 'N/A'),
                                'Tipo': ', '.join(prop.get('dataType', [])),
                                'Descrizione': prop.get('description', 'N/A'),
                                'Indicizzato': prop.get('indexFilterable', False)
                            })
                        
                        prop_df = pd.DataFrame(prop_data)
                        st.dataframe(prop_df, use_container_width=True)
                    else:
                        st.info("Nessuna proprietà definita per questa classe")
                
                # Schema completo JSON
                with st.expander("🔧 Schema JSON Completo"):
                    st.json(class_info)

# Tab 3: Esplora Oggetti
with tab3:
    st.header("🔍 Esplora Oggetti")
    
    if schema:
        classes = schema.get('classes', [])
        
        if classes:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                selected_class = st.selectbox(
                    "Seleziona classe:",
                    [cls['class'] for cls in classes],
                    key="explore_class"
                )
            
            with col2:
                limit = st.number_input("Limite oggetti", min_value=1, max_value=100, value=10)
            
            if st.button("📥 Carica Oggetti"):
                with st.spinner("Caricamento oggetti..."):
                    objects_result = get_class_objects(client, selected_class, limit)
                    
                    if objects_result and objects_result.objects:
                        objects = objects_result.objects
                        
                        st.success(f"✅ Trovati {len(objects)} oggetti")
                        
                        # Mostra oggetti
                        for i, obj in enumerate(objects):
                            with st.expander(f"Oggetto {i+1} - ID: {str(obj.uuid)[:8]}..."):
                                # Mostra proprietà
                                st.json(obj.properties)
                                
                                # Mostra metadati
                                st.write("**Metadati:**")
                                metadata = {
                                    'uuid': str(obj.uuid),
                                    'creation_time': str(obj.metadata.creation_time) if obj.metadata and hasattr(obj.metadata, 'creation_time') else None,
                                    'update_time': str(obj.metadata.last_update_time) if obj.metadata and hasattr(obj.metadata, 'last_update_time') else None
                                }
                                st.json(metadata)
                    else:
                        st.info("Nessun oggetto trovato per questa classe")

# Tab 4: Ricerca
with tab4:
    st.header("🔎 Ricerca per Similarità")
    
    if schema:
        classes = schema.get('classes', [])
        
        if classes:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                search_class = st.selectbox(
                    "Classe per la ricerca:",
                    [cls['class'] for cls in classes],
                    key="search_class"
                )
                
                query_text = st.text_input(
                    "Testo di ricerca:",
                    placeholder="Inserisci il testo da cercare..."
                )
            
            with col2:
                search_limit = st.number_input("Numero risultati", min_value=1, max_value=20, value=5)
            
            if query_text and st.button("🔍 Cerca"):
                with st.spinner("Ricerca in corso..."):
                    search_results = search_objects(client, search_class, query_text, search_limit)
                    
                    if search_results and search_results.objects:
                        objects = search_results.objects
                        
                        st.success(f"✅ Trovati {len(objects)} risultati")
                        
                        for i, obj in enumerate(objects):
                            # Estrai punteggio di similarità
                            certainty = obj.metadata.certainty if obj.metadata and hasattr(obj.metadata, 'certainty') else None
                            distance = obj.metadata.distance if obj.metadata and hasattr(obj.metadata, 'distance') else None
                            
                            certainty_display = f"{certainty:.4f}" if certainty is not None else "N/A"
                            
                            with st.expander(f"Risultato {i+1} - Certainty: {certainty_display}"):
                                st.json(obj.properties)
                                
                                if certainty is not None:
                                    st.progress(float(certainty))
                                    
                                # Mostra metadati
                                st.write("**Metadati:**")
                                metadata = {
                                    'uuid': str(obj.uuid),
                                    'certainty': certainty,
                                    'distance': distance
                                }
                                st.json(metadata)
                    else:
                        st.info("Nessun risultato trovato")

# Tab 5: Query GraphQL
with tab5:
    st.header("⚡ Query GraphQL Personalizzate")
    
    # Esempi di query
    st.subheader("📝 Esempi di Query")
    
    example_queries = {
        "Conta oggetti per classe": '''
{
  Aggregate {
    YourClassName {
      meta {
        count
      }
    }
  }
}''',
        "Query con filtro": '''
{
  Get {
    YourClassName(
      limit: 10
      where: {
        path: ["property"]
        operator: Equal
        valueString: "value"
      }
    ) {
      property1
      property2
    }
  }
}''',
        "Query con near text": '''
{
  Get {
    YourClassName(
      limit: 5
      nearText: {
        concepts: ["your search term"]
      }
    ) {
      property1
      property2
      _additional {
        certainty
        id
      }
    }
  }
}'''
    }
    
    selected_example = st.selectbox("Seleziona un esempio:", list(example_queries.keys()))
    
    if st.button("📋 Usa Esempio"):
        st.session_state.graphql_query = example_queries[selected_example]
    
    # Editor per query personalizzata
    query_text = st.text_area(
        "Query GraphQL:",
        value=st.session_state.get('graphql_query', ''),
        height=200,
        placeholder="Inserisci la tua query GraphQL qui..."
    )
    
    if st.button("▶️ Esegui Query"):
        if query_text:
            with st.spinner("Esecuzione query..."):
                result = execute_graphql_query(client, query_text)
                
                if result:
                    st.subheader("📊 Risultati")
                    st.json(result)
                    
                    # Opzione per scaricare i risultati
                    if st.button("💾 Scarica Risultati JSON"):
                        st.download_button(
                            label="📥 Download JSON",
                            data=json.dumps(result, indent=2),
                            file_name="weaviate_query_results.json",
                            mime="application/json"
                        )
        else:
            st.warning("⚠️ Inserisci una query GraphQL")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "🔍 Weaviate Explorer - Sviluppato con Streamlit"
    "</div>", 
    unsafe_allow_html=True
)