"""
Modulo base per le fonti di notizie
Contiene classi base, dataclass e utilities comuni a tutte le implementazioni
"""

import os
import time
import hashlib
import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin

# from langchain.schema import Document  # Commentato per testing

from .config import get_search_config
from .domain_config import get_domain_config, get_active_domains
from .log import get_news_logger

logger = get_news_logger(__name__)

@dataclass
class NewsQuery:
    """Configurazione per la ricerca di notizie"""
    keywords: List[str]
    domain: str = ""
    max_results: int = 10
    language: str = "it"
    time_range: str = "1d"  # 1d, 1w, 1m
    sources: Optional[List[str]] = None
    include_content: bool = True
    include_raw_content: bool = True
    preferred_sources: Optional[List[str]] = None

@dataclass
class NewsArticle:
    """Rappresenta un articolo di notizie"""
    title: str
    content: str
    url: str
    published_date: Optional[datetime] = None
    source: Optional[str] = None
    score: Optional[float] = None
    raw_content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass 
class SourceMetrics:
    """Metriche per una fonte di notizie"""
    success_count: int = 0
    error_count: int = 0
    last_request_time: Optional[datetime] = None
    rate_limit_until: Optional[datetime] = None
    avg_response_time: float = 0.0
    last_success_time: Optional[datetime] = None
    adaptive_delay: float = 1.0  # Delay adattivo

