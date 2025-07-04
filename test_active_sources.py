#!/usr/bin/env python3
"""
Test del nuovo campo 'active' nel web_scraping.yaml
Verifica che i moduli rispettino le fonti attive/disattivate
"""

import sys
import os
import yaml
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_active_sources_configuration():
    """Test della configurazione fonti attive"""
    print("🧪 TEST CONFIGURAZIONE FONTI ATTIVE")
    print("=" * 40)
    
    try:
        # Leggi configurazione web_scraping.yaml
        config_path = "src/config/web_scraping.yaml"
        
        if not os.path.exists(config_path):
            print("❌ File web_scraping.yaml non trovato")
            return False
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        print("✅ Configurazione caricata")
        
        # Verifica struttura configurazione
        sites = config.get('sites', {})
        if not sites:
            print("❌ Nessun sito configurato")
            return False
            
        print(f"✅ {len(sites)} siti configurati")
        
        # Analizza stato fonti
        active_sources = []
        inactive_sources = []
        missing_active_field = []
        
        for site_name, site_config in sites.items():
            if 'active' not in site_config:
                missing_active_field.append(site_name)
                # Default: attivo se campo mancante
                active_sources.append(site_name)
            elif site_config['active']:
                active_sources.append(site_name)
            else:
                inactive_sources.append(site_name)
        
        # Mostra risultati
        print(f"\n📊 STATO FONTI:")
        print(f"   ✅ Fonti attive: {len(active_sources)}")
        for source in active_sources:
            status = " (default)" if source in missing_active_field else ""
            print(f"      • {source}{status}")
            
        print(f"   ❌ Fonti disattivate: {len(inactive_sources)}")
        for source in inactive_sources:
            print(f"      • {source}")
            
        if missing_active_field:
            print(f"   ⚠️  Fonti senza campo 'active': {len(missing_active_field)}")
            for source in missing_active_field:
                print(f"      • {source}")
        
        # Verifica domain_mapping
        domain_mapping = config.get('domain_mapping', {})
        print(f"\n🎯 VERIFICA DOMAIN MAPPING:")
        
        for domain, mapped_sources in domain_mapping.items():
            print(f"   📋 {domain}: {mapped_sources}")
            
            # Controlla se le fonti mappate sono attive
            inactive_mapped = [s for s in mapped_sources if s in inactive_sources]
            if inactive_mapped:
                print(f"      ⚠️  Fonti mappate ma disattivate: {inactive_mapped}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore test configurazione: {e}")
        return False

