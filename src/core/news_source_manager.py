"""
Manager per fonti di notizie multiple con sistema migliorato
"""

import hashlib
from typing import List, Dict, Optional, Any, Set
from datetime import datetime

from .news_source_base import NewsSource, NewsQuery, NewsArticle
from .domain_config import get_domain_config
from .log import get_news_logger

logger = get_news_logger(__name__)

class NewsSourceManager:
    """Gestore intelligente per multiple fonti di notizie"""
    
    def __init__(self):
        self.sources: Dict[str, NewsSource] = {}
        self.logger = get_news_logger(f"{__name__}.{self.__class__.__name__}")
        self._url_cache: Set[str] = set()  # Cache per deduplica URL
        self.domain_config = get_domain_config()
        
        # Mapping domini → fonti preferite (dinamico da domains.yaml)
        self.domain_preferences = self._build_domain_preferences()
    
    def _build_domain_preferences(self) -> Dict[str, List[str]]:
        """Costruisce le preferenze dei domini dinamicamente da domains.yaml"""
        preferences = {}
        active_domains = self.domain_config.get_active_domains()
        
        for domain in active_domains:
            # Logica per assegnare fonti basata sul tipo di dominio
            if domain == 'calcio':
                preferences[domain] = ['rss', 'scraping', 'newsapi', 'tavily']
            elif domain == 'tecnologia':
                preferences[domain] = ['tavily', 'newsapi', 'rss', 'scraping']
            elif domain == 'finanza':
                preferences[domain] = ['newsapi', 'rss', 'scraping', 'tavily']
            elif domain in ['salute', 'ambiente']:
                preferences[domain] = ['rss', 'newsapi', 'scraping', 'tavily']
            else:
                # Default per domini non specificati
                preferences[domain] = ['rss', 'newsapi', 'scraping', 'tavily']
        
        return preferences
    
    def add_source(self, name: str, source: NewsSource):
        """Aggiunge una fonte di notizie"""
        self.sources[name] = source
        self.logger.info(f"Aggiunta fonte: {name} (priorità: {source.priority})")
    
    def remove_source(self, name: str):
        """Rimuove una fonte di notizie"""
        if name in self.sources:
            del self.sources[name]
            self.logger.info(f"Rimossa fonte: {name}")
    
    def get_available_sources(self) -> List[str]:
        """Ottiene fonti disponibili ordinate per priorità, affidabilità e salute"""
        available = []
        for name, source in self.sources.items():
            if source.is_available() and source.can_make_request():
                available.append((name, source.priority, source.reliability_score, source.health_score))
        
        # Ordina per priorità (1=alta), poi per health score, poi per affidabilità
        available.sort(key=lambda x: (x[1], -x[3], -x[2]))
        return [name for name, _, _, _ in available]
    
    def get_domain_sources(self, domain: str) -> List[str]:
        """Ottiene fonti appropriate per un dominio specifico"""
        # Valida che il dominio sia configurato e attivo
        if not self.domain_config.validate_domain(domain):
            self.logger.warning(f"Dominio non configurato: {domain}")
            return self.get_available_sources()
        
        if not self.domain_config.is_domain_active(domain):
            self.logger.warning(f"Dominio non attivo: {domain}")
            return []
        
        domain_lower = domain.lower()
        
        # Usa le preferenze configurate dinamicamente
        if domain_lower in self.domain_preferences:
            preferred_sources = self.domain_preferences[domain_lower]
            available = self.get_available_sources()
            ordered_sources = []
            
            # Prima aggiungi fonti preferite per il dominio
            for pref_source in preferred_sources:
                if pref_source in available:
                    ordered_sources.append(pref_source)
                    
            # Poi aggiungi altre fonti disponibili
            for source in available:
                if source not in ordered_sources:
                    ordered_sources.append(source)
                    
            return ordered_sources
        
        # Fallback: tutte le fonti disponibili
        return self.get_available_sources()
    
    def deduplicate_articles(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Rimuove articoli duplicati basandosi su URL e contenuto"""
        seen_urls = set()
        seen_content_hashes = set()
        deduplicated = []
        
        for article in articles:
            # Deduplica per URL
            if article.url and article.url in seen_urls:
                continue
            
            # Deduplica per contenuto (hash del titolo + primi 200 char)
            content_for_hash = f"{article.title}{article.content[:200]}"
            content_hash = hashlib.md5(content_for_hash.encode()).hexdigest()
            
            if content_hash in seen_content_hashes:
                continue
                
            # Articolo unico
            if article.url:
                seen_urls.add(article.url)
            seen_content_hashes.add(content_hash)
            deduplicated.append(article)
        
        removed_count = len(articles) - len(deduplicated)
        if removed_count > 0:
            self.logger.info(f"Rimossi {removed_count} articoli duplicati")
            
        return deduplicated
    
    def search_hybrid(self, query: NewsQuery) -> List[NewsArticle]:
        """
        Ricerca ibrida: combina risultati da multiple fonti con deduplica
        """
        # Ottieni fonti appropriate per il dominio
        domain_sources = self.get_domain_sources(query.domain)
        
        if not domain_sources:
            self.logger.warning("Nessuna fonte disponibile")
            return []
        
        all_articles = []
        articles_per_source = max(1, query.max_results // len(domain_sources))
        
        for source_name in domain_sources:
            try:
                source = self.sources[source_name]
                
                # Crea query specifica per questa fonte
                source_query = NewsQuery(
                    keywords=query.keywords,
                    domain=query.domain,
                    max_results=articles_per_source,
                    language=query.language,
                    time_range=query.time_range,
                    preferred_sources=query.preferred_sources
                )
                
                articles = source.search_news(source_query)
                all_articles.extend(articles)
                
                self.logger.info(f"Fonte {source_name}: {len(articles)} articoli")
                
                # Se abbiamo abbastanza articoli, fermiamoci
                if len(all_articles) >= query.max_results * 1.5:  # 50% extra per deduplica
                    break
                    
            except Exception as e:
                self.logger.error(f"Errore ricerca su {source_name}: {e}")
                continue
        
        # Deduplica e ordina per rilevanza
        deduplicated = self.deduplicate_articles(all_articles)
        
        # Ordina per score e data
        deduplicated.sort(
            key=lambda x: (
                x.score or 0.0,
                x.published_date or datetime.min
            ), 
            reverse=True
        )
        
        return deduplicated[:query.max_results]
    
    def search_best_source(self, query: NewsQuery) -> List[NewsArticle]:
        """Cerca notizie sulla migliore fonte disponibile per il dominio"""
        domain_sources = self.get_domain_sources(query.domain)
        
        if not domain_sources:
            self.logger.warning("Nessuna fonte disponibile")
            return []
        
        # Prova fonti in ordine di priorità
        for source_name in domain_sources:
            try:
                source = self.sources[source_name]
                articles = source.search_news(query)
                
                if articles:
                    self.logger.info(f"Utilizzata fonte {source_name}: {len(articles)} articoli")
                    return articles
                    
            except Exception as e:
                self.logger.error(f"Errore ricerca su {source_name}: {e}")
                continue
        
        self.logger.warning("Nessuna fonte ha prodotto risultati")
        return []
    
    def search_all_sources(self, query: NewsQuery) -> Dict[str, List[NewsArticle]]:
        """Cerca notizie su tutte le fonti disponibili (per debug/analisi)"""
        results = {}
        
        for name, source in self.sources.items():
            if source.is_available():
                try:
                    articles = source.search_news(query)
                    results[name] = articles
                    self.logger.info(f"Fonte {name}: {len(articles)} articoli")
                except Exception as e:
                    self.logger.error(f"Errore nella ricerca su {name}: {e}")
                    results[name] = []
            else:
                self.logger.warning(f"Fonte {name} non disponibile")
                results[name] = []
        
        return results
    
    def get_source_stats(self) -> Dict[str, Dict[str, Any]]:
        """Ottiene statistiche sulle fonti"""
        stats = {}
        
        for name, source in self.sources.items():
            stats[name] = {
                'available': source.is_available(),
                'can_request': source.can_make_request(),
                'priority': source.priority,
                'reliability': source.reliability_score,
                'health_score': source.health_score,
                'success_count': source.metrics.success_count,
                'error_count': source.metrics.error_count,
                'avg_response_time': source.metrics.avg_response_time,
                'adaptive_delay': source.metrics.adaptive_delay,
                'last_request': source.metrics.last_request_time.isoformat() if source.metrics.last_request_time else None,
                'last_success': source.metrics.last_success_time.isoformat() if source.metrics.last_success_time else None,
                'rate_limit_until': source.metrics.rate_limit_until.isoformat() if source.metrics.rate_limit_until else None
            }
            
        return stats
    
    def get_health_report(self) -> Dict[str, Any]:
        """Genera report completo sulla salute del sistema"""
        stats = self.get_source_stats()
        
        working_sources = [name for name, stat in stats.items() if stat['available'] and stat['health_score'] > 0.5]
        failing_sources = [name for name, stat in stats.items() if stat['health_score'] <= 0.3]
        
        # Fonti per dominio
        domain_health = {}
        for domain in self.domain_config.get_active_domains():
            domain_sources = self.get_domain_sources(domain)
            domain_working = [s for s in domain_sources if s in working_sources]
            domain_health[domain] = {
                'total_sources': len(domain_sources),
                'working_sources': len(domain_working),
                'health_ratio': len(domain_working) / len(domain_sources) if domain_sources else 0
            }
        
        return {
            'total_sources': len(self.sources),
            'working_sources': len(working_sources),
            'failing_sources': len(failing_sources),
            'overall_health': len(working_sources) / len(self.sources) if self.sources else 0,
            'working_source_names': working_sources,
            'failing_source_names': failing_sources,
            'domain_health': domain_health,
            'source_details': stats
        }