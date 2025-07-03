#!/usr/bin/env python3
"""
Script di test per verificare la coerenza tra domains.yaml e le configurazioni di scraping
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.domain_config import get_domain_config
import yaml

def test_domain_consistency():
    """Test di coerenza tra configurazioni"""
    print("🔍 Test di coerenza configurazioni domini...")
    
    # 1. Carica configurazione domini
    domain_config = get_domain_config()
    all_domains = domain_config.get_all_domains()
    active_domains = domain_config.get_active_domains()
    
    print(f"\n📋 Domini configurati: {all_domains}")
    print(f"✅ Domini attivi: {active_domains}")
    
    # 2. Verifica web_scraping.yaml
    web_scraping_path = os.path.join(os.path.dirname(__file__), 'config', 'web_scraping.yaml')
    try:
        with open(web_scraping_path, 'r', encoding='utf-8') as f:
            web_scraping_config = yaml.safe_load(f)
        
        web_domain_mapping = web_scraping_config.get('domain_mapping', {})
        web_configured_domains = set(web_domain_mapping.keys())
        
        print(f"\n🌐 Domini in web_scraping.yaml: {list(web_configured_domains)}")
        
        # Controlla coerenza
        missing_in_web = set(all_domains) - web_configured_domains
        extra_in_web = web_configured_domains - set(all_domains)
        
        if missing_in_web:
            print(f"⚠️  Domini mancanti in web_scraping.yaml: {missing_in_web}")
        if extra_in_web:
            print(f"⚠️  Domini extra in web_scraping.yaml: {extra_in_web}")
        
        if not missing_in_web and not extra_in_web:
            print("✅ Web scraping mapping coerente con domains.yaml")
    
    except Exception as e:
        print(f"❌ Errore lettura web_scraping.yaml: {e}")
    
    # 3. Verifica rss_feeds.yaml
    rss_feeds_path = os.path.join(os.path.dirname(__file__), 'config', 'rss_feeds.yaml')
    try:
        with open(rss_feeds_path, 'r', encoding='utf-8') as f:
            rss_config = yaml.safe_load(f)
        
        rss_domain_mapping = rss_config.get('domain_mapping', {})
        rss_configured_domains = set(rss_domain_mapping.keys())
        
        print(f"\n📡 Domini in rss_feeds.yaml: {list(rss_configured_domains)}")
        
        # Controlla coerenza
        missing_in_rss = set(all_domains) - rss_configured_domains
        extra_in_rss = rss_configured_domains - set(all_domains)
        
        if missing_in_rss:
            print(f"⚠️  Domini mancanti in rss_feeds.yaml: {missing_in_rss}")
        if extra_in_rss:
            print(f"⚠️  Domini extra in rss_feeds.yaml: {extra_in_rss}")
        
        if not missing_in_rss and not extra_in_rss:
            print("✅ RSS feeds mapping coerente con domains.yaml")
    
    except Exception as e:
        print(f"❌ Errore lettura rss_feeds.yaml: {e}")
    
    # 4. Test NewsSourceManager
    try:
        from src.core.news_sources import NewsSourceManager
        
        manager = NewsSourceManager()
        manager_domains = set(manager.domain_preferences.keys())
        
        print(f"\n🔧 Domini in NewsSourceManager: {list(manager_domains)}")
        
        # Controlla coerenza con domini attivi
        missing_in_manager = set(active_domains) - manager_domains
        extra_in_manager = manager_domains - set(active_domains)
        
        if missing_in_manager:
            print(f"⚠️  Domini attivi mancanti in NewsSourceManager: {missing_in_manager}")
        if extra_in_manager:
            print(f"⚠️  Domini extra in NewsSourceManager: {extra_in_manager}")
        
        if not missing_in_manager and not extra_in_manager:
            print("✅ NewsSourceManager coerente con domini attivi")
            
        # 5. Test che le fonti usino domains.yaml
        print(f"\n🔍 Test uso domains.yaml nelle fonti:")
        
        # Test che domain_config sia importato e usato
        import src.core.news_sources as ns_module
        source_code = open('src/core/news_sources.py', 'r').read()
        
        checks = [
            ('domain_config import', 'from .domain_config import' in source_code),
            ('get_domain_config usage', 'get_domain_config()' in source_code),
            ('domain validation', 'domain_config.validate_domain' in source_code),
            ('domain keywords', 'domain_config.get_domain_keywords' in source_code),
            ('active domains', 'domain_config.get_active_domains' in source_code)
        ]
        
        for check_name, result in checks:
            status = "✅" if result else "❌"
            print(f"  {status} {check_name}")
    
    except Exception as e:
        print(f"❌ Errore test NewsSourceManager: {e}")
    
    # 5. Test dettagliato per domini attivi
    print(f"\n📊 Dettagli domini attivi:")
    for domain in active_domains:
        info = domain_config.get_domain_info(domain)
        keywords_count = len(domain_config.get_domain_keywords(domain))
        max_results = domain_config.get_domain_max_results(domain)
        
        print(f"  • {domain}: {keywords_count} keywords, max {max_results} risultati")
        print(f"    Descrizione: {info.get('description', 'N/A')}")

if __name__ == "__main__":
    test_domain_consistency()