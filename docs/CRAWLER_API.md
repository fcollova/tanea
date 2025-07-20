# API Reference - Sistema Crawler Tanea

## 📚 Panoramica API

Il sistema crawler espone API programmatiche per integrazioni custom e automazione avanzata. Tutte le API sono asincrone e utilizzano context manager per gestione risorse.

## 🏗️ Componenti Principali

### TrafilaturaCrawler - Orchestratore

```python
from crawler.trafilatura_crawler import TrafilaturaCrawler

async with TrafilaturaCrawler(environment='dev') as crawler:
    # Tutte le operazioni crawler
    pass
```

#### Metodi Pubblici

##### `crawl_all_sites()`
```python
async def crawl_all_sites(
    site_names: List[str] = None,
    domain_filter: str = None, 
    max_links_per_site: int = None
) -> Dict[str, Any]:
    """
    Crawla tutti i siti configurati
    
    Args:
        site_names: Lista nomi siti specifici (None = tutti)
        domain_filter: Filtra solo siti per questo dominio  
        max_links_per_site: Limite massimo link per sito
        
    Returns:
        dict: Statistiche crawling {
            'sites_processed': int,
            'links_discovered': int,
            'links_crawled': int,
            'articles_extracted': int,
            'errors': int,
            'start_time': datetime,
            'end_time': datetime
        }
    """
```

**Esempio:**
```python
# Crawling completo dominio calcio
stats = await crawler.crawl_all_sites(
    domain_filter='calcio',
    max_links_per_site=25
)
print(f"Articoli estratti: {stats['articles_extracted']}")
```

##### `crawl_domain()`
```python
async def crawl_domain(
    domain: str, 
    max_articles: int = 50,
    max_links_per_site: int = None
) -> Dict[str, Any]:
    """Crawla solo siti di un dominio specifico"""
```

##### `crawl_site()`
```python
async def crawl_site(site_name: str) -> Dict[str, Any]:
    """Crawla un singolo sito specifico"""
```

##### `get_crawl_statistics()`
```python
def get_crawl_statistics() -> Dict[str, Any]:
    """
    Returns:
        dict: {
            'crawl_stats': {...},
            'discovery': {...},
            'extraction': {...},
            'rate_limiting': {...}
        }
    """
```

---

### TrafilaturaLinkDiscoverer - Discovery

```python
from crawler.trafilatura_link_discoverer import TrafilaturaLinkDiscoverer

async with TrafilaturaLinkDiscoverer() as discoverer:
    links = await discoverer.discover_site_links(site_config)
```

#### Metodi Pubblici

##### `discover_site_links()`
```python
async def discover_site_links(site_config: Dict) -> List[str]:
    """
    Scopre link usando strategie multiple
    
    Args:
        site_config: Configurazione sito da web_crawling.yaml
        
    Returns:
        list: Lista URL articoli scoperti
        
    Strategie utilizzate:
        1. Trafilatura Spider (principale)
        2. Sitemap Discovery (fallback)  
        3. Extraction da pagine categoria
        4. BeautifulSoup (ultimo resort)
    """
```

**Esempio:**
```python
site_config = {
    'name': 'TuttoMercatoWeb',
    'base_url': 'https://www.tuttomercatoweb.com',
    'domain': 'calcio',
    'active': True
}

links = await discoverer.discover_site_links(site_config)
print(f"Link scoperti: {len(links)}")
```

##### `get_discovery_stats()`
```python
def get_discovery_stats() -> Dict[str, int]:
    """
    Returns:
        dict: {
            'total_discovered': int,
            'spider_max_depth': int, 
            'spider_max_pages': int
        }
    """
```

---

### ContentExtractor - Estrazione

```python
from crawler.content_extractor import ContentExtractor

async with ContentExtractor() as extractor:
    article = await extractor.extract_article(url, domain, keywords)
```

#### Metodi Pubblici

##### `extract_article()`
```python
async def extract_article(
    url: str,
    domain: str = "general",
    keywords: List[str] = None
) -> Optional[Dict]:
    """
    Estrae contenuto articolo da URL con filtraggio multi-livello
    
    Args:
        url: URL articolo da estrarre
        domain: Dominio di appartenenza (calcio, tecnologia, etc.)
        keywords: Keywords per validazione rilevanza
        
    Returns:
        dict o None: {
            'title': str,
            'content': str,
            'url': str,
            'published_date': datetime,
            'author': str,
            'source': str,
            'domain': str,
            'quality_score': float,
            'keywords': List[str],
            'metadata': dict
        }
    """
```

