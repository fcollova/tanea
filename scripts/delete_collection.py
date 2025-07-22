#!/usr/bin/env python3
"""
Script dedicato per eliminare una collezione specifica di Weaviate
"""

import sys
import os
import asyncio

# Aggiungi src al path e scripts
script_dir = os.path.dirname(__file__)
src_path = os.path.join(script_dir, '..', 'src')
sys.path.insert(0, src_path)
sys.path.insert(0, script_dir)

from clean_databases import DatabaseCleaner

async def main():
    """Eliminazione collezione specifica"""
    print("🗑️  ELIMINAZIONE COLLEZIONE WEAVIATE")
    print("=" * 50)
    print()
    
    cleaner = None
    try:
        cleaner = DatabaseCleaner()
        await cleaner.delete_specific_collection()
    except KeyboardInterrupt:
        print("\n❌ Operazione interrotta dall'utente")
    except Exception as e:
        print(f"❌ Errore: {e}")
    finally:
        if cleaner:
            await cleaner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())