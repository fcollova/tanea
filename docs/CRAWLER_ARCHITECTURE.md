# Architettura del Sistema Crawler Tanea

## 📋 Panoramica

Il sistema crawler di Tanea è un'architettura modulare e scalabile per l'estrazione automatica di contenuti web con filtraggio semantico avanzato. Il sistema combina tecnologie moderne come **Trafilatura** per l'estrazione, **PostgreSQL** per la gestione operativa e **Weaviate** per la ricerca semantica.

## 🏗️ Architettura Generale

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Sources   │───▶│   Crawler Core   │───▶│   Storage Layer │
│  (News Sites)   │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │ Filtering Engine│
                       │ (Multi-Level)   │
                       └─────────────────┘
```

### Componenti Principali

1. **Crawler Core** - Orchestrazione e controllo flusso
2. **Link Discovery** - Scoperta automatica URL articoli
3. **Content Extraction** - Estrazione contenuti con Trafilatura
4. **Keyword Filtering** - Filtraggio multi-livello per rilevanza
5. **Storage Manager** - Persistenza ibrida PostgreSQL + Weaviate
6. **Report Generator** - Reportistica operazioni crawler

## 📁 Struttura del Codice

```
src/crawler/
├── trafilatura_crawler.py          # Orchestratore principale
├── trafilatura_link_discoverer.py  # Discovery automatico link
├── content_extractor.py            # Estrazione contenuti
├── keyword_filter.py               # Algoritmi filtraggio keywords
├── rate_limiter.py                 # Rate limiting avanzato
└── report_generator.py             # Generazione report

src/core/
├── storage/
│   ├── database_manager.py         # Coordinatore storage ibrido
│   ├── link_database.py            # Gestione PostgreSQL
│   └── vector_collections.py       # Gestione Weaviate
├── domain_manager.py               # Gestione domini semantici
└── config.py                       # Sistema configurazione

src/config/
├── domains.yaml                    # Definizione domini e keywords
├── web_crawling.yaml              # Configurazione siti e parametri
├── config.conf                    # Configurazione base
└── config.dev.conf               # Configurazione sviluppo
```

## 🔄 Flusso di Elaborazione

### 1. Inizializzazione
```python
async with TrafilaturaCrawler() as crawler:
    # Carica configurazioni da YAML e config files
    # Inizializza connessioni database (PostgreSQL + Weaviate)
    # Configura rate limiting e SSL
```

### 2. Discovery Links (4 Strategie)
```python
# STRATEGIA 1: Trafilatura Spider (principale)
spider_results = focused_crawler(
    homepage=base_url,                    # Parte da base_url del sito
    max_seen_urls=50,                     # Pagine da visitare
    max_known_urls=150,                   # URL totali mantenuti
    lang='it'                             # Lingua italiana
)
# → Esplorazione automatica intelligente del sito

# STRATEGIA 2: Sitemap Discovery (fallback)
sitemap_urls = sitemap_search(base_url)  # Cerca sitemap.xml
# → URL strutturati dal sito

# STRATEGIA 3: Extraction da pagine categoria (fallback)
category_pages = [f"{base_url}/news/", f"{base_url}/sport/", f"{base_url}/notizie/"]
# → Pagine categoria hardcoded con selectors automatici

# STRATEGIA 4: BeautifulSoup (ultimo resort)
soup.select('a[href*="/news/"], .title a, h2 a, h3 a')
# → Selectors generici hardcoded nel codice
```

### 3. Filtraggio Multi-Livello con Keywords Dominio
```python
# PREPARAZIONE: Carica keywords dominio
domain_config = self.domain_manager.get_domain(domain)
domain_keywords = domain_config.keywords  # Es: ["calcio", "Serie A", "Champions League"]

# LIVELLO 1: Titoli link durante discovery
if keyword_filter.title_matches_keywords(link_title, domain_keywords):
    accept_link()
# → Filtraggio rapido sui titoli dei link trovati

# LIVELLO 2: Pre-filtraggio metadati (PRIMA dell'extraction)
metadata = trafilatura.extract_metadata(html)
if keyword_filter.metadata_matches_keywords(metadata.title, metadata.description, domain_keywords):
    proceed_to_extraction()
else:
    return None  # ← BLOCCA extraction per risparmiare risorse

