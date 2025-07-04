# 🎯 Campo 'active' - Controllo Fonti Scraping

Implementazione del campo `active` nel file `web_scraping.yaml` per il controllo granulare delle fonti di scraping.

## ✅ **Modifiche Implementate**

### 📝 **File `src/config/web_scraping.yaml`:**

**Aggiunto campo `active` per ogni fonte:**
```yaml
# Fonte attiva
ansa:
  name: "ANSA"
  base_url: "https://www.ansa.it"
  active: true              # ← NUOVO: Fonte attiva per scraping
  priority: 2

# Fonte disattivata  
tuttomercatoweb:
  name: "Tuttomercatoweb"
  base_url: "https://www.tuttomercatoweb.com"
  active: false             # ← NUOVO: Fonte disattivata
  priority: 1
```

### 🔧 **Aggiornamento moduli core:**

**`news_source_webscraping.py`:**
- ✅ Controlla campo `active` in `is_available()`
- ✅ Filtra fonti disattivate in `_get_domain_sites()`
- ✅ Log debug per fonti saltate

**`news_source_trafilatura.py`:**
- ✅ Stesso controllo campo `active`
- ✅ Compatibilità completa con sistema

## 📊 **Stato Fonti Configurate**

| Fonte | Stato | Motivo |
|-------|-------|---------|
| ✅ ANSA | Attiva | Affidabile, selettori aggiornati |
| ✅ Corriere della Sera | Attiva | Fonte autorevole |
| ✅ La Repubblica | Attiva | Buona copertura |
| ✅ Gazzetta dello Sport | Attiva | Specializzata sport |
| ✅ Corriere dello Sport | Attiva | Specializzata calcio |
| ✅ ANSA Sport | Attiva | Affidabile per sport |
| ✅ Il Sole 24 Ore | Attiva | Specializzata economia |
| ❌ Tuttomercatoweb | **Disattivata** | Problemi affidabilità |
| ❌ CalcioMercato.com | **Disattivata** | Selettori obsoleti |

## 🎯 **Domain Mapping Aggiornato**

**Solo fonti attive nei mapping:**
```yaml
domain_mapping:
  calcio: ["gazzetta", "corriere_sport", "ansa_sport"]  # Rimosse fonti disattivate
  tecnologia: ["repubblica", "corriere", "ansa"]
  finanza: ["sole24ore", "corriere", "ansa"]
  salute: ["ansa", "corriere", "repubblica"]
  ambiente: ["ansa", "corriere", "repubblica"]
```

## 🔧 **Utilizzo**

### **Disattivare una fonte:**
```yaml
problematic_site:
  name: "Sito Problematico"
  base_url: "https://example.com"
  active: false  # ← Disattiva fonte
  priority: 1
```

### **Riattivare una fonte:**
```yaml
fixed_site:
  name: "Sito Riparato"
  base_url: "https://example.com"
  active: true   # ← Riattiva fonte
  priority: 1
```

### **Controllo via codice:**
```python
# Il sistema rispetta automaticamente il campo active
from src.core.news_sources import create_default_news_manager

manager = create_default_news_manager()
# Solo fonti attive verranno utilizzate
```

## 🚀 **Vantaggi**

### **Gestione Dinamica:**
- 🎯 **Controllo granulare** per ogni fonte
- ⚡ **Disattivazione immediata** fonti problematiche
- 🔧 **Nessuna modifica codice** necessaria
- 📊 **Risparmio risorse** su fonti non funzionanti

### **Manutenzione:**
- 🛠️ **Riparazione selettiva** di singole fonti
- 📈 **Test incrementale** di nuove fonti
- 🎛️ **Configurazione centralizzata** in YAML
- 🔄 **Retrocompatibilità** (default `active: true`)

### **Performance:**
- ⚡ **Meno richieste HTTP** a fonti disattivate
- 🎯 **Focus su fonti affidabili**
- 📉 **Riduzione errori** e timeout
- 🚀 **Scraping più veloce**

## 📋 **Test Implementati**

**`test_active_sources.py`** verifica:
- ✅ Configurazione YAML corretta
- ✅ Moduli rispettano campo `active`
- ✅ Logica filtraggio funzionante
- ✅ Domain mapping aggiornato

## 🎊 **Risultato**

**Prima**: Tutte le fonti erano sempre attive, anche se problematiche
**Dopo**: Controllo granulare con possibilità di disattivare fonti specifiche

```bash
# Test del sistema
python3 test_active_sources.py

# Risultato: 9 fonti configurate → 7 attive, 2 disattivate
# Sistema rispetta automaticamente le impostazioni
```

**Il campo `active` è ora completamente integrato nel sistema di scraping per un controllo ottimale delle fonti!** 🎯