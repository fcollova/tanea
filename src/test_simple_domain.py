#!/usr/bin/env python3
"""
Test semplificato per verificare l'uso di domains.yaml
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_domain_usage():
    """Test che verifica l'uso di domains.yaml nel codice"""
    print("🔍 Test uso domains.yaml nel codice...")
    
    # Leggi il codice sorgente
    with open('src/core/news_sources.py', 'r') as f:
        source_code = f.read()
    
    # Controlli specifici
    checks = [
        ('Import domain_config', 'from .domain_config import' in source_code),
        ('Uso get_domain_config()', 'get_domain_config()' in source_code),
        ('Validazione domini', 'domain_config.validate_domain' in source_code),
        ('Keywords da domini', 'domain_config.get_domain_keywords' in source_code),
        ('Domini attivi', 'domain_config.get_active_domains' in source_code),
        ('Commenti aggiornati', 'basato su domains.yaml' in source_code),
        ('Fallback dinamico', 'all_domains = domain_config.get_all_domains()' in source_code)
    ]
    
    print("\n📋 Verifiche nel codice:")
    all_passed = True
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"  {status} {check_name}")
        if not result:
            all_passed = False
    
    # Conta occorrenze di domain_config
    domain_config_count = source_code.count('domain_config.')
    get_domain_config_count = source_code.count('get_domain_config()')
    
    print(f"\n📊 Statistiche uso:")
    print(f"  • Chiamate domain_config.*: {domain_config_count}")
    print(f"  • Chiamate get_domain_config(): {get_domain_config_count}")
    
    if all_passed and domain_config_count > 0:
        print(f"\n✅ Tutte le fonti sono armonizzate con domains.yaml!")
    else:
        print(f"\n⚠️  Alcune verifiche sono fallite")
    
    # Test domain_config module
    try:
        from src.core.domain_config import get_domain_config
        domain_config = get_domain_config()
        domains = domain_config.get_all_domains()
        active = domain_config.get_active_domains()
        
        print(f"\n🎯 Test modulo domain_config:")
        print(f"  ✅ Caricamento riuscito")
        print(f"  ✅ Domini trovati: {len(domains)}")
        print(f"  ✅ Domini attivi: {len(active)}")
        
        if 'calcio' in domains:
            keywords = domain_config.get_domain_keywords('calcio')
            print(f"  ✅ Keywords calcio: {len(keywords)}")
    
    except Exception as e:
        print(f"\n❌ Errore test domain_config: {e}")

if __name__ == "__main__":
    test_domain_usage()