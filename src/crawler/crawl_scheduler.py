"""
Crawl Scheduler - Gestione scheduling e automazione crawling
"""

import asyncio
import schedule
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from .trafilatura_crawler import TrafilaturaCrawler
from core.storage.database_manager import DatabaseManager
from core.domain_manager import DomainManager
from core.config import get_scheduler_config, get_crawler_config
from core.log import get_news_logger

logger = get_news_logger(__name__)

class JobType(Enum):
    """Tipi di job schedulabili"""
    DOMAIN_CRAWL = "domain_crawl"
    FULL_CRAWL = "full_crawl"
    CLEANUP = "cleanup"
    SYNC = "sync"
    REFRESH = "refresh"

class JobPriority(Enum):
    """Priorità job"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class CrawlScheduler:
    """
    Scheduler per automatizzare crawling e manutenzione
    Gestisce job periodici e on-demand
    """
    
    def __init__(self, environment: str = None):
        self.environment = environment or 'dev'
        self.scheduler_config = get_scheduler_config()
        self.crawler_config = get_crawler_config()
        
        # Componenti
        self.db_manager = None
        self.crawler = None
        self.domain_manager = DomainManager()
        
        # Stato scheduler
        self._running = False
        self._jobs = {}
        self._job_history = []
        
        # Stats
        self.stats = {
            'jobs_completed': 0,
            'jobs_failed': 0,
            'last_run': None,
            'uptime_start': None
        }
    
    async def initialize(self):
        """Inizializza componenti scheduler"""
        if not self.db_manager:
            self.db_manager = DatabaseManager(self.environment)
            await self.db_manager.initialize()
        
        if not self.crawler:
            self.crawler = TrafilaturaCrawler(self.environment)
        
        logger.info("CrawlScheduler inizializzato")
    
    async def close(self):
        """Chiudi componenti"""
        if self.db_manager:
            await self.db_manager.close()
        
        self._running = False
        logger.info("CrawlScheduler chiuso")
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    # ========================================================================
    # CONFIGURAZIONE JOBS AUTOMATICI
    # ========================================================================
    
    def setup_default_schedule(self):
        """Configura schedule default basato su configurazione"""
        try:
            config = self.scheduler_config
            
            # Aggiornamenti giornalieri domini attivi
            schedule.every().day.at(config['update_time']).do(
                self._schedule_job,
                JobType.DOMAIN_CRAWL,
                {'domains': 'active_only'},
                JobPriority.NORMAL
            )
            
            # Cleanup settimanale
            cleanup_day = getattr(schedule.every(), config['cleanup_day'])
            cleanup_day.at(config['cleanup_time']).do(
                self._schedule_job,
                JobType.CLEANUP,
                {'days_old': config['cleanup_days_old']},
                JobPriority.LOW
            )
            
            # Sync database ogni 12 ore
            schedule.every(12).hours.do(
                self._schedule_job,
                JobType.SYNC,
                {},
                JobPriority.LOW
            )
            
            # Refresh contenuti ogni 4 ore per domini ad alta priorità
            schedule.every(4).hours.do(
                self._schedule_job,
                JobType.REFRESH,
                {'domains': ['calcio'], 'hours_old': 12},
                JobPriority.HIGH
            )
            
            logger.info("Schedule default configurato")
            
        except Exception as e:
            logger.error(f"Errore configurazione schedule: {e}")
    
    def add_custom_schedule(self, job_type: JobType, schedule_spec: str, 
                          params: Dict[str, Any] = None, priority: JobPriority = JobPriority.NORMAL):
        """
        Aggiunge schedule personalizzato
        
        Args:
            job_type: Tipo job
            schedule_spec: Specifica schedule (es. "daily", "hourly", "weekly")
            params: Parametri job
            priority: Priorità job
        """
        try:
            params = params or {}
            
            if schedule_spec == "daily":
                schedule.every().day.do(self._schedule_job, job_type, params, priority)
            elif schedule_spec == "hourly":
                schedule.every().hour.do(self._schedule_job, job_type, params, priority)
            elif schedule_spec == "weekly":
                schedule.every().week.do(self._schedule_job, job_type, params, priority)
            elif schedule_spec.startswith("every"):
                # Es. "every 2 hours", "every 30 minutes"
                parts = schedule_spec.split()
                if len(parts) >= 3:
                    interval = int(parts[1])
                    unit = parts[2]
                    
                    if unit.startswith('hour'):
                        schedule.every(interval).hours.do(self._schedule_job, job_type, params, priority)
                    elif unit.startswith('minute'):
                        schedule.every(interval).minutes.do(self._schedule_job, job_type, params, priority)
                    elif unit.startswith('day'):
                        schedule.every(interval).days.do(self._schedule_job, job_type, params, priority)
            
            logger.info(f"Schedule personalizzato aggiunto: {job_type.value} - {schedule_spec}")
            
        except Exception as e:
            logger.error(f"Errore aggiunta schedule personalizzato: {e}")
    
    # ========================================================================
    # ESECUZIONE JOBS
    # ========================================================================
    
    def _schedule_job(self, job_type: JobType, params: Dict[str, Any], priority: JobPriority):
        """Schedula un job per l'esecuzione"""
        job_id = f"{job_type.value}_{int(time.time())}"
        
        job_data = {
            'id': job_id,
            'type': job_type,
            'params': params,
            'priority': priority,
            'scheduled_at': datetime.now(),
            'status': 'scheduled'
        }
        
        self._jobs[job_id] = job_data
        logger.info(f"Job schedulato: {job_id} ({job_type.value})")
        
        # Esegui job asincrono
        asyncio.create_task(self._execute_job(job_data))
    
    async def _execute_job(self, job_data: Dict[str, Any]):
        """Esegue un job specifico"""
        job_id = job_data['id']
        job_type = job_data['type']
        params = job_data['params']
        
        try:
            logger.info(f"Inizio esecuzione job {job_id}")
            job_data['status'] = 'running'
            job_data['started_at'] = datetime.now()
            
            await self.initialize()
            
            # Dispatch per tipo job
            if job_type == JobType.DOMAIN_CRAWL:
                result = await self._execute_domain_crawl(params)
            elif job_type == JobType.FULL_CRAWL:
                result = await self._execute_full_crawl(params)
            elif job_type == JobType.CLEANUP:
                result = await self._execute_cleanup(params)
            elif job_type == JobType.SYNC:
                result = await self._execute_sync(params)
            elif job_type == JobType.REFRESH:
                result = await self._execute_refresh(params)
            else:
                raise ValueError(f"Tipo job non supportato: {job_type}")
            
            # Job completato
            job_data['status'] = 'completed'
            job_data['completed_at'] = datetime.now()
            job_data['result'] = result
            
            self.stats['jobs_completed'] += 1
            self.stats['last_run'] = datetime.now()
            
            logger.info(f"Job {job_id} completato: {result}")
            
        except Exception as e:
            # Job fallito
            job_data['status'] = 'failed'
            job_data['error'] = str(e)
            job_data['failed_at'] = datetime.now()
            
            self.stats['jobs_failed'] += 1
            
            logger.error(f"Job {job_id} fallito: {e}")
        
        finally:
            # Sposta in history
            self._job_history.append(job_data)
            if job_id in self._jobs:
                del self._jobs[job_id]
            
            # Limita history
            if len(self._job_history) > 100:
                self._job_history = self._job_history[-50:]
    
    async def _execute_domain_crawl(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Esegue crawling domini"""
        domains = params.get('domains', 'active_only')
        
        if domains == 'active_only':
            domain_list = self.domain_manager.get_domain_list(active_only=True)
        elif isinstance(domains, list):
            domain_list = domains
        else:
            domain_list = [domains]
        
        results = {}
        async with self.crawler:
            for domain in domain_list:
                try:
                    result = await self.crawler.crawl_domain(domain)
                    results[domain] = result
                    
                    # Pausa tra domini
                    await asyncio.sleep(2.0)
                    
                except Exception as e:
                    results[domain] = {'error': str(e)}
        
        return {
            'domains_processed': len(domain_list),
            'results': results
        }
    
    async def _execute_full_crawl(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Esegue crawling completo"""
        site_names = params.get('site_names')
        domain_filter = params.get('domain_filter')
        
        async with self.crawler:
            result = await self.crawler.crawl_all_sites(site_names, domain_filter)
        
        return result
    
    async def _execute_cleanup(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Esegue cleanup dati vecchi"""
        days_old = params.get('days_old', 30)
        
        # Cleanup PostgreSQL
        pg_cleanup = await self.db_manager.link_db.cleanup_obsolete_links(days_old)
        failed_cleanup = await self.db_manager.link_db.cleanup_failed_links()
        data_cleanup = await self.db_manager.link_db.delete_obsolete_data(days_old * 3)
        
        # Cleanup Weaviate
        weaviate_cleanup = self.db_manager.vector_db.cleanup_old_articles(days_old)
        
        return {
            'postgresql': {
                'obsolete_links': pg_cleanup,
                'failed_links': failed_cleanup,
                'old_data': data_cleanup
            },
            'weaviate': {
                'old_articles': weaviate_cleanup
            }
        }
    
    async def _execute_sync(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Esegue sync database"""
        return await self.db_manager.sync_databases()
    
    async def _execute_refresh(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Esegue refresh contenuti recenti"""
        domains = params.get('domains', [])
        hours_old = params.get('hours_old', 24)
        
        results = {}
        async with self.crawler:
            if domains:
                for domain in domains:
                    result = await self.crawler.crawl_domain(domain)
                    results[domain] = result
            else:
                result = await self.crawler.refresh_recent_content(hours_old)
                results['refresh'] = result
        
        return results
    
    # ========================================================================
    # GESTIONE MANUALE JOBS
    # ========================================================================
    
    async def run_job_now(self, job_type: JobType, params: Dict[str, Any] = None, 
                         priority: JobPriority = JobPriority.HIGH) -> str:
        """
        Esegue job immediatamente
        
        Args:
            job_type: Tipo job
            params: Parametri job
            priority: Priorità (default HIGH per jobs manuali)
            
        Returns:
            str: ID job
        """
        params = params or {}
        job_id = f"manual_{job_type.value}_{int(time.time())}"
        
        job_data = {
            'id': job_id,
            'type': job_type,
            'params': params,
            'priority': priority,
            'scheduled_at': datetime.now(),
            'status': 'manual',
            'manual': True
        }
        
        # Esegui immediatamente
        await self._execute_job(job_data)
        
        return job_id
    
    async def crawl_domain_now(self, domain: str) -> Dict[str, Any]:
        """Crawla dominio immediatamente"""
        job_id = await self.run_job_now(
            JobType.DOMAIN_CRAWL,
            {'domains': [domain]},
            JobPriority.HIGH
        )
        
        # Trova risultato
        for job in self._job_history:
            if job['id'] == job_id:
                return job.get('result', {})
        
        return {'job_id': job_id, 'status': 'submitted'}
    
    async def cleanup_now(self, days_old: int = 30) -> Dict[str, Any]:
        """Esegue cleanup immediatamente"""
        job_id = await self.run_job_now(
            JobType.CLEANUP,
            {'days_old': days_old},
            JobPriority.NORMAL
        )
        
        return {'job_id': job_id, 'status': 'submitted'}
    
    # ========================================================================
    # SCHEDULER LOOP
    # ========================================================================
    
    def start_scheduler(self):
        """Avvia scheduler in background"""
        if self._running:
            logger.warning("Scheduler già in esecuzione")
            return
        
        self._running = True
        self.stats['uptime_start'] = datetime.now()
        
        logger.info("Avvio scheduler automatico...")
        
        try:
            while self._running:
                schedule.run_pending()
                time.sleep(self.scheduler_config['check_interval'])
                
        except KeyboardInterrupt:
            logger.info("Scheduler interrotto da utente")
        except Exception as e:
            logger.error(f"Errore scheduler: {e}")
        finally:
            self._running = False
    
    def stop_scheduler(self):
        """Ferma scheduler"""
        self._running = False
        logger.info("Scheduler fermato")
    
    # ========================================================================
    # MONITORING E STATISTICHE
    # ========================================================================
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Stato corrente scheduler"""
        return {
            'running': self._running,
            'active_jobs': len(self._jobs),
            'stats': self.stats,
            'next_jobs': [
                {
                    'job': str(job),
                    'next_run': job.next_run.isoformat() if job.next_run else None
                }
                for job in schedule.jobs[:5]  # Prossimi 5 job
            ],
            'uptime': (
                datetime.now() - self.stats['uptime_start']
            ).total_seconds() if self.stats['uptime_start'] else 0
        }
    
    def get_job_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """History job recenti"""
        return self._job_history[-limit:]
    
    def get_active_jobs(self) -> Dict[str, Dict[str, Any]]:
        """Jobs attualmente in esecuzione"""
        return self._jobs.copy()
    
    def clear_job_history(self):
        """Pulisce history job"""
        self._job_history.clear()
        logger.info("Job history pulita")


# ========================================================================
# UTILITY FUNCTIONS
# ========================================================================

async def run_one_time_crawl(domain: str = None, environment: str = None) -> Dict[str, Any]:
    """
    Utility per crawling one-time
    
    Args:
        domain: Dominio specifico (None = tutti)
        environment: Ambiente
        
    Returns:
        dict: Risultati crawling
    """
    async with CrawlScheduler(environment) as scheduler:
        if domain:
            return await scheduler.crawl_domain_now(domain)
        else:
            return await scheduler.run_job_now(JobType.FULL_CRAWL)

def create_crawler_scheduler(environment: str = None) -> CrawlScheduler:
    """Factory function per CrawlScheduler"""
    return CrawlScheduler(environment)