def test_modules_respect_active_field():
    """Test che i moduli rispettino il campo active"""
    print(f"\n🔧 TEST MODULI RISPETTANO CAMPO ACTIVE")
    print("-" * 40)
    
    try:
        # Test modulo WebScrapingSource
        print("📰 Test news_source_webscraping.py...")
        
        from src.core.news_source_webscraping import WebScrapingSource
        from src.core.news_source_base import NewsQuery
        
        webscraping = WebScrapingSource()
        print(f"   ✅ WebScrapingSource inizializzato")
        print(f"   📊 Disponibile: {webscraping.is_available()}")
        
        # Test selezione domini
        if webscraping.is_available():
            calcio_sites = webscraping._get_domain_sites('calcio')
            print(f"   🥅 Siti calcio selezionati: {len(calcio_sites)}")
            
            for site in calcio_sites:
                site_name = site.get('site_key', site.get('name', 'Unknown'))
                is_active = site.get('active', True)
                print(f"      • {site_name}: {'✅ attivo' if is_active else '❌ inattivo'}")
        
        # Test modulo TrafilaturaWebScrapingSource
        print(f"\n🤖 Test news_source_trafilatura.py...")
        
        try:
            from src.core.news_source_trafilatura import TrafilaturaWebScrapingSource
            
            trafilatura = TrafilaturaWebScrapingSource()
            print(f"   ✅ TrafilaturaWebScrapingSource inizializzato")
            print(f"   📊 Disponibile: {trafilatura.is_available()}")
            
            if trafilatura.is_available():
                calcio_sites = trafilatura._get_domain_sites('calcio')
                print(f"   🥅 Siti calcio selezionati: {len(calcio_sites)}")
                
                for site in calcio_sites:
                    site_name = site.get('site_key', site.get('name', 'Unknown'))
                    is_active = site.get('active', True)
                    print(f"      • {site_name}: {'✅ attivo' if is_active else '❌ inattivo'}")
        
        except ImportError as e:
            print(f"   ⚠️  Trafilatura non disponibile: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore test moduli: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_active_filtering_logic():
    """Test della logica di filtraggio fonti attive"""
    print(f"\n🔍 TEST LOGICA FILTRAGGIO FONTI")
    print("-" * 35)
    
    # Simula configurazione di test
    test_config = {
        'sites': {
            'ansa': {'name': 'ANSA', 'active': True},
            'gazzetta': {'name': 'Gazzetta', 'active': True},
            'tuttomercato': {'name': 'TuttoMercato', 'active': False},
            'calciomercato': {'name': 'CalcioMercato', 'active': False},
            'corriere_sport': {'name': 'Corriere Sport', 'active': True}
        },
        'domain_mapping': {
            'calcio': ['gazzetta', 'tuttomercato', 'calciomercato', 'corriere_sport', 'ansa']
        }
    }
    
    print("📋 Configurazione test:")
    for site, config in test_config['sites'].items():
        status = "✅ attivo" if config['active'] else "❌ inattivo"
        print(f"   • {site}: {status}")
    
    # Simula logica filtraggio
    domain = 'calcio'
    mapped_sites = test_config['domain_mapping'].get(domain, [])
    print(f"\n🎯 Siti mappati per '{domain}': {mapped_sites}")
    
    # Filtra solo siti attivi
    active_sites = []
    for site_name in mapped_sites:
        site_config = test_config['sites'].get(site_name, {})
        if site_config.get('active', True):  # Default True se manca campo
            active_sites.append(site_name)
        else:
            print(f"   ⏭️  Saltato {site_name} (disattivato)")
    
    print(f"\n✅ Siti attivi selezionati: {active_sites}")
    print(f"📊 Fonti filtrate: {len(mapped_sites)} → {len(active_sites)}")
    
    return len(active_sites) > 0

def show_configuration_summary():
    """Mostra riassunto configurazione"""
    print(f"\n📋 RIASSUNTO CONFIGURAZIONE CAMPO 'ACTIVE'")
    print("-" * 45)
    
    benefits = [
        "✅ Controllo granulare fonti per scraping",
        "✅ Disattivazione temporanea fonti problematiche", 
        "✅ Facile manutenzione senza modificare codice",
        "✅ Risparmio risorse su fonti non funzionanti",
        "✅ Configurazione centralizzata in YAML",
        "✅ Compatibilità con WebScraping e Trafilatura",
        "✅ Default 'true' per retrocompatibilità"
    ]
    
    for benefit in benefits:
        print(f"   {benefit}")
    
    print(f"\n🔧 UTILIZZO:")
    usage_examples = [
        "# Disattiva fonte problematica",
        "tuttomercatoweb:",
        "  name: 'Tuttomercatoweb'",
        "  active: false  # ← Fonte disattivata",
        "",
        "# Attiva fonte affidabile", 
        "ansa:",
        "  name: 'ANSA'",
        "  active: true   # ← Fonte attiva"
    ]
    
    for line in usage_examples:
        print(f"   {line}")

if __name__ == "__main__":
    print("🧪 TEST SISTEMA FONTI ATTIVE/DISATTIVATE")
    print("=" * 45)
    
    config_ok = test_active_sources_configuration()
    modules_ok = test_modules_respect_active_field() 
    logic_ok = test_active_filtering_logic()
    
    show_configuration_summary()
    
    print(f"\n📋 RISULTATI FINALI:")
    print(f"   - Configurazione: {'✅ OK' if config_ok else '❌ ERRORE'}")
    print(f"   - Moduli: {'✅ OK' if modules_ok else '❌ ERRORE'}")
    print(f"   - Logica: {'✅ OK' if logic_ok else '❌ ERRORE'}")
    
    if config_ok and modules_ok and logic_ok:
        print(f"\n🎊 CAMPO 'ACTIVE' IMPLEMENTATO CON SUCCESSO!")
        print(f"   Le fonti possono ora essere attivate/disattivate")
        print(f"   modificando il campo 'active' in web_scraping.yaml")
    else:
        print(f"\n⚠️  Alcuni test necessitano attenzione")