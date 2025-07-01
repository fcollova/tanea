#!/usr/bin/env python3
# ============================================================================
# explore_db.py
"""
Script per esplorare e visualizzare i contenuti del vector database
"""

import json
from datetime import datetime
from news_vector_db import NewsVectorDB
from config import WEAVIATE_URL, TAVILY_API_KEY, VECTOR_DB_CONFIG, EMBEDDING_MODEL

class DatabaseExplorer:
    """Esploratore per il database vettoriale"""
    
    def __init__(self):
        self.news_db = NewsVectorDB(
            weaviate_url=WEAVIATE_URL,
            tavily_api_key=TAVILY_API_KEY,
            index_name=VECTOR_DB_CONFIG["index_name"],
            embedding_model=EMBEDDING_MODEL
        )
    
    def get_all_articles(self, limit=50):
        """Recupera tutti gli articoli dal database"""
        try:
            collection = self.news_db.weaviate_client.collections.get(self.news_db.index_name)
            
            response = collection.query.fetch_objects(
                return_properties=[
                    "title", "content", "url", "domain", 
                    "published_date", "source", "content_hash"
                ],
                limit=limit
            )
            
            articles = []
            for obj in response.objects:
                article = {
                    "id": str(obj.uuid),
                    **obj.properties
                }
                articles.append(article)
            
            return articles
            
        except Exception as e:
            print(f"❌ Errore nel recupero articoli: {e}")
            return []
    
    def get_statistics(self):
        """Ottieni statistiche dettagliate"""
        try:
            collection = self.news_db.weaviate_client.collections.get(self.news_db.index_name)
            
            # Conta totale
            total = collection.aggregate.over_all(total_count=True).total_count
            
            # Recupera tutti per analisi
            all_articles = self.get_all_articles(limit=1000)
            
            # Analisi per dominio
            domain_stats = {}
            source_stats = {}
            date_stats = {}
            
            for article in all_articles:
                # Per dominio
                domain = article.get("domain", "Unknown")
                domain_stats[domain] = domain_stats.get(domain, 0) + 1
                
                # Per fonte
                source = article.get("source", "Unknown")
                source_stats[source] = source_stats.get(source, 0) + 1
                
                # Per data (solo giorno)
                pub_date = article.get("published_date", "")
                if pub_date:
                    try:
                        date_key = pub_date.split("T")[0]  # Solo YYYY-MM-DD
                        date_stats[date_key] = date_stats.get(date_key, 0) + 1
                    except:
                        pass
            
            return {
                "total_articles": total,
                "domain_stats": dict(sorted(domain_stats.items())),
                "source_stats": dict(sorted(source_stats.items(), key=lambda x: x[1], reverse=True)),
                "date_stats": dict(sorted(date_stats.items(), reverse=True)),
                "sample_articles": all_articles[:5]  # Prime 5 per anteprima
            }
            
        except Exception as e:
            print(f"❌ Errore nelle statistiche: {e}")
            return {"error": str(e)}
    
    def search_by_keyword(self, keyword, limit=10):
        """Cerca articoli per parola chiave"""
        try:
            # Usa il sistema di ricerca semantica
            relevant_docs = self.news_db.search_relevant_context(keyword, k=limit)
            
            results = []
            for doc in relevant_docs:
                result = {
                    "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                    "metadata": doc.metadata
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"❌ Errore nella ricerca: {e}")
            return []
    
    def delete_article_by_id(self, article_id):
        """Elimina un articolo per ID"""
        try:
            collection = self.news_db.weaviate_client.collections.get(self.news_db.index_name)
            collection.data.delete_by_id(article_id)
            print(f"✅ Articolo {article_id} eliminato")
            return True
        except Exception as e:
            print(f"❌ Errore nell'eliminazione: {e}")
            return False

def quick_stats():
    """Mostra velocemente le statistiche senza menu interattivo"""
    print("🔍 Database Explorer - News Vector DB")
    print("=" * 50)
    
    explorer = DatabaseExplorer()
    print("\n📊 Statistiche Database:")
    print("-" * 30)
    stats = explorer.get_statistics()
    
    if "error" in stats:
        print(f"❌ {stats['error']}")
        return
    
    print(f"📈 Totale articoli: {stats['total_articles']}")
    
    print(f"\n🏷️  Per dominio:")
    for domain, count in stats['domain_stats'].items():
        print(f"  • {domain}: {count}")
    
    print(f"\n📰 Top fonti:")
    for source, count in list(stats['source_stats'].items())[:5]:
        print(f"  • {source}: {count}")
    
    print(f"\n📅 Per data:")
    for date, count in list(stats['date_stats'].items())[:5]:
        print(f"  • {date}: {count}")
    
    print(f"\n📰 Anteprima articoli:")
    print("-" * 30)
    for i, article in enumerate(stats['sample_articles'], 1):
        print(f"\n{i}. 📰 {article.get('title', 'N/A')}")
        print(f"   🌐 Fonte: {article.get('source', 'N/A')}")
        print(f"   🏷️  Dominio: {article.get('domain', 'N/A')}")

