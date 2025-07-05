# Moduli Crawler Tanea

Documentazione per i due moduli separati di crawling e caricamento news.

## 🕷️ Modulo 1: Crawler Executor (`crawler_exec.py`)

**Scopo**: Modulo autonomo per eseguire operazioni di crawling utilizzando la configurazione in `web_crawling.yaml`

### Funzionalità
- Discovery di link da nodi padre configurati
- Crawling completo con estrazione contenuto
- Filtering per domini (da `domains.yaml`) e siti specifici
- Configurazione autonoma e logging integrato

### Utilizzo

```bash
# Mostra configurazione domini e siti
python src/scripts/crawler_exec.py --config

# Mostra siti disponibili per crawling
python src/scripts/crawler_exec.py --sites

# Discovery link (senza estrazione)
python src/scripts/crawler_exec.py --discover
python src/scripts/crawler_exec.py --discover --domain calcio
python src/scripts/crawler_exec.py --discover --site gazzetta ansa

# Crawling completo (discovery + extraction + storage)
python src/scripts/crawler_exec.py --crawl
python src/scripts/crawler_exec.py --crawl --domain calcio
python src/scripts/crawler_exec.py --crawl --site gazzetta --max-links 30
python src/scripts/crawler_exec.py --crawl --domain calcio tecnologia --verbose
```

### Parametri

**Operazioni principali:**
- `--config`: Mostra configurazione corrente
- `--sites`: Lista siti disponibili  
- `--discover`: Solo discovery link
- `--crawl`: Crawling completo

**Filtri:**
- `--domain DOMAIN [DOMAIN...]`: Filtra per domini da `domains.yaml`
- `--site SITE [SITE...]`: Filtra per siti da `web_scraping.yaml`
- `--max-links N`: Limite link per sito (default: 50)

**Output:**
- `--verbose, -v`: Output dettagliato
- `--quiet, -q`: Output minimo

### Configurazione

Il modulo utilizza il **sistema unificato**:
1. **`config.conf`**: Configurazioni comuni crawler
2. **`config.dev.conf`**: Parametri ambiente (rate limits, etc.)
3. **`web_crawling.yaml`**: Nodi padre e configurazione dettagliata
4. **`domains.yaml`**: Domini sistema (condiviso)

### Logica Domini - VERSIONE CORRETTA

Il crawler usa **validazione domini centralizzata**:
- Domini devono essere ATTIVI SOLO in `domains.yaml` (gestiti da `DomainManager`)
- `web_crawling.yaml` contiene solo mapping domini → siti e configurazione link
- Solo i domini attivi in `domains.yaml` vengono processati per crawling

---

## 📰 Modulo 2: News Loader (`news_loader.py`) 

**Scopo**: Caricamento news nel database Weaviate tramite Trafilatura mantenendo coerenza con domini esistenti

### Funzionalità
- Caricamento news per domini specifici
- Integrazione con `NewsVectorDBV2` e sistema esistente
- Ricerca in database esistente
- Statistiche e pulizia database
- Coerenza totale con `domains.yaml`

### Utilizzo

```bash
# Mostra configurazione domini e news
python src/scripts/news_loader.py --config

# Statistiche database
python src/scripts/news_loader.py --stats

# Carica dominio specifico
python src/scripts/news_loader.py --domain calcio
python src/scripts/news_loader.py --domain calcio --max-results 30 --force

# Carica multipli domini
python src/scripts/news_loader.py --domains calcio tecnologia
python src/scripts/news_loader.py --domains calcio tecnologia --time-range 1w

# Cerca news esistenti
python src/scripts/news_loader.py --search calcio "Serie A" "Inter"
python src/scripts/news_loader.py --search tecnologia "AI" "machine learning"

# Pulizia database
python src/scripts/news_loader.py --cleanup 7
python src/scripts/news_loader.py --cleanup 30 --verbose
```

### Parametri

**Operazioni principali:**
- `--config`: Configurazione domini e news
- `--stats`: Statistiche database
- `--domain DOMAIN`: Carica dominio specifico
- `--domains DOMAIN [DOMAIN...]`: Carica multipli domini
- `--search DOMAIN KEYWORD [KEYWORD...]`: Cerca news esistenti
- `--cleanup DAYS`: Pulisci articoli vecchi

**Parametri caricamento:**
- `--max-results N`: Max risultati per dominio (default: 50)
- `--time-range {1d,1w,1m}`: Range temporale (default: 1d)
- `--force`: Forza aggiornamento anche se recente

**Output:**
- `--verbose, -v`: Output dettagliato  
- `--quiet, -q`: Output minimo

### Integrazione Sistema

Il modulo si integra con:
1. **`domains.yaml`**: Legge domini attivi e keywords
2. **`NewsVectorDBV2`**: Sistema database migliorato
3. **`TrafilaturaSourceV2`**: Fonte news AI-powered
4. **Sistema logging**: Usa `log.py` per logging coerente

---

## 🔧 Configurazione

### File di Configurazione

#### 1. `domains.yaml` (Domini)
```yaml
domains:
  calcio:
    name: "Calcio"
    active: true
    keywords: ["calcio", "Serie A", "Champions League"]
    priority: 1
    max_results:
      dev: 50
      prod: 100
```

