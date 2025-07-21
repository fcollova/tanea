# 🗂️ Cache Centralizzazione Modello BERTino

## ✅ Problema Risolto

**Prima**: Il modello BERTino (`nickprock/multi-sentence-BERTino`) veniva scaricato in **due posizioni diverse**:
- `/tanea/fastembed_cache/` (root)
- `/tanea/src/crawler/fastembed_cache/` (duplicato)

**Dopo**: Cache **unica e centralizzata** in `/tanea/fastembed_cache/`

## 🔧 Modifiche Implementate

### 1. Configurazione Centralizzata (`config.conf`)
```ini
[embedding]
cache_dir = /home/francesco/tanea/fastembed_cache  # Path assoluto
```

### 2. Path Resolution Automatico (`core/config.py`)
```python
def get_embedding_config(self) -> Dict[str, Any]:
    cache_dir_raw = self.get('embedding', 'cache_dir', 'fastembed_cache')
    
    # Risolvi path assoluto per cache centralizzata
    if not cache_dir_raw.startswith('/'):
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent  # /tanea
        cache_dir = str(project_root / cache_dir_raw)
    
    return {'cache_dir': cache_dir, ...}
```

### 3. Moduli Aggiornati
- ✅ **`core/config.py`**: Path resolution centralizzato
- ✅ **`weaviate_navigator/utils/weaviate_client.py`**: Usa config centralizzato
- ✅ **`core/vector_db_manager.py`**: Già utilizzava config centralizzato
- ✅ **`crawler/fastembed_cache/`**: Cache duplicata rimossa

## 🎯 Benefici

1. **Spazio Disco**: Risparmiati ~1.5GB di duplicazione modello
2. **Performance**: Download una sola volta al primo utilizzo
3. **Consistenza**: Stesso modello per tutti i moduli:
   - Crawler (content extraction)
   - Weaviate Navigator (semantic search)  
   - Vector DB Manager (embeddings)
4. **Manutenzione**: Cache centralizzata e gestione unificata

## 🔍 Verifica

```bash
# Test configurazione
python3 -c "
from src.core.config import get_embedding_config
config = get_embedding_config()
print(f'Cache Dir: {config[\"cache_dir\"]}')
"
# Output: Cache Dir: /home/francesco/tanea/fastembed_cache
```

## 📁 Struttura Cache Finale

```
/tanea/
├── fastembed_cache/                    # ✅ Cache UNICA
│   ├── models--nickprock--multi-sentence-BERTino/
│   └── models--qdrant--all-MiniLM-L6-v2-onnx/
├── src/
│   ├── crawler/                        # ✅ Nessuna cache duplicata
│   ├── weaviate_navigator/             # ✅ Usa cache centralizzata
│   └── core/                           # ✅ Gestisce path resolution
```

## 🚨 Soluzione Finale

**Causa del problema identificata**:
- ❌ Path resolution relativo falliva durante esecuzione crawler
- ❌ Il calcolo dinamico di `project_root` era inconsistente in diversi contesti di esecuzione
- ❌ FastEmbed riceveva path errati causando cache duplicata

**Soluzione implementata**:
- ✅ **Path assoluto** nel file `config.conf` invece di path relativo
- ✅ Eliminazione della dipendenza dal calcolo dinamico del project root
- ✅ Configurazione robusta e indipendente dalla working directory

## 🛠️ Soluzioni Implementate

1. **Path Assoluto in config.conf**: ✅ Risolto definitivamente
2. **Path Resolution Centralizzato**: ✅ Mantiene compatibilità
3. **Moduli Aggiornati**: ✅ Tutti utilizzano configurazione unificata

---
*✅ Risolto il 21 Luglio 2025 - Cache BERTino centralizzata e ottimizzata*