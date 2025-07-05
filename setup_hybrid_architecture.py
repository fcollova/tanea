#!/usr/bin/env python3
"""
Setup Hybrid Architecture - Inizializza e testa architettura ibrida
PostgreSQL + Weaviate + Trafilatura Crawler
"""

import asyncio
import os
import sys
from pathlib import Path

# Aggiungi src al path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.core.storage.database_manager import DatabaseManager
from src.core.crawler.trafilatura_crawler import TrafilaturaCrawler
from src.core.news_db_manager_v2 import NewsVectorDBV2
from src.core.config import get_database_config, get_weaviate_config

async def setup_database():
    """Setup database PostgreSQL"""
    print("🔧 Setup Database PostgreSQL...")
    
    try:
        # Test connessione database
        db_config = get_database_config()
        print(f"Database URL: {db_config['url']}")
        
        # Inizializza database manager
        async with DatabaseManager('dev') as db_manager:
            # Test connessioni
            health = await db_manager.health_check()
            print(f"Health Check: {health}")
            
            if health['postgresql']:
                print("✅ PostgreSQL connesso correttamente")
            else:
                print("❌ Errore connessione PostgreSQL")
                return False
            
            if health['weaviate']:
                print("✅ Weaviate connesso correttamente")
            else:
                print("❌ Errore connessione Weaviate")
                return False
            
            return True
            
    except Exception as e:
        print(f"❌ Errore setup database: {e}")
        return False

async def setup_sites_from_config():
    """Inizializza siti dal config YAML"""
    print("🏗️ Setup Siti da Configurazione...")
    
    try:
        async with DatabaseManager('dev') as db_manager:
            # Carica config siti
            import yaml
            config_path = src_path / "config" / "web_scraping.yaml"
            
            with open(config_path, 'r', encoding='utf-8') as f:
                sites_config = yaml.safe_load(f)
            
            sites = sites_config.get('sites', {})
            print(f"Trovati {len(sites)} siti nel config")
            
            # Inizializza siti nel database
            for site_name, site_config in sites.items():
                existing = await db_manager.link_db.get_site_by_name(site_name)
                if not existing:
                    await db_manager.link_db.create_site(
                        name=site_name,
                        base_url=site_config['base_url'],
                        config=site_config
                    )
                    print(f"✅ Sito {site_name} aggiunto")
                else:
                    # Aggiorna config
                    await db_manager.link_db.update_site_config(existing.id, site_config)
                    print(f"🔄 Sito {site_name} aggiornato")
            
            return True
            
    except Exception as e:
        print(f"❌ Errore setup siti: {e}")
        return False

async def test_crawler():
    """Test crawler trafilatura"""
    print("🕷️ Test Crawler Trafilatura...")
    
    try:
        async with TrafilaturaCrawler('dev') as crawler:
            # Test crawling di un singolo sito
            print("Test crawling sito ANSA...")
            stats = await crawler.crawl_site('ansa')
            
            print(f"Statistiche crawling: {stats}")
            
            if stats.get('articles_extracted', 0) > 0:
                print("✅ Crawler funziona correttamente")
                return True
            else:
                print("⚠️ Crawler completato ma nessun articolo estratto")
                return True
            
    except Exception as e:
        print(f"❌ Errore test crawler: {e}")
        return False

async def test_search():
    """Test ricerca semantica"""
    print("🔍 Test Ricerca Semantica...")
    
    try:
        async with NewsVectorDBV2('dev') as news_db:
            # Test ricerca
            results = await news_db.search_news(
                domain="calcio",
                keywords=["Serie A", "calcio"],
                max_results=3
            )
            
            print(f"Trovati {len(results)} articoli")
            
            for i, article in enumerate(results):
                print(f"{i+1}. {article['title'][:80]}...")
                print(f"   Fonte: {article['source']}")
                print(f"   Score: {article.get('score', 0):.2f}")
                print()
            
            if results:
                print("✅ Ricerca semantica funziona")
                return True
            else:
                print("⚠️ Nessun risultato trovato (database vuoto?)")
                return True
            
    except Exception as e:
        print(f"❌ Errore test ricerca: {e}")
        return False

async def test_full_workflow():
    """Test workflow completo"""
    print("🔄 Test Workflow Completo...")
    
    try:
        async with NewsVectorDBV2('dev') as news_db:
            # 1. Update dominio calcio
            print("1. Update dominio calcio...")
            result = await news_db.update_domain_news("calcio")
            print(f"Risultato update: {result}")
            
            # 2. Ricerca dopo update
            print("2. Ricerca dopo update...")
            results = await news_db.search_news(
                domain="calcio",
                keywords=["Inter", "Juventus"],
                max_results=2
            )
            
            print(f"Trovati {len(results)} articoli dopo update")
            
            # 3. Statistiche sistema
            print("3. Statistiche sistema...")
            stats = await news_db.get_system_stats()
            print(f"Stats database: {stats.get('database_stats', {})}")
            
            print("✅ Workflow completo testato")
            return True
            
    except Exception as e:
        print(f"❌ Errore test workflow: {e}")
        return False

async def main():
    """Setup e test completo architettura ibrida"""
    print("🚀 Setup Architettura Ibrida Tanea")
    print("=" * 50)
    
    # Step 1: Database Setup
    if not await setup_database():
        print("❌ Setup database fallito, interrompo")
        return False
    
    # Step 2: Sites Setup  
    if not await setup_sites_from_config():
        print("❌ Setup siti fallito, continuo comunque...")
    
    # Step 3: Test Crawler
    if not await test_crawler():
        print("❌ Test crawler fallito, continuo comunque...")
    
    # Step 4: Test Search
    if not await test_search():
        print("❌ Test ricerca fallito, continuo comunque...")
    
    # Step 5: Test Full Workflow
    if not await test_full_workflow():
        print("❌ Test workflow fallito")
    
    print("=" * 50)
    print("🎉 Setup completato!")
    print()
    print("Prossimi passi:")
    print("1. Avvia PostgreSQL: sudo service postgresql start")
    print("2. Avvia Weaviate: docker-compose up weaviate")
    print("3. Esegui migrations: prisma db push")
    print("4. Test manuale: python test_hybrid_architecture.py")
    
    return True

if __name__ == "__main__":
    asyncio.run(main())