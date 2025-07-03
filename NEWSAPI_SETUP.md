# 🔑 NewsAPI Configuration Guide

NewsAPI è una delle fonti di notizie disponibili nel sistema. Per utilizzarla è necessaria una chiave API gratuita.

## 📋 Requisiti

- NewsAPI richiede registrazione gratuita
- Piano gratuito: 1000 richieste/mese, solo sviluppo
- Piano a pagamento: per produzione

## 🚀 Setup Rapido

### 1. Ottieni la chiave API
1. Vai su [newsapi.org](https://newsapi.org)
2. Clicca "Get API Key"
3. Registrati con email
4. Copia la tua API key

### 2. Configura la chiave

**Opzione A - Variabile d'ambiente (consigliata):**
```bash
export NEWSAPI_API_KEY="your_api_key_here"
```

**Opzione B - File di configurazione:**
Aggiungi al file `config.dev.conf` o `config.prod.conf`:
```ini
[search]
newsapi_api_key = your_api_key_here
```

### 3. Test della configurazione
```bash
# Testa se NewsAPI funziona
python3 load_news.py --test

# Carica solo da NewsAPI
python3 load_news.py --newsapi
```

## 📰 Fonti Italiane Supportate

### Notizie Generali:
- ANSA
- La Repubblica  
- Corriere della Sera
- Il Sole 24 Ore

### Sport:
- Gazzetta dello Sport
- Corriere dello Sport
- Tuttosport

### Calcio:
- Gazzetta dello Sport
- Corriere dello Sport
- Tuttosport
- Goal.com

## 💡 Priorità nel Sistema

1. **RSS** (priorità 1) - Sempre disponibile, gratuito
2. **NewsAPI** (priorità 2) - Richiede API key, alta qualità
3. **Web Scraping** (priorità 2) - Sempre disponibile, più lento
4. **Tavily** (priorità 3) - Fallback, richiede API key

## 🔍 Comandi Utili

```bash
# Solo NewsAPI
python3 load_news.py --newsapi

# NewsAPI + RSS
python3 load_news.py --sources newsapi rss

# Test tutte le fonti
python3 load_news.py --test

# Statistiche fonti
python3 load_news.py --stats
```

## ⚠️ Note Importanti

- **Piano gratuito**: limitato a sviluppo, max 1000 richieste/mese
- **Rate limiting**: il sistema rispetta i limiti API automaticamente
- **Fallback**: se NewsAPI non è disponibile, usa altre fonti
- **Sicurezza**: non commitare mai la API key nel codice
- **API Limitation**: usa strategia dual-endpoint per evitare errori 400

## 🔧 Risoluzione Errori Comuni

**Errore HTTP 400**: 
- ✅ **Risolto**: il sistema ora usa `/top-headlines` + `/everything` separatamente
- Non più conflitti tra parametri `sources` e `q`

**Fonti non trovate**:
- Usa domini italiani verificati invece di source IDs
- Fallback automatico a ricerca per keywords

## 🎯 Risultati Attesi

Con NewsAPI configurata correttamente vedrai:
- 🟢 newsapi: Disponibile
- Articoli da fonti italiane verificate
- Migliore qualità dei metadati (data, autore, etc.)