# LIVELLO 3: Contenuto completo con scoring (DOPO l'extraction)
is_relevant, score = keyword_filter.is_content_relevant(title, content, domain_keywords)
if is_relevant:
    store_article()
else:
    return None  # ← BLOCCA storage articolo non rilevante
```

### 4. Estrazione e Storage
```python
# Estrazione multi-step con Trafilatura
async def extract_article(url: str, domain: str, keywords: List[str]):
    # STEP 1: Fetch HTML con rate limiting
    html = await self._fetch_article_page(url)
    
    # STEP 2: Pre-filtraggio metadati (LIVELLO 2)
    if keywords and not await self._quick_metadata_filter(html, url, keywords):
        return None
    
    # STEP 3: Estrazione Trafilatura
    content = trafilatura.extract(html, config=trafilatura_config)
    metadata = trafilatura.extract_metadata(html)
    
    # STEP 4: Validazione finale (LIVELLO 3)
    if keywords:
        is_relevant, score = keyword_filter.is_content_relevant(title, content, keywords)
        if not is_relevant:
            return None
    
    return article_data

# Storage ibrido coordinato
success = await database_manager.process_crawled_article(link_id, article_data)
# → PostgreSQL: metadati operativi + link tracking
# → Weaviate: contenuto vettoriale per ricerca semantica
```

## 🎯 Sistema di Domini e Configurazione

### Configurazione Domini (`domains.yaml`)
```yaml
domains:
  calcio:
    name: "Calcio"
    active: true
    keywords:
      - "Serie A"
      - "Juventus"
      - "Inter"
      # ... altre keywords
    max_results:
      dev: 5
      prod: 50
```

### Configurazione Crawling Sites (`web_crawling.yaml`)

Il file `web_crawling.yaml` definisce la configurazione operativa del crawler con una struttura gerarchica:

#### Configurazione Generale
```yaml
general:
  rate_limit_delay: 2.0          # Delay tra richieste (secondi)
  timeout: 15                    # Timeout richieste HTTP (secondi)
  max_retries: 3                 # Numero massimo retry per richiesta
  max_concurrent_requests: 5     # Richieste concorrenti massime
  max_links_per_site: 25         # Link massimi per sito per sessione
  min_quality_score: 0.3         # Score minimo qualità Trafilatura
  respect_robots_txt: true       # Rispetta robots.txt
  enable_deduplication: true     # Evita duplicati per URL e contenuto
```

#### Headers HTTP
```yaml
headers:
  User-Agent: "Mozilla/5.0 (compatible; TaneaCrawler/2.0; +https://tanea.news/bot)"
  Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
  Accept-Language: "it-IT,it;q=0.9,en;q=0.8"
```

#### Struttura Domini e Siti
```yaml
crawling_sites:
  calcio:                        # Dominio
    priority: 1                  # Priorità dominio per crawling
    max_articles_per_domain: 100 # Limite articoli per sessione dominio
    
    sites:
      tuttomercatoweb:           # Sito key
        name: "TuttoMercatoWeb"  # Nome display
        base_url: "https://www.tuttomercatoweb.com"  # ← Punto partenza spider
        active: true             # Sito attivo
        priority: 3              # Priorità sito
        rate_limit_override: 2.5 # Override rate limit specifico
        domain: calcio           # ← Assegnazione esplicita dominio
        
        extraction:              # Configurazione estrazione
          content_selectors:
            main: ".news-body, .article-text"  # Selectors contenuto principale
          title_selectors: "h1.news-title"     # Selectors titolo
          author_selectors: ".author"          # Selectors autore
          date_selectors: ".news-date"         # Selectors data
```

#### Domain Mapping e Keywords
```yaml
domain_mapping:
  calcio:
    sites: ["gazzetta", "corriere_sport", "tuttomercatoweb"]
    crawling_keywords: ["calcio", "Serie A", "Champions League", "calciomercato"]
  
  tecnologia:
    sites: ["ansa_tech"]
    crawling_keywords: ["tecnologia", "AI", "software", "hardware"]
```

### Differenza base_url vs discovery_pages

**IMPORTANTE**: Il sistema crawler attuale **utilizza solo `base_url`**:

- **`base_url`**: Punto di partenza per Trafilatura Spider automatico
- **`discovery_pages`**: **NON UTILIZZATE** - erano configurazioni legacy per selectors manuali

**Flusso Discovery Reale**:
1. Spider parte da `base_url` (es: `https://www.tuttomercatoweb.com`)
2. Trafilatura Spider esplora automaticamente il sito
3. **Non utilizza** URLs specifiche come `/serie-a` o `/calciomercato`
4. **Non utilizza** selectors configurati come `"h2 a, .title a"`

