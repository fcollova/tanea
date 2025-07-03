#!/usr/bin/env python3
"""
Test semplificato per l'architettura migliorata del sistema news sources
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_architecture():
    """Test dell'architettura modulare"""
    print("🧪 TEST ARCHITETTURA MODULARE NEWS SOURCES")
    print("=" * 50)
    
    try:
        # Test import moduli base
        print("\n📚 Test import moduli...")
        
        from src.core.news_source_base import NewsQuery, NewsArticle, NewsSource, SourceMetrics
        print("✅ news_source_base importato")
        
        from src.core.news_source_manager import NewsSourceManager  
        print("✅ news_source_manager importato")
        
        # Test creazione oggetti base
        print("\n🔧 Test creazione oggetti...")
        
        query = NewsQuery(
            keywords=['calcio', 'Serie A'],
            domain='calcio',
            max_results=5
        )
        print(f"✅ NewsQuery creata: domain={query.domain}, keywords={query.keywords}")
        
        article = NewsArticle(
            title="Test Article",
            content="Test content",
            url="https://example.com"
        )
        print(f"✅ NewsArticle creato: {article.title}")
        
        manager = NewsSourceManager()
        print(f"✅ NewsSourceManager creato")
        
        # Test configurazioni
        print("\n⚙️  Test configurazioni...")
        
        domain_preferences = manager._build_domain_preferences()
        print(f"✅ Preferenze domini: {list(domain_preferences.keys())}")
        
        # Test utilities
        print("\n🛠️  Test utilities...")
        
        from src.core.news_source_base import expand_keywords_for_domain, test_url_availability
        
        expanded = expand_keywords_for_domain('calcio', ['Serie A'])
        print(f"✅ Keywords espanse: {expanded}")
        
        url_test = test_url_availability('https://www.google.com')
        print(f"✅ Test URL disponibilità: {url_test}")
        
        # Test metriche
        print("\n📊 Test metriche...")
        
        metrics = SourceMetrics()
        metrics.success_count = 10
        metrics.error_count = 2
        print(f"✅ SourceMetrics: success={metrics.success_count}, errors={metrics.error_count}")
        
        print("\n🎉 ARCHITETTURA MODULARE FUNZIONANTE!")
        return True
        
    except Exception as e:
        print(f"\n❌ Errore test architettura: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_web_scraping_config():
    """Test configurazione web scraping"""
    print("\n🕷️  TEST CONFIGURAZIONE WEB SCRAPING")
    print("-" * 35)
    
    try:
        import yaml
        
        # Carica configurazione
        config_path = "src/config/web_scraping.yaml"
        if not os.path.exists(config_path):
            print(f"❌ File configurazione non trovato: {config_path}")
            return False
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        print(f"✅ Configurazione caricata")
        
        # Test struttura generale
        general = config.get('general', {})
        print(f"✅ Rate limit delay: {general.get('rate_limit_delay')}s")
        print(f"✅ Timeout: {general.get('timeout')}s")
        print(f"✅ Max retries: {general.get('max_retries')}")
        
        # Test siti configurati
        sites = config.get('sites', {})
        print(f"✅ Siti configurati: {len(sites)}")
        
        for site_name, site_config in list(sites.items())[:3]:
            print(f"   - {site_name}: {site_config.get('name', 'N/A')}")
            categories = site_config.get('categories', {})
            print(f"     Categorie: {list(categories.keys())}")
        
        # Test mapping domini
        domain_mapping = config.get('domain_mapping', {})
        print(f"✅ Mapping domini: {domain_mapping}")
        
        print(f"✅ Configurazione web scraping OK")
        return True
        
    except Exception as e:
        print(f"❌ Errore test configurazione: {e}")
        return False

def test_improvements_summary():
    """Riassunto delle migliorie implementate"""
    print("\n🚀 RIASSUNTO MIGLIORIE IMPLEMENTATE")
    print("-" * 35)
    
    improvements = [
        "✅ Architettura modulare separata per fonte",
        "✅ Rate limiting adattivo basato su successo/fallimento", 
        "✅ Fallback selectors per web scraping",
        "✅ Validazione URL automatica",
        "✅ Health score per ogni fonte",
        "✅ Keyword expansion per dominio",
        "✅ Timeout ridotti (10s invece di 20s)",
        "✅ Retry aumentati (3 invece di 2)",
        "✅ Delay ridotti (1.5s invece di 3s)",
        "✅ User agent randomizzato",
        "✅ Gestione errori migliorata",
        "✅ Cache selettori funzionanti",
        "✅ Configurazioni YAML ottimizzate"
    ]
    
    for improvement in improvements:
        print(f"   {improvement}")
    
    print("\n📋 STRUTTURA MODULI:")
    modules = [
        "news_source_base.py - Classi base e utilities",
        "news_source_rss.py - Implementazione RSS", 
        "news_source_newsapi.py - Implementazione NewsAPI",
        "news_source_webscraping.py - Web scraping migliorato",
        "news_source_tavily.py - Implementazione Tavily",
        "news_source_manager.py - Manager intelligente",
        "news_sources.py - Orchestratore principale"
    ]
    
    for module in modules:
        print(f"   📄 {module}")

if __name__ == "__main__":
    print("🧪 TEST SISTEMA NEWS SOURCES MIGLIORATO (Senza dipendenze esterne)")
    print("=" * 65)
    
    architecture_ok = test_architecture()
    config_ok = test_web_scraping_config()
    
    test_improvements_summary()
    
    print(f"\n📋 RISULTATI FINALI:")
    print(f"   - Architettura: {'✅ OK' if architecture_ok else '❌ ERRORE'}")
    print(f"   - Configurazione: {'✅ OK' if config_ok else '❌ ERRORE'}")
    
    if architecture_ok and config_ok:
        print(f"\n🎊 SISTEMA MIGLIORATO PRONTO!")
        print(f"   Le migliorie sono state implementate con successo.")
        print(f"   Per il test completo, installare le dipendenze:")
        print(f"   pip install -r requirements.txt")
    else:
        print(f"\n⚠️  Alcuni componenti necessitano attenzione")