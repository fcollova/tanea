# 🌐 Tanea - Sistema di Web Crawling e Analisi Intelligente

**Tanea** è un sistema avanzato di web crawling e analisi di contenuti multi-dominio con storage ibrido (PostgreSQL + Weaviate) e architettura modulare.

## 🚀 Caratteristiche Principali

- **🕷️ Web Crawling Intelligente**: Trafilatura-based per estrazione contenuti
- **🎯 Multi-Dominio**: Gestione separata domini (calcio, tecnologia, general, etc.)
- **🧠 Vector Database**: Weaviate per ricerca semantica avanzata
- **📊 Storage Ibrido**: PostgreSQL per metadati + Weaviate per contenuti
- **🔍 Keyword Filtering**: Filtraggio avanzato basato su relevance scoring
- **⚡ Async Architecture**: Gestione concurrent crawling e rate limiting
- **🛠️ Strumenti Management**: Suite completa per database operations

## 📁 Struttura Progetto

```
tanea/
├── src/                          # Codice sorgente principale
│   ├── config/                   # File configurazione
│   │   ├── domains.yaml         # Domini e keywords
│   │   ├── web_crawling.yaml    # Siti e impostazioni crawler
│   │   └── config.conf          # Configurazioni globali
│   ├── core/                    # Componenti core
│   │   ├── domain_manager.py    # Gestione domini
│   │   ├── vector_db_manager.py # Gestione Weaviate
│   │   └── storage/             # Storage components
│   ├── crawler/                 # Sistema crawler
│   │   ├── trafilatura_crawler.py # Crawler principale
│   │   └── content_extractor.py   # Estrazione contenuti
│   └── weaviate_explorer/       # Interfaccia web Streamlit
├── scripts/                     # Script utilities
│   ├── clean_db.sh             # Script bash pulizia DB
│   ├── clean_databases.py      # Script Python completo
│   ├── list_collections.py     # Lista collezioni Weaviate  
│   ├── delete_collection.py    # Elimina collezione specifica
│   └── quick_reset.py          # Reset rapido database
├── docs/                       # Documentazione completa
└── README.md                   # Questo file
```

## 🔧 Setup e Installazione

### Prerequisiti
- **Python 3.12+**
- **PostgreSQL 14+** 
- **Weaviate 1.24+**
- **Node.js** (per Prisma)

### Installazione
```bash
# Clone repository
git clone <repository-url>
cd tanea

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup database
npx prisma generate
npx prisma db push

# Setup Weaviate (Docker)
docker run -d \
  --name weaviate \
  -p 8080:8080 \
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
  -e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
  cr.weaviate.io/semitechnologies/weaviate:1.24.4
```

## 🎯 Quick Start

### 1. Avvio Crawler
```bash
# Crawler completo tutti i domini attivi
python3 src/crawler/trafilatura_crawler.py

# Crawler dominio specifico
python3 src/crawler/trafilatura_crawler.py --domain calcio
```

### 2. Gestione Database
```bash
# Menu interattivo completo
./clean_db.sh

# Lista collezioni Weaviate
./clean_db.sh  # Seleziona opzione 4

# Reset database completo
./clean_db.sh  # Seleziona opzione 3
```

### 3. Interfaccia Web Explorer
```bash
cd src/weaviate_navigator
streamlit run main.py
```
Accedi a: http://localhost:8501

## 📚 Documentazione

La documentazione completa è disponibile nella cartella `docs/`:

| File | Descrizione |
|------|-------------|
| [**CRAWLER_ARCHITECTURE.md**](docs/CRAWLER_ARCHITECTURE.md) | 🏗️ Architettura completa del sistema, configurazioni, parametri e flussi |
| [**CRAWLER_USAGE.md**](docs/CRAWLER_USAGE.md) | 🚀 Guida utilizzo crawler, comandi e esempi pratici |
| [**CRAWLER_API.md**](docs/CRAWLER_API.md) | 📡 Documentazione API e interfacce programmatiche |
| [**DATABASE_CLEANUP.md**](docs/DATABASE_CLEANUP.md) | 🗂️ Guida completa strumenti pulizia e gestione database |
| [**README_DATABASE_SCRIPTS.md**](docs/README_DATABASE_SCRIPTS.md) | 🔧 Documentazione tecnica script database per sviluppatori |
| [**CACHE_CENTRALIZATION.md**](docs/CACHE_CENTRALIZATION.md) | 🗂️ Centralizzazione cache modelli embedding (BERTino) |