def main():
    """Menu interattivo per esplorare il database"""
    import sys
    
    # Se non c'è input interattivo, mostra solo statistiche
    if not sys.stdin.isatty():
        quick_stats()
        return
    
    print("🔍 Database Explorer - News Vector DB")
    print("=" * 50)
    
    explorer = DatabaseExplorer()
    
    while True:
        print("\n📋 Cosa vuoi fare?")
        print("1. 📊 Mostra statistiche generali")
        print("2. 📰 Lista tutti gli articoli")
        print("3. 🔍 Cerca per parola chiave")
        print("4. 📋 Mostra articoli per dominio")
        print("5. 🗑️  Elimina articolo per ID")
        print("6. 💾 Esporta dati in JSON")
        print("0. ❌ Esci")
        
        choice = input("\n👉 Scelta (0-6): ").strip()
        
        if choice == "0":
            print("👋 Arrivederci!")
            break
        
        elif choice == "1":
            print("\n📊 Statistiche Database:")
            print("-" * 30)
            stats = explorer.get_statistics()
            
            if "error" in stats:
                print(f"❌ {stats['error']}")
                continue
            
            print(f"📈 Totale articoli: {stats['total_articles']}")
            
            print(f"\n🏷️  Per dominio:")
            for domain, count in stats['domain_stats'].items():
                print(f"  • {domain}: {count}")
            
            print(f"\n📰 Top fonti:")
            for source, count in list(stats['source_stats'].items())[:5]:
                print(f"  • {source}: {count}")
            
            print(f"\n📅 Per data:")
            for date, count in list(stats['date_stats'].items())[:5]:
                print(f"  • {date}: {count}")
        
        elif choice == "2":
            limit = input("📰 Numero articoli da mostrare (default 10): ").strip()
            limit = int(limit) if limit.isdigit() else 10
            
            articles = explorer.get_all_articles(limit)
            print(f"\n📰 Ultimi {len(articles)} articoli:")
            print("-" * 50)
            
            for i, article in enumerate(articles, 1):
                print(f"\n{i}. 📰 {article.get('title', 'N/A')}")
                print(f"   🌐 Fonte: {article.get('source', 'N/A')}")
                print(f"   🏷️  Dominio: {article.get('domain', 'N/A')}")
                print(f"   📅 Data: {article.get('published_date', 'N/A')}")
                print(f"   🆔 ID: {article.get('id', 'N/A')}")
                content = article.get('content', '')
                if content:
                    preview = content[:150] + "..." if len(content) > 150 else content
                    print(f"   📝 Anteprima: {preview}")
        
        elif choice == "3":
            keyword = input("🔍 Inserisci parola chiave: ").strip()
            if keyword:
                results = explorer.search_by_keyword(keyword)
                print(f"\n🔍 Risultati per '{keyword}':")
                print("-" * 30)
                
                if not results:
                    print("❌ Nessun risultato trovato")
                else:
                    for i, result in enumerate(results, 1):
                        print(f"\n{i}. 📰 {result['metadata'].get('title', 'N/A')}")
                        print(f"   🌐 {result['metadata'].get('source', 'N/A')}")
                        print(f"   📝 {result['content']}")
        
        elif choice == "4":
            stats = explorer.get_statistics()
            if "domain_stats" in stats:
                domain = input(f"🏷️  Domini disponibili: {list(stats['domain_stats'].keys())}\nScegli dominio: ").strip()
                
                articles = explorer.get_all_articles(limit=100)
                domain_articles = [a for a in articles if a.get('domain') == domain]
                
                print(f"\n📰 Articoli per '{domain}' ({len(domain_articles)}):")
                print("-" * 40)
                
                for i, article in enumerate(domain_articles, 1):
                    print(f"{i}. {article.get('title', 'N/A')}")
        
        elif choice == "5":
            article_id = input("🆔 Inserisci ID articolo da eliminare: ").strip()
            if article_id:
                confirm = input(f"⚠️  Sicuro di voler eliminare {article_id}? (y/N): ").strip().lower()
                if confirm == 'y':
                    explorer.delete_article_by_id(article_id)
        
        elif choice == "6":
            print("💾 Esportazione dati...")
            articles = explorer.get_all_articles(limit=1000)
            filename = f"database_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Dati esportati in: {filename}")
        
        else:
            print("❌ Scelta non valida")

if __name__ == "__main__":
    main()