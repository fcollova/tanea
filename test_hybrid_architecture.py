#!/usr/bin/env python3
"""
Test Hybrid Architecture - Test completo architettura ibrida
"""

import asyncio
import sys
from pathlib import Path

# Aggiungi src al path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.core.news_db_manager_v2 import NewsVectorDBV2
from src.core.crawler.crawl_scheduler import CrawlScheduler
from src.core.storage.database_manager import DatabaseManager

async def test_basic_operations():
    """Test operazioni base"""
    print("🧪 Test Operazioni Base")
    print("-" * 30)
    
    try:
        async with NewsVectorDBV2('dev') as news_db:
            # Test 1: Health check
            print("1. Health Check...")
            health = await news_db.db_manager.health_check()
            print(f"   PostgreSQL: {'✅' if health['postgresql'] else '❌'}")
            print(f"   Weaviate: {'✅' if health['weaviate'] else '❌'}")
            print(f"   Overall: {'✅' if health['overall'] else '❌'}")
            print()
            
            # Test 2: Statistiche
            print("2. Statistiche Sistema...")
            stats = await news_db.get_system_stats()
            
            db_stats = stats.get('database_stats', {})
            pg_stats = db_stats.get('postgresql', {})
            weaviate_stats = db_stats.get('weaviate', {})
            
            print(f"   Link totali: {pg_stats.get('new', 0) + pg_stats.get('crawled', 0)}")
            print(f"   Articoli estratti: {pg_stats.get('articles_extracted', 0)}")
            print(f"   Collezione Weaviate: {weaviate_stats.get('total_articles', 0)} articoli")
            print()
            
            # Test 3: Domini
            print("3. Domini Configurati...")
            domain_stats = stats.get('domain_stats', {})
            for domain_id, domain_info in domain_stats.items():
                status = "🟢" if domain_info['active'] else "🔴"
                print(f"   {status} {domain_info['name']} ({len(domain_info.get('keywords', []))} keywords)")
            print()
            
        return True
        
    except Exception as e:
        print(f"❌ Errore test base: {e}")
        return False

async def test_crawling():
    """Test crawling"""
    print("🕷️ Test Crawling")
    print("-" * 20)
    
    try:
        async with NewsVectorDBV2('dev') as news_db:
            # Test crawling dominio calcio
            print("Crawling dominio calcio (limitato)...")
            
            result = await news_db.update_domain_news("calcio")
            
            crawl_stats = result.get('crawl_stats', {})
            print(f"Siti processati: {crawl_stats.get('sites_processed', 0)}")
            print(f"Link scoperti: {crawl_stats.get('links_discovered', 0)}")
            print(f"Articoli estratti: {crawl_stats.get('articles_extracted', 0)}")
            print(f"Errori: {crawl_stats.get('errors', 0)}")
            print()
            
        return True
        
    except Exception as e:
        print(f"❌ Errore test crawling: {e}")
        return False

async def test_search():
    """Test ricerca semantica"""
    print("🔍 Test Ricerca Semantica")
    print("-" * 25)
    
    try:
        async with NewsVectorDBV2('dev') as news_db:
            # Test ricerche diverse
            test_queries = [
                ("calcio", ["Serie A", "campionato"], "Ricerca calcio generale"),
                ("calcio", ["Inter", "Juventus"], "Ricerca squadre specifiche"),
                ("tecnologia", ["AI", "intelligenza artificiale"], "Ricerca tecnologia"),
                ("general", ["notizie", "Italia"], "Ricerca generale")
            ]
            
            for domain, keywords, description in test_queries:
                print(f"{description}...")
                results = await news_db.search_news(
                    domain=domain,
                    keywords=keywords,
                    max_results=3
                )
                
                print(f"   Risultati: {len(results)}")
                for i, article in enumerate(results[:2]):
                    print(f"   {i+1}. {article['title'][:60]}...")
                    print(f"      Fonte: {article['source']} | Score: {article.get('score', 0):.2f}")
                print()
            
        return True
        
    except Exception as e:
        print(f"❌ Errore test ricerca: {e}")
        return False

