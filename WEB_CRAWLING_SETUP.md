# Web Crawling Setup - Implementazione Completata

## 🎯 **Implementazione Completata e Corretta**

Sono stati creati **due moduli separati e specializzati** per il crawling Tanea con configurazione dedicata e logica domini integrata.

**✨ AGGIORNAMENTO FINALE**: Corretta la gestione domini seguendo le specifiche - domini definiti SOLO in `domains.yaml` e gestiti esclusivamente tramite core modules.

## 📁 **File Creati/Aggiornati**

### **Nuovo File di Configurazione**
- **`src/config/web_crawling.yaml`** - Configurazione dedicata crawler con nodi padre

### **Moduli Crawler**
- **`src/scripts/crawler_exec.py`** - Modulo autonomo per crawling
- **`src/scripts/news_loader.py`** - Modulo per caricamento news in Weaviate

### **Documentazione**
- **`CRAWLER_MODULES.md`** - Guida completa utilizzo moduli
- **`WEB_CRAWLING_SETUP.md`** - Questo documento

---

## 🔧 **Sistema di Configurazione Unificato**

### **Gerarchia Configurazione**
Il crawler utilizza un **sistema a tre livelli**:

1. **`config.conf`**: Configurazioni comuni (globali)
2. **`config.dev.conf`**: Configurazioni ambiente specifiche
3. **`web_crawling.yaml`**: Dettagli crawling (nodi padre, siti, etc.)

### **Sezione [web_crawling] nei config.***
```ini
[web_crawling]
# File YAML da caricare
config_file = web_crawling.yaml

# Parametri base
rate_limit_delay = 2.0
max_links_per_site = 25
min_quality_score = 0.3
max_concurrent_requests = 5

# Comportamento (in config.conf)
respect_robots_txt = true
extract_metadata = true
```

### **Struttura `web_crawling.yaml`**

### **Struttura Gerarchica**
```yaml
general:                          # Configurazione globale crawler
  rate_limit_delay: 2.0
  max_links_per_site: 25
  min_quality_score: 0.3

crawling_sites:                   # Organizzazione per domini
  calcio:                         # DOMINIO
    domain_active: true           # Attivo per crawling
    priority: 1
    max_articles_per_domain: 100
    
    sites:                        # Siti del dominio
      gazzetta:                   # SITO
        name: "Gazzetta dello Sport"
        active: true              # Sito attivo
        priority: 1
        
        discovery_pages:          # NODI PADRE
          calcio_generale:        # Pagina discovery
            url: "https://www.gazzetta.it/Calcio/"
            active: true          # Page attiva
            selectors:
              article_links: "h2 a[href*='/calcio/']"
            max_links: 15
```

### **Logica Domini Centralizzata - VERSIONE CORRETTA**
- **`domains.yaml`**: UNICA fonte per definizioni domini (attivi/inattivi)
- **`web_crawling.yaml`**: Solo mapping domini → siti e configurazione link
- **`DomainManager`**: Core modules per tutte le operazioni domini
- **Crawling SOLO se domini attivi in `domains.yaml`**

---

## 🕷️ **Modulo 1: `crawler_exec.py`**

### **Funzionalità**
- ✅ **Discovery link** da nodi padre configurati
- ✅ **Crawling completo** con estrazione contenuto  
- ✅ **Logica domini** - solo domini/siti/link attivi
- ✅ **Filtering avanzato** per domini e siti specifici
- ✅ **Configurazione autonoma** da `web_crawling.yaml`

### **Utilizzo**
```bash
# Configurazione e status
python src/scripts/crawler_exec.py --config    # Configurazione completa
python src/scripts/crawler_exec.py --sites     # Siti disponibili

# Discovery (senza estrazione)
python src/scripts/crawler_exec.py --discover                    # Tutti domini attivi
python src/scripts/crawler_exec.py --discover --domain calcio    # Solo calcio
python src/scripts/crawler_exec.py --discover --site gazzetta    # Solo gazzetta

# Crawling completo (discovery + extraction + storage)
python src/scripts/crawler_exec.py --crawl                       # Tutti domini attivi
python src/scripts/crawler_exec.py --crawl --domain calcio       # Solo calcio
python src/scripts/crawler_exec.py --crawl --site gazzetta       # Solo gazzetta
python src/scripts/crawler_exec.py --crawl --max-links 20        # Limite link
```

