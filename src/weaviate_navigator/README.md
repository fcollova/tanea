# 🔍 Weaviate Navigator - Streamlit Dashboard

Dashboard interattiva Streamlit per esplorare e visualizzare i contenuti del database vettoriale Weaviate.

## 🚀 Quick Start

1. **Avvia i servizi:**
   ```bash
   ./start_weaviate_explorer.sh
   ```

2. **Accedi alla Dashboard:**
   - URL: http://localhost:8501
   - Auto-refresh ogni 30 secondi

## 📊 Features

### 🏠 **Home Dashboard**
- Statistiche generali database
- Metriche in tempo reale
- Grafici overview domini e fonti

### 🔍 **Explorer**
- Ricerca semantica avanzata
- Filtri per dominio, fonte, data
- Visualizzazione risultati paginata
- Export dati CSV/JSON

### 📈 **Analytics**
- Analisi temporali articoli
- Heatmap pubblicazioni
- Word clouds per dominio
- Statistiche quality score

### ⚙️ **Admin**
- Info schema Weaviate
- Connessioni e stato servizi
- Strumenti di manutenzione

## 🎨 Interfaccia

- **Sidebar** navigazione con icone
- **Layout responsive** per desktop e mobile
- **Dark/Light mode** toggle
- **Real-time updates** con auto-refresh
- **Progress indicators** per operazioni lunghe

## 🔧 Configurazione

Variabili ambiente nel container:
- `WEAVIATE_URL=http://weaviate:8080`
- `INDEX_NAME=NewsArticles_DEV`

## 📁 Struttura

```
weaviate_navigator/
├── app.py                  # App principale Streamlit
├── pages/                  # Pagine dashboard
│   ├── 01_🔍_Explorer.py   # Explorer ricerca
│   ├── 02_📈_Analytics.py  # Analisi statistiche
│   └── 03_⚙️_Admin.py     # Pannello admin
├── components/             # Componenti riutilizzabili
│   ├── __init__.py
│   ├── sidebar.py         # Sidebar con filtri
│   ├── metrics.py         # Widget metriche
│   └── charts.py          # Grafici Plotly
├── utils/                 # Utilities
│   ├── __init__.py
│   ├── weaviate_client.py # Client Weaviate
│   └── data_processing.py # Processing dati
├── Dockerfile            # Container Streamlit
└── README.md            # Questa documentazione
```

## 🚀 Sviluppo Locale

```bash
# Installa tutte le dipendenze
pip install -r ../../requirements.txt

# O usa lo script di installazione
../../install_dashboard_deps.sh

# Avvia in locale
streamlit run app.py

# Con auto-reload
streamlit run app.py --server.runOnSave true
```

## 📦 Dipendenze Dashboard

Le dipendenze sono definite in `requirements.txt`:

- **streamlit** >= 1.28.0 - Framework dashboard
- **plotly** >= 5.17.0 - Grafici interattivi  
- **pandas** >= 2.0.0 - Manipolazione dati
- **numpy** >= 1.24.0 - Calcoli numerici
- **weaviate-client** >= 4.0.0 - Client database
- **matplotlib** >= 3.7.0 - Grafici statici
- **seaborn** >= 0.12.0 - Visualizzazioni statistiche
- **wordcloud** >= 1.9.2 - Generazione word clouds
- **streamlit-option-menu** >= 0.3.6 - Menu navigazione
- **streamlit-aggrid** >= 0.3.4 - Tabelle avanzate

## 🎯 Roadmap

- [ ] Filtri avanzati con date picker
- [ ] Export report PDF
- [ ] Notifiche real-time
- [ ] Integrazione API esterne
- [ ] Dashboard personalizzabili