"""
Link Database Manager - PostgreSQL con Prisma
Gestisce URL, stati crawling, metadati operativi
"""

import os
import hashlib
import asyncio
import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from prisma import Prisma
from prisma.models import Site, DiscoveredLink, CrawlAttempt, ExtractedArticle, CrawlStats
from prisma.enums import PageType, LinkStatus, JobType, JobStatus

from ..config import get_database_config
from ..log import get_news_logger

logger = get_news_logger(__name__)

class LinkDatabase:
    """Database PostgreSQL per gestione link e crawler"""
    
    def __init__(self):
        self.db_config = get_database_config()
        self.db = Prisma()
        self._connected = False
    
    async def connect(self):
        """Connetti al database"""
        if not self._connected:
            await self.db.connect()
            self._connected = True
            logger.info("Connesso a PostgreSQL via Prisma")
    
    async def disconnect(self):
        """Disconnetti dal database"""
        if self._connected:
            await self.db.disconnect()
            self._connected = False
            logger.info("Disconnesso da PostgreSQL")
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
    
    # ========================================================================
    # GESTIONE SITI
    # ========================================================================
    
    async def create_site(self, name: str, base_url: str, config: Dict[str, Any] = None) -> Site:
        """Crea nuovo sito"""
        # Converte config in JSON se è un dict
        config_json = json.dumps(config) if config else None
        
        site = await self.db.site.create(
            data={
                'name': name,
                'base_url': base_url,
                'config': config_json
            }
        )
        logger.info(f"Sito creato: {name} ({site.id})")
        return site
    
    async def get_site_by_name(self, name: str) -> Optional[Site]:
        """Recupera sito per nome"""
        return await self.db.site.find_unique(where={'name': name})
    
    async def get_active_sites(self) -> List[Site]:
        """Recupera tutti i siti attivi"""
        return await self.db.site.find_many(
            where={'active': True},
            order={'priority': 'asc'}
        )
    
    async def update_site_config(self, site_id: str, config: Dict[str, Any]):
        """Aggiorna configurazione sito"""
        # Converte config in JSON se è un dict
        config_json = json.dumps(config) if config else None
        
        await self.db.site.update(
            where={'id': site_id},
            data={'config': config_json, 'updated_at': datetime.now()}
        )
        logger.info(f"Configurazione sito {site_id} aggiornata")
    
    # ========================================================================
    # GESTIONE LINK
    # ========================================================================
    
    def _hash_url(self, url: str) -> str:
        """Genera hash SHA256 per URL"""
        return hashlib.sha256(url.encode('utf-8')).hexdigest()
    
    async def add_discovered_links(self, links: List[str], site_id: str, 
                                 parent_url: str = None, page_type: PageType = PageType.ARTICLE,
                                 depth: int = 0) -> int:
        """Aggiunge link scoperti (batch insert)"""
        if not links:
            return 0
            
        # Prepara dati per batch insert
        link_data = []
        for url in links:
            link_data.append({
                'url': url,
                'url_hash': self._hash_url(url),
                'site_id': site_id,
                'parent_url': parent_url,
                'page_type': page_type,
                'depth': depth,
                'status': LinkStatus.NEW
            })
        
        # Batch insert con skip duplicati
        created_count = 0
        for data in link_data:
            try:
                await self.db.discoveredlink.create(data=data)
                created_count += 1
            except Exception:
                # Skip duplicati (constraint violation)
                continue
        
        logger.info(f"Aggiunti {created_count}/{len(links)} nuovi link per sito {site_id}")
        return created_count
    
    async def get_links_to_crawl(self, site_id: str = None, limit: int = 100, 
                               status: LinkStatus = LinkStatus.NEW) -> List[DiscoveredLink]:
        """Recupera link da crawlare"""
        where_clause = {'status': status}
        if site_id:
            where_clause['site_id'] = site_id
        
        links = await self.db.discoveredlink.find_many(
            where=where_clause,
            include={'site': True},
            order={'discovered_at': 'asc'},
            take=limit
        )
        
        logger.debug(f"Recuperati {len(links)} link da crawlare")
        return links
    
    async def mark_link_crawling(self, link_id: str):
        """Marca link come in corso di crawling"""
        await self.db.discoveredlink.update(
            where={'id': link_id},
            data={'status': LinkStatus.CRAWLING, 'updated_at': datetime.now()}
        )
    
    async def mark_link_crawled(self, link_id: str, success: bool, 
                              response_time: int = None, content_length: int = None,
                              content_hash: str = None, error_message: str = None):
        """Marca link come crawlato"""
        # Aggiorna link
        status = LinkStatus.CRAWLED if success else LinkStatus.FAILED
        update_data = {
            'status': status,
            'last_crawled': datetime.now(),
            'crawl_count': {'increment': 1},
            'updated_at': datetime.now()
        }
        
        if not success:
            update_data['error_count'] = {'increment': 1}
        if content_hash:
            update_data['content_hash'] = content_hash
            
        await self.db.discoveredlink.update(
            where={'id': link_id},
            data=update_data
        )
        
        # Registra tentativo
        await self.db.crawlattempt.create(
            data={
                'link_id': link_id,
                'success': success,
                'response_time': response_time,
                'content_length': content_length,
                'error_message': error_message
            }
        )
        
        logger.debug(f"Link {link_id} marcato come {'crawlato' if success else 'fallito'}")
    
    async def get_link_by_url(self, url: str) -> Optional[DiscoveredLink]:
        """Recupera link per URL"""
        url_hash = self._hash_url(url)
        return await self.db.discoveredlink.find_unique(
            where={'url_hash': url_hash},
            include={'site': True}
        )
    
    async def check_content_duplicate(self, content_hash: str) -> Optional[DiscoveredLink]:
        """Verifica se contenuto è duplicato"""
        return await self.db.discoveredlink.find_first(
            where={'content_hash': content_hash},
            include={'extracted_article': True}
        )
    
    # ========================================================================
    # GESTIONE ARTICOLI ESTRATTI
    # ========================================================================
    
    async def store_extracted_article(self, link_id: str, title: str, author: str = None,
                                    published_date: datetime = None, content_length: int = 0,
                                    quality_score: float = 0.0, domain: str = "general",
                                    keywords: List[str] = None, weaviate_id: str = None,
                                    metadata: Dict[str, Any] = None) -> ExtractedArticle:
        """Salva metadati articolo estratto"""
        # Converte metadata in JSON se è un dict
        metadata_json = json.dumps(metadata) if metadata else None
        
        article = await self.db.extractedarticle.create(
            data={
                'link_id': link_id,
                'weaviate_id': weaviate_id,
                'title': title,
                'author': author,
                'published_date': published_date,
                'content_length': content_length,
                'quality_score': quality_score,
                'domain': domain,
                'keywords': keywords or [],
                'metadata': metadata_json
            }
        )
        
        logger.info(f"Articolo estratto salvato: {title[:50]}... (ID: {article.id})")
        return article
    
    async def get_articles_by_domain(self, domain: str, limit: int = 50, 
                                   min_quality: float = 0.0) -> List[ExtractedArticle]:
        """Recupera articoli per dominio"""
        return await self.db.extractedarticle.find_many(
            where={
                'domain': domain,
                'quality_score': {'gte': min_quality}
            },
            include={'link': {'include': {'site': True}}},
            order={'published_date': 'desc'},
            take=limit
        )
    
    async def get_recent_articles(self, hours: int = 24, limit: int = 100) -> List[ExtractedArticle]:
        """Recupera articoli recenti"""
        since = datetime.now() - timedelta(hours=hours)
        return await self.db.extractedarticle.find_many(
            where={'extracted_at': {'gte': since}},
            include={'link': {'include': {'site': True}}},
            order={'extracted_at': 'desc'},
            take=limit
        )
    
    # ========================================================================
    # CLEANUP E MANUTENZIONE
    # ========================================================================
    
    async def cleanup_obsolete_links(self, days_old: int = 30) -> int:
        """Rimuove link obsoleti"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        # Marca come obsoleti i link vecchi falliti o mai crawlati
        result = await self.db.discoveredlink.update_many(
            where={
                'discovered_at': {'lt': cutoff_date},
                'status': {'in': [LinkStatus.FAILED, LinkStatus.NEW]}
            },
            data={'status': LinkStatus.OBSOLETE}
        )
        
        logger.info(f"Marcati {result.count} link come obsoleti")
        return result.count
    
    async def cleanup_failed_links(self, max_failures: int = 3) -> int:
        """Rimuove link con troppi fallimenti"""
        result = await self.db.discoveredlink.update_many(
            where={'error_count': {'gte': max_failures}},
            data={'status': LinkStatus.BLOCKED}
        )
        
        logger.info(f"Bloccati {result.count} link per troppi fallimenti")
        return result.count
    
    async def delete_obsolete_data(self, days_old: int = 90) -> Dict[str, int]:
        """Elimina dati troppo vecchi"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        # Elimina tentativi di crawling vecchi
        crawl_attempts = await self.db.crawlattempt.delete_many(
            where={'attempted_at': {'lt': cutoff_date}}
        )
        
        # Elimina link obsoleti vecchi
        obsolete_links = await self.db.discoveredlink.delete_many(
            where={
                'status': LinkStatus.OBSOLETE,
                'updated_at': {'lt': cutoff_date}
            }
        )
        
        result = {
            'crawl_attempts': crawl_attempts.count,
            'obsolete_links': obsolete_links.count
        }
        
        logger.info(f"Dati eliminati: {result}")
        return result
    
    # ========================================================================
    # STATISTICHE
    # ========================================================================
    
    async def get_crawl_stats(self, site_id: str = None, days: int = 7) -> Dict[str, Any]:
        """Statistiche crawling"""
        since = datetime.now() - timedelta(days=days)
        
        where_clause = {'discovered_at': {'gte': since}}
        if site_id:
            where_clause['site_id'] = site_id
        
        # Count per status
        stats = {}
        for status in LinkStatus:
            count = await self.db.discoveredlink.count(
                where={**where_clause, 'status': status}
            )
            stats[status.value.lower()] = count
        
        # Articoli estratti
        articles_count = await self.db.extractedarticle.count(
            where={'extracted_at': {'gte': since}}
        )
        stats['articles_extracted'] = articles_count
        
        # Rate di successo
        total_attempts = stats.get('crawled', 0) + stats.get('failed', 0)
        stats['success_rate'] = (stats.get('crawled', 0) / total_attempts) if total_attempts > 0 else 0
        
        return stats
    
    async def update_daily_stats(self, site_id: str):
        """Aggiorna statistiche giornaliere per sito"""
        today = datetime.now().date()
        
        # Calcola statistiche
        links_discovered = await self.db.discoveredlink.count(
            where={
                'site_id': site_id,
                'discovered_at': {
                    'gte': datetime.combine(today, datetime.min.time()),
                    'lt': datetime.combine(today, datetime.max.time())
                }
            }
        )
        
        links_crawled = await self.db.discoveredlink.count(
            where={
                'site_id': site_id,
                'status': LinkStatus.CRAWLED,
                'last_crawled': {
                    'gte': datetime.combine(today, datetime.min.time()),
                    'lt': datetime.combine(today, datetime.max.time())
                }
            }
        )
        
        articles_extracted = await self.db.extractedarticle.count(
            where={
                'link': {'site_id': site_id},
                'extracted_at': {
                    'gte': datetime.combine(today, datetime.min.time()),
                    'lt': datetime.combine(today, datetime.max.time())
                }
            }
        )
        
        errors_count = await self.db.crawlattempt.count(
            where={
                'success': False,
                'attempted_at': {
                    'gte': datetime.combine(today, datetime.min.time()),
                    'lt': datetime.combine(today, datetime.max.time())
                },
                'link': {'site_id': site_id}
            }
        )
        
        # Upsert statistiche
        await self.db.crawlstats.upsert(
            where={'site_id_date': {'site_id': site_id, 'date': today}},
            data={
                'create': {
                    'site_id': site_id,
                    'date': today,
                    'links_discovered': links_discovered,
                    'links_crawled': links_crawled,
                    'articles_extracted': articles_extracted,
                    'errors_count': errors_count
                },
                'update': {
                    'links_discovered': links_discovered,
                    'links_crawled': links_crawled,
                    'articles_extracted': articles_extracted,
                    'errors_count': errors_count
                }
            }
        )
        
        logger.info(f"Statistiche giornaliere aggiornate per sito {site_id}")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

async def init_sites_from_config(link_db: LinkDatabase, sites_config: Dict[str, Any]):
    """Inizializza siti dal config YAML"""
    if 'sites' not in sites_config:
        return
    
    for site_key, site_config in sites_config['sites'].items():
        existing_site = await link_db.get_site_by_name(site_key)
        if not existing_site:
            await link_db.create_site(
                name=site_key,
                base_url=site_config['base_url'],
                config=site_config
            )
            logger.info(f"Sito {site_key} inizializzato nel database")
        else:
            # Aggiorna configurazione se necessario
            await link_db.update_site_config(existing_site.id, site_config)