### Validazione Rigorosa Domini
- ❌ **Errore** se dominio non esiste in `domains.yaml`
- ❌ **Errore** se dominio non è attivo (`active: false`) in `domains.yaml`
- ❌ **Errore** se sito non ha dominio assegnato in `web_crawling.yaml`
- ❌ **Errore** se dominio del sito non è attivo per crawling
- ✅ **Nessun fallback silenzioso** - tutti i problemi sono espliciti

**Controllo Doppia Attivazione**:
```python
# 1. Dominio deve essere attivo in domains.yaml
if not self.domain_manager.is_domain_active(domain):
    raise ValueError(f"Dominio '{domain}' non attivo in domains.yaml")

# 2. Dominio deve esistere nella configurazione crawling
if domain not in crawling_sites:
    raise ValueError(f"Dominio '{domain}' non configurato per crawling")
```

## 🔍 Algoritmi di Filtraggio Keywords

### Classe KeywordFilter (`keyword_filter.py`)

Il sistema utilizza un filtro multi-livello progressivo con keywords del dominio per massimizzare precision e minimizzare false positive.

#### Livello 1: Titoli Link (Discovery Phase)
```python
def title_matches_keywords(title: str, keywords: List[str]) -> bool:
    # Verifica presenza di almeno una keyword nel titolo del link
    # Case-insensitive matching semplice
    # Utilizzato durante discovery per accettare/rifiutare link
    
    for keyword in keywords:
        if keyword.lower() in title.lower():
            return True  # ← Accetta link per processing
    return False         # ← Rifiuta link
```

**Utilizzo**: Filtraggio rapido durante discovery per ridurre il numero di link da processare.

#### Livello 2: Metadati Pre-Estrazione
```python
def metadata_matches_keywords(title: str, description: str, keywords: List[str]) -> bool:
    # Combina titolo + descrizione dai metadati HTML
    # Filtraggio rapido PRIMA dell'estrazione completa
    # Evita spreco risorse su contenuti non rilevanti
    
    check_text = f"{title} {description}".lower()
    for keyword in keywords:
        if keyword.lower() in check_text:
            return True  # ← Procedi con extraction
    return False         # ← BLOCCA extraction
```

**Utilizzo**: Pre-filtraggio veloce sui metadati HTML prima dell'estrazione Trafilatura completa.

#### Livello 3: Contenuto Completo Post-Estrazione
```python
def calculate_keyword_relevance(title: str, content: str, keywords: List[str]) -> float:
    # Scoring sofisticato multi-dimensionale:
    score = 0.0
    
    for keyword in keywords:
        keyword_score = 0.0
        
        # Peso maggiore per match nel titolo (40%)
        if keyword in title.lower():
            keyword_score += 0.4
        
        # Peso per match nel contenuto (10% * occorrenze, max 30%)
        if keyword in content.lower():
            occurrences = content.lower().count(keyword)
            keyword_score += min(0.3, 0.1 * occurrences)
        
        # Bonus per keywords lunghe/specifiche (+10%)
        if len(keyword.split()) > 2:
            keyword_score += 0.1
        
        score += keyword_score
    
    # Normalizza score realisticamente (max 3.0 → 1.0)
    return min(1.0, score / 3.0)

def is_content_relevant(title: str, content: str, keywords: List[str]) -> tuple[bool, float]:
    # Decisione finale rilevanza con scoring
    score = self.calculate_keyword_relevance(title, content, keywords)
    is_relevant = score >= self.MIN_RELEVANCE_THRESHOLD  # 10%
    return is_relevant, score
```

**Utilizzo**: Validazione finale dopo estrazione completa prima dello storage.

### Parametri di Scoring Configurabili
```python
class KeywordFilter:
    TITLE_WEIGHT = 0.4              # 40% peso per match nel titolo
    CONTENT_WEIGHT = 0.1            # 10% peso base per match contenuto  
    CONTENT_MAX_WEIGHT = 0.3        # 30% peso massimo per contenuto
    LONG_KEYWORD_BONUS = 0.1        # 10% bonus per keywords > 2 parole
    MIN_RELEVANCE_THRESHOLD = 0.1   # 10% soglia minima rilevanza
    MAX_REALISTIC_SCORE = 3.0       # Score massimo per normalizzazione
```

