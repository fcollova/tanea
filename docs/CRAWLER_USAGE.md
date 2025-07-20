# Guida Utente Sistema Crawler Tanea

## 🚀 Quick Start

### Requisiti Preliminari
```bash
# Assicurarsi che i servizi siano attivi
docker-compose up weaviate postgres  # Se usando Docker
# oppure servizi locali su porte standard

# Verificare configurazione
python3 -c "from src.core.config import get_config; print('✅ Config OK')"
```

### Primo Crawling
```bash
# Crawling completo dominio calcio (configurazione default)
./run_crawler.sh --crawl --domain calcio

# Alternativa: discovery + crawl separati
./run_crawler.sh --discover --domain calcio
./run_crawler.sh --crawl --domain calcio
```

## 📋 Comandi Disponibili

### Discovery Links
```bash
# Scopri link per tutti i siti attivi
./run_crawler.sh --discover

# Scopri link per dominio specifico
./run_crawler.sh --discover --domain calcio

# Scopri link per singolo sito
./run_crawler.sh --discover --site tuttomercatoweb

# Limita numero link per sito
./run_crawler.sh --discover --domain calcio --max-links 10
```

### Crawling Contenuti
```bash
# Crawla tutti i contenuti scoperti
./run_crawler.sh --crawl

# Crawla solo dominio specifico
./run_crawler.sh --crawl --domain calcio

# Crawla singolo sito
./run_crawler.sh --crawl --site tuttomercatoweb

# Crawla con limite articoli
./run_crawler.sh --crawl --domain calcio --max-links 25
```

### Operazioni Combinate
```bash
# Discovery + Crawling in una sola operazione
./run_crawler.sh --crawl --domain calcio --max-links 20

# Modalità completa (tutti i domini attivi)
./run_crawler.sh --crawl
```

## ⚙️ Configurazione

### File di Configurazione

#### `src/config/domains.yaml`
```yaml
domains:
  calcio:
    name: "Calcio"
    active: true                    # Abilita/disabilita dominio
    keywords:
      - "Serie A"
      - "Juventus"
      - "Inter"
      # Aggiungi keywords specifiche del dominio
    max_results:
      dev: 5                       # Limite per sviluppo
      prod: 50                     # Limite per produzione
```

#### `src/config/web_crawling.yaml`
```yaml
crawling_sites:
  calcio:                          # Dominio di appartenenza
    sites:
      nuovo_sito:
        name: "Nome Sito"
        base_url: "https://sito.com"
        active: true               # Abilita/disabilita sito
        domain: calcio             # Assegnazione esplicita dominio
        priority: 1                # Priorità crawling (1=alta)
        
        discovery_pages:           # Pagine per discovery link
          categoria:
            url: "https://sito.com/categoria"
            active: true
            max_links: 15
```

#### `src/config/config.dev.conf`
```ini
[crawler]
rate_limit = 2.0                  # Delay tra richieste (secondi)
max_concurrent = 3                # Richieste concorrenti massime
timeout = 15                      # Timeout richieste HTTP
verify_ssl = false               # SSL verification (dev: false, prod: true)

[web_crawling]
max_links_per_site = 25          # Limite default link per sito
min_quality_score = 0.3          # Score minimo qualità contenuto
spider_max_pages = 100           # Limite spider Trafilatura
```

### Gestione Domini

#### Attivare/Disattivare Domini
```yaml
# In domains.yaml
tecnologia:
  active: false    # Disattiva dominio tecnologia
  
calcio:
  active: true     # Mantieni attivo dominio calcio
```

#### Aggiungere Nuovo Dominio
```yaml
# 1. Definire in domains.yaml
sport_motor:
  name: "Sport Motoristici"
  active: true
  keywords:
    - "Formula 1"
    - "MotoGP"
    - "Ferrari"
    - "Verstappen"
  max_results:
    dev: 3
    prod: 25

# 2. Configurare siti in web_crawling.yaml
sport_motor:
  sites:
    gazzetta_motor:
      name: "Gazzetta Motor"
      base_url: "https://gazzetta.it/motor"
      domain: sport_motor
      active: true
```