## 🎯 Domini Supportati

Il sistema supporta crawling multi-dominio con configurazione separata:

| Dominio | Siti Supportati | Keywords Principali |
|---------|-----------------|-------------------|
| **calcio** | Gazzetta dello Sport, Corriere dello Sport, TMW | calcio, Serie A, Champions League, calciomercato |
| **tecnologia** | ANSA Tech | tecnologia, AI, software, hardware |
| **general** | Altri siti | keywords generiche |

Configurazione in: `src/config/domains.yaml`

## 🗂️ Storage e Database

### PostgreSQL
- **Tabella `Site`**: Metadati siti web
- **Tabella `DiscoveredLink`**: Link scoperti durante crawling
- **Connection**: Prisma ORM con async support

### Weaviate (Vector Database)
- **Indici per Dominio**: `Tanea_[Domain]_[Environment]`
- **Schema**: Documenti con metadati e embeddings
- **Search**: Ricerca semantica avanzata

## 🛠️ Strumenti di Gestione

### Script Database
```bash
./clean_db.sh                    # Menu interattivo principale
python3 scripts/clean_databases.py    # Menu Python completo
python3 scripts/list_collections.py   # Lista collezioni
python3 scripts/delete_collection.py  # Elimina collezione specifica
```

### Opzioni Disponibili
- ✅ Verifica stato database
- ✅ Pulizia PostgreSQL e/o Weaviate
- ✅ Reset completo con creazione schemi
- ✅ Gestione granulare collezioni Weaviate
- ✅ Procedure sicure con conferme

## ⚙️ Configurazione

### File Principali
- **`src/config/domains.yaml`**: Domini, keywords, indici Weaviate
- **`src/config/web_crawling.yaml`**: Siti web, selectors, impostazioni
- **`src/config/config.conf`**: Configurazioni globali (embeddings, cache)

### Parametri Chiave
- **Rate Limiting**: Controllo carico server
- **Keyword Scoring**: Relevance filtering avanzato
- **Content Extraction**: Selectors CSS per ogni sito
- **Domain Mapping**: Assegnazione siti a domini

## 🚨 Sicurezza e Manutenzione

### Operazioni Sicure
- **Conferme Esplicite**: `RESET` per reset completo, `DELETE` per eliminazioni
- **Backup Raccomandato**: Prima di operazioni distruttive
- **Resource Management**: Chiusura automatica connessioni

### Troubleshooting
- **Connection Issues**: Verifica servizi PostgreSQL e Weaviate attivi
- **Import Errors**: Verifica virtual environment e paths
- **Memory Leaks**: Gestione automatica resource cleanup

## 🤝 Sviluppo

### Architettura Modulare
- **`core/`**: Domain manager, vector DB manager, storage
- **`crawler/`**: Web crawler, content extractor
- **`storage/`**: Database managers per PostgreSQL e Weaviate

### Pattern Utilizzati
- **Async/Await**: Per operazioni I/O non-bloccanti
- **Domain-Driven Design**: Separazione per domini semantici
- **Factory Pattern**: Per inizializzazione database managers
- **Resource Management**: Context managers e cleanup automatico

## 📊 Monitoraggio

### Logging
- **Crawler Operations**: Log dettagliati discovery ed estrazione
- **Database Operations**: Tracking inserimenti e aggiornamenti
- **Error Handling**: Gestione eccezioni con retry logic

### Metriche
- **Articoli per Dominio**: Tracking contenuti estratti
- **Performance**: Rate limiting e tempi di risposta
- **Quality Scoring**: Relevance threshold e filtering

## 📝 License

[Specificare licenza del progetto]

## 🆘 Supporto

Per questioni tecniche:
1. Consulta la [documentazione completa](docs/)
2. Verifica [troubleshooting](docs/DATABASE_CLEANUP.md#troubleshooting)
3. Apri issue su repository

---

**Tanea v2.1** - Sistema di Web Crawling e Analisi Intelligente Multi-Dominio  
*Ultima modifica: 22 Luglio 2025*