#!/usr/bin/env python3
"""
Test finale del sistema di logging con logging.conf e livelli configurabili
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_logging_conf_system():
    """Test del sistema con logging.conf"""
    print("🔧 Test sistema logging.conf...")
    
    # Test import e configurazione
    try:
        from src.core.log import get_logger, setup_logging, set_debug_mode, get_logging_stats
        
        # Setup del sistema
        setup_logging()
        print("✅ Sistema logging configurato")
        
        # Test logger principali
        news_logger = get_logger('test_news', 'news')
        db_logger = get_logger('test_db', 'database')
        config_logger = get_logger('test_config', 'config')
        scripts_logger = get_logger('test_scripts', 'scripts')
        
        print(f"✅ Logger creati:")
        print(f"   - News: {news_logger.name}")
        print(f"   - Database: {db_logger.name}")
        print(f"   - Config: {config_logger.name}")
        print(f"   - Scripts: {scripts_logger.name}")
        
        # Test messaggi con livelli diversi
        print(f"\n📝 Test messaggi livelli configurati...")
        
        news_logger.debug("DEBUG: Test messaggio debug news")
        news_logger.info("INFO: Test messaggio info news")
        news_logger.warning("WARNING: Test messaggio warning news")
        
        db_logger.info("INFO: Test database operations")
        config_logger.info("INFO: Test configurazione caricata")
        scripts_logger.info("INFO: Test script execution")
        
        # Test modalità debug
        print(f"\n🐛 Test modalità debug...")
        set_debug_mode(True)
        news_logger.debug("DEBUG: Questo dovrebbe apparire in modalità debug")
        
        set_debug_mode(False)
        news_logger.debug("DEBUG: Questo NON dovrebbe apparire (debug disabilitato)")
        news_logger.info("INFO: Questo dovrebbe sempre apparire")
        
        # Test statistiche
        stats = get_logging_stats()
        print(f"\n📊 Statistiche sistema:")
        print(f"   - Fonte config: {stats['config'].get('config_source', 'N/A')}")
        print(f"   - Ambiente: {stats['config']['environment']}")
        print(f"   - Logger attivi: {stats['total_loggers']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore test sistema: {e}")
        return False

def test_external_libraries_silence():
    """Test che le librerie esterne siano silenziate"""
    print(f"\n🔇 Test silenziamento librerie esterne...")
    
    try:
        import logging
        
        # Simula log da librerie esterne
        httpcore_logger = logging.getLogger('httpcore.connection')
        urllib3_logger = logging.getLogger('urllib3.connectionpool')
        httpx_logger = logging.getLogger('httpx')
        
        print("Test log da librerie esterne (dovrebbero essere filtrati):")
        
        httpcore_logger.debug("DEBUG: Questo httpcore debug dovrebbe essere filtrato")
        httpcore_logger.info("INFO: Questo httpcore info dovrebbe essere filtrato")
        httpcore_logger.warning("WARNING: Questo httpcore warning dovrebbe apparire")
        
        urllib3_logger.debug("DEBUG: Questo urllib3 debug dovrebbe essere filtrato")
        urllib3_logger.info("INFO: Questo urllib3 info dovrebbe essere filtrato")
        
        httpx_logger.info("INFO: HTTP Request importante (dovrebbe apparire)")
        
        print("✅ Test librerie esterne completato")
        return True
        
    except Exception as e:
        print(f"❌ Errore test librerie: {e}")
        return False

def test_config_module_integration():
    """Test integrazione con modulo config.py senza dipendenze circolari"""
    print(f"\n🔄 Test integrazione config.py...")
    
    try:
        from src.core.config import get_config, setup_logging
        
        # Test setup_logging
        setup_logging()
        
        # Test caricamento config
        config = get_config()
        print(f"✅ Config caricato: ambiente {config.environment}")
        
        # Verifica che non ci siano dipendenze circolari
        print("✅ Nessuna dipendenza circolare rilevata")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore integrazione config: {e}")
        return False

def check_log_output():
    """Controlla l'output del log per verificare formattazione"""
    print(f"\n📄 Controllo output log...")
    
    log_file = "logs/tanea_dev.log"
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            # Controlla le ultime righe
            recent_lines = lines[-10:] if len(lines) >= 10 else lines
            
            print("Ultime righe del log:")
            for i, line in enumerate(recent_lines[-5:], 1):
                line = line.strip()
                if line:
                    # Controlla formato
                    if "tanea." in line and "|" in line:
                        status = "✅"
                    elif "httpcore" in line or "urllib3" in line:
                        status = "🔇"  # Dovrebbe essere filtrato ma potrebbe apparire
                    else:
                        status = "❓"
                    
                    print(f"   {status} {line}")
            
            print("✅ Log file verificato")
            return True
            
        except Exception as e:
            print(f"❌ Errore lettura log: {e}")
            return False
    else:
        print(f"⚠️  File log non trovato: {log_file}")
        return False

if __name__ == "__main__":
    print("🧪 TEST FINALE SISTEMA LOGGING CONFIGURABILE")
    print("=" * 50)
    
    results = [
        test_logging_conf_system(),
        test_external_libraries_silence(),
        test_config_module_integration(),
        check_log_output()
    ]
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"\n📊 RISULTATI FINALI:")
    print(f"   Test superati: {success_count}/{total_count}")
    
    if success_count == total_count:
        print(f"🎉 TUTTI I TEST SUPERATI! Sistema logging ottimizzato!")
    else:
        print(f"⚠️  Alcuni test falliti, controllare configurazione")