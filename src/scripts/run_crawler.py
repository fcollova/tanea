#!/usr/bin/env python3
"""
Script per eseguire il crawler Tanea in diverse modalità
"""

import asyncio
import sys
import os
import argparse

# Aggiungi src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.crawler.trafilatura_crawler import TrafilaturaCrawler
from core.storage.database_manager import DatabaseManager
from core.domain_manager import DomainManager
from core.news_db_manager_v2 import NewsVectorDBV2

async def crawl_domain(domain_name: str):
    """Crawling di un dominio specifico"""
    print(f"🎯 Crawling dominio: {domain_name}")
    
    crawler = TrafilaturaCrawler()
    
    try:
        stats = await crawler.crawl_domain(domain_name)
        
        print("\n📊 Risultati Crawling:")
        print(f"  • Siti processati: {stats['sites_processed']}")
        print(f"  • Link scoperti: {stats['links_discovered']}")
        print(f"  • Link crawlati: {stats['links_crawled']}")
        print(f"  • Articoli estratti: {stats['articles_extracted']}")
        print(f"  • Errori: {stats['errors']}")
        
        return stats
        
    finally:
        await crawler.disconnect()

async def crawl_site(site_name: str):
    """Crawling di un sito specifico"""
    print(f"🌐 Crawling sito: {site_name}")
    
    crawler = TrafilaturaCrawler()
    
    try:
        stats = await crawler.crawl_single_site(site_name)
        
        print("\n📊 Risultati:")
        print(f"  • Link scoperti: {stats.get('links_discovered', 0)}")
        print(f"  • Articoli estratti: {stats.get('articles_extracted', 0)}")
        
        return stats
        
    finally:
        await crawler.disconnect()

async def test_full_system():
    """Test completo sistema ibrido"""
    print("🔄 Test sistema completo...")
    
    news_db = NewsVectorDBV2()
    
    try:
        # Update dominio calcio
        result = await news_db.update_domain('calcio')
        
        print("📊 Risultati update:")
        print(f"  • Dominio: {result['domain_name']}")
        print(f"  • Siti processati: {result['crawl_stats']['sites_processed']}")
        print(f"  • Link scoperti: {result['crawl_stats']['links_discovered']}")
        print(f"  • Articoli estratti: {result['crawl_stats']['articles_extracted']}")
        
        # Test ricerca
        articles = await news_db.search_news('calcio', ['Serie A', 'Inter'], max_results=3)
        print(f"  • Articoli trovati: {len(articles)}")
        
        for i, article in enumerate(articles[:2]):
            title = article.get('title', 'N/A')[:50]
            print(f"    {i+1}. {title}...")
        
        return result
        
    finally:
        await news_db.disconnect()

async def show_domains():
    """Mostra domini configurati"""
    domain_manager = DomainManager()
    
    print("📂 Domini configurati:")
    all_domains = domain_manager.get_domain_list(active_only=False)
    active_domains = domain_manager.get_domain_list(active_only=True)
    
    for domain in all_domains:
        status = "🟢 ATTIVO" if domain in active_domains else "🔴 INATTIVO"
        domain_config = domain_manager.get_domain(domain)
        keywords = domain_config.keywords[:3] if domain_config else []
        
        print(f"  • {domain} - {status}")
        print(f"    Keywords: {keywords}")

def main():
    parser = argparse.ArgumentParser(description='Tanea Crawler Script')
    parser.add_argument('--domain', help='Crawl dominio specifico (es: calcio)')
    parser.add_argument('--site', help='Crawl sito specifico (es: gazzetta)')
    parser.add_argument('--full', action='store_true', help='Test sistema completo')
    parser.add_argument('--domains', action='store_true', help='Mostra domini configurati')
    
    args = parser.parse_args()
    
    if args.domains:
        asyncio.run(show_domains())
    elif args.domain:
        asyncio.run(crawl_domain(args.domain))
    elif args.site:
        asyncio.run(crawl_site(args.site))
    elif args.full:
        asyncio.run(test_full_system())
    else:
        print("🕷️ Tanea Crawler")
        print("Opzioni disponibili:")
        print("  --domain <nome>  : Crawl dominio specifico")
        print("  --site <nome>    : Crawl sito specifico")
        print("  --full           : Test sistema completo")
        print("  --domains        : Mostra domini configurati")
        print("\nEsempi:")
        print("  python run_crawler.py --domains")
        print("  python run_crawler.py --domain calcio")
        print("  python run_crawler.py --site gazzetta")
        print("  python run_crawler.py --full")

if __name__ == "__main__":
    main()