### Flusso Completo Filtraggio
```python
# 1. DISCOVERY: Filtra link sui titoli
discovered_links = []
for link in all_links:
    if keyword_filter.title_matches_keywords(link.title, domain_keywords):
        discovered_links.append(link)

# 2. PRE-EXTRACTION: Filtra sui metadati
for link in discovered_links:
    html = fetch_page(link.url)
    metadata = extract_metadata(html)
    
    if keyword_filter.metadata_matches_keywords(metadata.title, metadata.description, domain_keywords):
        # 3. EXTRACTION: Estrai contenuto
        content = trafilatura.extract(html)
        
        # 4. FINAL VALIDATION: Scoring completo
        is_relevant, score = keyword_filter.is_content_relevant(
            metadata.title, content, domain_keywords
        )
        
        if is_relevant:
            store_article(content, score)  # ← Storage finale
        else:
            logger.debug(f"Articolo non rilevante (score: {score:.2f})")
    else:
        logger.debug("Metadati non rilevanti, skip extraction")
```

### Ottimizzazioni Specifiche Domini
- **Calcio**: 22 keywords specifiche, soglia 8% (ottimizzata)
- **Tecnologia**: Keywords tecniche, peso extra per termini lunghi
- **Finanza**: Keywords economiche, focus su terminologia specifica

## ⚙️ Configurazione Parametri e Impatti

### Parametri Globali (`web_crawling.yaml` - `general`)

| Parametro | Valore Default | Impatto Discovery | Impatto Extraction | Note |
|-----------|----------------|-------------------|---------------------|------|
| `rate_limit_delay` | 2.0s | ⚡ **ALTO** - Controlla velocità discovery | ⚡ **ALTO** - Controlla velocità fetch articoli | Valori bassi = più veloce ma rischio ban |
| `timeout` | 15s | 🔹 **MEDIO** - Timeout per fetch pagine discovery | 🔹 **MEDIO** - Timeout per fetch articoli | Valori alti = più resilienza, valori bassi = più veloce |
| `max_retries` | 3 | 🔹 **MEDIO** - Retry su errori discovery | 🔹 **MEDIO** - Retry su errori extraction | Aumenta resilienza ma rallenta in caso errori |
| `max_concurrent_requests` | 5 | ⚡ **ALTO** - Parallelismo discovery | ⚡ **ALTO** - Parallelismo extraction | Valori alti = più veloce ma maggior carico server |
| `max_links_per_site` | 25 | 🔴 **CRITICO** - Limite link scoperti | ❌ **NESSUNO** - Non influenza extraction | Controlla volume totale crawling |
| `min_quality_score` | 0.3 | ❌ **NESSUNO** - Non influenza discovery | 🔹 **MEDIO** - Filtra articoli estratti | Score Trafilatura 0.0-1.0 |
| `respect_robots_txt` | true | 🔹 **MEDIO** - Può limitare discovery | ❌ **NESSUNO** - Non influenza extraction | Compliance legale |
| `enable_deduplication` | true | 🔸 **BASSO** - Cache URL discovery | 🔹 **MEDIO** - Evita articoli duplicati | Migliora efficienza |

### Parametri Spider Trafilatura (`trafilatura_link_discoverer.py`)

| Parametro | Valore Default | Impatto Discovery | Descrizione |
|-----------|----------------|-------------------|-------------|
| `spider_max_depth` | 2 | 🔴 **CRITICO** | Profondità esplorazione sito (max livelli link) |
| `spider_max_pages` | 50 | 🔴 **CRITICO** | Pagine massime visitate per sito |
| `spider_max_known_urls` | 150 | 🔹 **MEDIO** | URL totali mantenuti in memoria spider |
| `spider_language` | 'it' | 🔸 **BASSO** | Lingua per ottimizzazione spider |

### Parametri Keywords Filtering (`keyword_filter.py`)

