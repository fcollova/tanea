"""
Modulo principale per fonti di notizie - Orchestratore
Importa e coordina i moduli specializzati per ogni fonte
"""

# Importa le classi base
from .news_source_base import NewsQuery, NewsArticle, NewsSource, SourceMetrics

# Importa le implementazioni specifiche
from .news_source_rss import RSSFeedSource
from .news_source_newsapi import NewsAPISource
from .news_source_webscraping import WebScrapingSource
from .news_source_tavily import TavilyNewsSource
from .news_source_trafilatura import TrafilaturaWebScrapingSource
from .news_source_manager import NewsSourceManager

# Importa utilities
from .log import get_news_logger

logger = get_news_logger(__name__)

def create_default_news_manager() -> NewsSourceManager:
    """
    Crea un NewsSourceManager con le fonti italiane predefinite
    
    Returns:
        Manager configurato con fonti disponibili
    """
    manager = NewsSourceManager()
    
    # 1. Trafilatura Web Scraping Source (priorità massima - AI-powered)
    try:
        trafilatura_source = TrafilaturaWebScrapingSource()
        if trafilatura_source.is_available():
            manager.add_source('trafilatura', trafilatura_source)
            logger.info("Trafilatura Web Scraping Source inizializzato")
        else:
            logger.info("Trafilatura non disponibile (libreria mancante)")
    except Exception as e:
        logger.warning(f"Impossibile inizializzare Trafilatura: {e}")
    
    # 2. RSS Feed Source (priorità alta - sempre disponibile)
    try:
        rss_source = RSSFeedSource()
        manager.add_source('rss', rss_source)
        logger.info("RSS Feed Source inizializzato")
    except Exception as e:
        logger.warning(f"Impossibile inizializzare RSS: {e}")
    
    # 3. Web Scraping Source (priorità media - fallback per Trafilatura)
    try:
        scraping_source = WebScrapingSource()
        if scraping_source.is_available():
            manager.add_source('scraping', scraping_source)
            logger.info("Web Scraping Source inizializzato")
        else:
            logger.info("Web Scraping non disponibile (configurazione mancante)")
    except Exception as e:
        logger.warning(f"Impossibile inizializzare Web Scraping: {e}")
    
    # 4. NewsAPI Source (priorità media)
    try:
        newsapi_source = NewsAPISource()
        if newsapi_source.is_available():
            manager.add_source('newsapi', newsapi_source)
            logger.info("NewsAPI Source inizializzato")
        else:
            logger.info("NewsAPI non disponibile (API key mancante)")
    except Exception as e:
        logger.warning(f"Impossibile inizializzare NewsAPI: {e}")
    
    # 5. Tavily Source (priorità bassa - fallback)
    try:
        tavily_source = TavilyNewsSource()
        if tavily_source.is_available():
            manager.add_source('tavily', tavily_source)
            logger.info("Tavily Source inizializzato")
        else:
            logger.info("Tavily non disponibile (API key mancante)")
    except Exception as e:
        logger.warning(f"Impossibile inizializzare Tavily: {e}")
    
    # Log fonti disponibili
    available = manager.get_available_sources()
    logger.info(f"Fonti disponibili: {available}")
    
    return manager

# Backward compatibility - mantieni le classi nel namespace principale per compatibilità
__all__ = [
    'NewsQuery',
    'NewsArticle', 
    'NewsSource',
    'SourceMetrics',
    'RSSFeedSource',
    'NewsAPISource', 
    'WebScrapingSource',
    'TavilyNewsSource',
    'TrafilaturaWebScrapingSource',
    'NewsSourceManager',
    'create_default_news_manager'
]