#### Gestire Keywords
```yaml
# Keywords efficaci per il filtraggio
calcio:
  keywords:
    # Teams specifici
    - "Juventus"
    - "Inter"
    
    # Competizioni
    - "Serie A"
    - "Champions League"
    
    # Termini tecnici
    - "calciomercato"
    - "gol"
    
    # Keywords composte (bonus scoring)
    - "campionato italiano"    # +10% bonus per keywords lunghe
    - "risultati Serie A"
```

## 📊 Monitoring e Report

### Report Automatici
```bash
# I report vengono generati automaticamente in:
logs/crawler_report/

# Formati disponibili:
- discovery_YYYYMMDD_HHMMSS.csv    # Preferito per analisi
- discovery_YYYYMMDD_HHMMSS.json   # Per integrazione API
- discovery_YYYYMMDD_HHMMSS.pdf    # Executive summary

# Configurazione report in config.dev.conf:
[logging]
report_formats = csv,json,pdf       # Formati da generare
report_cleanup_days = 7             # Giorni di retention report
```

### Monitoraggio Real-time
```bash
# Log in tempo reale
tail -f logs/crawler.log

# Filtro per errori
tail -f logs/crawler.log | grep ERROR

# Statistiche filtraggio
tail -f logs/crawler.log | grep "FILTER\|Score rilevanza"
```

### Metriche Chiave
- **Links Discovered**: Totale link trovati
- **Valid Articles**: Link che passano validazione URL
- **Filtered by Title**: Scartati nel filtraggio livello 1
- **Filtered by Metadata**: Scartati nel filtraggio livello 2  
- **Filtered by Content**: Scartati nel filtraggio livello 3
- **Articles Stored**: Salvati con successo in Weaviate

## 🔧 Troubleshooting

### Problemi Comuni

#### 1. "Nessun dominio trovato per sito"
```bash
# ERRORE: Dominio non configurato per sito 'nome_sito'
# SOLUZIONE: Verificare web_crawling.yaml

# Controllo configurazione
python3 -c "
from src.crawler.trafilatura_crawler import TrafilaturaCrawler
import asyncio

async def check():
    async with TrafilaturaCrawler() as crawler:
        sites = crawler._get_sites_to_crawl()
        for name, config in sites.items():
            try:
                domain = crawler._determine_domain_for_site(config)
                print(f'✅ {name}: {domain}')
            except Exception as e:
                print(f'❌ {name}: {e}')

asyncio.run(check())
"
```

#### 2. "SSL Warning" o "InsecureRequestWarning"
```ini
# In config.dev.conf
[crawler]
verify_ssl = false    # Per sviluppo locale

# Per produzione mantenere:
verify_ssl = true
```

#### 3. "Filtrati 0 link rilevanti"
```yaml
# Verificare keywords in domains.yaml
calcio:
  keywords:
    # Assicurarsi che le keywords siano presenti nei titoli
    # Keywords troppo specifiche = pochi match
    # Keywords troppo generiche = troppi match
    
    # BUONE:
    - "Serie A"        # Specifica e comune
    - "Juventus"       # Team popolare
    
    # EVITARE:
    - "gol della vittoria al 90esimo minuto"  # Troppo specifica
```

#### 4. Rate Limiting o Errori 429
```ini
# In config.dev.conf - aumentare delay
[crawler]
rate_limit = 3.0              # Da 2.0 a 3.0 secondi
max_concurrent = 2            # Da 3 a 2 richieste concorrenti

# Verificare robots.txt del sito:
curl https://sito.com/robots.txt
```

#### 5. Weaviate Connection Error
```bash
# Verificare servizio Weaviate
curl http://localhost:8080/v1/meta

# In config.dev.conf verificare:
[weaviate]
url = http://localhost:8080
```

### Debug Mode

#### Abilita Debug Filtraggio
```python
# In crawler_exec.py o test script
from crawler.keyword_filter import KeywordFilter

# Crea filtro con debug
filter_debug = KeywordFilter(debug=True)

# Output dettagliato:
# [FILTER L1] ✅ Keyword 'Juventus' trovata in titolo
# [FILTER L2] ❌ Keywords NON trovate nei metadati
# [FILTER L3] Score finale: 0.533 (raw: 1.600)
```

#### Log Level Debug
```bash
# Ambiente con debug completo
export LOG_LEVEL=DEBUG
./run_crawler.sh --discover --domain calcio
```

## 📈 Ottimizzazione Performance