| Parametro | Valore Default | Impatto Discovery | Impatto Extraction | Descrizione |
|-----------|----------------|-------------------|---------------------|-------------|
| `TITLE_WEIGHT` | 0.4 (40%) | 🔹 **MEDIO** - Filtra link sui titoli | 🔴 **CRITICO** - Peso titolo nello scoring | Match nel titolo ha peso maggiore |
| `CONTENT_WEIGHT` | 0.1 (10%) | ❌ **NESSUNO** | 🔴 **CRITICO** - Peso base contenuto | Peso per ogni occorrenza keyword |
| `CONTENT_MAX_WEIGHT` | 0.3 (30%) | ❌ **NESSUNO** | 🔹 **MEDIO** - Limite peso contenuto | Evita spam keywords |
| `LONG_KEYWORD_BONUS` | 0.1 (10%) | 🔸 **BASSO** | 🔹 **MEDIO** - Bonus keywords specifiche | Keywords > 2 parole ottengono bonus |
| `MIN_RELEVANCE_THRESHOLD` | 0.1 (10%) | ❌ **NESSUNO** | 🔴 **CRITICO** - Soglia accettazione | Score minimo per storage articolo |

### Parametri Sito-Specifici (`web_crawling.yaml` - per sito)

| Parametro | Esempio | Impatto Discovery | Impatto Extraction | Note |
|-----------|---------|-------------------|---------------------|------|
| `active` | true/false | 🔴 **CRITICO** - Skip completo se false | 🔴 **CRITICO** - Skip completo se false | Abilita/disabilita sito |
| `priority` | 1-5 | 🔸 **BASSO** - Ordine processing | ❌ **NESSUNO** | Ordine elaborazione siti |
| `rate_limit_override` | 2.5s | ⚡ **ALTO** - Rate limit specifico sito | ⚡ **ALTO** - Rate limit specifico sito | Override globale per siti lenti |
| `base_url` | "https://..." | 🔴 **CRITICO** - Punto partenza spider | ❌ **NESSUNO** | Homepage per discovery |
| `domain` | "calcio" | ❌ **NESSUNO** - Solo validazione | 🔴 **CRITICO** - Carica keywords dominio | Assegnazione semantica |

### Parametri Estrazione (`web_crawling.yaml` - `extraction`)

| Parametro | Esempio | Impatto Extraction | Descrizione |
|-----------|---------|---------------------|-------------|
| `content_selectors.main` | ".news-body, .article-text" | 🔹 **MEDIO** | Selectors CSS per contenuto principale |
| `content_selectors.fallback` | ".content, .text" | 🔸 **BASSO** | Selectors fallback se main fallisce |
| `title_selectors` | "h1.news-title" | 🔹 **MEDIO** | Selectors per titolo articolo |
| `author_selectors` | ".author" | 🔸 **BASSO** | Selectors per autore (metadati) |
| `date_selectors` | ".news-date" | 🔸 **BASSO** | Selectors per data pubblicazione |

### Parametri Trafilatura (`content_extractor.py`)

| Parametro | Valore Default | Impatto Extraction | Descrizione |
|-----------|----------------|---------------------|-------------|
| `MIN_EXTRACTED_SIZE` | 200 caratteri | 🔹 **MEDIO** | Lunghezza minima contenuto estratto |
| `MAX_OUTPUT_SIZE` | 50000 caratteri | 🔸 **BASSO** | Lunghezza massima contenuto |
| `FAVOR_PRECISION` | True | 🔹 **MEDIO** | Privilegia precisione su completezza |
| `INCLUDE_COMMENTS` | False | 🔸 **BASSO** | Esclude commenti dal contenuto |
| `INCLUDE_TABLES` | True | 🔸 **BASSO** | Include tabelle (utile per sport/stats) |
| `INCLUDE_FORMATTING` | True | 🔸 **BASSO** | Mantiene formattazione base |

### Matrice Impatti per Tuning Performance

| Obiettivo | Parametri da Modificare | Effetto |
|-----------|-------------------------|---------|
| **🚀 Velocità Discovery** | ↓ `rate_limit_delay`, ↑ `max_concurrent_requests`, ↓ `max_links_per_site` | Più veloce ma maggior carico server |
| **🎯 Qualità Contenuti** | ↑ `min_quality_score`, ↑ `MIN_RELEVANCE_THRESHOLD`, ↑ `TITLE_WEIGHT` | Meno articoli ma più rilevanti |
| **📊 Volume Crawling** | ↑ `max_links_per_site`, ↑ `spider_max_pages`, ↓ `MIN_RELEVANCE_THRESHOLD` | Più articoli ma qualità variabile |
| **⚡ Resilienza Errori** | ↑ `max_retries`, ↑ `timeout`, ↑ `rate_limit_delay` | Più lento ma più robusto |
| **🔍 Precisione Keywords** | ↑ `TITLE_WEIGHT`, ↓ `CONTENT_MAX_WEIGHT`, ↑ `LONG_KEYWORD_BONUS` | Focus su keywords nel titolo |

