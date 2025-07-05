"""
Database Manager - Coordinatore architettura ibrida
Coordina PostgreSQL (link management) + Weaviate (semantic search)
"""

import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime

from .link_database import LinkDatabase
from .vector_collections import VectorCollections
from ..config import get_database_config, get_weaviate_config
from ..log import get_news_logger

logger = get_news_logger(__name__)

class DatabaseManager:
    """Coordinatore per architettura ibrida PostgreSQL + Weaviate"""
    
    def __init__(self, environment: str = None):
        self.environment = environment or 'dev'
        
        # Inizializza componenti storage
        self.link_db = LinkDatabase()
        self.vector_db = VectorCollections(environment)
        
        self._link_db_connected = False
        self._vector_db_initialized = False
    
    async def initialize(self):
        """Inizializza entrambi i database"""
        await self._init_link_database()
        self._init_vector_database()
        logger.info("DatabaseManager inizializzato completamente")
    
    async def _init_link_database(self):
        """Inizializza connessione PostgreSQL"""
        if not self._link_db_connected:
            await self.link_db.connect()
            self._link_db_connected = True
    
    def _init_vector_database(self):
        """Inizializza connessione Weaviate"""
        if not self._vector_db_initialized:
            self.vector_db.initialize()
            self._vector_db_initialized = True
    
    async def close(self):
        """Chiudi tutte le connessioni"""
        if self._link_db_connected:
            await self.link_db.disconnect()
            self._link_db_connected = False
        
        if self._vector_db_initialized:
            self.vector_db.close()
            self._vector_db_initialized = False
        
        logger.info("DatabaseManager disconnesso")
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    # ========================================================================
    # ORCHESTRAZIONE CRAWLING + STORAGE
    # ========================================================================
    
    async def process_crawled_article(self, link_id: str, article_data: Dict[str, Any]) -> bool:
        """
        Processa articolo crawlato: salva in Weaviate + aggiorna PostgreSQL
        
        Args:
            link_id: ID del link in PostgreSQL
            article_data: Dati articolo estratto da trafilatura
            
        Returns:
            bool: True se successo, False altrimenti
        """
        try:
            # 1. Verifica che il link esista
            link = await self.link_db.db.discoveredlink.find_unique(
                where={'id': link_id},
                include={'site': True}
            )
            
            if not link:
                logger.error(f"Link {link_id} non trovato in database")
                return False
            
            # 2. Calcola hash contenuto per duplicati
            content_hash = self.link_db._hash_url(article_data.get('content', ''))
            
            # 3. Verifica duplicati
            existing_duplicate = await self.link_db.check_content_duplicate(content_hash)
            if existing_duplicate and existing_duplicate.id != link_id:
                logger.info(f"Contenuto duplicato trovato: {existing_duplicate.url}")
                await self.link_db.mark_link_crawled(
                    link_id, 
                    success=False, 
                    error_message="Contenuto duplicato"
                )
                return False
            
            # 4. Salva articolo in Weaviate
            weaviate_id = self.vector_db.store_article(article_data, link_id)
            if not weaviate_id:
                await self.link_db.mark_link_crawled(
                    link_id,
                    success=False,
                    error_message="Errore salvataggio Weaviate"
                )
                return False
            
            # 5. Salva metadati in PostgreSQL
            extracted_article = await self.link_db.store_extracted_article(
                link_id=link_id,
                title=article_data.get('title', ''),
                author=article_data.get('author'),
                published_date=article_data.get('published_date'),
                content_length=len(article_data.get('content', '')),
                quality_score=article_data.get('quality_score', 0.0),
                domain=article_data.get('domain', 'general'),
                keywords=article_data.get('keywords', []),
                weaviate_id=weaviate_id,
                metadata=article_data.get('metadata', {})
            )
            
            # 6. Marca link come crawlato con successo
            await self.link_db.mark_link_crawled(
                link_id,
                success=True,
                content_length=len(article_data.get('content', '')),
                content_hash=content_hash
            )
            
            logger.info(f"Articolo processato con successo: {article_data.get('title', 'No title')[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Errore processing articolo {link_id}: {e}")
            try:
                await self.link_db.mark_link_crawled(
                    link_id,
                    success=False,
                    error_message=str(e)
                )
            except:
                pass
            return False
    
    async def batch_process_articles(self, articles_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Processa batch di articoli crawlati
        
        Args:
            articles_data: Lista dizionari con 'link_id' e dati articolo
            
        Returns:
            dict: Statistiche processing
        """
        stats = {'success': 0, 'failed': 0, 'duplicates': 0}
        
        for article_item in articles_data:
            link_id = article_item.get('link_id')
            article_data = article_item.get('article_data', {})
            
            if not link_id:
                stats['failed'] += 1
                continue
            
            success = await self.process_crawled_article(link_id, article_data)
            if success:
                stats['success'] += 1
            else:
                stats['failed'] += 1
        
        logger.info(f"Batch processing completato: {stats}")
        return stats
    
    # ========================================================================
    # RICERCA UNIFICATA
    # ========================================================================
    
    async def search_articles(self, query: str, domain: str = None, limit: int = 10,
                            include_metadata: bool = True) -> List[Dict[str, Any]]:
        """
        Ricerca articoli con metadati enriched
        
        Args:
            query: Query di ricerca semantica
            domain: Filtra per dominio
            limit: Numero massimo risultati
            include_metadata: Include metadati da PostgreSQL
            
        Returns:
            list: Lista articoli con metadati completi
        """
        try:
            # 1. Ricerca semantica in Weaviate
            articles = self.vector_db.search_articles(query, domain, limit)
            
            if not include_metadata or not articles:
                return articles
            
            # 2. Enrichment con metadati PostgreSQL
            enriched_articles = []
            for article in articles:
                link_id = article.get('link_id')
                if link_id:
                    try:
                        # Recupera metadati link dal PostgreSQL
                        link_metadata = await self.link_db.db.discoveredlink.find_unique(
                            where={'id': link_id},
                            include={
                                'site': True,
                                'extracted_article': True,
                                'crawl_attempts': {
                                    'order_by': {'attempted_at': 'desc'},
                                    'take': 1
                                }
                            }
                        )
                        
                        if link_metadata:
                            # Enrichment con dati PostgreSQL
                            article.update({
                                'site_name': link_metadata.site.name if link_metadata.site else '',
                                'discovered_at': link_metadata.discovered_at.isoformat() if link_metadata.discovered_at else '',
                                'crawl_count': link_metadata.crawl_count,
                                'last_crawled': link_metadata.last_crawled.isoformat() if link_metadata.last_crawled else '',
                                'page_type': link_metadata.page_type.value if link_metadata.page_type else '',
                                'extraction_metadata': link_metadata.extracted_article.metadata if link_metadata.extracted_article else {}
                            })
                    
                    except Exception as e:
                        logger.warning(f"Errore enrichment metadati per link {link_id}: {e}")
                
                enriched_articles.append(article)
            
            return enriched_articles
            
        except Exception as e:
            logger.error(f"Errore ricerca articoli: {e}")
            return []
    
    async def get_articles_by_domain(self, domain: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Recupera articoli per dominio con metadati"""
        return await self.search_articles("", domain=domain, limit=limit)
    
    # ========================================================================
    # SYNC E MANUTENZIONE
    # ========================================================================
    
    async def sync_databases(self) -> Dict[str, Any]:
        """
        Sincronizza dati tra PostgreSQL e Weaviate
        Identifica e risolve inconsistenze
        """
        sync_stats = {
            'orphaned_weaviate': 0,
            'missing_weaviate': 0,
            'fixed_inconsistencies': 0
        }
        
        try:
            # 1. Trova articoli in PostgreSQL senza corrispondente Weaviate
            extracted_articles = await self.link_db.db.extractedarticle.find_many(
                where={'weaviate_id': {'not': None}},
                include={'link': True}
            )
            
            for article in extracted_articles:
                if article.weaviate_id:
                    # Verifica che esista in Weaviate
                    try:
                        collection = self.vector_db.weaviate_client.collections.get(
                            self.vector_db.articles_collection_name
                        )
                        weaviate_obj = collection.query.fetch_object_by_id(article.weaviate_id)
                        
                        if not weaviate_obj:
                            # Articolo orfano in PostgreSQL
                            logger.warning(f"Articolo {article.id} ha weaviate_id {article.weaviate_id} ma non esiste in Weaviate")
                            # Rimuovi riferimento weaviate_id
                            await self.link_db.db.extractedarticle.update(
                                where={'id': article.id},
                                data={'weaviate_id': None}
                            )
                            sync_stats['missing_weaviate'] += 1
                            
                    except Exception as e:
                        logger.warning(f"Errore verifica articolo {article.weaviate_id}: {e}")
            
            # 2. Cleanup articoli Weaviate orfani (opzionale - più complesso)
            # Per ora log solo inconsistenze trovate
            
            logger.info(f"Sync database completato: {sync_stats}")
            return sync_stats
            
        except Exception as e:
            logger.error(f"Errore sync database: {e}")
            return sync_stats
    
    async def cleanup_old_data(self, days_old: int = 90) -> Dict[str, Any]:
        """Cleanup dati vecchi da entrambi i database"""
        cleanup_stats = {}
        
        try:
            # 1. Cleanup PostgreSQL
            pg_stats = await self.link_db.delete_obsolete_data(days_old)
            cleanup_stats.update({'postgresql': pg_stats})
            
            # 2. Cleanup Weaviate  
            weaviate_deleted = self.vector_db.cleanup_old_articles(days_old)
            cleanup_stats.update({'weaviate_articles': weaviate_deleted})
            
            logger.info(f"Cleanup completato: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Errore cleanup: {e}")
            return cleanup_stats
    
    # ========================================================================
    # STATISTICHE UNIFICATE
    # ========================================================================
    
    async def get_unified_stats(self) -> Dict[str, Any]:
        """Statistiche unificate entrambi database"""
        try:
            # Stats PostgreSQL
            pg_stats = await self.link_db.get_crawl_stats()
            
            # Stats Weaviate
            weaviate_stats = self.vector_db.get_collection_stats()
            
            # Stats unificate
            unified_stats = {
                'postgresql': pg_stats,
                'weaviate': weaviate_stats,
                'environment': self.environment,
                'last_updated': datetime.now().isoformat()
            }
            
            return unified_stats
            
        except Exception as e:
            logger.error(f"Errore recupero statistiche: {e}")
            return {}
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    async def health_check(self) -> Dict[str, bool]:
        """Verifica salute entrambi database"""
        health = {
            'postgresql': False,
            'weaviate': False,
            'overall': False
        }
        
        try:
            # Test PostgreSQL
            await self.link_db.db.site.count()
            health['postgresql'] = True
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
        
        try:
            # Test Weaviate
            self.vector_db.get_collection_stats()
            health['weaviate'] = True
        except Exception as e:
            logger.error(f"Weaviate health check failed: {e}")
        
        health['overall'] = health['postgresql'] and health['weaviate']
        return health