class NewsSource(ABC):
    """Classe base astratta per fonti di notizie con miglioramenti"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_news_logger(f"{__name__}.{self.__class__.__name__}")
        self.metrics = SourceMetrics()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self._get_user_agent()
        })
        
        # Rate limiting migliorato
        self.base_rate_limit_delay = config.get('rate_limit_delay', 1.0)
        self.timeout = config.get('timeout', 10)  # Ridotto da 20 a 10
        self.max_retries = config.get('max_retries', 3)
        
        # Inizializza delay adattivo
        self.metrics.adaptive_delay = self.base_rate_limit_delay
        
    def _get_user_agent(self) -> str:
        """Ottiene User-Agent randomizzato"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        ]
        import random
        return random.choice(user_agents)
    
    @property
    def priority(self) -> int:
        """Priorità della fonte (1=alta, 2=media, 3=bassa)"""
        return 3
    
    @property
    def reliability_score(self) -> float:
        """Punteggio affidabilità basato su metriche"""
        total_requests = self.metrics.success_count + self.metrics.error_count
        if total_requests == 0:
            return 1.0
        return self.metrics.success_count / total_requests
    
    @property 
    def health_score(self) -> float:
        """Punteggio salute complessivo (0-1)"""
        if not self.metrics.last_success_time:
            return 0.0
            
        # Fattori: affidabilità, recency, response time
        reliability = self.reliability_score
        
        # Recency: successo nelle ultime 24h = 1.0, più vecchio = meno
        hours_since_success = (datetime.now() - self.metrics.last_success_time).total_seconds() / 3600
        recency = max(0.0, 1.0 - (hours_since_success / 24.0))
        
        # Response time: < 2s = 1.0, > 10s = 0.0
        response_factor = max(0.0, 1.0 - (self.metrics.avg_response_time / 10.0))
        
        return (reliability * 0.5 + recency * 0.3 + response_factor * 0.2)
    
    def can_make_request(self) -> bool:
        """Verifica se può fare una richiesta (rate limiting migliorato)"""
        now = datetime.now()
        
        # Controlla rate limit
        if self.metrics.rate_limit_until and now < self.metrics.rate_limit_until:
            return False
            
        # Controlla delay adattivo
        if (self.metrics.last_request_time and 
            (now - self.metrics.last_request_time).total_seconds() < self.metrics.adaptive_delay):
            return False
            
        return True
    
    def update_adaptive_delay(self, success: bool, response_time: float):
        """Aggiorna delay adattivo basato su successo/fallimento"""
        if success:
            # Successo: riduci delay gradualmente
            if self.metrics.success_count % 5 == 0:  # Ogni 5 successi
                self.metrics.adaptive_delay = max(
                    self.base_rate_limit_delay * 0.5,  # Minimo 50% del base
                    self.metrics.adaptive_delay * 0.9
                )
            # Penalty per response time lento
            if response_time > 5.0:
                self.metrics.adaptive_delay = min(
                    self.base_rate_limit_delay * 3.0,  # Massimo 3x base
                    self.metrics.adaptive_delay * 1.2
                )
        else:
            # Fallimento: aumenta delay
            self.metrics.adaptive_delay = min(
                self.base_rate_limit_delay * 4.0,  # Massimo 4x base
                self.metrics.adaptive_delay * 1.5
            )
    
    def wait_for_rate_limit(self):
        """Aspetta se necessario per rispettare il rate limiting"""
        if not self.can_make_request():
            if self.metrics.rate_limit_until:
                wait_time = (self.metrics.rate_limit_until - datetime.now()).total_seconds()
                if wait_time > 0:
                    time.sleep(min(wait_time, 60))
            else:
                time.sleep(self.metrics.adaptive_delay)
    
    def _make_request_with_retry(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Effettua richiesta HTTP con retry e gestione errori migliorata"""
        for attempt in range(self.max_retries):
            try:
                self.wait_for_rate_limit()
                
                start_time = time.time()
                response = self.session.get(url, timeout=self.timeout, **kwargs)
                response_time = time.time() - start_time
                
                # Aggiorna metriche
                self.metrics.last_request_time = datetime.now()
                
                if response.status_code == 200:
                    self._update_success_metrics(response_time)
                    self.update_adaptive_delay(True, response_time)
                    return response
                elif response.status_code == 429:  # Rate limited
                    retry_after = int(response.headers.get('Retry-After', 60))
                    self.metrics.rate_limit_until = datetime.now() + timedelta(seconds=retry_after)
                    self.logger.warning(f"Rate limited, retry after {retry_after}s")
                elif response.status_code == 404:
                    self.logger.warning(f"HTTP 404 for {url}")
                    break  # Non fare retry per 404
                else:
                    self.logger.warning(f"HTTP {response.status_code} for {url}")
                    
            except requests.exceptions.Timeout:
                self.logger.warning(f"Timeout for {url} (attempt {attempt + 1})")
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                
            if attempt < self.max_retries - 1:
                backoff_time = min(2 ** attempt, 10)  # Max 10s backoff
                time.sleep(backoff_time)
                
        # Tutte le richieste fallite
        self._update_error_metrics()
        self.update_adaptive_delay(False, 0)
        return None
    
    def _update_success_metrics(self, response_time: float):
        """Aggiorna metriche di successo"""
        self.metrics.success_count += 1
        self.metrics.last_success_time = datetime.now()
        
        # Aggiorna tempo medio response
        if self.metrics.avg_response_time == 0:
            self.metrics.avg_response_time = response_time
        else:
            self.metrics.avg_response_time = (
                (self.metrics.avg_response_time * (self.metrics.success_count - 1) + response_time) /
                self.metrics.success_count
            )
    
    def _update_error_metrics(self):
        """Aggiorna metriche di errore"""
        self.metrics.error_count += 1
    
    @abstractmethod
    def search_news(self, query: NewsQuery) -> List[NewsArticle]:
        """Cerca notizie basate sulla query fornita"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Verifica se la fonte è disponibile e configurata correttamente"""
        pass
    
    def to_documents(self, articles: List[NewsArticle]) -> List[Dict[str, Any]]:
        """Converte gli articoli in oggetti Document-like (senza LangChain per testing)"""
        documents = []
        
        for article in articles:
            # Contenuto principale
            content = f"Titolo: {article.title}\n\n{article.content}"
            
            # Metadati
            metadata = {
                'title': article.title,
                'url': article.url,
                'source': article.source or 'unknown',
                'published_date': article.published_date.isoformat() if article.published_date else None,
                'score': article.score,
                'raw_content': article.raw_content
            }
            
            # Aggiungi metadati aggiuntivi se presenti
            if article.metadata:
                metadata.update(article.metadata)
            
            # Documento simulato senza LangChain
            documents.append({
                'page_content': content,
                'metadata': metadata
            })
        
        return documents

def expand_keywords_for_domain(domain: str, base_keywords: List[str]) -> List[str]:
    """Espande keywords per dominio per aumentare recall"""
    expanded = base_keywords.copy() if base_keywords else []
    
    domain_expansions = {
        'calcio': ['Serie A', 'Champions League', 'Europa League', 'nazionale', 'calciomercato', 'squadra'],
        'tecnologia': ['AI', 'intelligenza artificiale', 'smartphone', 'software', 'innovation', 'tech'],
        'finanza': ['borsa', 'mercati', 'economia', 'investimenti', 'trading', 'criptovalute'],
        'salute': ['medicina', 'sanità', 'ricerca medica', 'farmaci', 'prevenzione'],
        'ambiente': ['clima', 'sostenibilità', 'energia rinnovabile', 'inquinamento', 'ecologia']
    }
    
    if domain.lower() in domain_expansions:
        expanded.extend(domain_expansions[domain.lower()])
    
    # Rimuovi duplicati mantenendo ordine
    seen = set()
    unique_expanded = []
    for keyword in expanded:
        if keyword.lower() not in seen:
            seen.add(keyword.lower())
            unique_expanded.append(keyword)
    
    return unique_expanded[:10]  # Max 10 keywords per evitare query troppo lunghe

def test_url_availability(url: str, timeout: int = 5) -> bool:
    """Testa se un URL è raggiungibile"""
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return response.status_code < 400
    except:
        return False