**Esempio:**
```python
from core.domain_manager import DomainManager

dm = DomainManager()
keywords = dm.get_keywords('calcio')

article = await extractor.extract_article(
    url='https://www.tuttomercatoweb.com/articolo-123',
    domain='calcio',
    keywords=keywords
)

if article:
    print(f"Titolo: {article['title']}")
    print(f"Score qualità: {article['quality_score']:.2f}")
```

##### `batch_extract_articles()`
```python
async def batch_extract_articles(
    urls: List[str],
    domain: str = "general",
    keywords: List[str] = None,
    max_concurrent: int = 3
) -> List[Dict]:
    """Estrae articoli in batch con concorrenza limitata"""
```

##### `get_extraction_stats()`
```python
def get_extraction_stats() -> Dict[str, Any]:
    """
    Returns:
        dict: {
            'total_attempts': int,
            'successful_extractions': int,
            'failed_extractions': int,
            'success_rate': float,
            'avg_content_length': float
        }
    """
```

---

### KeywordFilter - Filtraggio

```python
from crawler.keyword_filter import KeywordFilter, create_domain_filter

# Filtro generico
filter = KeywordFilter(debug=True)

# Filtro ottimizzato per dominio  
filter = create_domain_filter(keywords=['Serie A', 'Juventus'], debug=False)
```

#### Metodi Pubblici

##### `title_matches_keywords()`
```python
def title_matches_keywords(title: str, keywords: List[str]) -> bool:
    """
    LIVELLO 1: Verifica se il titolo contiene keywords del dominio
    
    Args:
        title: Titolo del link/articolo
        keywords: Keywords del dominio da cercare
        
    Returns:
        bool: True se il titolo contiene almeno una keyword
    """
```

##### `metadata_matches_keywords()`
```python
def metadata_matches_keywords(
    title: str, 
    description: str, 
    keywords: List[str]
) -> bool:
    """
    LIVELLO 2: Pre-filtraggio sui metadati (titolo + descrizione)
    """
```

##### `calculate_keyword_relevance()`
```python
def calculate_keyword_relevance(
    title: str, 
    content: str, 
    keywords: List[str]
) -> float:
    """
    LIVELLO 3: Calcola score di rilevanza basato sulle keywords
    
    Returns:
        float: Score da 0.0 a 1.0 che indica rilevanza per il dominio
        
    Algoritmo:
        - Peso titolo: 40%
        - Peso contenuto: 10-30% (basato su occorrenze)
        - Bonus keywords lunghe: +10%
        - Normalizzazione: score / 3.0 (score massimo realistico)
    """
```

##### `is_content_relevant()`
```python
def is_content_relevant(
    title: str,
    content: str, 
    keywords: List[str],
    threshold: float = None
) -> tuple[bool, float]:
    """
    Verifica completa di rilevanza contenuto
    
    Returns:
        tuple: (is_relevant: bool, score: float)
    """
```

**Esempio:**
```python
keywords = ['Serie A', 'Juventus', 'Inter']

# Test singolo
is_relevant, score = filter.is_content_relevant(
    title="Juventus batte l'Inter 2-1",
    content="Nel big match di Serie A...",
    keywords=keywords
)
print(f"Rilevante: {is_relevant}, Score: {score:.3f}")

# Test configurazione
stats = filter.get_filter_stats()
print(f"Soglia: {stats['min_threshold']}")
```

##### Configurazione Avanzata
```python
# Modifica soglie e pesi
filter.update_thresholds(
    title_weight=0.5,          # Aumenta peso titolo a 50%
    min_threshold=0.15,        # Soglia più restrittiva
    content_max_weight=0.4     # Max peso contenuto a 40%
)
```

---

### DatabaseManager - Storage Ibrido

```python
from core.storage.database_manager import DatabaseManager

async with DatabaseManager(environment='dev') as db:
    success = await db.process_crawled_article(link_id, article_data)
```

#### Metodi Pubblici

##### `process_crawled_article()`
```python
async def process_crawled_article(
    link_id: str, 
    article_data: Dict[str, Any]
) -> bool:
    """
    Processa articolo crawlato: salva in Weaviate + aggiorna PostgreSQL
    
    Args:
        link_id: ID del link in PostgreSQL
        article_data: Dati articolo estratto da trafilatura
        
    Returns:
        bool: True se successo, False altrimenti
        
    Operazioni:
        1. Verifica link esiste in PostgreSQL
        2. Calcola hash contenuto per duplicati
        3. Salva articolo in Weaviate (con embedding)
        4. Salva metadati in PostgreSQL  
        5. Marca link come crawlato
    """
```

