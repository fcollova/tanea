#!/usr/bin/env python3
"""
Test Database Connection - Verifica connessione PostgreSQL
"""

import asyncio
import sys
from pathlib import Path

# Aggiungi src al path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.core.config import get_database_config

async def test_postgresql_connection():
    """Test connessione PostgreSQL con asyncpg"""
    print("🔗 Test Connessione PostgreSQL")
    print("-" * 30)
    
    try:
        import asyncpg
        
        db_config = get_database_config()
        db_url = db_config['url']
        
        print(f"Database URL: {db_url}")
        print("Connessione in corso...")
        
        # Test connessione
        conn = await asyncpg.connect(db_url)
        
        # Test query
        version = await conn.fetchval('SELECT version()')
        print(f"✅ Connessione riuscita!")
        print(f"PostgreSQL Version: {version.split(',')[0]}")
        
        # Test privileges
        result = await conn.fetchval("SELECT current_user, session_user")
        print(f"Utente connesso: {result}")
        
        # Test database existence/creation
        db_name = db_url.split('/')[-1].split('?')[0]
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", 
            db_name
        )
        
        if exists:
            print(f"✅ Database '{db_name}' esiste")
        else:
            print(f"⚠️ Database '{db_name}' non esiste")
            
            # Prova a creare database
            try:
                await conn.execute(f'CREATE DATABASE "{db_name}"')
                print(f"✅ Database '{db_name}' creato")
            except Exception as e:
                print(f"❌ Impossibile creare database: {e}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Errore connessione: {e}")
        return False

async def test_prisma_connection():
    """Test connessione Prisma"""
    print("\n🔧 Test Connessione Prisma")
    print("-" * 25)
    
    try:
        from prisma import Prisma
        
        db = Prisma()
        await db.connect()
        
        # Test query semplice
        result = await db.query_raw('SELECT 1 as test')
        print(f"✅ Prisma connesso: {result}")
        
        await db.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ Errore Prisma: {e}")
        print("Potrebbe essere necessario eseguire: prisma generate && prisma db push")
        return False

async def test_weaviate_connection():
    """Test connessione Weaviate"""
    print("\n🧠 Test Connessione Weaviate")
    print("-" * 28)
    
    try:
        import weaviate
        from src.core.config import get_weaviate_config
        
        weaviate_config = get_weaviate_config()
        
        # Usa Weaviate client v4
        from urllib.parse import urlparse
        parsed_url = urlparse(weaviate_config['url'])
        
        client = weaviate.connect_to_local(
            host=parsed_url.hostname,
            port=parsed_url.port or 8080
        )
        
        # Test health
        if client.is_ready():
            print("✅ Weaviate connesso e pronto")
            
            # Informazioni cluster
            meta = client.get_meta()
            print(f"Weaviate Version: {meta.get('version', 'Unknown')}")
            
            client.close()
            return True
        else:
            print("❌ Weaviate non pronto")
            client.close()
            return False
            
    except Exception as e:
        print(f"❌ Errore Weaviate: {e}")
        print("Assicurati che Weaviate sia avviato: docker-compose up weaviate")
        return False

async def main():
    """Test completo connessioni"""
    print("🧪 Test Connessioni Database Tanea")
    print("=" * 40)
    
    results = {}
    
    # Test PostgreSQL
    results['postgresql'] = await test_postgresql_connection()
    
    # Test Prisma
    results['prisma'] = await test_prisma_connection()
    
    # Test Weaviate
    results['weaviate'] = await test_weaviate_connection()
    
    # Riepilogo
    print("\n" + "=" * 40)
    print("📊 RIEPILOGO TEST CONNESSIONI")
    print("=" * 40)
    
    for service, success in results.items():
        status = "✅ OK" if success else "❌ FAIL"
        print(f"{status:8} {service.title()}")
    
    all_ok = all(results.values())
    
    if all_ok:
        print("\n🎉 Tutte le connessioni funzionano!")
        print("Puoi procedere con: python setup_hybrid_architecture.py")
    else:
        print("\n⚠️ Alcune connessioni hanno problemi.")
        print("Risolvi i problemi prima di procedere.")
    
    return all_ok

if __name__ == "__main__":
    asyncio.run(main())