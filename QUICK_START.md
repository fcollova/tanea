# 🚀 Quick Start - News Vector DB System

Guida rapida per l'installazione e l'uso del sistema News Vector DB con **Trafilatura AI-powered scraping**.

## 📋 Requisiti

- **Python 3.8+** 
- **Docker** (per Weaviate)
- **Git** (per clonare il repository)

## ⚡ Installazione Rapida

### 1. Installa il sistema
```bash
./install.sh
```

Questo script:
- ✅ Crea virtual environment Python
- ✅ Installa tutte le dipendenze (incluso **Trafilatura**)
- ✅ Configura file .env
- ✅ Verifica configurazioni sistema
- ✅ Testa importazioni moduli

### 2. Avvia Weaviate
```bash
./start.sh
```

### 3. Esegui l'esempio
```bash
./run_example.sh
```

## 🎯 Scripts Disponibili

| Script | Descrizione | Uso |
|--------|------------|-----|
| `./install.sh` | **Installazione completa sistema** | Una sola volta |
| `./start.sh` | Avvia Weaviate (Docker) | Prima di usare il sistema |
| `./stop.sh` | Ferma Weaviate | Quando finisci |
| `./run_example.sh` | **Esegue applicazione di esempio** | Per testare il sistema |
| `./load_news_trafilatura.sh` | **Solo Trafilatura AI-powered** | Caricamento notizie ottimale |

## 🚀 Trafilatura - AI Powered Scraping

Il sistema ora usa **Trafilatura** come fonte primaria con priorità massima:

### Vantaggi Trafilatura:
- 🧠 **AI-powered**: Riconoscimento automatico contenuto
- 🔧 **Zero manutenzione**: Nessun selettore CSS da aggiornare
- ⚡ **Performance**: ~1s per estrazione vs parsing DOM completo
- 📊 **Metadati automatici**: Autore, data, descrizione estratti
- 🛡️ **Robustezza**: Funziona anche se i siti cambiano layout

### Utilizzo Trafilatura:
```bash
# Solo Trafilatura (consigliato)
./load_news_trafilatura.sh

# O con opzioni CLI
python src/scripts/load_news.py --trafilatura

# Combinato con altre fonti
python src/scripts/load_news.py --sources trafilatura rss
```

## 📊 Fonti di Notizie Configurate

| Priorità | Fonte | Tecnologia | Manutenzione | Disponibilità |
|-----------|-------|------------|--------------|---------------|
| 🥇 | **Trafilatura** | AI-powered scraping | Zero | Sempre |
| 🥈 | RSS Feeds | Feed XML | Bassa | Sempre |
| 🥉 | Web Scraping | BeautifulSoup CSS | Alta | Fallback |
| 🔑 | NewsAPI | API REST | Nessuna | API key |
| 🔑 | Tavily | Search API | Nessuna | API key |

## 🔧 Configurazione

### File `.env` (creato automaticamente da `install.sh`):
```env
# Database
WEAVIATE_URL=http://localhost:8080

# API Keys (opzionali)
TAVILY_API_KEY=your-tavily-api-key-here
NEWSAPI_API_KEY=your-newsapi-key-here

# Modello embedding (italiano)
EMBEDDING_MODEL=nickprock/multi-sentence-BERTino

# Fonti abilitate
ENABLE_TRAFILATURA=true  # Raccomandato!
ENABLE_RSS=true
ENABLE_SCRAPING=true
ENABLE_NEWSAPI=false
ENABLE_TAVILY=false
```

## 📖 Esempi di Uso

### Installazione Completa
```bash
# 1. Installazione sistema
./install.sh

# 2. Avvia database
./start.sh

# 3. Test con esempio
./run_example.sh
```

### Caricamento Notizie
```bash
# Metodo consigliato (solo Trafilatura)
./load_news_trafilatura.sh

# Tutti i metodi disponibili
python src/scripts/load_news.py --help

# Test tutte le fonti
python src/scripts/load_news.py --test

# Solo RSS + Trafilatura
python src/scripts/load_news.py --sources trafilatura rss
```

### Monitoraggio
```bash
# Logs in tempo reale
tail -f logs/tanea_dev.log

# Stato Weaviate
curl http://localhost:8080/v1/meta

# Statistiche database
python src/scripts/load_news.py --stats
```

## 🆘 Risoluzione Problemi

### Installazione
```bash
# Se install.sh fallisce
./install.sh  # Riprova (gestisce virtual env esistenti)

# Verifica Python
python3 --version  # Deve essere 3.8+

# Verifica Docker
docker --version
```

### Weaviate
```bash
# Se Weaviate non si avvia
./stop.sh && ./start.sh

# Verifica Docker
docker ps  # Deve mostrare weaviate

# Riavvia Docker se necessario
sudo systemctl restart docker
```

### Dipendenze
```bash
# Se mancano dipendenze
source venv/bin/activate
pip install -r requirements.txt

# Verifica Trafilatura
python3 -c "import trafilatura; print('OK')"
```

## 📈 Performance

### Trafilatura vs Altri Metodi:
- **Trafilatura**: ~1s per articolo, qualità alta, zero manutenzione
- **BeautifulSoup**: ~2-3s per articolo, qualità variabile, alta manutenzione
- **RSS**: ~0.5s per articolo, qualità limitata, bassa manutenzione

### Raccomandazioni:
1. **Usa principalmente Trafilatura** per web scraping
2. **RSS come complemento** per copertura aggiuntiva  
3. **API keys opzionali** per funzionalità extra
4. **Monitora logs** per ottimizzazioni

## 🎯 Prossimi Passi

Dopo l'installazione:
1. ✅ Testa con `./run_example.sh`
2. 🔧 Configura API keys in `.env` (opzionale)
3. 🚀 Carica notizie con `./load_news_trafilatura.sh`
4. 📊 Monitora con `python src/scripts/load_news.py --stats`
5. 🔍 Esplora con l'interfaccia web (se configurata)

---

**🎊 Il sistema è ora pronto con Trafilatura AI-powered scraping per estrazione intelligente di notizie!**