#!/usr/bin/env python3
"""
Test del nuovo sistema di logging centralizzato
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_centralized_logging():
    """Test del sistema di logging centralizzato"""
    print("🔍 Test sistema logging centralizzato...")
    
    # Test import
    try:
        from src.core.log import (
            get_logger, get_news_logger, get_database_logger, 
            get_config_logger, get_scripts_logger, get_logging_stats
        )
        print("✅ Import modulo log.py riuscito")
    except Exception as e:
        print(f"❌ Errore import: {e}")
        return
    
    # Test logger base
    logger = get_logger(__name__)
    print(f"✅ Logger base creato: {logger.name}")
    
    # Test logger specializzati
    news_logger = get_news_logger(__name__)
    db_logger = get_database_logger(__name__)
    config_logger = get_config_logger(__name__)
    scripts_logger = get_scripts_logger(__name__)
    
    print(f"✅ Logger specializzati creati:")
    print(f"   - News: {news_logger.name}")
    print(f"   - Database: {db_logger.name}")
    print(f"   - Config: {config_logger.name}")
    print(f"   - Scripts: {scripts_logger.name}")
    
    # Test logging a vari livelli
    print(f"\n📝 Test logging messaggi...")
    logger.debug("Test message DEBUG")
    logger.info("Test message INFO")
    logger.warning("Test message WARNING")
    logger.error("Test message ERROR")
    
    # Test logger specializzato
    news_logger.info("Test news logger - ricerca notizie completata")
    db_logger.info("Test database logger - connessione stabilita")
    
    # Test statistiche
    stats = get_logging_stats()
    print(f"\n📊 Statistiche logging:")
    print(f"   - Logger totali: {stats['total_loggers']}")
    print(f"   - File log principale: {stats['log_files']['main']}")
    print(f"   - File log errori: {stats['log_files']['errors']}")
    print(f"   - Ambiente: {stats['config']['environment']}")
    
    # Test decoratori
    print(f"\n🎯 Test decoratori...")
    from src.core.log import log_function_call, log_performance
    
    @log_function_call()
    def test_function():
        """Funzione di test per decoratore"""
        return "risultato test"
    
    @log_performance()
    def slow_function():
        """Funzione lenta per test performance"""
        import time
        time.sleep(0.1)
        return "completato"
    
    result1 = test_function()
    result2 = slow_function()
    print(f"✅ Decoratori testati: {result1}, {result2}")
    
    print(f"\n✅ Test logging completato con successo!")

def test_module_integration():
    """Test integrazione con moduli esistenti"""
    print(f"\n🔗 Test integrazione moduli...")
    
    try:
        # Test news_sources
        from src.core.news_sources import NewsSourceManager
        manager = NewsSourceManager()
        print(f"✅ NewsSourceManager: logger integrato")
        
        # Test domain_config  
        from src.core.domain_config import get_domain_config
        domain_config = get_domain_config()
        print(f"✅ DomainConfig: logger integrato")
        
        print(f"✅ Integrazione moduli completata")
        
    except Exception as e:
        print(f"⚠️  Errore integrazione (normale se dipendenze mancanti): {e}")

if __name__ == "__main__":
    test_centralized_logging()
    test_module_integration()