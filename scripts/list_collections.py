#!/usr/bin/env python3
"""
Script dedicato per listare le collezioni Weaviate
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
    """Lista collezioni Weaviate"""
    cleaner = None
    try:
        cleaner = DatabaseCleaner()
        await cleaner.list_weaviate_collections()
    except KeyboardInterrupt:
        print("\n❌ Operazione interrotta dall'utente")
    except Exception as e:
        print(f"❌ Errore: {e}")
    finally:
        if cleaner:
            await cleaner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())