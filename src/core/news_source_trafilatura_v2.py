"""
News Source Trafilatura V2 - Architettura Ibrida
Usa crawler PostgreSQL + ricerca semantica Weaviate
"""

import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

from .news_source_base import NewsSource, NewsQuery, NewsArticle
from .storage.database_manager import DatabaseManager
from .crawler.trafilatura_crawler import TrafilaturaCrawler
from .config import get_crawler_config
from .log import get_news_logger

logger = get_news_logger(__name__)

class TrafilaturaSourceV2(NewsSource):
    """
    News Source che usa architettura ibrida:
    - Crawler per raccolta proattiva contenuti
    - PostgreSQL per link management 
    - Weaviate per ricerca semantica
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        if config is None:
            config = {}
        super().__init__(config)
        
        self.environment = config.get('environment', 'dev')
        self.crawler_config = get_crawler_config()
        
        # Modalità di funzionamento
        self.use_crawler = config.get('use_crawler', True)
        self.auto_crawl = config.get('auto_crawl', False)  # Crawl automatico se no risultati
        
        # Database manager per accesso storage
        self.db_manager = None
        self._db_initialized = False
        
        # Crawler per modalità pro-attiva
        self.crawler = None
    
    @property
    def priority(self) -> int:
        return 1  # Alta priorità - ricerca semantica molto efficace
    
    async def _ensure_db_initialized(self):
        """Assicura che database manager sia inizializzato"""
        if not self._db_initialized:
            self.db_manager = DatabaseManager(self.environment)
            await self.db_manager.initialize()
            self._db_initialized = True
            logger.debug("DatabaseManager inizializzato per TrafilaturaSourceV2")
    
    async def _cleanup_db(self):
        """Cleanup connessioni database"""
        if self._db_initialized and self.db_manager:
            await self.db_manager.close()
            self._db_initialized = False
    
    def is_available(self) -> bool:
        """Source disponibile se trafilatura installata"""
        try:
            import trafilatura
            return True
        except ImportError:
            return False
    
    def search_news(self, query: NewsQuery) -> List[NewsArticle]:
        """
        Cerca notizie usando ricerca semantica su contenuti crawlati
        
        Args:
            query: Query di ricerca
            
        Returns:
            list: Lista NewsArticle trovati
        """
        try:
            # Converte a asyncio per compatibilità
            return asyncio.run(self._search_news_async(query))
            
        except Exception as e:
            logger.error(f"Errore ricerca TrafilaturaSourceV2: {e}")
            return []
    
    async def _search_news_async(self, query: NewsQuery) -> List[NewsArticle]:
        """Implementazione asincrona ricerca"""
        try:
            await self._ensure_db_initialized()
            
            # 1. Ricerca semantica su contenuti esistenti
            articles = await self._search_existing_content(query)
            
            # 2. Se pochi risultati e auto_crawl attivo, lancia crawling
            if len(articles) < query.max_results // 2 and self.auto_crawl:
                logger.info("Pochi risultati trovati, avvio crawling supplementare")
                await self._trigger_supplementary_crawl(query)
                
                # Ri-cerca dopo crawling
                articles = await self._search_existing_content(query)
            
            # 3. Converte in NewsArticle
            news_articles = self._convert_to_news_articles(articles, query)
            
            logger.info(f"TrafilaturaSourceV2: {len(news_articles)} articoli trovati per query: {query.keywords}")
            return news_articles
            
        except Exception as e:
            logger.error(f"Errore ricerca asincrona: {e}")
            return []
        finally:
            # Cleanup connessioni se necessario
            # await self._cleanup_db()  # Commenta per performance - riusa connessioni
            pass
    
    async def _search_existing_content(self, query: NewsQuery) -> List[Dict[str, Any]]:
        """Ricerca semantica su contenuti già crawlati"""
        try:
            # Costruisci query di ricerca semantica
            search_query = " ".join(query.keywords) if query.keywords else ""
            
            # Filtra per dominio se specificato
            domain_filter = query.domain if query.domain != "general" else None
            
            # Ricerca con enrichment metadati
            articles = await self.db_manager.search_articles(
                query=search_query,
                domain=domain_filter,
                limit=query.max_results * 2,  # Recupera più risultati per filtering
                include_metadata=True
            )
            
            # Filtra per time_range se specificato
            if query.time_range and query.time_range != "all":
                articles = self._filter_by_time_range(articles, query.time_range)
            
            # Ordina per score e data
            articles.sort(
                key=lambda x: (
                    x.get('score', 0.0),
                    self._parse_date_for_sort(x.get('published_date'))
                ),
                reverse=True
            )
            
            return articles[:query.max_results]
            
        except Exception as e:
            logger.error(f"Errore ricerca contenuti esistenti: {e}")
            return []
    
    async def _trigger_supplementary_crawl(self, query: NewsQuery):
        """Lancia crawling supplementare per migliorare risultati"""
        try:
            if not self.crawler:
                self.crawler = TrafilaturaCrawler(self.environment)
            
            async with self.crawler:
                # Crawl mirato al dominio della query
                if query.domain and query.domain != "general":
                    await self.crawler.crawl_domain(query.domain, max_articles=20)
                else:
                    # Crawl veloce siti principali
                    await self.crawler.crawl_all_sites()
            
            logger.info("Crawling supplementare completato")
            
        except Exception as e:
            logger.error(f"Errore crawling supplementare: {e}")
    
    def _filter_by_time_range(self, articles: List[Dict], time_range: str) -> List[Dict]:
        """Filtra articoli per intervallo temporale"""
        if time_range == "all":
            return articles
        
        try:
            # Parse time_range (es. "1d", "2h", "1w")
            if time_range.endswith('d'):
                days = int(time_range[:-1])
                cutoff = datetime.now() - timedelta(days=days)
            elif time_range.endswith('h'):
                hours = int(time_range[:-1])
                cutoff = datetime.now() - timedelta(hours=hours)
            elif time_range.endswith('w'):
                weeks = int(time_range[:-1])
                cutoff = datetime.now() - timedelta(weeks=weeks)
            else:
                # Default 1 giorno
                cutoff = datetime.now() - timedelta(days=1)
            
            filtered_articles = []
            for article in articles:
                pub_date = self._parse_date_for_sort(article.get('published_date'))
                if pub_date and pub_date >= cutoff:
                    filtered_articles.append(article)
            
            return filtered_articles
            
        except Exception as e:
            logger.warning(f"Errore filtraggio time_range {time_range}: {e}")
            return articles
    
    def _parse_date_for_sort(self, date_str: str) -> datetime:
        """Parse data per ordinamento"""
        if not date_str:
            return datetime.min
        
        try:
            if isinstance(date_str, str):
                # Prova ISO format
                if 'T' in date_str:
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    return datetime.fromisoformat(date_str)
            elif isinstance(date_str, datetime):
                return date_str
            else:
                return datetime.min
                
        except Exception:
            return datetime.min
    
    def _convert_to_news_articles(self, articles: List[Dict], query: NewsQuery) -> List[NewsArticle]:
        """Converte risultati database in NewsArticle"""
        news_articles = []
        
        for article in articles:
            try:
                # Parse data pubblicazione
                pub_date = None
                if article.get('published_date'):
                    pub_date = self._parse_date_for_sort(article['published_date'])
                    if pub_date == datetime.min:
                        pub_date = None
                
                # Crea NewsArticle
                news_article = NewsArticle(
                    title=article.get('title', ''),
                    content=article.get('content', ''),
                    url=article.get('url', ''),
                    published_date=pub_date,
                    source=article.get('source', 'TrafilaturaV2'),
                    score=float(article.get('score', 0.0)),
                    metadata={
                        'domain': article.get('domain', query.domain),
                        'author': article.get('author', ''),
                        'keywords': article.get('keywords', []),
                        'quality_score': article.get('quality_score', 0.0),
                        'content_length': article.get('content_length', 0),
                        'extraction_method': 'trafilatura_v2_hybrid',
                        'site_name': article.get('site_name', ''),
                        'weaviate_id': article.get('id', ''),
                        'link_id': article.get('link_id', ''),
                        'last_crawled': article.get('last_crawled', ''),
                        'search_query': " ".join(query.keywords) if query.keywords else ""
                    }
                )
                
                news_articles.append(news_article)
                
            except Exception as e:
                logger.warning(f"Errore conversione articolo: {e}")
                continue
        
        return news_articles
    
    # ========================================================================
    # METODI UTILITY PER GESTIONE CRAWLER
    # ========================================================================
    
    async def trigger_crawl_domain(self, domain: str, max_articles: int = 50) -> Dict[str, Any]:
        """
        Lancia crawling per un dominio specifico
        
        Args:
            domain: Dominio da crawlare (calcio, tecnologia, etc.)
            max_articles: Massimo articoli da crawlare
            
        Returns:
            dict: Statistiche crawling
        """
        try:
            if not self.crawler:
                self.crawler = TrafilaturaCrawler(self.environment)
            
            async with self.crawler:
                stats = await self.crawler.crawl_domain(domain, max_articles)
                logger.info(f"Crawling dominio {domain} completato: {stats}")
                return stats
                
        except Exception as e:
            logger.error(f"Errore crawling dominio {domain}: {e}")
            return {'error': str(e)}
    
    async def trigger_full_crawl(self) -> Dict[str, Any]:
        """
        Lancia crawling completo di tutti i siti
        
        Returns:
            dict: Statistiche crawling
        """
        try:
            if not self.crawler:
                self.crawler = TrafilaturaCrawler(self.environment)
            
            async with self.crawler:
                stats = await self.crawler.crawl_all_sites()
                logger.info(f"Crawling completo completato: {stats}")
                return stats
                
        except Exception as e:
            logger.error(f"Errore crawling completo: {e}")
            return {'error': str(e)}
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """
        Recupera statistiche storage (PostgreSQL + Weaviate)
        
        Returns:
            dict: Statistiche unificate
        """
        try:
            await self._ensure_db_initialized()
            return await self.db_manager.get_unified_stats()
            
        except Exception as e:
            logger.error(f"Errore recupero statistiche: {e}")
            return {'error': str(e)}
    
    async def cleanup_old_data(self, days_old: int = 90) -> Dict[str, Any]:
        """
        Cleanup dati vecchi da entrambi i database
        
        Args:
            days_old: Età in giorni per considerare dati obsoleti
            
        Returns:
            dict: Statistiche cleanup
        """
        try:
            await self._ensure_db_initialized()
            return await self.db_manager.cleanup_old_data(days_old)
            
        except Exception as e:
            logger.error(f"Errore cleanup: {e}")
            return {'error': str(e)}
    
    # ========================================================================
    # METODI OVERRIDE PER COMPATIBILITÀ
    # ========================================================================
    
    def get_trafilatura_stats(self) -> Dict[str, Any]:
        """Statistiche trafilatura (compatibilità)"""
        # Implementazione asincrona non supportata in metodo sync
        # Ritorna placeholder
        return {
            'source_type': 'trafilatura_v2_hybrid',
            'storage_type': 'postgresql_weaviate',
            'environment': self.environment,
            'crawler_enabled': self.use_crawler,
            'auto_crawl': self.auto_crawl
        }
    
    def __del__(self):
        """Cleanup al destroy object"""
        if self._db_initialized:
            try:
                # Cleanup finale connessioni
                asyncio.run(self._cleanup_db())
            except Exception:
                pass


# ========================================================================
# FACTORY FUNCTION PER COMPATIBILITY
# ========================================================================

def create_trafilatura_source_v2(config: Dict[str, Any] = None) -> TrafilaturaSourceV2:
    """
    Factory function per creare TrafilaturaSourceV2
    
    Args:
        config: Configurazione opzionale
        
    Returns:
        TrafilaturaSourceV2: Istanza configurata
    """
    if config is None:
        config = {}
    
    # Configurazioni default
    default_config = {
        'use_crawler': True,
        'auto_crawl': False,  # Disattivato di default per performance
        'environment': 'dev'
    }
    
    # Merge config
    final_config = {**default_config, **config}
    
    return TrafilaturaSourceV2(final_config)