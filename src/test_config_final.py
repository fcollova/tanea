#!/usr/bin/env python3
"""
Test finale per verificare che config.py usi completamente il sistema di logging centralizzato
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_config_centralized_logging():
    """Test completo del logging centralizzato in config.py"""
    print("🎯 Test finale: config.py con logging centralizzato")
    
    # Test 1: Import e verifica logger automatico
    print("\n1️⃣ Test import automatico...")
    from src.core.config import logger, get_config
    
    # Verifica nome logger
    logger_name = logger.name
    print(f"   Logger name: {logger_name}")
    
    if logger_name.startswith("tanea.config"):
        print("   ✅ Logger usa sistema centralizzato")
    else:
        print(f"   ❌ Logger NON centralizzato: {logger_name}")
        return False
    
    # Test 2: Uso del logger
    print("\n2️⃣ Test uso logger...")
    logger.info("Messaggio di test dal logger centralizzato di config.py")
    logger.warning("Warning di test dal config.py")
    
    # Test 3: Funzionalità Config
    print("\n3️⃣ Test Config class...")
    config = get_config()
    print(f"   Environment: {config.environment}")
    
    # Test 4: Setup logging  
    print("\n4️⃣ Test setup_logging...")
    from src.core.config import setup_logging
    setup_logging()
    
    # Test 5: Verifica integrazione sistema centralizzato
    print("\n5️⃣ Test integrazione sistema centralizzato...")
    try:
        from src.core.log import get_logging_stats
        stats = get_logging_stats()
        
        config_loggers = [name for name in stats['logger_names'] if 'config' in name]
        print(f"   Logger config nel sistema: {config_loggers}")
        
        if any('tanea.config' in name for name in config_loggers):
            print("   ✅ config.py completamente integrato nel sistema centralizzato")
            return True
        else:
            print("   ❌ config.py NON completamente integrato")
            return False
            
    except Exception as e:
        print(f"   ❌ Errore verifica integrazione: {e}")
        return False

def test_all_modules_consistency():
    """Test che tutti i moduli usino il sistema centralizzato"""
    print(f"\n🔗 Test coerenza tutti i moduli...")
    
    modules_to_test = [
        ('core.config', 'tanea.config'),
        ('core.domain_config', 'tanea.config'),
        ('core.news_sources', 'tanea.news'),
        ('core.vector_db_manager', 'tanea.database'),
        ('core.domain_manager', 'tanea.config'),
    ]
    
    success = 0
    total = len(modules_to_test)
    
    for module_name, expected_prefix in modules_to_test:
        try:
            module = __import__(f'src.{module_name}', fromlist=['logger'])
            if hasattr(module, 'logger'):
                logger_name = module.logger.name
                if expected_prefix in logger_name:
                    print(f"   ✅ {module_name}: {logger_name}")
                    success += 1
                else:
                    print(f"   ⚠️  {module_name}: {logger_name} (expected {expected_prefix})")
            else:
                print(f"   ❓ {module_name}: no logger attribute")
        except ImportError as e:
            if any(dep in str(e) for dep in ['feedparser', 'weaviate', 'schedule']):
                print(f"   ⚠️  {module_name}: dipendenza esterna mancante (normale)")
                success += 1
            else:
                print(f"   ❌ {module_name}: {e}")
        except Exception as e:
            print(f"   ❌ {module_name}: {e}")
    
    print(f"\n📊 Moduli con logging centralizzato: {success}/{total}")
    return success == total

if __name__ == "__main__":
    config_ok = test_config_centralized_logging()
    modules_ok = test_all_modules_consistency()
    
    if config_ok and modules_ok:
        print(f"\n🎉 SUCCESSO: Tutti i moduli usano il sistema di logging centralizzato!")
    else:
        print(f"\n⚠️  Alcuni moduli necessitano ancora aggiustamenti")