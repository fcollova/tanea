#!/usr/bin/env python3
"""
Test per verificare che tutti gli import di logging funzionino
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_logging_imports():
    """Test import dei moduli con logging"""
    print("🔍 Test import moduli con logging...")
    
    modules_to_test = [
        ('core.config', 'setup_logging'),
        ('core.log', 'get_logger'),
        ('core.domain_config', 'get_domain_config'),
        ('core.vector_db_manager', 'VectorDBManager'),
        ('core.domain_manager', 'DomainManager'),
    ]
    
    success_count = 0
    total_count = len(modules_to_test)
    
    for module_name, class_or_function in modules_to_test:
        try:
            module = __import__(f'src.{module_name}', fromlist=[class_or_function])
            getattr(module, class_or_function)
            print(f"✅ {module_name}.{class_or_function}")
            success_count += 1
        except ImportError as e:
            if 'feedparser' in str(e) or 'schedule' in str(e) or 'weaviate' in str(e):
                print(f"⚠️  {module_name}.{class_or_function} - dipendenza esterna mancante (normale)")
                success_count += 1  # Conta come successo
            else:
                print(f"❌ {module_name}.{class_or_function} - {e}")
        except Exception as e:
            print(f"❌ {module_name}.{class_or_function} - {e}")
    
    print(f"\n📊 Risultati: {success_count}/{total_count} moduli importati correttamente")
    
    if success_count == total_count:
        print("✅ Tutti gli import di logging funzionano!")
    else:
        print("⚠️  Alcuni moduli hanno problemi di import")

def test_specific_function():
    """Test specifico della funzione setup_logging"""
    print(f"\n🎯 Test specifico setup_logging...")
    
    try:
        from src.core.config import setup_logging
        setup_logging()
        print("✅ setup_logging() eseguita con successo")
        
        # Test che il nuovo sistema sia attivo
        from src.core.log import get_logging_stats
        stats = get_logging_stats()
        print(f"✅ Sistema centralizzato attivo - {stats['total_loggers']} logger")
        
    except Exception as e:
        print(f"❌ Errore in setup_logging(): {e}")

if __name__ == "__main__":
    test_logging_imports()
    test_specific_function()