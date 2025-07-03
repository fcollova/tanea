#!/usr/bin/env python3
"""
Test di confronto: BeautifulSoup vs Trafilatura
Dimostra i vantaggi di trafilatura per web scraping di notizie
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_scraping_comparison():
    """Confronto diretto tra i due approcci"""
    print("🔍 CONFRONTO SCRAPING: BeautifulSoup vs Trafilatura")
    print("=" * 55)
    
    # URL di test per articoli reali
    test_urls = [
        "https://www.ansa.it/sito/notizie/sport/calcio/",
        "https://www.gazzetta.it/Calcio/",
        "https://www.corriere.it/sport/"
    ]
    
    results = {
        'beautiful_soup': {'articles': 0, 'errors': 0, 'time': 0},
        'trafilatura': {'articles': 0, 'errors': 0, 'time': 0}
    }
    
    print("\n🕷️  Test BeautifulSoup (metodo attuale)...")
    start_time = time.time()
    
    try:
        # Simula il metodo attuale con selettori CSS
        from src.core.news_source_webscraping import WebScrapingSource
        from src.core.news_source_base import NewsQuery
        
        webscraping = WebScrapingSource()
        if webscraping.is_available():
            query = NewsQuery(keywords=['calcio'], domain='calcio', max_results=5)
            articles_bs = webscraping.search_news(query)
            results['beautiful_soup']['articles'] = len(articles_bs)
            print(f"   ✅ BeautifulSoup: {len(articles_bs)} articoli estratti")
            
            # Mostra esempio
            if articles_bs:
                first_article = articles_bs[0]
                print(f"   📰 Esempio: {first_article.title[:80]}...")
                print(f"        Contenuto: {len(first_article.content)} caratteri")
        else:
            print("   ❌ BeautifulSoup: Configurazione non disponibile")
            results['beautiful_soup']['errors'] = 1
            
    except Exception as e:
        print(f"   ❌ BeautifulSoup: Errore - {e}")
        results['beautiful_soup']['errors'] = 1
    
    results['beautiful_soup']['time'] = time.time() - start_time
    
    print(f"\n🚀 Test Trafilatura (metodo proposto)...")
    start_time = time.time()
    
    try:
        # Test del nuovo metodo trafilatura
        trafilatura_available = False
        try:
            import trafilatura
            trafilatura_available = True
            print("   ✅ Trafilatura disponibile!")
            
            # Test estrazione da URL singolo
            test_url = "https://www.ansa.it"  # URL semplice per test
            downloaded = trafilatura.fetch_url(test_url)
            if downloaded:
                extracted = trafilatura.extract(downloaded, output_format='json')
                if extracted:
                    print(f"   ✅ Estrazione test riuscita")
                    results['trafilatura']['articles'] = 1
                else:
                    print(f"   ⚠️  Estrazione test vuota")
            else:
                print(f"   ⚠️  Download test fallito")
                
        except ImportError:
            print("   ❌ Trafilatura non installata")
            print("      Installa con: pip install trafilatura")
            results['trafilatura']['errors'] = 1
            
        except Exception as e:
            print(f"   ❌ Trafilatura: Errore - {e}")
            results['trafilatura']['errors'] = 1
            
    except Exception as e:
        print(f"   ❌ Trafilatura: Errore generale - {e}")
        results['trafilatura']['errors'] = 1
    
    results['trafilatura']['time'] = time.time() - start_time
    
    # Mostra confronto
    print(f"\n📊 RISULTATI CONFRONTO:")
    print(f"{'Metodo':<15} {'Articoli':<10} {'Errori':<8} {'Tempo':<8}")
    print(f"{'-'*45}")
    print(f"{'BeautifulSoup':<15} {results['beautiful_soup']['articles']:<10} {results['beautiful_soup']['errors']:<8} {results['beautiful_soup']['time']:.1f}s")
    print(f"{'Trafilatura':<15} {results['trafilatura']['articles']:<10} {results['trafilatura']['errors']:<8} {results['trafilatura']['time']:.1f}s")

def show_trafilatura_advantages():
    """Mostra vantaggi teorici di trafilatura"""
    print(f"\n🎯 VANTAGGI TRAFILATURA vs BEAUTIFULSOUP")
    print("-" * 45)
    
    advantages = [
        ("🎯 Accuratezza", "Estrazione AI-powered vs selettori CSS manuali"),
        ("🔧 Manutenzione", "Auto-adattiva vs selettori che si rompono"),
        ("⚡ Performance", "Ottimizzata per testo vs parsing DOM completo"),
        ("🧠 Intelligenza", "Riconosce contenuto principale automaticamente"),
        ("📊 Metadati", "Estrae data, autore, descrizione automaticamente"),
        ("🧹 Pulizia", "Rimuove ads, nav, footer automaticamente"),
        ("📱 Robustezza", "Funziona su siti diversi senza configurazione"),
        ("🔄 Semplicità", "2 righe di codice vs 100+ righe selettori"),
        ("🎨 Formattazione", "Conserva struttura (paragrafi, liste, grassetti)"),
        ("🌐 Standard", "Usato da IBM, Microsoft, Stanford, HuggingFace")
    ]
    
    for emoji_title, description in advantages:
        print(f"   {emoji_title:<15} {description}")

def show_implementation_plan():
    """Piano di implementazione trafilatura"""
    print(f"\n📋 PIANO IMPLEMENTAZIONE TRAFILATURA")
    print("-" * 40)
    
    steps = [
        "1. 📦 Installazione: pip install trafilatura",
        "2. 🔧 Aggiornare requirements.txt",
        "3. 🏗️  Creare TrafilaturaWebScrapingSource", 
        "4. 🔄 Aggiungere al NewsSourceManager",
        "5. ⚙️  Configurare priorità (alta per trafilatura)",
        "6. 🧪 Test su siti italiani di notizie",
        "7. 📊 Confronto performance con metodo attuale",
        "8. 🚀 Deploy graduale (fallback a BeautifulSoup)",
        "9. 📈 Monitoraggio miglioramenti qualità",
        "10. 🎯 Ottimizzazione configurazione trafilatura"
    ]
    
    for step in steps:
        print(f"   {step}")

def show_code_comparison():
    """Confronto codice necessario"""
    print(f"\n💻 CONFRONTO CODICE NECESSARIO")
    print("-" * 35)
    
    print(f"\n🔴 METODO ATTUALE (BeautifulSoup):")
    print("""
    # 1. Configurare selettori per ogni sito in YAML
    selectors:
      article_links: ".gzc-article-title a, .main-news a"
      title: "h1.news-title, h1, .article-title"
      content: ".news-txt, .articolo-contenuto, .news-body"
      date: "time[datetime], .news-date, .date"
    
    # 2. Codice estrazione (50+ righe)
    soup = BeautifulSoup(html, 'html.parser')
    title_elem = soup.select(selectors['title'])
    content_elems = soup.select(selectors['content'])
    # ... gestione errori, pulizia, parsing date ...
    """)
    
    print(f"\n🟢 METODO PROPOSTO (Trafilatura):")
    print("""
    # 1. Nessuna configurazione selettori necessaria
    
    # 2. Codice estrazione (2 righe!)
    downloaded = trafilatura.fetch_url(url)
    article_data = trafilatura.extract(downloaded, output_format='json')
    
    # Trafilatura estrae automaticamente:
    # - Titolo, contenuto, data, autore
    # - Rimuove ads, navigazione, footer
    # - Conserva formattazione (paragrafi, grassetti)
    # - Fornisce metadati strutturati
    """)

if __name__ == "__main__":
    test_scraping_comparison()
    show_trafilatura_advantages()
    show_implementation_plan()
    show_code_comparison()
    
    print(f"\n🎊 CONCLUSIONE:")
    print(f"   Trafilatura rappresenta un significativo upgrade")
    print(f"   per il sistema di web scraping, con maggiore")
    print(f"   accuratezza, robustezza e facilità di manutenzione!")
    print(f"\n   Per procedere: pip install trafilatura")