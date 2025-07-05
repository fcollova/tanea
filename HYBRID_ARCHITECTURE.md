# Architettura Ibrida Tanea News System

## Overview

L'architettura ibrida combina **PostgreSQL** per il link management e **Weaviate** per la ricerca semantica, con un crawler **Trafilatura** automatizzato per la raccolta proattiva di contenuti.

## Componenti Principali

### 🗄️ Storage Layer

#### PostgreSQL (Link Management)
- **Tabelle**: `sites`, `discovered_links`, `crawl_attempts`, `extracted_articles`, `crawl_stats`
- **Responsabilità**: 
  - Gestione URL e stati crawling
  - Metadati operativi
  - Statistiche e analytics
  - Scheduling jobs

#### Weaviate (Semantic Search)
- **Collezioni**: `NewsArticles_DEV`, `LinksMetadata_DEV`
- **Responsabilità**:
  - Contenuti articoli con embeddings
  - Ricerca semantica
  - Similarity search
  - RAG context

### 🕷️ Crawler System

#### TrafilaturaCrawler
- **Link Discovery**: Scoperta automatica nuovi link
- **Content Extraction**: Estrazione contenuto con trafilatura
- **Storage Coordination**: Salvataggio PostgreSQL + Weaviate

#### CrawlScheduler
- **Jobs Automatici**: Scheduling crawling e manutenzione
- **Monitoring**: Tracking performance e errori
- **Cleanup**: Pulizia dati obsoleti

### 🔍 News Sources

#### TrafilaturaSourceV2
- **Ricerca Semantica**: Query su contenuti crawlati
- **Auto-Crawl**: Trigger crawling se pochi risultati
- **Compatibility**: Interface compatibile con sistema esistente

## Struttura Directory

```
src/core/
├── storage/
│   ├── link_database.py          # PostgreSQL management
│   ├── vector_collections.py     # Weaviate collections
│   └── database_manager.py       # Coordinator PostgreSQL+Weaviate
├── crawler/
│   ├── link_discoverer.py        # Link discovery
│   ├── content_extractor.py      # Content extraction
│   ├── trafilatura_crawler.py    # Main crawler
│   └── crawl_scheduler.py        # Scheduling & automation
├── news_source_trafilatura_v2.py # V2 news source
└── news_db_manager_v2.py         # V2 main manager
```

## Setup e Configurazione

### 1. Database Setup

```bash
# PostgreSQL
sudo service postgresql start
createdb tanea_news

# Weaviate
docker-compose up weaviate

# Prisma
pip install prisma asyncpg
prisma generate
prisma db push
```

### 2. Configurazione

File `src/config/config.dev.conf`:

```ini
[database]
url = postgresql://postgres:password@localhost:5432/tanea_news
schema = public
pool_size = 5

[crawler]
user_agent = TaneaBot/1.0
rate_limit = 2.0
max_concurrent = 3
timeout = 15

[weaviate]
url = http://localhost:8080
index_name = NewsArticles_DEV
```

### 3. Setup Iniziale

```bash
# Setup automatico
python setup_hybrid_architecture.py

# Test sistema
python test_hybrid_architecture.py
```

## Utilizzo

### Basic Usage

```python
from src.core.news_db_manager_v2 import NewsVectorDBV2

async def main():
    async with NewsVectorDBV2('dev') as news_db:
        # Update dominio calcio
        result = await news_db.update_domain_news("calcio")
        
        # Ricerca semantica
        articles = await news_db.search_news(
            domain="calcio",
            keywords=["Serie A", "Inter"],
            max_results=10
        )
        
        for article in articles:
            print(f"{article['title']} - {article['source']}")
```

### Crawler Management

```python
from src.core.crawler.trafilatura_crawler import TrafilaturaCrawler

async def crawl_domain():
    async with TrafilaturaCrawler('dev') as crawler:
        stats = await crawler.crawl_domain("calcio")
        print(f"Articoli estratti: {stats['articles_extracted']}")
```

### Scheduler Automation

