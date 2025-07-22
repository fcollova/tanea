#!/usr/bin/env python3
"""
Quick Reset Script - Pulizia rapida completa dei database
"""

import sys
import os
import asyncio

# Aggiungi src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scripts.clean_databases import DatabaseCleaner

async def quick_reset():
    """Reset rapido completo: pulizia + creazione schemi domini attivi"""
    
    print("🚀 QUICK RESET - Pulizia completa database")
    print("=" * 50)
    
    cleaner = DatabaseCleaner()
    
    try:
        # 1. Pulizia completa
        print("🧹 Pulizia completa database...")
        success = await cleaner.clean_all(confirm=True)
        
        if not success:
            print("❌ Errore durante la pulizia")
            return False
        
        # 2. Creazione schemi domini attivi
        print("\n🏗️  Creazione schemi domini attivi...")
        schemas_created = await cleaner.create_fresh_schemas()
        
        if not schemas_created:
            print("⚠️  Nessuno schema creato")
        
        # 3. Verifica finale
        print("\n🔍 Verifica stato finale...")
        clean_verified = await cleaner.verify_clean_state()
        
        if clean_verified:
            print("\n✅ RESET COMPLETATO CON SUCCESSO!")
            print("   Il sistema è pronto per il crawler")
            return True
        else:
            print("\n⚠️  Reset completato ma verifica fallita")
            return False
            
    except Exception as e:
        print(f"\n❌ ERRORE durante il reset: {e}")
        return False
    finally:
        await cleaner.cleanup()

if __name__ == "__main__":
    asyncio.run(quick_reset())