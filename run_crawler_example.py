#!/usr/bin/env python3
"""
Esempio di esecuzione crawler Tanea in modalità programmatica
"""

import asyncio
import sys
import os

# Aggiungi src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.crawler.trafilatura_crawler import TrafilaturaCrawler
from core.storage.database_manager import DatabaseManager
from core.domain_manager import DomainManager

async def run_crawler_example():
    """Esempio completo di utilizzo crawler"""
    
    print("🕷️ Avvio Crawler Tanea...")
    
    # 1. Inizializza componenti
    crawler = TrafilaturaCrawler()
    domain_manager = DomainManager()
    
    try:
        # 2. Verifica domini attivi
        active_domains = domain_manager.get_domain_list(active_only=True)
        print(f"📂 Domini attivi: {active_domains}")
        
        if not active_domains:
            print("❌ Nessun dominio attivo configurato")
            return
        
        # 3. Crawling di un dominio specifico
        domain = active_domains[0]  # Prende il primo dominio attivo
        print(f"🎯 Crawling dominio: {domain}")
        
        stats = await crawler.crawl_domain(domain)
        
        # 4. Risultati
        print("\n📊 Risultati Crawling:")
        print(f"  • Siti processati: {stats['sites_processed']}")
        print(f"  • Link scoperti: {stats['links_discovered']}")
        print(f"  • Link crawlati: {stats['links_crawled']}")
        print(f"  • Articoli estratti: {stats['articles_extracted']}")
        print(f"  • Errori: {stats['errors']}")
        
        # 5. Test ricerca semantica
        if stats['articles_extracted'] > 0:
            print("\n🔍 Test ricerca semantica...")
            db_manager = DatabaseManager()
            await db_manager.connect()
            
            domain_config = domain_manager.get_domain(domain)
            keywords = domain_config.keywords[:2] if domain_config else ["news"]
            
            results = await db_manager.search_articles(
                query=" ".join(keywords),
                domain=domain,
                limit=3
            )
            
            print(f"  • Risultati trovati: {len(results)}")
            for i, article in enumerate(results):
                print(f"    {i+1}. {article.get('title', 'N/A')[:60]}...")
            
            await db_manager.disconnect()
        
    except Exception as e:
        print(f"❌ Errore: {e}")
    
    finally:
        # 6. Cleanup
        await crawler.disconnect()
        print("✅ Crawler disconnesso")

async def run_specific_site_crawler():
    """Esempio crawling sito specifico"""
    
    print("🎯 Crawling sito specifico...")
    
    crawler = TrafilaturaCrawler()
    
    try:
        # Crawl solo Gazzetta dello Sport
        stats = await crawler.crawl_single_site('gazzetta')
        
        print("📊 Risultati:")
        print(f"  • Link scoperti: {stats['links_discovered']}")
        print(f"  • Articoli estratti: {stats['articles_extracted']}")
        
    except Exception as e:
        print(f"❌ Errore: {e}")
    
    finally:
        await crawler.disconnect()

async def run_full_system_test():
    """Test completo sistema ibrido"""
    
    print("🔄 Test sistema completo...")
    
    # Import del news manager V2
    from core.news_db_manager_v2 import NewsVectorDBV2
    
    try:
        # 1. Inizializza database manager V2
        news_db = NewsVectorDBV2()
        
        # 2. Update dominio calcio
        result = await news_db.update_domain('calcio')
        
        print("📊 Risultati update:")
        print(f"  • Dominio: {result['domain_name']}")
        print(f"  • Siti processati: {result['crawl_stats']['sites_processed']}")
        print(f"  • Link scoperti: {result['crawl_stats']['links_discovered']}")
        print(f"  • Articoli estratti: {result['crawl_stats']['articles_extracted']}")
        
        # 3. Test ricerca
        articles = await news_db.search_news('calcio', ['Serie A', 'Juventus'], max_results=5)
        print(f"  • Articoli trovati nella ricerca: {len(articles)}")
        
    except Exception as e:
        print(f"❌ Errore: {e}")
    
    finally:
        await news_db.disconnect()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Esempi crawler Tanea')
    parser.add_argument('--mode', choices=['domain', 'site', 'full'], default='domain',
                      help='Modalità di test (default: domain)')
    
    args = parser.parse_args()
    
    if args.mode == 'domain':
        asyncio.run(run_crawler_example())
    elif args.mode == 'site':
        asyncio.run(run_specific_site_crawler())
    elif args.mode == 'full':
        asyncio.run(run_full_system_test())