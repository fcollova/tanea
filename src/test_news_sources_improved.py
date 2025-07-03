#!/usr/bin/env python3
"""
Test per il sistema di news sources migliorato
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.news_sources import create_default_news_manager, NewsQuery
from src.core.config import setup_logging

def test_improved_system():
    """Test completo del sistema migliorato"""
    print("🧪 TEST SISTEMA NEWS SOURCES MIGLIORATO")
    print("=" * 50)
    
    # Setup logging
    setup_logging()
    
    try:
        # Crea manager con nuova architettura
        print("\n📚 Inizializzazione manager...")
        manager = create_default_news_manager()
        
        # Mostra fonti disponibili
        available_sources = manager.get_available_sources()
        print(f"✅ Fonti disponibili: {available_sources}")
        
        # Test health report
        print("\n🏥 Health Report del sistema:")
        health_report = manager.get_health_report()
        print(f"   - Salute complessiva: {health_report['overall_health']:.2%}")
        print(f"   - Fonti funzionanti: {health_report['working_source_names']}")
        print(f"   - Fonti problematiche: {health_report['failing_source_names']}")
        
        # Test ricerca per dominio calcio
        print("\n⚽ Test ricerca dominio CALCIO...")
        query = NewsQuery(
            keywords=['calcio', 'Serie A'],
            domain='calcio',
            max_results=5,
            time_range='1d'
        )
        
        # Test ricerca ibrida (tutte le fonti)
        print("\n🔄 Test ricerca ibrida...")
        articles_hybrid = manager.search_hybrid(query)
        print(f"   Articoli trovati (ibrida): {len(articles_hybrid)}")
        
        for i, article in enumerate(articles_hybrid[:3], 1):
            print(f"   {i}. {article.title[:80]}... (fonte: {article.source})")
        
        # Test ricerca migliore fonte
        print("\n🎯 Test ricerca migliore fonte...")
        articles_best = manager.search_best_source(query)
        print(f"   Articoli trovati (migliore fonte): {len(articles_best)}")
        
        # Test statistiche fonti
        print("\n📊 Statistiche fonti:")
        stats = manager.get_source_stats()
        for source_name, source_stats in stats.items():
            print(f"   {source_name}:")
            print(f"     - Disponibile: {source_stats['available']}")
            print(f"     - Health Score: {source_stats['health_score']:.2f}")
            print(f"     - Affidabilità: {source_stats['reliability']:.2%}")
            print(f"     - Delay adattivo: {source_stats['adaptive_delay']:.1f}s")
        
        # Test web scraping specifico
        if 'scraping' in available_sources:
            print("\n🕷️  Test Web Scraping migliorato...")
            scraping_source = manager.sources['scraping']
            
            # Test health report scraping
            scraping_health = scraping_source.get_scraping_health_report()
            print(f"   - Siti totali configurati: {scraping_health['total_sites']}")
            print(f"   - Siti funzionanti: {scraping_health['working_sites']}")
            print(f"   - Siti problematici: {scraping_health['failing_sites']}")
            print(f"   - Success rate: {scraping_health['success_rate']:.2%}")
            
            # Test solo scraping
            articles_scraping = scraping_source.search_news(query)
            print(f"   - Articoli da scraping: {len(articles_scraping)}")
        
        print("\n🎉 Test completato con successo!")
        return True
        
    except Exception as e:
        print(f"\n❌ Errore durante il test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_webscraping_validation():
    """Test specifico per validazione web scraping"""
    print("\n🔍 TEST VALIDAZIONE WEB SCRAPING")
    print("-" * 30)
    
    try:
        from src.core.news_source_webscraping import WebScrapingSource
        
        scraping = WebScrapingSource()
        
        if not scraping.is_available():
            print("❌ Web scraping non disponibile")
            return False
        
        # Test validazione configurazione siti
        sites_config = scraping.scraping_config.get('sites', {})
        
        for site_key, site_config in list(sites_config.items())[:3]:  # Test primi 3 siti
            print(f"\n🌐 Validazione sito: {site_config.get('name', site_key)}")
            
            validation = scraping.validate_site_configuration(site_config)
            
            if validation['issues']:
                print(f"   ⚠️  Problemi trovati:")
                for issue in validation['issues']:
                    print(f"     - {issue}")
                    
            if validation['fixes']:
                print(f"   🔧 Fix suggeriti:")
                for fix_key, fix_value in validation['fixes'].items():
                    print(f"     - {fix_key}: {fix_value}")
            else:
                print(f"   ✅ Configurazione OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore validazione: {e}")
        return False

if __name__ == "__main__":
    success = test_improved_system()
    validation_success = test_webscraping_validation()
    
    print(f"\n📋 RISULTATI FINALI:")
    print(f"   - Test sistema: {'✅ SUCCESSO' if success else '❌ FALLITO'}")
    print(f"   - Test validazione: {'✅ SUCCESSO' if validation_success else '❌ FALLITO'}")
    
    if success and validation_success:
        print(f"\n🎊 TUTTI I TEST SUPERATI! Sistema migliorato funzionante!")
    else:
        print(f"\n⚠️  Alcuni test falliti, verificare configurazione")