### Configurazioni Ambiente

| Ambiente | Discovery | Extraction | Keywords | Note |
|----------|-----------|------------|----------|------|
| **Development** | `max_links_per_site: 5`, `spider_max_pages: 10` | `min_quality_score: 0.2` | `MIN_RELEVANCE_THRESHOLD: 0.08` | Veloce per testing |
| **Staging** | `max_links_per_site: 15`, `spider_max_pages: 30` | `min_quality_score: 0.25` | `MIN_RELEVANCE_THRESHOLD: 0.09` | Bilanciato |
| **Production** | `max_links_per_site: 25`, `spider_max_pages: 50` | `min_quality_score: 0.3` | `MIN_RELEVANCE_THRESHOLD: 0.1` | Qualità massima |

### Impatti Combinati - Esempi Pratici

#### Scenario 1: Crawling Veloce (Testing)
```yaml
general:
  rate_limit_delay: 0.5          # ↓ Veloce
  max_concurrent_requests: 8     # ↑ Parallelo
  max_links_per_site: 5          # ↓ Limitato
  min_quality_score: 0.2         # ↓ Permissivo

# Risultato: ~2-3 minuti per dominio, 5-15 articoli
```

#### Scenario 2: Crawling Qualità (Production)
```yaml
general:
  rate_limit_delay: 2.0          # Standard
  max_concurrent_requests: 3     # ↓ Conservativo  
  max_links_per_site: 50         # ↑ Esteso
  min_quality_score: 0.4         # ↑ Selettivo

keyword_filter:
  MIN_RELEVANCE_THRESHOLD: 0.12  # ↑ Rigoroso
  TITLE_WEIGHT: 0.5              # ↑ Focus titolo

# Risultato: ~10-15 minuti per dominio, 20-40 articoli alta qualità
```

#### Scenario 3: Crawling Volume (Ricerca)
```yaml
general:
  max_links_per_site: 100        # ↑ Alto volume
  min_quality_score: 0.25        # ↓ Permissivo

spider:
  spider_max_pages: 80           # ↑ Esplorazione estesa
  
keyword_filter:
  MIN_RELEVANCE_THRESHOLD: 0.08  # ↓ Inclusivo

# Risultato: ~20-30 minuti per dominio, 50-100 articoli
```

## 💾 Architettura Storage Ibrida

### PostgreSQL (Operazionale)
```sql
-- Gestione siti e link
Sites, DiscoveredLinks, CrawlAttempts

-- Metadati articoli
ExtractedArticles (title, author, quality_score, keywords)

-- Statistiche operative
CrawlStats (daily aggregations)
```

### Weaviate (Semantico)
```python
# Collezioni per ricerca semantica
NewsArticles_DEV/PROD {
    title, content, url, source, domain,
    published_date, quality_score, keywords,
    link_id  # ← Collegamento con PostgreSQL
}
```

### Coordinazione DatabaseManager
```python
async def process_crawled_article(link_id: str, article_data: Dict):
    # 1. Verifica link in PostgreSQL
    # 2. Calcola hash per duplicati
    # 3. Salva articolo in Weaviate (con embedding)
    # 4. Salva metadati in PostgreSQL
    # 5. Aggiorna stato link
    # → Transazione coordinata tra i due database
```

## 📊 Sistema di Reporting

### Report Multi-Formato
- **CSV**: Preferito per analisi dati
- **JSON**: Strutturato per integrazione API
- **PDF**: Executive summary senza dettagli siti
- **Excel**: Backup formato tabellare

### Contenuto Report
```python
# Discovery Report
{
    "session_info": {...},
    "sites_processed": [...],
    "links_summary": {
        "total_discovered": 150,
        "valid_articles": 75,
        "filtered_out": 60,
        "duplicates": 15
    },
    "domain_breakdown": {...}
}

# Crawl Report  
{
    "crawl_summary": {...},
    "articles_extracted": 45,
    "quality_metrics": {...},
    "performance_stats": {...}
}
```