### **Output Esempio**
```
📋 Configurazione Crawler (web_crawling.yaml + domains.yaml)
======================================================================

📂 Domini Sistema (5 totali, 1 attivi, 1 crawling):
  • calcio       - 🟢 ATTIVO CRAWLING - Keywords: ['Serie A', 'calcio italiano']
  • tecnologia   - 🔴 INATTIVO - Keywords: ['AI', 'machine learning']

🌐 Configurazione Crawling (3 domini):
  🟢 calcio (Priorità: 1, Max articoli: 100)
    🟢 gazzetta        - Priorità: 1, Pages: 3/3
    🟢 corriere_sport  - Priorità: 2, Pages: 2/2

📊 Risultati Discovery:
  • Siti processati: 3
  • Link scoperti: 35
```

---

## 📰 **Modulo 2: `news_loader.py`**

### **Funzionalità**
- ✅ **Caricamento news** nel database Weaviate tramite Trafilatura
- ✅ **Integrazione sistema** con `NewsVectorDBV2` e `TrafilaturaSourceV2`
- ✅ **Coerenza domini** totale con `domains.yaml`
- ✅ **Ricerca database** esistente
- ✅ **Statistiche e cleanup** database

### **Utilizzo**
```bash
# Configurazione e stats
python src/scripts/news_loader.py --config     # Domini e configurazione
python src/scripts/news_loader.py --stats      # Statistiche database

# Caricamento news
python src/scripts/news_loader.py --domain calcio                      # Dominio singolo
python src/scripts/news_loader.py --domain calcio --max-results 50     # Con limiti
python src/scripts/news_loader.py --domains calcio tecnologia          # Multi-dominio

# Ricerca e manutenzione
python src/scripts/news_loader.py --search calcio "Serie A" "Inter"    # Ricerca
python src/scripts/news_loader.py --cleanup 30                         # Pulizia
```

---

## 🔄 **Workflow Operativo**

### **1. Verifica Configurazione**
```bash
# Verifica configurazione crawler
python src/scripts/crawler_exec.py --config

# Verifica configurazione news
python src/scripts/news_loader.py --config
```

### **2. Discovery e Crawling**
```bash
# Discovery link per tutti i domini attivi
python src/scripts/crawler_exec.py --discover

# Crawling completo dominio calcio
python src/scripts/crawler_exec.py --crawl --domain calcio --verbose
```

### **3. Caricamento Database**
```bash
# Carica news dal crawling nel database
python src/scripts/news_loader.py --domain calcio --max-results 50

# Verifica risultati
python src/scripts/news_loader.py --stats
```

### **4. Ricerca e Test**
```bash
# Cerca contenuti caricati
python src/scripts/news_loader.py --search calcio "Juventus" "Inter"

# Pulizia periodica
python src/scripts/news_loader.py --cleanup 30
```

---

## 🎯 **Vantaggi Implementazione**

### **Separazione Responsabilità**
- **`crawler_exec.py`**: Focus su discovery e crawling tecnico
- **`news_loader.py`**: Focus su database e integrazione sistema

### **Configurazione Coerente - VERSIONE CORRETTA**
- **`domains.yaml`**: UNICA fonte domini (condiviso con tutti i moduli)
- **`web_crawling.yaml`**: Solo mapping e configurazione link crawler
- **`DomainManager`**: Validazione centralizzata domini
- **Pattern uniforme**: Coerente con `web_scraping.yaml` e architettura esistente

### **Modularità e Flessibilità**
- **Moduli autonomi**: Funzionano indipendentemente
- **Command options specifiche**: Ogni modulo ha le sue opzioni
- **Filtering avanzato**: Per domini, siti, parametri
- **Logging integrato**: Usa sistema `log.py` esistente