### Tuning Rate Limiting
```ini
# Per siti veloci (buona banda, server potenti)
[crawler]
rate_limit = 1.0
max_concurrent = 5

# Per siti lenti o con rate limiting severo
[crawler]
rate_limit = 5.0
max_concurrent = 1
```

### Memoria e Performance
```bash
# Limita scope per ridurre utilizzo memoria
./run_crawler.sh --crawl --domain calcio --max-links 10

# Monitor utilizzo memoria
htop
# Cercare processi python3

# Se memoria elevata:
# 1. Ridurre max_links_per_site
# 2. Ridurre spider_max_pages  
# 3. Aumentare rate_limit (meno concorrenza)
```

### Batch Processing
```yaml
# In web_crawling.yaml - ottimizza batch size
general:
  max_concurrent_requests: 3       # Per server limitati
  # max_concurrent_requests: 8     # Per server potenti
```

## 🔍 Analisi Risultati

### Query Database Utili

#### PostgreSQL
```sql
-- Statistiche recenti
SELECT 
    s.name as site_name,
    COUNT(dl.id) as total_links,
    COUNT(ea.id) as articles_extracted,
    AVG(ea.quality_score) as avg_quality
FROM sites s
LEFT JOIN discovered_links dl ON s.id = dl.site_id
LEFT JOIN extracted_articles ea ON dl.id = ea.link_id
WHERE dl.discovered_at > NOW() - INTERVAL '24 hours'
GROUP BY s.name;

-- Link per stato
SELECT status, COUNT(*) 
FROM discovered_links 
WHERE discovered_at > NOW() - INTERVAL '24 hours'
GROUP BY status;
```

#### Weaviate (tramite API)
```python
# Ricerca articoli per dominio
from src.core.storage.database_manager import DatabaseManager

async with DatabaseManager() as db:
    articles = await db.search_articles(
        query="Juventus Inter",
        domain="calcio", 
        limit=10
    )
    for article in articles:
        print(f"Score: {article['score']:.3f} - {article['title']}")
```

### Report Analysis
```python
# Analisi CSV report
import pandas as pd

df = pd.read_csv('logs/crawler_report/discovery_20250707_143000.csv')

# Efficacia filtraggio per sito
efficiency = df.groupby('site_name').agg({
    'links_discovered': 'sum',
    'valid_articles': 'sum',
    'filtered_by_keywords': 'sum'
}).eval('efficiency = valid_articles / links_discovered * 100')

print(efficiency.sort_values('efficiency', ascending=False))
```

## 🎯 Best Practices

### Configurazione Domini
1. **Keywords Bilanciate**: Non troppo specifiche, non troppo generiche
2. **Test Incrementale**: Iniziare con poche keywords, espandere gradualmente
3. **Monitoraggio Efficacia**: Verificare ratio link_scoperti/articoli_salvati

### Gestione Siti
1. **Priorità Chiare**: Siti principali priority=1, secondari priority=2+
2. **Rate Limiting Rispettoso**: Rispettare robots.txt e limitazioni server
3. **Monitoraggio Errori**: Disattivare temporaneamente siti problematici

### Maintenance
1. **Cleanup Periodico**: I report vengono puliti automaticamente
2. **Monitoraggio Spazio**: Database PostgreSQL e Weaviate crescono nel tempo
3. **Update Keywords**: Aggiornare keywords basandosi sui risultati di ricerca

---

## 📞 Supporto

### Log Files
- `logs/crawler.log` - Log principale operazioni
- `logs/crawler_report/` - Report dettagliati per sessione
- Console output durante esecuzione

### Health Check
```python
# Verifica salute sistema
from src.core.storage.database_manager import DatabaseManager
import asyncio

async def health():
    async with DatabaseManager() as db:
        health = await db.health_check()
        print(f"PostgreSQL: {health['postgresql']}")
        print(f"Weaviate: {health['weaviate']}")
        print(f"Overall: {health['overall']}")

asyncio.run(health())
```

### Configuration Validation
```python
# Valida configurazione domini
from src.core.domain_manager import DomainManager

dm = DomainManager()
if dm.validate_domain_config():
    print("✅ Configurazione domini valida")
else:
    print("❌ Errori in configurazione domini")
```

---

*Guida aggiornata al: 7 Luglio 2025*  
*Per issue e richieste di feature: aprire ticket nel repository*