## ⚙️ Configurazione SSL e Rate Limiting

### SSL Configuration
```ini
[crawler]
verify_ssl = false  # Sviluppo
verify_ssl = true   # Produzione (default)
```

### Rate Limiting Avanzato
```python
class AdvancedRateLimiter:
    # Rate limiting per dominio
    # Backoff esponenziale per errori
    # Rispetto robots.txt
    # Gestione 429 (Too Many Requests)
```

## 🚀 Modalità di Esecuzione

### Crawling Completo
```bash
./run_crawler.sh --crawl --domain calcio
```

### Discovery Only
```bash
./run_crawler.sh --discover --site tuttomercatoweb
```

### Parametri Configurabili
- `--max-links N`: Limita link per sito
- `--domain NOME`: Filtra per dominio specifico
- `--site NOME`: Crawla singolo sito

## 📈 Monitoraggio e Statistiche

### Metriche Operative
- Links scoperti vs articoli estratti
- Tasso successo estrazione
- Score qualità medio contenuti
- Performance rate limiting

### Validazioni Salute Sistema
```python
# Health check database
health = await database_manager.health_check()
# {"postgresql": true, "weaviate": true, "overall": true}

# Sync controllo integrità
sync_stats = await database_manager.sync_databases()
# Identifica inconsistenze PostgreSQL ↔ Weaviate
```

## 🔧 Estendibilità

### Aggiungere Nuovo Dominio
1. Aggiungere in `domains.yaml`:
```yaml
tecnologia:
  name: "Tecnologia"
  active: true
  keywords: ["AI", "machine learning", ...]
```

2. Configurare siti in `web_crawling.yaml`:
```yaml
tecnologia:
  sites:
    nuovo_sito:
      domain: tecnologia
```

### Aggiungere Nuovo Algoritmo Filtraggio
```python
# In keyword_filter.py
def semantic_similarity_filter(content: str, domain_embeddings: List[float]) -> float:
    # Implementa filtraggio basato su similarità vettoriale
    pass
```

## 🛡️ Sicurezza e Compliance

### Rispetto robots.txt
- Parsing automatico robots.txt per ogni dominio
- Cache 24h per robots.txt
- Rispetto `Crawl-delay` e `User-agent` restrictions

### User-Agent Responsabile
```
TaneaBot/1.0 (+https://tanea.local/bot)
```

### Rate Limiting Adaptive
- Default: 0.5 RPS per dominio
- Backoff automatico su errori 429/503
- Rispetto header `Retry-After`

## 📚 Dipendenze Principali

- **trafilatura**: Estrazione contenuti web
- **aiohttp**: Client HTTP asincrono
- **beautifulsoup4**: Parsing HTML fallback
- **prisma**: ORM PostgreSQL
- **weaviate-client**: Vector database
- **fastembed**: Embeddings multilingue
- **pyyaml**: Configurazione YAML
- **pandas**: Elaborazione dati report
- **reportlab**: Generazione PDF

---

## 📞 Note per Sviluppatori

### Debug Configuration
```python
# Abilita debug filtraggio
keyword_filter = KeywordFilter(debug=True)

# Logging dettagliato
export LOG_LEVEL=DEBUG
```

### Common Issues
1. **Dominio "general"**: Verificare mapping in `web_crawling.yaml`
2. **SSL Warnings**: Controllare `verify_ssl` in config
3. **Rate Limiting**: Verificare `robots.txt` del sito target
4. **Weaviate Connection**: Controllare servizio e porte

### Performance Tips
- Utilizzare `max_links_per_site` per limitare scope
- Configurare `batch_size` appropriato per la banda
- Monitorare memoria per siti con molti link
- Usare filtraggio precoce per ridurre processing

---

---

## 📋 Riepilogo Configurazioni

### File di Configurazione Chiave

1. **`domains.yaml`**: Definisce domini semantici e keywords
   - Domini attivi/inattivi per l'intero sistema
   - Keywords specifiche per filtraggio contenuti
   - Limiti risultati per ambiente (dev/prod)

2. **`web_crawling.yaml`**: Configurazione operativa crawler
   - Parametri tecnici (rate limiting, timeout, retry)
   - Headers HTTP per richieste
   - Struttura domini → siti con `base_url`
   - Selectors per estrazione contenuti (utilizzati)
   - ~~Discovery pages~~ (rimossi - non utilizzati)

