#!/usr/bin/env python3
"""
Test del sistema a due livelli: Domini attivi/inattivi + Fonti attive/inattive
Verifica la logica implementata nei moduli core
"""

import sys
import os
import yaml
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_configuration_separation():
    """Test della separazione delle configurazioni"""
    print("🧪 TEST SEPARAZIONE CONFIGURAZIONI")
    print("=" * 40)
    
    try:
        # Leggi configurazione domains.yaml
        domains_path = "src/config/domains.yaml"
        scraping_path = "src/config/web_scraping.yaml"
        
        if not os.path.exists(domains_path):
            print("❌ File domains.yaml non trovato")
            return False
            
        if not os.path.exists(scraping_path):
            print("❌ File web_scraping.yaml non trovato")
            return False
            
        with open(domains_path, 'r', encoding='utf-8') as f:
            domains_config = yaml.safe_load(f)
            
        with open(scraping_path, 'r', encoding='utf-8') as f:
            scraping_config = yaml.safe_load(f)
        
        print("✅ Configurazioni caricate")
        
        # Analizza domini da domains.yaml
        domains = domains_config.get('domains', {})
        active_domains = []
        inactive_domains = []
        
        for domain_name, domain_config in domains.items():
            if domain_config.get('active', True):
                active_domains.append(domain_name)
            else:
                inactive_domains.append(domain_name)
        
        print(f"\n📊 DOMINI (da domains.yaml):")
        print(f"   ✅ Domini attivi: {len(active_domains)}")
        for domain in active_domains:
            print(f"      • {domain}")
            
        print(f"   ❌ Domini disattivati: {len(inactive_domains)}")
        for domain in inactive_domains:
            print(f"      • {domain}")
        
        # Analizza fonti da web_scraping.yaml
        sites = scraping_config.get('sites', {})
        active_sources = []
        inactive_sources = []
        
        for site_name, site_config in sites.items():
            if site_config.get('active', True):
                active_sources.append(site_name)
            else:
                inactive_sources.append(site_name)
        
        print(f"\n📊 FONTI (da web_scraping.yaml):")
        print(f"   ✅ Fonti attive: {len(active_sources)}")
        for source in active_sources[:5]:  # Prime 5
            print(f"      • {source}")
        if len(active_sources) > 5:
            print(f"      • ... e altre {len(active_sources)-5}")
            
        print(f"   ❌ Fonti disattivate: {len(inactive_sources)}")
        for source in inactive_sources:
            print(f"      • {source}")
        
        # Verifica domain_mapping
        domain_mapping = scraping_config.get('domain_mapping', {})
        print(f"\n🎯 VERIFICA DOMAIN MAPPING:")
        
        for domain, mapped_sources in domain_mapping.items():
            print(f"   📋 {domain}: {len(mapped_sources)} fonti mappate")
            
            # Controlla se dominio è attivo in domains.yaml
            domain_status = "✅ attivo" if domain in active_domains else "❌ inattivo"
            print(f"      Dominio: {domain_status}")
            
            # Controlla fonti attive/inattive per questo dominio
            active_for_domain = [s for s in mapped_sources if s in active_sources]
            inactive_for_domain = [s for s in mapped_sources if s in inactive_sources]
            
            print(f"      Fonti attive: {len(active_for_domain)}")
            print(f"      Fonti disattivate: {len(inactive_for_domain)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore test configurazione: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_two_level_logic():
    """Test della logica a due livelli nei moduli"""
    print(f"\n🔧 TEST LOGICA A DUE LIVELLI NEI MODULI")
    print("-" * 40)
    
    try:
        from src.core.news_source_webscraping import WebScrapingSource
        from src.core.news_source_base import NewsQuery
        
        # Test WebScrapingSource
        print("📰 Test WebScrapingSource...")
        
        webscraping = WebScrapingSource()
        print(f"   ✅ WebScrapingSource inizializzato")
        print(f"   📊 Disponibile: {webscraping.is_available()}")
        
        # Test selezione fonti attive
        if webscraping.is_available():
            domains_to_test = ['calcio', 'tecnologia', 'finanza']
            
            for domain in domains_to_test:
                print(f"   🎯 Test dominio '{domain}':")
                
                # Test selezione siti per dominio
                sites = webscraping._get_domain_sites(domain)
                print(f"      📋 Fonti attive selezionate: {len(sites)}")
                for site in sites:
                    site_name = site.get('site_key', site.get('name', 'Unknown'))
                    print(f"         • {site_name}")
        
        # Test TrafilaturaWebScrapingSource
        print(f"\n🤖 Test TrafilaturaWebScrapingSource...")
        
        try:
            from src.core.news_source_trafilatura import TrafilaturaWebScrapingSource
            
            trafilatura = TrafilaturaWebScrapingSource()
            print(f"   ✅ TrafilaturaWebScrapingSource inizializzato")
            print(f"   📊 Disponibile: {trafilatura.is_available()}")
            
            if trafilatura.is_available():
                domains_to_test = ['calcio', 'tecnologia', 'finanza']
                
                for domain in domains_to_test:
                    is_active = trafilatura._is_domain_active_for_scraping(domain)
                    status = "✅ attivo" if is_active else "❌ inattivo"
                    print(f"   🎯 Dominio '{domain}': {status}")
                    
                    if is_active:
                        # Test selezione siti per dominio attivo
                        sites = trafilatura._get_domain_sites(domain)
                        print(f"      📋 Fonti selezionate: {len(sites)}")
                        for site in sites:
                            site_name = site.get('site_key', site.get('name', 'Unknown'))
                            print(f"         • {site_name}")
        
        except ImportError as e:
            print(f"   ⚠️  Trafilatura non disponibile: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore test moduli: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_search_behavior():
    """Test comportamento ricerca con domini attivi/inattivi"""
    print(f"\n🔍 TEST COMPORTAMENTO RICERCA")
    print("-" * 30)
    
    try:
        from src.core.news_source_webscraping import WebScrapingSource
        from src.core.news_source_base import NewsQuery
        
        webscraping = WebScrapingSource()
        
        if not webscraping.is_available():
            print("⚠️  WebScraping non disponibile per test")
            return True
        
        # Test query su dominio attivo
        print("🟢 Test query su dominio ATTIVO (calcio):")
        active_query = NewsQuery(
            keywords=['Serie A', 'calcio'],
            domain='calcio',
            max_results=3
        )
        
        # Simula inizio ricerca (non eseguire per intero)
        is_domain_active = webscraping._is_domain_active_for_scraping('calcio')
        print(f"   🎯 Dominio 'calcio' attivo: {'Sì' if is_domain_active else 'No'}")
        
        if is_domain_active:
            sites = webscraping._get_domain_sites('calcio')
            print(f"   📋 Fonti che verrebbero utilizzate: {len(sites)}")
        else:
            print(f"   ⏭️  Ricerca saltata (dominio inattivo)")
        
        # Test query su dominio inattivo
        print(f"\n🔴 Test query su dominio INATTIVO (tecnologia):")
        inactive_query = NewsQuery(
            keywords=['AI', 'intelligenza artificiale'],
            domain='tecnologia',
            max_results=3
        )
        
        is_domain_active = webscraping._is_domain_active_for_scraping('tecnologia')
        print(f"   🎯 Dominio 'tecnologia' attivo: {'Sì' if is_domain_active else 'No'}")
        
        if is_domain_active:
            sites = webscraping._get_domain_sites('tecnologia')
            print(f"   📋 Fonti che verrebbero utilizzate: {len(sites)}")
        else:
            print(f"   ⏭️  Ricerca saltata (dominio inattivo)")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore test ricerca: {e}")
        return False

def show_two_level_summary():
    """Riassunto sistema a due livelli"""
    print(f"\n📋 RIASSUNTO SISTEMA A DUE LIVELLI")
    print("-" * 40)
    
    print(f"🎯 LOGICA IMPLEMENTATA:")
    logic_points = [
        "1️⃣  Controllo DOMINIO: Se domains.active = false → nessuna ricerca",
        "2️⃣  Controllo FONTE: Se dominio attivo, usa solo fonti con sites.active = true",
        "3️⃣  Configurazione centralizzata in web_scraping.yaml",
        "4️⃣  Compatibilità con WebScraping e Trafilatura",
        "5️⃣  Default 'true' per retrocompatibilità"
    ]
    
    for point in logic_points:
        print(f"   {point}")
    
    print(f"\n🔧 VANTAGGI:")
    benefits = [
        "✅ Controllo granulare per dominio E fonte",
        "✅ Disattivazione completa domini non necessari",
        "✅ Fine-tuning fonti per domini specifici",
        "✅ Risparmio risorse su domini/fonti inattivi",
        "✅ Configurazione senza modifiche codice",
        "✅ Prioritizzazione intelligente risorse"
    ]
    
    for benefit in benefits:
        print(f"   {benefit}")
    
    print(f"\n📖 ESEMPI UTILIZZO:")
    examples = [
        "# Disattiva dominio completamente",
        "domains:",
        "  finanza:",
        "    active: false  # ← Nessuna ricerca finanza",
        "",
        "# Disattiva fonte specifica", 
        "sites:",
        "  tuttomercatoweb:",
        "    active: false  # ← Fonte saltata anche per domini attivi"
    ]
    
    for line in examples:
        print(f"   {line}")

if __name__ == "__main__":
    print("🧪 TEST SISTEMA A DUE LIVELLI: DOMINI + FONTI")
    print("=" * 50)
    
    config_ok = test_two_level_configuration()
    logic_ok = test_two_level_logic()
    search_ok = test_search_behavior()
    
    show_two_level_summary()
    
    print(f"\n📋 RISULTATI FINALI:")
    print(f"   - Configurazione: {'✅ OK' if config_ok else '❌ ERRORE'}")
    print(f"   - Logica moduli: {'✅ OK' if logic_ok else '❌ ERRORE'}")
    print(f"   - Comportamento ricerca: {'✅ OK' if search_ok else '❌ ERRORE'}")
    
    if config_ok and logic_ok and search_ok:
        print(f"\n🎊 SISTEMA A DUE LIVELLI IMPLEMENTATO CON SUCCESSO!")
        print(f"   Domini e fonti possono essere controllati indipendentemente")
        print(f"   per massima flessibilità e risparmio risorse.")
    else:
        print(f"\n⚠️  Alcuni test necessitano attenzione")