```python
from src.core.crawler.crawl_scheduler import CrawlScheduler

async def setup_automation():
    async with CrawlScheduler('dev') as scheduler:
        # Setup schedule default
        scheduler.setup_default_schedule()
        
        # Run job immediato
        await scheduler.crawl_domain_now("calcio")
        
        # Avvia scheduler
        scheduler.start_scheduler()
```

## Workflow Dati

### 1. Crawling Pipeline

```
Config YAML → Link Discovery → PostgreSQL Storage
     ↓
Content Extraction (Trafilatura) → Weaviate Storage
     ↓
Metadata Update → PostgreSQL → Analytics
```

### 2. Search Pipeline

```
User Query → Semantic Search (Weaviate) → Results Enrichment (PostgreSQL) → Response
```

### 3. Maintenance Pipeline

```
Scheduler → Cleanup Old Data → Sync Databases → Update Stats
```

## Performance Optimizations

### PostgreSQL
- **Indici**: URL hash, status, site_id, date ranges
- **Partitioning**: Per data su tabelle grandi
- **Connection Pooling**: asyncpg con pool size configurabile

### Weaviate
- **Embedding Model**: BERTino multilingue ottimizzato italiano
- **Vector Compression**: ONNX runtime per performance CPU
- **Batch Operations**: Inserimenti e query batch

### Crawler
- **Rate Limiting**: Adattivo per sito
- **Concurrent Limits**: Max 3-5 thread concorrenti
- **Smart Retry**: Exponential backoff
- **Content Deduplication**: SHA256 hash validation

## Monitoring

### Health Checks

```python
async with NewsVectorDBV2('dev') as news_db:
    health = await news_db.db_manager.health_check()
    # {'postgresql': True, 'weaviate': True, 'overall': True}
```

### Statistiche

```python
stats = await news_db.get_system_stats()
# {
#   'database_stats': {...},
#   'domain_stats': {...},
#   'health_check': {...}
# }
```

### Scheduler Status

```python
async with CrawlScheduler('dev') as scheduler:
    status = scheduler.get_scheduler_status()
    history = scheduler.get_job_history()
```

## Troubleshooting

### Errori Comuni

1. **PostgreSQL Connection Error**
   ```bash
   sudo service postgresql start
   # Verifica credenziali in config.dev.conf
   ```

2. **Weaviate Not Available**
   ```bash
   docker-compose up weaviate
   # Verifica URL in config
   ```

3. **Trafilatura Import Error**
   ```bash
   pip install trafilatura
   ```

4. **Prisma Generation Error**
   ```bash
   prisma generate
   prisma db push
   ```

### Performance Issues

- **Slow Crawling**: Riduci `max_concurrent` in config
- **High Memory**: Abilita cleanup automatico più frequente
- **Slow Search**: Verifica indici PostgreSQL e Weaviate embeddings

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Per crawler
crawler_config = {'debug': True}
```

## Migration da V1

La nuova architettura è backward compatible:

```python
# Vecchio sistema
from src.core.news_db_manager import NewsVectorDB

# Nuovo sistema (drop-in replacement)
from src.core.news_db_manager_v2 import NewsVectorDBV2 as NewsVectorDB
```

### Migrazione Graduale

1. **Setup nuovo sistema** parallelamente al vecchio
2. **Sync dati** esistenti con `sync_databases()`
3. **Test** con traffic limitato
4. **Switch** completo quando stabile

## Roadmap

### Prossime Features

- [ ] **Multi-tenancy**: Supporto più progetti
- [ ] **Real-time Updates**: WebSocket notifications
- [ ] **Advanced Analytics**: Trend analysis, sentiment
- [ ] **Content Classification**: ML-powered categorization
- [ ] **API Gateway**: REST/GraphQL interface
- [ ] **Distributed Crawling**: Multi-node crawler cluster

### Optimization Backlog

- [ ] **Query Optimization**: Parallel PostgreSQL+Weaviate queries
- [ ] **Caching Layer**: Redis per frequent queries
- [ ] **Content Deduplication**: Advanced similarity detection
- [ ] **Smart Scheduling**: ML-based optimal crawling times

## Licenza

Questo progetto è parte del sistema Tanea News ed è soggetto alla stessa licenza del progetto principale.