##### `search_articles()`
```python
async def search_articles(
    query: str,
    domain: str = None,
    limit: int = 10,
    include_metadata: bool = True
) -> List[Dict[str, Any]]:
    """
    Ricerca articoli con metadati enriched
    
    Args:
        query: Query di ricerca semantica
        domain: Filtra per dominio
        limit: Numero massimo risultati
        include_metadata: Include metadati da PostgreSQL
        
    Returns:
        list: Lista articoli con metadati completi da entrambi DB
    """
```

**Esempio:**
```python
# Ricerca semantica
articles = await db.search_articles(
    query="Juventus campionato",
    domain="calcio",
    limit=5
)

for article in articles:
    print(f"Score: {article['score']:.3f}")
    print(f"Titolo: {article['title']}")
    print(f"Sito: {article['site_name']}")
```

##### `get_unified_stats()`
```python
async def get_unified_stats() -> Dict[str, Any]:
    """
    Statistiche unificate entrambi database
    
    Returns:
        dict: {
            'postgresql': {...},
            'weaviate': {...},
            'environment': str,
            'last_updated': str
        }
    """
```

##### `health_check()`
```python
async def health_check() -> Dict[str, bool]:
    """
    Verifica salute entrambi database
    
    Returns:
        dict: {
            'postgresql': bool,
            'weaviate': bool,
            'overall': bool
        }
    """
```

##### `sync_databases()`
```python
async def sync_databases() -> Dict[str, Any]:
    """
    Sincronizza dati tra PostgreSQL e Weaviate
    Identifica e risolve inconsistenze
    
    Returns:
        dict: {
            'orphaned_weaviate': int,
            'missing_weaviate': int, 
            'fixed_inconsistencies': int
        }
    """
```

---

### DomainManager - Gestione Domini

```python
from core.domain_manager import DomainManager

dm = DomainManager()  # Carica automaticamente domains.yaml
```

#### Metodi Pubblici

##### `get_domain()`
```python
def get_domain(domain_id: str) -> Optional[DomainConfig]:
    """Ottiene la configurazione di un dominio"""
```

##### `get_keywords()`
```python
def get_keywords(domain_id: str) -> List[str]:
    """
    Ottiene le keywords di un dominio
    
    Returns:
        list: Lista delle keywords o lista vuota se dominio non trovato
    """
```

##### `is_domain_active()`
```python
def is_domain_active(domain_id: str) -> bool:
    """Verifica se un dominio è attivo"""
```

##### `get_active_domains()`
```python
def get_active_domains() -> Dict[str, DomainConfig]:
    """Ottiene solo i domini attivi"""
```

**Esempio:**
```python
# Verifica domini
active_domains = dm.get_active_domains()
print(f"Domini attivi: {list(active_domains.keys())}")

# Keywords per dominio
calcio_keywords = dm.get_keywords('calcio')
print(f"Keywords calcio: {len(calcio_keywords)}")

# Validazione
if dm.validate_domain_config():
    print("✅ Configurazione domini valida")
```

---

## 🔧 Utility Functions

### Report Generator
```python
from crawler.report_generator import ReportGenerator

# Inizializza con configurazione
report_gen = ReportGenerator()

# Genera report discovery
report_files = report_gen.generate_discovery_report(
    results={
        'sites_processed': ['tuttomercatoweb'],
        'total_links_discovered': 45,
        'valid_article_links': 30,
        'filtered_links': 15
    },
    operation_type="discovery"
)

# Genera report crawling  
report_files = report_gen.generate_crawl_report(
    results={
        'articles_extracted': 25,
        'failed_extractions': 5,
        'avg_quality_score': 0.75
    },
    operation_type="crawl"
)
```

### Configuration Access
```python
from core.config import (
    get_crawler_config,
    get_web_crawling_config, 
    get_weaviate_config,
    get_database_config
)

# Configurazioni specifiche
crawler_config = get_crawler_config()
ssl_verify = crawler_config['verify_ssl']

crawling_config = get_web_crawling_config()
max_links = crawling_config['max_links_per_site']
```

---

## 📊 Esempi di Integrazione

### Crawling Programmato
```python
import asyncio
from datetime import datetime
from crawler.trafilatura_crawler import TrafilaturaCrawler

async def daily_crawling():
    """Crawling giornaliero automatico"""
    
    async with TrafilaturaCrawler() as crawler:
        # Crawling mattutino - focus calcio
        morning_stats = await crawler.crawl_domain(
            domain='calcio', 
            max_links_per_site=20
        )
        
        print(f"Mattino: {morning_stats['articles_extracted']} articoli")
        
        # Evening crawling - tutti i domini
        if datetime.now().hour >= 18:
            evening_stats = await crawler.crawl_all_sites(
                max_links_per_site=10
            )
            print(f"Sera: {evening_stats['articles_extracted']} articoli")

# Esecuzione
asyncio.run(daily_crawling())
```

