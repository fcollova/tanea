# 🧹 Database Cleanup Procedure

## Panoramica

Questa procedura pulisce completamente i database PostgreSQL e Weaviate, riportandoli ad uno stato clean pronto per il crawler con l'architettura multi-domain.

## 🎯 Cosa fa la pulizia

### PostgreSQL
- ✅ Elimina tutti i **siti** dalla tabella `Site`
- ✅ Elimina tutti i **link** dalla tabella `DiscoveredLink` 
- ✅ Reset delle sequenze auto-increment
- ✅ Mantiene la struttura delle tabelle intatta

### Weaviate
- ✅ Elimina tutte le **collezioni** che iniziano con `Tanea_`
- ✅ Rimuove tutti i **documenti** e **vettori** esistenti
- ✅ Ricrea gli **schemi** per i domini attivi
- ✅ Prepara gli index nel formato `Tanea_[domain]_[environment]`

## 🚀 Modi per eseguire la pulizia

### 1. Script Bash (Più semplice)
```bash
./clean_db.sh
```

**Opzioni disponibili:**
- `1` - 🔍 Verifica stato database
- `2` - 🧹 Menu completo interattivo  
- `3` - 🚀 Reset rapido completo
- `4` - 📋 Lista collezioni Weaviate
- `5` - 🗑️ Elimina collezione specifica
- `0` - ❌ Annulla

### 2. Script Python Interattivo
```bash
python3 scripts/clean_databases.py
```

**Opzioni avanzate:**
- `1` - 🔍 Verifica stato attuale database
- `2` - 🧹 Pulizia COMPLETA (PostgreSQL + Weaviate)
- `3` - 🗄️ Pulizia solo PostgreSQL
- `4` - 🔍 Pulizia solo Weaviate
- `5` - 🏗️ Crea schemi domini attivi (dopo pulizia)
- `6` - ✅ Procedura completa (pulizia + schemi)
- `7` - 📋 Lista collezioni Weaviate
- `8` - 🗑️ Elimina collezione specifica Weaviate

### 3. Reset Rapido Python
```bash
python3 scripts/quick_reset.py
```
Esegue automaticamente: pulizia completa + creazione schemi + verifica

## 📋 Procedura completa consigliata

### Step 1: Verifica stato attuale
```bash
./clean_db.sh
# Seleziona opzione 1
```

### Step 2: Reset completo
```bash
./clean_db.sh
# Seleziona opzione 3
# Conferma con 'RESET'
```

### Step 3: Verifica risultato
Il sistema mostrerà:
```
✅ STATO CLEAN VERIFICATO - Sistema pronto per il crawler

📊 PostgreSQL:
   • Siti: 0
   • Link: 0

📊 Weaviate:
   • Collezioni Tanea: 1
     - Tanea_Calcio_DEV: 0 documenti
```

## 🗂️ Struttura finale attesa

### PostgreSQL (vuoto)
```sql
Site                 (0 record)
DiscoveredLink       (0 record)
```

### Weaviate (schemi domini attivi)
```
Tanea_Calcio_DEV     (0 documenti) ← Solo se dominio calcio è attivo
Tanea_Tecnologia_DEV (0 documenti) ← Solo se dominio tecnologia è attivo
... altri domini attivi
```

## ⚠️ Avvertenze di sicurezza

### 🔒 Conferme richieste
- **PostgreSQL + Weaviate**: Richiede conferma `'CLEAN'`
- **Reset completo**: Richiede conferma `'RESET'`
- **Operazioni irreversibili**: Nessun backup automatico

### 📊 Cosa viene preservato
- ✅ **Schema database** PostgreSQL (struttura tabelle)
- ✅ **Configurazioni** in `domains.yaml`, `config.conf`
- ✅ **Codice** e **documenti**

### ❌ Cosa viene eliminato
- ❌ **Tutti i dati** siti e link in PostgreSQL
- ❌ **Tutti i documenti** e vettori in Weaviate
- ❌ **Tutte le collezioni** Tanea esistenti

## 🎯 Gestione Collezioni Weaviate

### Lista Collezioni
Per vedere tutte le collezioni esistenti in Weaviate:
```bash
./clean_db.sh
# Seleziona opzione 4
```

Oppure direttamente:
```bash
python3 scripts/clean_databases.py
# Seleziona opzione 7
```

**Output esempio:**
```
🔍 COLLEZIONI WEAVIATE DISPONIBILI
📊 Stato attuale Weaviate:
   • Collezioni Tanea: 2
   • Altre collezioni: 0

🎯 Collezioni Tanea:
   1. Tanea_Calcio_DEV: 125 documenti (dominio: calcio)
   2. Tanea_Tecnologia_DEV: 87 documenti (dominio: tecnologia)
```

### Eliminazione Collezione Specifica
Per eliminare una singola collezione:
```bash
./clean_db.sh
# Seleziona opzione 5
```

**Procedura:**
1. 📋 Visualizza lista collezioni disponibili
2. 🔢 Scegli il numero della collezione da eliminare
3. ⚠️ Conferma eliminazione scrivendo `DELETE`
4. ✅ Collezione eliminata

**Vantaggi rispetto alla pulizia completa:**
- ✅ Elimina solo una collezione specifica
- ✅ Mantiene le altre collezioni intatte
- ✅ Utile per test o correzioni mirate

## 🔧 Troubleshooting

### Database non disponibile
```bash
# Verifica PostgreSQL
docker ps | grep postgres

# Verifica Weaviate  
docker ps | grep weaviate

# Avvia i servizi se necessario
docker-compose up -d
```

### Errore permessi
```bash
chmod +x clean_db.sh
chmod +x scripts/clean_databases.py
chmod +x scripts/quick_reset.py
```

### Virtual environment
```bash
source venv/bin/activate
pip install -r requirements.txt
```

## 🎯 Quando usare la pulizia

### ✅ Situazioni consigliate
- **Prima di test** completi del crawler
- **Cambio architettura** domini
- **Reset sviluppo** per ripartire da zero
- **Problemi dati** corrotti o inconsistenti
- **Migrazione** a nuova versione schema

### ⚠️ Evita in produzione
- **Dati importanti** non salvati altrove
- **Sistema in uso** attivo
- **Senza backup** se necessario

## 📈 Dopo la pulizia

### Prossimi passi
1. ✅ **Verifica** domini attivi in `domains.yaml`
2. ✅ **Avvia crawler** per domini desiderati
3. ✅ **Monitora** creazione dati nei database
4. ✅ **Verifica** separazione domini in Weaviate

### Test rapido
```bash
# Avvia crawler per dominio calcio
python3 src/crawler/crawler_exec.py --discover --domain calcio --max-links 5

# Verifica risultati in Prisma Studio
npx prisma studio  # http://localhost:5555
```

---

*Procedura aggiornata per architettura multi-domain - Gennaio 2025*