### **Logica Domini Avanzata**
- **Attivazione granulare**: Domini → Siti → Pages → Link
- **Priorità intelligenti**: Per domini e siti
- **Rate limiting**: Configurabile per sito
- **Quality control**: Score minimo qualità contenuto

---

## 📊 **Status Configurazione Attuale**

### **Domini Attivi - STATO CORRENTE**
- **calcio**: ✅ Attivo in `domains.yaml`
  - 3 siti configurati (Gazzetta, Corriere Sport, TuttoMercatoWeb)
  - 7 discovery pages totali attive
  - Max 100 articoli per sessione

### **Domini Inattivi**  
- **tecnologia**: 🔴 Inattivo in `domains.yaml`
- **finanza**: 🔴 Inattivo in `domains.yaml`
- **salute**: 🔴 Inattivo in `domains.yaml`
- **ambiente**: 🔴 Inattivo in `domains.yaml`

### **Per Attivare Altri Domini - PROCEDURA CORRETTA**
1. Impostare `active: true` SOLO in `domains.yaml`
2. Verificare mapping in `web_crawling.yaml` (sezione `domain_mapping`)
3. Verificare che siti abbiano `active: true`
4. Verificare che discovery pages abbiano `active: true`

**Nota**: Non serve più `domain_active` in `web_crawling.yaml` - rimosso!

---

## 🚀 **Prossimi Passi**

1. **Test Produzione**: Testare su contenuti reali
2. **Estensione Domini**: Attivare tecnologia/finanza se richiesto
3. **Monitoring**: Aggiungere metriche performance
4. **Automazione**: Scheduler per crawling automatico
5. **Ottimizzazioni**: Rate limiting adattivo per sito

---

## 📋 **Summary Tecnico**

### **Architettura Implementata**
```
domains.yaml (Sistema) ←→ web_crawling.yaml (Crawler)
            ↓                       ↓
    DomainManager           CrawlerExecutor
            ↓                       ↓
    NewsLoader  ←→  TrafilaturaCrawler ←→ DatabaseManager
            ↓                       ↓
    NewsVectorDBV2          PostgreSQL + Weaviate
```

### **File Principali**
- ✅ `src/config/web_crawling.yaml` - Configurazione crawler
- ✅ `src/scripts/crawler_exec.py` - Modulo crawling autonomo  
- ✅ `src/scripts/news_loader.py` - Modulo news database
- ✅ `CRAWLER_MODULES.md` - Documentazione completa

### **Integrazione Sistema - VERSIONE CORRETTA**
- ✅ Usa `log.py` per logging unificato
- ✅ Usa `config.py` per configurazione sistema
- ✅ Usa `DomainManager` per operazioni domini (core modules)
- ✅ Domini gestiti ESCLUSIVAMENTE tramite `domains.yaml`
- ✅ Pattern coerente con `web_scraping.yaml`
- ✅ Architettura centralizzata e uniforme

**🎉 Implementazione completata, corretta e funzionante!**

---

## 📝 **Correzioni Finali Applicate**

### **Problema Identificato**
❌ **Prima**: `web_crawling.yaml` conteneva definizioni domini (`domain_active`)
❌ **Prima**: Logica domini duplicata e confusa
❌ **Prima**: Non seguiva il pattern di `web_scraping.yaml`

### **Soluzione Implementata**
✅ **Dopo**: Domini definiti SOLO in `domains.yaml`
✅ **Dopo**: `web_crawling.yaml` gestisce solo mapping domini → siti
✅ **Dopo**: `DomainManager` centralizza tutte le operazioni domini
✅ **Dopo**: Architettura coerente e allineata

### **File Corretti**
1. **`src/config/web_crawling.yaml`**: Rimosso `domain_active`, aggiornato `domain_mapping`
2. **`src/scripts/crawler_exec.py`**: Aggiornato per usare solo `DomainManager`
3. **Documentazione**: Aggiornata per riflettere l'architettura corretta

**Sistema ora perfettamente allineato alle specifiche utente!** ✅