#### 2. `web_crawling.yaml` (Mapping e Link Crawling) - VERSIONE CORRETTA
```yaml
general:
  rate_limit_delay: 2.0
  timeout: 15
  max_links_per_site: 25
  min_quality_score: 0.3

crawling_sites:
  calcio:                        # Mapping dominio (definito in domains.yaml)
    priority: 1                  # Solo priorità e parametri tecnici
    max_articles_per_domain: 100
    
    sites:
      gazzetta:                  # Sito
        name: "Gazzetta dello Sport"
        base_url: "https://www.gazzetta.it"
        active: true             # Sito attivo
        priority: 1
        
        discovery_pages:         # Nodi padre
          calcio_generale:
            url: "https://www.gazzetta.it/Calcio/"
            active: true         # Page attiva
            selectors:
              article_links: "h2 a[href*='/calcio/']"
            max_links: 15
            
        extraction:              # Parametri estrazione
          content_selectors:
            main: "article .article-body"
          title_selectors: "h1"

# Mapping domini → siti (come web_scraping.yaml)
domain_mapping:
  calcio:
    sites: ["gazzetta", "corriere_sport", "tuttomercatoweb"]
    crawling_keywords: ["calcio", "Serie A", "Champions League"]
```

#### 3. `config.dev.conf` (Database e Sistema)
```ini
[database]
postgresql_url = postgresql://tanea_user:pass@localhost:5432/tanea_news
weaviate_url = http://localhost:8080

[crawler]
rate_limit_delay = 1.5
max_concurrent_requests = 5
```

---

## 🔄 Workflow Tipico

### 1. Setup Iniziale
```bash
# Verifica configurazione
python src/scripts/crawler_exec.py --config
python src/scripts/news_loader.py --config
```

### 2. Discovery e Crawling
```bash
# Discovery link per dominio
python src/scripts/crawler_exec.py --discover --domain calcio

# Crawling completo
python src/scripts/crawler_exec.py --crawl --domain calcio --verbose
```

### 3. Caricamento Database
```bash
# Carica news nel database
python src/scripts/news_loader.py --domain calcio --max-results 50

# Verifica risultati
python src/scripts/news_loader.py --stats
```

### 4. Ricerca e Manutenzione
```bash
# Cerca contenuti
python src/scripts/news_loader.py --search calcio "Juventus" "Inter"

# Pulizia periodica
python src/scripts/news_loader.py --cleanup 30
```

---

## 🎯 Vantaggi Architettura

### Separazione Responsabilità
- **`crawler_exec.py`**: Focus su crawling e discovery
- **`news_loader.py`**: Focus su database e integrazione sistema

### Coerenza Configurazione - VERSIONE CORRETTA
- Utilizza `log.py` e `config.py` esistenti
- Rispetta `domains.yaml` come UNICA fonte per definizioni domini
- Domini gestiti esclusivamente tramite `DomainManager` (core modules)
- `web_crawling.yaml` solo per mapping e configurazione link
- Pattern coerente con `web_scraping.yaml`

### Modularità
- Ogni modulo può funzionare indipendentemente
- Integrazione trasparente con sistema esistente
- Logging e error handling unificati

### Flessibilità
- Command line options specifiche per ogni uso
- Filtering avanzato per domini e siti
- Output configurabile (verbose/quiet)

---

## 📝 Esempi Avanzati

### Crawling Selettivo
```bash
# Solo siti sportivi per dominio calcio
python src/scripts/crawler_exec.py --crawl --domain calcio --site gazzetta corriere_sport

# Discovery multipli domini, verbose
python src/scripts/crawler_exec.py --discover --domain calcio tecnologia --verbose
```

### Caricamento Strategico
```bash
# Caricamento force per aggiornamento immediato
python src/scripts/news_loader.py --domain calcio --force --max-results 100

# Caricamento multiplo con range temporale esteso
python src/scripts/news_loader.py --domains calcio tecnologia finanza --time-range 1w
```

### Monitoraggio e Manutenzione
```bash
# Statistiche dettagliate
python src/scripts/news_loader.py --stats --verbose

# Pulizia conservativa
python src/scripts/news_loader.py --cleanup 14 --verbose

# Ricerca specifica
python src/scripts/news_loader.py --search tecnologia "AI" "artificial intelligence" --max-results 20
```

---

## 📝 **AGGIORNAMENTO FINALE - Correzioni Applicate**

### **Problema Risolto**
❌ **Prima**: Gestione domini duplicata tra `web_crawling.yaml` e `domains.yaml`
❌ **Prima**: `domain_active` definito in `web_crawling.yaml`  
❌ **Prima**: Logica domini mista e non coerente

### **Soluzione Implementata** 
✅ **Dopo**: Domini definiti ESCLUSIVAMENTE in `domains.yaml`
✅ **Dopo**: `web_crawling.yaml` gestisce solo mapping domini → siti
✅ **Dopo**: `DomainManager` unico punto di accesso per operazioni domini
✅ **Dopo**: Coerenza totale con `web_scraping.yaml` e architettura esistente

### **Benefici**
- 🎯 **Coerenza architettonica**: Pattern uniforme in tutto il sistema
- 🔧 **Manutenibilità**: Un solo posto per gestire domini  
- 🚀 **Semplicità**: Logica domini centralizzata
- 🛡️ **Robustezza**: Core modules testati e affidabili

**🎉 Sistema ora completamente allineato alle specifiche utente e funzionante!** ✅