# News Vector DB System

Sistema di raccolta e ricerca semantica di notizie italiane con focus sul **calcio Serie A**.

## 🚀 Avvio Rapido

### 1. Avvia tutto con un comando
```bash
./start.sh
```

Lo script automaticamente:
- ✅ Crea e attiva virtual environment Python
- ✅ Installa tutte le dipendenze
- ✅ Avvia Weaviate database
- ✅ Scarica il modello di embedding (primo avvio)
- ✅ Avvia l'applicazione

### 2. Configura API Key (necessario)
Prima dell'avvio, ottieni una API key gratuita da [Tavily](https://tavily.com) e modificala nel file `.env`:
```bash
TAVILY_API_KEY=your-actual-api-key-here
```

### 3. Ferma il sistema
```bash
./stop.sh
```

## 📋 Prerequisiti
- Python 3.8+
- Docker e Docker Compose
- Connessione internet (per scaricare notizie e modello)

## 🔧 Configurazione Avanzata

### Dominio di notizie configurato:
- **⚽ Calcio Serie A**: squadre italiane, calciomercato, risultati, classifiche

### File di configurazione:
- `config.py`: Domini e keywords
- `.env`: API keys e configurazioni
- `docker-compose.yml`: Setup Weaviate

## 🎯 Utilizzo

### Esempio di domande:
- "Chi ha vinto l'ultima partita di Serie A?"
- "Come sta andando la Juventus in campionato?"
- "Quali sono i risultati dell'ultima giornata?"
- "Ci sono novità sul calciomercato?"

### API programmatica:
```python
from main import NewsVectorDB
from config import NEWS_DOMAINS

# Inizializza
news_db = NewsVectorDB(tavily_api_key="your-key")

# Carica notizie
news_db.update_daily_news(NEWS_DOMAINS)

# Cerca contesto
context = news_db.get_context_for_question("Juventus ultima partita")
```

## 🏗️ Architettura

- **Weaviate**: Database vettoriale per ricerca semantica
- **FastEmbed**: Modello di embedding multilingue veloce e leggero
- **Tavily**: API per ricerca notizie web
- **LangChain**: Framework per processing dei documenti

## 📊 Caratteristiche

- ✅ Completamente gratuito (nessun costo per embeddings)
- ✅ Ottimizzato per contenuti italiani
- ✅ Aggiornamenti automatici programmabili
- ✅ Deduplicazione automatica
- ✅ Cleanup automatico articoli vecchi
- ✅ Ricerca semantica avanzata

## 🛠️ Manutenzione

### Logs
```bash
docker-compose logs weaviate  # Logs Weaviate
```

### Reset database
```bash
docker-compose down -v  # Rimuove tutti i dati
```

### Aggiornamento manuale notizie
```python
python -c "from example_usage import NewsQASystem; NewsQASystem().initial_setup()"
```

## 📝 Note

- **Primo avvio**: Download modello FastEmbed (~150MB)
- **Memoria**: ~1GB RAM consigliati
- **Storage**: ~300MB per modello + dati
- **Rete**: Necessaria per notizie e primo setup

## 🤝 Supporto

Per problemi o domande, controlla i logs con:
```bash
docker-compose logs
```