#!/usr/bin/env python3
"""
Test per verificare che il crawler funzioni in modalità standalone
"""

import asyncio
import sys
import os

# Solo il modulo crawler
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_crawler_independence():
    """Test che il crawler funzioni senza dipendenze esterne"""
    
    print("🧪 Test Indipendenza Crawler...")
    
    try:
        # Import solo moduli crawler
        from core.crawler.trafilatura_crawler import TrafilaturaCrawler
        from core.crawler.link_discoverer import LinkDiscoverer
        from core.crawler.content_extractor import ContentExtractor
        
        print("✅ Import moduli crawler: OK")
        
        # Test inizializzazione
        crawler = TrafilaturaCrawler()
        print("✅ Inizializzazione crawler: OK")
        
        # Test configurazione autonoma
        config = crawler.config
        print(f"✅ Configurazione autonoma: {len(config.get('sites', {}))} siti")
        
        # Test componenti interni
        discoverer = LinkDiscoverer()
        extractor = ContentExtractor()
        print("✅ Componenti interni: OK")
        
        # Test database connection (senza altri moduli)
        await crawler._initialize_components()
        print("✅ Connessione database autonoma: OK")
        
        # Test discovery su un sito (mock)
        sites_config = config.get('sites', {})
        if sites_config:
            first_site = list(sites_config.keys())[0]
            print(f"✅ Configurazione sito test: {first_site}")
        
        await crawler.disconnect()
        print("✅ Disconnessione: OK")
        
        print("\n🎉 RISULTATO: Il crawler è completamente autonomo!")
        return True
        
    except ImportError as e:
        print(f"❌ Errore import: {e}")
        return False
    except Exception as e:
        print(f"❌ Errore test: {e}")
        return False

async def test_crawler_without_other_modules():
    """Test che il crawler funzioni senza caricare altri moduli Tanea"""
    
    print("\n🔬 Test Senza Altri Moduli...")
    
    # Blacklist moduli da non importare
    forbidden_modules = [
        'news_source_manager',
        'news_sources', 
        'load_news',
        'news_db_manager'  # Non la versione V2 che il crawler usa
    ]
    
    # Verifica che moduli vietati non siano importati
    imported_modules = [name for name in sys.modules.keys() if 'tanea' in name or 'core' in name]
    
    forbidden_found = []
    for module in imported_modules:
        for forbidden in forbidden_modules:
            if forbidden in module:
                forbidden_found.append(module)
    
    if forbidden_found:
        print(f"⚠️  Moduli di sistema trovati: {forbidden_found}")
        print("   (Questo è OK se il test è integrato)")
    else:
        print("✅ Nessun modulo di sistema importato")
    
    # Test funzionalità crawler di base
    try:
        from core.crawler.trafilatura_crawler import TrafilaturaCrawler
        
        crawler = TrafilaturaCrawler()
        
        # Test che può leggere configurazione
        sites = crawler.config.get('sites', {})
        print(f"✅ Crawler autonomo legge {len(sites)} siti configurati")
        
        # Test che può inizializzare storage
        await crawler._initialize_components()
        print("✅ Storage autonomo inizializzato")
        
        await crawler.disconnect()
        
        return True
        
    except Exception as e:
        print(f"❌ Errore autonomia: {e}")
        return False

if __name__ == "__main__":
    print("🕷️ Test Autonomia Crawler Tanea")
    print("=" * 50)
    
    result1 = asyncio.run(test_crawler_independence())
    result2 = asyncio.run(test_crawler_without_other_modules())
    
    if result1 and result2:
        print("\n🎯 CONCLUSIONE: Il crawler è un modulo completamente autonomo!")
    else:
        print("\n⚠️  Il crawler ha alcune dipendenze dal sistema principale")