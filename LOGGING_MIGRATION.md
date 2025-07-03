# 📋 Migrazione Sistema Logging Centralizzato

## 🎯 Obiettivo
Centralizzare e standardizzare il logging dell'applicazione News Vector DB per:
- Configurazione uniforme
- Logger specializzati per aree funzionali
- Migliore debugging e monitoraggio
- Separazione log per ambiente (dev/prod)

## 🏗️ Architettura Nuovo Sistema

### Modulo `src/core/log.py`
- **LoggerManager**: Singleton per gestione centralizzata
- **Factory Functions**: `get_logger()`, `get_news_logger()`, etc.
- **Decoratori**: `@log_function_call`, `@log_performance`
- **Utilities**: Statistiche, flush, context manager

### Configurazione Automatica
- **Ambiente**: Auto-rilevamento da `ENV` variable
- **File Log**: `logs/tanea_{env}.log` + `logs/tanea_errors_{env}.log`
- **Livelli**: DEBUG (dev) / INFO (prod)
- **Rotazione**: 10MB max, 5 backup files
- **Console**: Solo in sviluppo

## 📁 File Modificati

### Core Modules
- ✅ `news_sources.py` → `get_news_logger()`
- ✅ `domain_config.py` → `get_config_logger()`
- ✅ `config.py` → `get_config_logger()`
- ✅ `vector_db_manager.py` → `get_database_logger()`
- ✅ `news_db_manager.py` → `get_database_logger()`
- ✅ `domain_manager.py` → `get_config_logger()`

### Scripts
- ✅ `load_news.py` → `get_scripts_logger()`
- ✅ `example_usage.py` → `get_scripts_logger()`

## 🏷️ Logger Specializzati

| Tipo | Funzione | Uso |
|------|----------|-----|
| **news** | `get_news_logger()` | Ricerca e gestione notizie |
| **database** | `get_database_logger()` | Vector DB, Weaviate |
| **config** | `get_config_logger()` | Configurazione, domini |
| **scripts** | `get_scripts_logger()` | Script di caricamento |

## 📊 Output Log

### Formato Standardizzato
```
2025-07-03 11:19:56 | tanea.news.news_sources | INFO | Trovati 5 articoli da RSS
```

### Struttura Files
```
logs/
├── tanea_dev.log          # Log generale sviluppo
├── tanea_errors_dev.log   # Solo errori sviluppo  
├── tanea_prod.log         # Log generale produzione
└── tanea_errors_prod.log  # Solo errori produzione
```

## 🔧 Utilità Avanzate

### Decoratori
```python
@log_function_call()  # Log ingresso/uscita funzioni
@log_performance()    # Log tempi esecuzione
```

### Context Manager
```python
with temporary_log_level('tanea.news', logging.DEBUG):
    # Temporaneamente più verboso
```

### Statistiche
```python
from core.log import get_logging_stats
stats = get_logging_stats()
print(f"Logger attivi: {stats['total_loggers']}")
```

## ✅ Benefici

1. **Standardizzazione**: Formato uniforme per tutti i log
2. **Specializzazione**: Logger dedicati per aree funzionali
3. **Ambiente-aware**: Configurazione automatica dev/prod
4. **Performance**: Tracking automatico tempi esecuzione
5. **Manutenibilità**: Configurazione centralizzata
6. **Debugging**: Separazione errori e log normale

## 🚀 Utilizzo

### Nei Moduli Esistenti
```python
# Prima
import logging
logger = logging.getLogger(__name__)

# Dopo  
from .log import get_news_logger
logger = get_news_logger(__name__)
```

### Nei Nuovi Moduli
```python
from core.log import get_logger, log_performance

logger = get_logger(__name__)

@log_performance()
def heavy_operation():
    logger.info("Operazione pesante iniziata")
    # ...
    logger.info("Operazione completata")
```

## 🧪 Test
- ✅ Test base logger: `python3 src/test_logging.py`
- ✅ Test integrazione moduli
- ✅ Test decoratori e utilities
- ✅ Test configurazione ambiente

## 📈 Statistiche Migrazione
- **File analizzati**: 14
- **File con logging**: 9  
- **Moduli aggiornati**: 8
- **Logger specializzati**: 4 tipi
- **Decoratori disponibili**: 3

Il sistema di logging è ora centralizzato, standardizzato e pronto per produzione! 🎉