### Ricerca e Analisi
```python
async def content_analysis():
    """Analisi contenuti estratti"""
    
    from core.storage.database_manager import DatabaseManager
    
    async with DatabaseManager() as db:
        # Ricerca articoli recenti
        recent_articles = await db.search_articles(
            query="calciomercato gennaio",
            domain="calcio",
            limit=20
        )
        
        # Analisi qualità
        quality_scores = [a['quality_score'] for a in recent_articles]
        avg_quality = sum(quality_scores) / len(quality_scores)
        
        print(f"Qualità media: {avg_quality:.3f}")
        
        # Top articoli per score rilevanza
        top_articles = sorted(
            recent_articles, 
            key=lambda x: x['score'], 
            reverse=True
        )[:5]
        
        print("\nTop 5 articoli per rilevanza:")
        for i, article in enumerate(top_articles, 1):
            print(f"{i}. {article['title'][:60]}... (Score: {article['score']:.3f})")

asyncio.run(content_analysis())
```

### Custom Filtering
```python
async def custom_keyword_filtering():
    """Filtraggio personalizzato con keywords custom"""
    
    from crawler.keyword_filter import create_domain_filter
    from crawler.content_extractor import ContentExtractor
    
    # Keywords custom per eventi specifici
    event_keywords = [
        "calciomercato gennaio", 
        "trasferimenti invernali",
        "sessione invernale"
    ]
    
    # Filtro ottimizzato
    custom_filter = create_domain_filter(event_keywords, debug=True)
    
    async with ContentExtractor() as extractor:
        # Test URLs
        test_urls = [
            "https://www.tuttomercatoweb.com/mercato-123",
            "https://www.tuttomercatoweb.com/risultati-456"
        ]
        
        relevant_articles = []
        
        for url in test_urls:
            article = await extractor.extract_article(
                url=url,
                domain='calcio', 
                keywords=event_keywords
            )
            
            if article:
                is_relevant, score = custom_filter.is_content_relevant(
                    article['title'],
                    article['content'], 
                    event_keywords
                )
                
                if is_relevant:
                    relevant_articles.append({
                        'article': article,
                        'relevance_score': score
                    })
        
        print(f"Articoli rilevanti trovati: {len(relevant_articles)}")

asyncio.run(custom_keyword_filtering())
```

---

## 🚨 Error Handling

### Gestione Eccezioni
```python
from crawler.trafilatura_crawler import TrafilaturaCrawler

async def robust_crawling():
    try:
        async with TrafilaturaCrawler() as crawler:
            stats = await crawler.crawl_all_sites(domain_filter='calcio')
            
    except ValueError as e:
        # Errori di configurazione (domini non trovati, etc.)
        print(f"Errore configurazione: {e}")
        
    except ConnectionError as e:
        # Errori di connessione database
        print(f"Errore connessione: {e}")
        
    except Exception as e:
        # Altri errori
        print(f"Errore generico: {e}")
```

### Validation Helpers
```python
# Validazione configurazione
from core.domain_manager import DomainManager

dm = DomainManager()
if not dm.validate_domain_config():
    print("❌ Configurazione domini non valida")
    exit(1)

# Health check database
from core.storage.database_manager import DatabaseManager

async with DatabaseManager() as db:
    health = await db.health_check()
    if not health['overall']:
        print(f"❌ Database non disponibili: {health}")
        exit(1)
```

---

## 📈 Performance Monitoring

### Metriche Real-time
```python
import time
from crawler.trafilatura_crawler import TrafilaturaCrawler

async def performance_monitoring():
    start_time = time.time()
    
    async with TrafilaturaCrawler() as crawler:
        # Crawling con monitoring
        stats = await crawler.crawl_domain('calcio', max_links_per_site=50)
        
        # Calcola metriche
        duration = time.time() - start_time
        articles_per_second = stats['articles_extracted'] / duration
        
        print(f"Performance Report:")
        print(f"Durata: {duration:.1f}s")
        print(f"Articoli/secondo: {articles_per_second:.2f}")
        print(f"Tasso successo: {stats['articles_extracted'] / stats['links_crawled'] * 100:.1f}%")
        
        # Statistiche dettagliate componenti
        detailed_stats = crawler.get_crawl_statistics()
        print(f"Rate limiting stats: {detailed_stats['rate_limiting']}")

asyncio.run(performance_monitoring())
```

---

*API Reference aggiornata al: 7 Luglio 2025*  
*Per esempi aggiuntivi e troubleshooting: consultare CRAWLER_USAGE.md*