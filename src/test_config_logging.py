#!/usr/bin/env python3
"""
Test specifico per verificare che config.py usi il sistema di logging centralizzato
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_config_logging():
    """Test che config.py usi il logging centralizzato"""
    print("🔍 Test logging centralizzato in config.py...")
    
    # Test 1: Verifica che il logger sia aggiornato automaticamente
    print("\n1️⃣ Test auto-upgrade logger...")
    
    # Prima importa config (che dovrebbe auto-upgradare il logger)
    from src.core.config import get_config, logger as config_logger
    
    # Verifica che il logger sia quello centralizzato
    logger_name = config_logger.name
    print(f"   Logger name: {logger_name}")
    
    if "tanea.config" in logger_name:
        print("   ✅ Logger usa naming convention centralizzato")
    else:
        print("   ❌ Logger NON usa naming convention centralizzato")
    
    # Test 2: Verifica funzionalità setup_logging
    print("\n2️⃣ Test setup_logging...")
    
    from src.core.config import setup_logging
    setup_logging()
    print("   ✅ setup_logging() eseguito senza errori")
    
    # Test 3: Verifica che i log vengano scritti correttamente
    print("\n3️⃣ Test scrittura log...")
    
    config_logger.info("Test message da config.py usando logger centralizzato")
    config_logger.warning("Test warning da config.py")
    
    # Test 4: Verifica che Config class usi il logger aggiornato  
    print("\n4️⃣ Test Config class...")
    
    config = get_config()
    print(f"   ✅ Config caricato: ambiente {config.environment}")
    
    # Test 5: Statistiche del sistema centralizzato
    print("\n5️⃣ Test statistiche sistema centralizzato...")
    
    try:
        from src.core.log import get_logging_stats
        stats = get_logging_stats()
        
        print(f"   Logger totali: {stats['total_loggers']}")
        print(f"   Logger config presenti: {[name for name in stats['logger_names'] if 'config' in name]}")
        
        # Verifica che ci sia almeno un logger config
        config_loggers = [name for name in stats['logger_names'] if 'config' in name]
        if config_loggers:
            print("   ✅ Logger config registrati nel sistema centralizzato")
        else:
            print("   ⚠️  Nessun logger config nel sistema centralizzato")
            
    except Exception as e:
        print(f"   ❌ Errore statistiche: {e}")
    
    print(f"\n✅ Test config.py logging completato!")

def test_logger_output_format():
    """Test che il formato di output sia quello centralizzato"""
    print(f"\n🎯 Test formato output...")
    
    from src.core.config import logger
    
    # Genera alcuni log di test
    logger.debug("DEBUG: Test formato log centralizzato")
    logger.info("INFO: Test formato log centralizzato") 
    logger.warning("WARNING: Test formato log centralizzato")
    
    print("✅ Log generati - controllare file logs/tanea_dev.log per formato")
    
    # Verifica che il file di log esista
    log_file = "logs/tanea_dev.log"
    if os.path.exists(log_file):
        print(f"✅ File log trovato: {log_file}")
        
        # Leggi le ultime righe per verificare il formato
        with open(log_file, 'r') as f:
            lines = f.readlines()
            if lines:
                last_line = lines[-1].strip()
                if "tanea.config" in last_line and "|" in last_line:
                    print("✅ Formato log centralizzato confermato")
                else:
                    print(f"⚠️  Formato log da verificare: {last_line}")
    else:
        print(f"⚠️  File log non trovato: {log_file}")

if __name__ == "__main__":
    test_config_logging()
    test_logger_output_format()