async def test_scheduler():
    """Test scheduler"""
    print("⏰ Test Scheduler")
    print("-" * 15)
    
    try:
        async with CrawlScheduler('dev') as scheduler:
            # Test job manuale
            print("Scheduling job manuale...")
            
            from src.core.crawler.crawl_scheduler import JobType
            
            # Job cleanup
            job_id = await scheduler.run_job_now(
                JobType.CLEANUP,
                {'days_old': 90}
            )
            
            print(f"Job cleanup eseguito: {job_id}")
            
            # Status scheduler
            status = scheduler.get_scheduler_status()
            print(f"Jobs completati: {status['stats']['jobs_completed']}")
            print(f"Jobs falliti: {status['stats']['jobs_failed']}")
            print()
            
        return True
        
    except Exception as e:
        print(f"❌ Errore test scheduler: {e}")
        return False

async def test_maintenance():
    """Test operazioni di manutenzione"""
    print("🧹 Test Manutenzione")
    print("-" * 18)
    
    try:
        async with NewsVectorDBV2('dev') as news_db:
            # Test sync database
            print("Sync database...")
            sync_result = await news_db.sync_databases()
            print(f"   Articoli orfani: {sync_result.get('missing_weaviate', 0)}")
            print()
            
            # Test cleanup (conservativo)
            print("Cleanup dati vecchi...")
            cleanup_result = await news_db.cleanup_old_articles(120)  # 4 mesi
            
            pg_cleanup = cleanup_result.get('postgresql', {})
            weaviate_cleanup = cleanup_result.get('weaviate_articles', 0)
            
            print(f"   PostgreSQL cleanup: {pg_cleanup}")
            print(f"   Weaviate cleanup: {weaviate_cleanup} articoli")
            print()
            
        return True
        
    except Exception as e:
        print(f"❌ Errore test manutenzione: {e}")
        return False

async def interactive_test():
    """Test interattivo"""
    print("💬 Test Interattivo")
    print("-" * 17)
    
    try:
        async with NewsVectorDBV2('dev') as news_db:
            print("Inserisci domanda di ricerca (o 'quit' per uscire):")
            
            while True:
                query = input("\n> ").strip()
                
                if query.lower() in ['quit', 'exit', 'q']:
                    break
                
                if not query:
                    continue
                
                # Ricerca nel contesto
                results = await news_db.search_news(
                    domain="general",
                    keywords=[query],
                    max_results=5
                )
                
                if results:
                    print(f"\n📰 Trovati {len(results)} articoli:")
                    for i, article in enumerate(results):
                        print(f"\n{i+1}. {article['title']}")
                        print(f"   Fonte: {article['source']}")
                        print(f"   URL: {article['url']}")
                        print(f"   Score: {article.get('score', 0):.2f}")
                        
                        # Mostra snippet contenuto
                        content = article.get('content', '')
                        if content:
                            snippet = content[:200] + "..." if len(content) > 200 else content
                            print(f"   Contenuto: {snippet}")
                else:
                    print("🤷 Nessun articolo trovato")
            
        return True
        
    except Exception as e:
        print(f"❌ Errore test interattivo: {e}")
        return False

async def main():
    """Esegue tutti i test"""
    print("🧪 Test Architettura Ibrida Tanea")
    print("=" * 40)
    print()
    
    tests = [
        ("Operazioni Base", test_basic_operations),
        ("Crawling", test_crawling),
        ("Ricerca Semantica", test_search),
        ("Scheduler", test_scheduler),
        ("Manutenzione", test_maintenance)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"🏃 Esecuzione: {test_name}")
        try:
            result = await test_func()
            results[test_name] = result
            print(f"{'✅' if result else '❌'} {test_name}: {'PASS' if result else 'FAIL'}")
        except Exception as e:
            print(f"❌ {test_name}: ERRORE - {e}")
            results[test_name] = False
        
        print()
    
    # Riepilogo
    print("=" * 40)
    print("📊 RIEPILOGO TEST")
    print("=" * 40)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:10} {test_name}")
    
    print("-" * 40)
    print(f"Totale: {passed}/{total} test passati")
    print()
    
    if passed == total:
        print("🎉 Tutti i test sono passati!")
        print("L'architettura ibrida è funzionante.")
    else:
        print("⚠️ Alcuni test sono falliti.")
        print("Controlla i log per dettagli.")
    
    # Opzione test interattivo
    if passed >= total // 2:  # Se almeno metà test passano
        response = input("\nVuoi eseguire il test interattivo? (y/n): ").strip().lower()
        if response in ['y', 'yes', 's', 'si']:
            await interactive_test()

if __name__ == "__main__":
    asyncio.run(main())