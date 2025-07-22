# 📚 Documentazione Tanea

Documentazione completa del sistema di web crawling e analisi intelligente Tanea.

## 📖 Guide Principali

### 🏗️ [CRAWLER_ARCHITECTURE.md](CRAWLER_ARCHITECTURE.md)
**Architettura e Design del Sistema**
- Architettura modulare multi-livello
- Configurazione domini e siti
- Parametri e tuning performance
- Flussi di elaborazione
- Validazione e controlli

### 🚀 [CRAWLER_USAGE.md](CRAWLER_USAGE.md) 
**Guida Utilizzo Crawler**
- Comandi e parametri
- Esempi pratici
- Modalità operative
- Monitoraggio e logging

### 📡 [CRAWLER_API.md](CRAWLER_API.md)
**API e Interfacce Programmatiche**  
- Endpoints disponibili
- Interfacce REST
- SDK e client libraries
- Esempi integrazione

## 🗂️ Gestione Sistema

### 🗂️ [CACHE_CENTRALIZATION.md](CACHE_CENTRALIZATION.md)
**Centralizzazione Cache Modelli Embedding**
- Problema cache duplicata BERTino
- Soluzione centralizzata
- Configurazione path assoluti
- Ottimizzazione storage

## 🗂️ Gestione Database

### 🔧 [DATABASE_CLEANUP.md](DATABASE_CLEANUP.md)
**Guida Completa Strumenti Database**
- Procedure pulizia database
- Menu interattivi e script
- Gestione collezioni Weaviate  
- Operazioni sicure e backup
- Troubleshooting comuni

### 💻 [README_DATABASE_SCRIPTS.md](README_DATABASE_SCRIPTS.md)
**Documentazione Tecnica Script Database**
- Architettura classe DatabaseCleaner
- API reference script
- Resource management
- Note sviluppatori
- Debugging e profiling

## 🎯 Guide per Ruolo

### 👩‍💻 **Sviluppatori**
1. [CRAWLER_ARCHITECTURE.md](CRAWLER_ARCHITECTURE.md) - Comprendi l'architettura
2. [README_DATABASE_SCRIPTS.md](README_DATABASE_SCRIPTS.md) - API e script tecnici
3. [CRAWLER_API.md](CRAWLER_API.md) - Interfacce programmatiche
4. [CACHE_CENTRALIZATION.md](CACHE_CENTRALIZATION.md) - Gestione cache embeddings

### 🔧 **System Administrators** 
1. [DATABASE_CLEANUP.md](DATABASE_CLEANUP.md) - Gestione e manutenzione
2. [CRAWLER_USAGE.md](CRAWLER_USAGE.md) - Operazioni routine
3. [CRAWLER_ARCHITECTURE.md](CRAWLER_ARCHITECTURE.md) - Configurazioni avanzate
4. [CACHE_CENTRALIZATION.md](CACHE_CENTRALIZATION.md) - Ottimizzazione storage

### 👤 **End Users**
1. [CRAWLER_USAGE.md](CRAWLER_USAGE.md) - Come usare il sistema
2. [DATABASE_CLEANUP.md](DATABASE_CLEANUP.md) - Operazioni base pulizia

## 🔗 Collegamenti Rapidi

### Configurazioni
- **Domini**: [`../src/config/domains.yaml`](../src/config/domains.yaml)
- **Siti Web**: [`../src/config/web_crawling.yaml`](../src/config/web_crawling.yaml)  
- **Globali**: [`../src/config/config.conf`](../src/config/config.conf)

### Script Utili
- **Pulizia DB**: [`../clean_db.sh`](../clean_db.sh)
- **Script Python**: [`../scripts/`](../scripts/)
- **Weaviate Explorer**: [`../src/weaviate_navigator/`](../src/weaviate_navigator/)

### Componenti Core
- **Crawler**: [`../src/crawler/trafilatura_crawler.py`](../src/crawler/trafilatura_crawler.py)
- **Domain Manager**: [`../src/core/domain_manager.py`](../src/core/domain_manager.py)
- **Vector DB**: [`../src/core/vector_db_manager.py`](../src/core/vector_db_manager.py)

## 📋 Indice per Argomento

### Architettura e Design
- [Architettura Generale](CRAWLER_ARCHITECTURE.md#architettura-generale)
- [Storage Ibrido](CRAWLER_ARCHITECTURE.md#storage-ibrido) 
- [Multi-Domain](CRAWLER_ARCHITECTURE.md#gestione-multi-dominio)
- [Patterns Utilizzati](CRAWLER_ARCHITECTURE.md#pattern-architetturali)

### Configurazione
- [Configurazione Domini](CRAWLER_ARCHITECTURE.md#configurazione-domini)
- [Configurazione Siti](CRAWLER_ARCHITECTURE.md#configurazione-siti)
- [Parametri Performance](CRAWLER_ARCHITECTURE.md#parametri-performance)
- [Keywords e Filtering](CRAWLER_ARCHITECTURE.md#keyword-filtering)
- [Cache Centralizzazione](CACHE_CENTRALIZATION.md#configurazione-centralizzata)

### Operazioni Database
- [Pulizia Completa](DATABASE_CLEANUP.md#pulizia-completa)
- [Gestione Collezioni](DATABASE_CLEANUP.md#gestione-collezioni-weaviate)
- [Script Automatici](README_DATABASE_SCRIPTS.md#script-principali)
- [Resource Management](README_DATABASE_SCRIPTS.md#gestione-connessioni)

### API e Integrazione  
- [REST Endpoints](CRAWLER_API.md#endpoints)
- [SDK Usage](CRAWLER_API.md#sdk)
- [Client Examples](CRAWLER_API.md#esempi)
- [Authentication](CRAWLER_API.md#autenticazione)

### Troubleshooting
- [Database Issues](DATABASE_CLEANUP.md#troubleshooting)
- [Connection Problems](README_DATABASE_SCRIPTS.md#troubleshooting)
- [Performance Tuning](CRAWLER_ARCHITECTURE.md#performance-tuning)
- [Error Handling](CRAWLER_USAGE.md#error-handling)

## 🆘 Quick Help

**Problema comune?** Consulta prima:
1. [DATABASE_CLEANUP.md - Troubleshooting](DATABASE_CLEANUP.md#troubleshooting)
2. [CRAWLER_USAGE.md - FAQ](CRAWLER_USAGE.md#faq) 

**Non trovi qualcosa?** 
- Usa la ricerca nel repository
- Controlla il [README principale](../README.md)
- Consulta i commenti nel codice sorgente

---

*Documentazione Tanea v2.1*  
*Ultima modifica: 22 Luglio 2025*