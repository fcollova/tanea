# Database Management Scripts

Collezione di script per la gestione e pulizia dei database PostgreSQL e Weaviate.

## 🚀 Script Principali

### `clean_db.sh` - Script Bash Principale
Script bash interattivo con menu per operazioni rapide:
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

### `clean_databases.py` - Script Python Completo
Menu interattivo avanzato con tutte le opzioni:
```bash
python3 scripts/clean_databases.py
```

**Opzioni avanzate**:
- `1` - 🔍 Verifica stato attuale database
- `2` - 🧹 Pulizia COMPLETA (PostgreSQL + Weaviate)
- `3` - 🗄️ Pulizia solo PostgreSQL
- `4` - 🔍 Pulizia solo Weaviate
- `5` - 🏗️ Crea schemi domini attivi (dopo pulizia)
- `6` - ✅ Procedura completa (pulizia + schemi)
- `7` - 📋 Lista collezioni Weaviate
- `8` - 🗑️ Elimina collezione specifica Weaviate

## 📋 Script Specializzati

### `list_collections.py` - Lista Collezioni
Mostra tutte le collezioni Weaviate con statistiche:
```bash
python3 scripts/list_collections.py
```

**Output**:
```
📊 Stato attuale Weaviate:
🎯 Collezioni Tanea:
    1. Tanea_Calcio_DEV: 95 documenti (dominio: calcio)
    2. Tanea_General_DEV: 0 documenti (dominio: unknown)
📋 Altre collezioni:
    3. LinksMetadata_DEV: 0 documenti
    4. NewsArticles_DEV: 210 documenti
```

### `delete_collection.py` - Eliminazione Specifica
Elimina una collezione Weaviate specifica:
```bash
python3 scripts/delete_collection.py
```

**Procedura sicura**:
1. 📋 Lista collezioni con numerazione unificata
2. 🎯 Selezione numero collezione
3. ⚠️ Conferma con `DELETE` (case-sensitive)
4. 🗑️ Eliminazione irreversibile

### `quick_reset.py` - Reset Rapido
Reset completo automatico senza conferme interattive:
```bash
python3 scripts/quick_reset.py
```

**Operazioni**:
- Pulizia completa PostgreSQL e Weaviate
- Creazione schemi per domini attivi
- Reset sequenze auto-increment

## 🔧 Architettura Tecnica

### Classe DatabaseCleaner
Gestisce tutte le operazioni di pulizia e manutenzione:

```python
class DatabaseCleaner:
    async def verify_clean_state()        # Verifica stato database
    async def clean_postgresql()          # Pulizia PostgreSQL
    async def clean_weaviate()           # Pulizia Weaviate
    async def list_weaviate_collections() # Lista collezioni
    async def delete_specific_collection() # Elimina collezione
    async def create_fresh_schemas()      # Crea schemi domini
    async def cleanup()                  # Chiude connessioni
```

### Gestione Connessioni
- **PostgreSQL**: Connessione via `LinkDatabase` con Prisma ORM
- **Weaviate**: Client diretto con gestione resource cleanup
- **Resource Management**: Chiusura automatica connessioni per evitare memory leak

### Domini e Indici Weaviate
Ogni dominio ha indice separato con formato:
```
Tanea_[DomainName]_[Environment]
```

Esempi:
- `Tanea_Calcio_DEV` → articoli calcio
- `Tanea_Tecnologia_DEV` → articoli tecnologia
- `Tanea_General_DEV` → articoli general

## ⚠️ Note di Sicurezza

### Conferme Richieste
- **Reset completo**: Richiede `RESET` 
- **Eliminazione collezione**: Richiede `DELETE`
- **Pulizia completa**: Richiede conferma esplicita

### Operazioni Irreversibili
Tutte le operazioni di pulizia sono **IRREVERSIBILI**:
- ❌ Eliminazione dati PostgreSQL (siti, link)
- ❌ Eliminazione documenti/vettori Weaviate
- ❌ Reset sequenze auto-increment

### Backup Raccomandato
Prima di operazioni di pulizia su dati production:
```bash
# Backup PostgreSQL
pg_dump tanea_dev > backup_$(date +%Y%m%d).sql

# Backup Weaviate (se necessario)
# Considerare export collezioni importanti
```

## 🐛 Troubleshooting

### Errore Connessione Database
```bash
# Verifica PostgreSQL
sudo systemctl status postgresql

# Verifica Weaviate  
curl http://localhost:8080/v1/.well-known/ready
```

### Resource Warning
Gli script gestiscono automaticamente:
- Chiusura connessioni PostgreSQL via Prisma
- Chiusura client Weaviate per evitare memory leak
- Cleanup risorse in caso di errori/interruzioni

### Import Error Script
Se errori di import nei script dedicati:
```bash
# Verifica virtual environment attivo
source venv/bin/activate

# Verifica path Python
python3 -c "import sys; print(sys.path)"
```

---

*Ultima modifica: 22 Luglio 2025*  
*Compatibilità: Python 3.12+, PostgreSQL 14+, Weaviate 1.24+*