3. **`config.conf` / `config.dev.conf`**: Configurazione base sistema
   - Connessioni database
   - SSL settings
   - Logging levels

### Flusso Configurazione → Execution

```
domains.yaml ──┐
               ├──→ Validazione Domini ──→ Keywords Loading
web_crawling.yaml ─┘                    │
                                        ▼
config.conf ────────→ Technical Setup → Crawler Execution
                                        │
                                        ▼
                              Discovery (base_url only)
                                        │
                                        ▼
                              Extraction (selectors used)
                                        │
                                        ▼
                               Storage (PostgreSQL + Weaviate)
```

### Controlli Validazione Pre-Crawling

1. **Dominio deve esistere** in `domains.yaml`
2. **Dominio deve essere attivo** (`active: true`) in `domains.yaml`  
3. **Sito deve avere `base_url`** in `web_crawling.yaml`
4. **Sito deve avere `domain` assignment** in `web_crawling.yaml`
5. **Sito deve essere attivo** (`active: true`) in `web_crawling.yaml`

**Fallimento di qualsiasi controllo → ERROR esplicito, nessun fallback silenzioso**

## 🗂️ Gestione Database e Strumenti di Pulizia

### Script di Pulizia Database

Il sistema include strumenti completi per la gestione e pulizia dei database:

#### Script Bash Principale (`clean_db.sh`)
```bash
./clean_db.sh
```

**Menu Opzioni**:
- `1` - 🔍 Verifica stato database
- `2` - 🧹 Menu completo interattivo  
- `3` - 🚀 Reset rapido completo
- `4` - 📋 Lista collezioni Weaviate
- `5` - 🗑️ Elimina collezione specifica
- `0` - ❌ Annulla

#### Script Python Dedicati

**Script Principale** (`clean_databases.py`):
```bash
python3 scripts/clean_databases.py  # Menu interattivo completo
```

**Script Specializzati**:
```bash
python3 scripts/list_collections.py      # Lista collezioni Weaviate
python3 scripts/delete_collection.py     # Elimina collezione specifica
python3 scripts/quick_reset.py          # Reset rapido completo
```

### Gestione Collezioni Weaviate

#### Architettura Indici per Dominio
Ogni dominio ha il proprio indice Weaviate isolato:
```
Tanea_Calcio_DEV        → articoli dominio calcio
Tanea_Tecnologia_DEV    → articoli dominio tecnologia  
Tanea_General_DEV       → articoli dominio general
```

#### Lista Collezioni
Visualizza tutte le collezioni con statistiche:
```
📊 Stato attuale Weaviate:
   • Collezioni Tanea: 2
   • Altre collezioni: 2

🎯 Collezioni Tanea:
    1. Tanea_Calcio_DEV: 95 documenti (dominio: calcio)
    2. Tanea_General_DEV: 0 documenti (dominio: unknown)

📋 Altre collezioni:  
    3. LinksMetadata_DEV: 0 documenti
    4. NewsArticles_DEV: 210 documenti
```

#### Eliminazione Granulare
**Vantaggi gestione per collezione singola**:
- ✅ Mantiene altre collezioni intatte
- ✅ Utile per test e correzioni mirate  
- ✅ Evita reset completo quando non necessario
- ✅ Numerazione unificata per selezione intuitiva

**Procedura Sicura**:
1. 📋 Mostra lista collezioni numerata
2. 🎯 Seleziona numero collezione
3. ⚠️ Conferma con `DELETE` (case-sensitive)
4. 🗑️ Eliminazione irreversibile

### Database PostgreSQL
**Gestione automatica**:
- Reset sequenze auto-increment (`Site_id_seq`, `DiscoveredLink_id_seq`)
- Pulizia tabelle `Site` e `DiscoveredLink`
- Verifica integrità connessioni

### Procedure di Manutenzione
- **Verifica stato**: Controlla connettività e conteggi
- **Reset completo**: PostgreSQL + Weaviate + creazione schemi
- **Pulizia selettiva**: Solo PostgreSQL o solo Weaviate
- **Resource cleanup**: Chiusura corretta tutte le connessioni

---

*Documentazione aggiornata il: 22 Luglio 2025*  
*Versione Crawler: 2.1*  
*Architettura: Modulare Multi-Livello con Storage Ibrido Domain-Separated e Strumenti Avanzati di Gestione Database*