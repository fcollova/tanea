"""
News Database Manager V2 - Architettura Ibrida
Coordina crawler, storage PostgreSQL+Weaviate, e domini
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import schedule
import time

from .storage.database_manager import DatabaseManager
from .crawler.trafilatura_crawler import TrafilaturaCrawler
from .news_source_trafilatura_v2 import TrafilaturaSourceV2
from .domain_manager import DomainManager
from .config import get_config, get_scheduler_config, get_database_config
from .log import get_database_logger

logger = get_database_logger(__name__)

class NewsVectorDBV2:
    """
    Manager principale per sistema notizie con architettura ibrida:
    - PostgreSQL per link management e metadati operativi
    - Weaviate per ricerca semantica su contenuti
    - Crawler automatico per raccolta proattiva
    - Gestione domini centralizzata
    """
    
    def __init__(self, environment: str = None):
        self.environment = environment or 'dev'
        self.config = get_config(environment)
        
        # Componenti principali
        self.db_manager = None
        self.crawler = None
        self.domain_manager = DomainManager()
        self.trafilatura_source = None
        
        # Stato inizializzazione
        self._initialized = False
        self._scheduler_running = False
    
    async def initialize(self):
        """Inizializza tutti i componenti"""
        if not self._initialized:
            # Database manager (PostgreSQL + Weaviate)
            self.db_manager = DatabaseManager(self.environment)
            await self.db_manager.initialize()
            
            # Crawler
            self.crawler = TrafilaturaCrawler(self.environment)
            
            # Source trafilatura v2
            self.trafilatura_source = TrafilaturaSourceV2({
                'environment': self.environment,
                'use_crawler': True,
                'auto_crawl': False  # Gestito manualmente
            })
            
            self._initialized = True
            logger.info(f"NewsVectorDBV2 inizializzato per ambiente: {self.environment}")
    
    async def close(self):
        """Chiudi tutte le connessioni"""
        if self._initialized:
            if self.db_manager:
                await self.db_manager.close()
            
            if self.trafilatura_source:
                await self.trafilatura_source._cleanup_db()
            
            self._initialized = False
            logger.info("NewsVectorDBV2 disconnesso")
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    # ========================================================================
    # GESTIONE DOMINI E NOTIZIE
    # ========================================================================
    
    async def update_domain_news(self, domain_id: str, force_inactive: bool = False) -> Dict[str, Any]:
        """
        Aggiorna notizie per un dominio specifico usando crawler
        
        Args:
            domain_id: ID dominio (calcio, tecnologia, etc.)
            force_inactive: Forza update anche se dominio inattivo
            
        Returns:
            dict: Statistiche aggiornamento
        """
        try:
            await self.initialize()
            
            # Verifica dominio
            domain_config = self.domain_manager.get_domain(domain_id)
            if not domain_config:
                logger.error(f"Dominio {domain_id} non trovato")
                return {'error': f'Dominio {domain_id} non trovato'}
            
            # Verifica se attivo
            if not domain_config.active and not force_inactive:
                logger.warning(f"Dominio {domain_id} ({domain_config.name}) è disattivato")
                return {'skipped': True, 'reason': 'domain_inactive'}
            
            logger.info(f"Aggiornamento notizie per dominio {domain_config.name}...")
            
            # Lancia crawler per il dominio
            async with self.crawler:
                crawl_stats = await self.crawler.crawl_domain(domain_id)
            
            # Aggiorna statistiche giornaliere
            await self._update_domain_daily_stats(domain_id)
            
            result = {
                'domain': domain_id,
                'domain_name': domain_config.name,
                'crawl_stats': crawl_stats,
                'updated_at': datetime.now().isoformat()
            }
            
            logger.info(f"Dominio {domain_config.name} aggiornato: {crawl_stats}")
            return result
            
        except Exception as e:
            logger.error(f"Errore aggiornamento dominio {domain_id}: {e}")
            return {'error': str(e)}
    
    async def update_all_domains(self, active_only: bool = True) -> Dict[str, Any]:
        """
        Aggiorna notizie per tutti i domini configurati
        
        Args:
            active_only: Solo domini attivi
            
        Returns:
            dict: Risultati per ogni dominio
        """
        try:
            await self.initialize()
            
            results = {}
            domains = self.domain_manager.get_domain_list(active_only=active_only)
            
            logger.info(f"Aggiornamento {len(domains)} domini: {domains}")
            
            for domain_id in domains:
                try:
                    result = await self.update_domain_news(domain_id)
                    results[domain_id] = result
                    
                    # Pausa tra domini per non sovraccaricare
                    await asyncio.sleep(2.0)
                    
                except Exception as e:
                    logger.error(f"Errore aggiornamento dominio {domain_id}: {e}")
                    results[domain_id] = {'error': str(e)}
            
            return {
                'total_domains': len(domains),
                'results': results,
                'completed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Errore aggiornamento tutti i domini: {e}")
            return {'error': str(e)}
    
    async def search_news(self, domain: str, keywords: List[str], max_results: int = 10,
                         language: str = "it", time_range: str = "1d") -> List[Dict[str, Any]]:
        """
        Cerca notizie usando ricerca semantica
        
        Args:
            domain: Dominio di ricerca
            keywords: Keywords di ricerca
            max_results: Massimo risultati
            language: Lingua (default: it)
            time_range: Intervallo temporale
            
        Returns:
            list: Lista articoli trovati
        """
        try:
            await self.initialize()
            
            # Usa TrafilaturaSourceV2 per ricerca semantica
            from .news_sources import NewsQuery
            
            query = NewsQuery(
                keywords=keywords,
                domain=domain,
                max_results=max_results,
                language=language,
                time_range=time_range
            )
            
            # Ricerca asincrona
            news_articles = await self.trafilatura_source._search_news_async(query)
            
            # Converte in dizionari per compatibilità
            results = []
            for article in news_articles:
                result = {
                    'title': article.title,
                    'content': article.content,
                    'url': article.url,
                    'published_date': article.published_date.isoformat() if article.published_date else None,
                    'source': article.source,
                    'score': article.score,
                    'domain': domain,
                    'keywords': keywords,
                    'metadata': article.metadata
                }
                results.append(result)
            
            logger.info(f"Ricerca completata: {len(results)} risultati per {keywords} in {domain}")
            return results
            
        except Exception as e:
            logger.error(f"Errore ricerca notizie: {e}")
            return []
    
    # ========================================================================
    # COMPATIBILITY METHODS (legacy interface)
    # ========================================================================
    
    async def update_football_news(self) -> int:
        """Aggiorna notizie calcio (compatibility method)"""
        logger.info("Aggiornamento notizie calcio (legacy method)")
        
        result = await self.update_domain_news("calcio")
        if 'crawl_stats' in result:
            return result['crawl_stats'].get('articles_extracted', 0)
        return 0
    
    async def search_relevant_context(self, question: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Cerca contesto rilevante per una domanda (compatibility)
        
        Args:
            question: Domanda di ricerca
            k: Numero documenti rilevanti
            
        Returns:
            list: Lista documenti rilevanti
        """
        try:
            await self.initialize()
            
            # Ricerca semantica generica
            articles = await self.db_manager.search_articles(
                query=question,
                limit=k,
                include_metadata=True
            )
            
            # Converte in formato legacy
            documents = []
            for article in articles:
                doc = {
                    'page_content': article.get('content', ''),
                    'metadata': {
                        'title': article.get('title', ''),
                        'source': article.get('source', ''),
                        'published_date': article.get('published_date', ''),
                        'url': article.get('url', ''),
                        'score': article.get('score', 0.0)
                    }
                }
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"Errore ricerca contesto: {e}")
            return []
    
    def get_context_for_question(self, question: str, max_context_length: int = 4000) -> str:
        """
        Ottiene contesto formattato per domanda (compatibility - sync)
        """
        try:
            # Converte a async
            documents = asyncio.run(self.search_relevant_context(question, k=5))
            
            context_parts = []
            current_length = 0
            
            for doc in documents:
                doc_context = f"""
Titolo: {doc['metadata'].get('title', 'N/A')}
Fonte: {doc['metadata'].get('source', 'N/A')}
Data: {doc['metadata'].get('published_date', 'N/A')}
Contenuto: {doc['page_content']}
---
"""
                
                if current_length + len(doc_context) > max_context_length:
                    break
                
                context_parts.append(doc_context)
                current_length += len(doc_context)
            
            return "\\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Errore get_context_for_question: {e}")
            return ""
    
    # ========================================================================
    # MANUTENZIONE E CLEANUP
    # ========================================================================
    
    async def cleanup_old_articles(self, days_old: int = 30) -> Dict[str, Any]:
        """
        Cleanup articoli vecchi da entrambi i database
        
        Args:
            days_old: Età in giorni per considerare obsoleto
            
        Returns:
            dict: Statistiche cleanup
        """
        try:
            await self.initialize()
            return await self.db_manager.cleanup_old_data(days_old)
            
        except Exception as e:
            logger.error(f"Errore cleanup: {e}")
            return {'error': str(e)}
    
    async def sync_databases(self) -> Dict[str, Any]:
        """Sincronizza PostgreSQL e Weaviate"""
        try:
            await self.initialize()
            return await self.db_manager.sync_databases()
            
        except Exception as e:
            logger.error(f"Errore sync database: {e}")
            return {'error': str(e)}
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Statistiche complete sistema"""
        try:
            await self.initialize()
            
            # Stats database
            db_stats = await self.db_manager.get_unified_stats()
            
            # Stats domini
            domain_stats = {}
            for domain_id in self.domain_manager.get_domain_list():
                domain_config = self.domain_manager.get_domain(domain_id)
                domain_stats[domain_id] = {
                    'name': domain_config.name,
                    'active': domain_config.active,
                    'keywords_count': len(domain_config.keywords)
                }
            
            # Health check
            health = await self.db_manager.health_check()
            
            return {
                'environment': self.environment,
                'database_stats': db_stats,
                'domain_stats': domain_stats,
                'health_check': health,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Errore recupero statistiche: {e}")
            return {'error': str(e)}
    
    async def _update_domain_daily_stats(self, domain_id: str):
        """Aggiorna statistiche giornaliere per dominio"""
        try:
            # Trova siti associati al dominio
            sites = await self.db_manager.link_db.get_active_sites()
            
            for site in sites:
                await self.db_manager.link_db.update_daily_stats(site.id)
            
        except Exception as e:
            logger.error(f"Errore aggiornamento stats giornaliere {domain_id}: {e}")
    
    # ========================================================================
    # SCHEDULER AUTOMATICO
    # ========================================================================
    
    def schedule_daily_updates(self):
        """Programma aggiornamenti giornalieri"""
        try:
            scheduler_config = get_scheduler_config()
            
            # Aggiornamenti automatici domini
            schedule.every().day.at(scheduler_config['update_time']).do(
                self._run_scheduled_update
            )
            logger.info(f"Aggiornamenti programmati alle {scheduler_config['update_time']}")
            
            # Cleanup settimanale
            cleanup_day = getattr(schedule.every(), scheduler_config['cleanup_day'])
            cleanup_day.at(scheduler_config['cleanup_time']).do(
                self._run_scheduled_cleanup,
                scheduler_config['cleanup_days_old']
            )
            logger.info(f"Cleanup programmato per {scheduler_config['cleanup_day']} alle {scheduler_config['cleanup_time']}")
            
        except Exception as e:
            logger.error(f"Errore configurazione scheduler: {e}")
    
    def _run_scheduled_update(self):
        """Esegue aggiornamento schedulato"""
        try:
            logger.info("Inizio aggiornamento schedulato")
            result = asyncio.run(self.update_all_domains())
            logger.info(f"Aggiornamento schedulato completato: {result}")
        except Exception as e:
            logger.error(f"Errore aggiornamento schedulato: {e}")
    
    def _run_scheduled_cleanup(self, days_old: int):
        """Esegue cleanup schedulato"""
        try:
            logger.info(f"Inizio cleanup schedulato ({days_old} giorni)")
            result = asyncio.run(self.cleanup_old_articles(days_old))
            logger.info(f"Cleanup schedulato completato: {result}")
        except Exception as e:
            logger.error(f"Errore cleanup schedulato: {e}")
    
    def run_scheduler(self):
        """Esegue scheduler in background"""
        if self._scheduler_running:
            logger.warning("Scheduler già in esecuzione")
            return
        
        try:
            scheduler_config = get_scheduler_config()
            self._scheduler_running = True
            
            logger.info("Avvio scheduler automatico...")
            while self._scheduler_running:
                schedule.run_pending()
                time.sleep(scheduler_config['check_interval'])
                
        except KeyboardInterrupt:
            logger.info("Scheduler interrotto da utente")
        except Exception as e:
            logger.error(f"Errore scheduler: {e}")
        finally:
            self._scheduler_running = False
    
    def stop_scheduler(self):
        """Ferma scheduler"""
        self._scheduler_running = False
        logger.info("Scheduler fermato")


# ========================================================================
# FACTORY FUNCTIONS
# ========================================================================

def create_news_db_v2(environment: str = None) -> NewsVectorDBV2:
    """
    Factory function per creare NewsVectorDBV2
    
    Args:
        environment: Ambiente (dev/prod)
        
    Returns:
        NewsVectorDBV2: Istanza configurata
    """
    return NewsVectorDBV2(environment)


# Compatibilità con codice esistente
NewsVectorDB = NewsVectorDBV2  # Alias per backward compatibility