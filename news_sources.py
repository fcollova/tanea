import os
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from langchain_community.tools import TavilySearchResults
from langchain.schema import Document

from config import get_search_config

logger = logging.getLogger(__name__)

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

class NewsSource(ABC):
    """Classe base astratta per fonti di notizie"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def search_news(self, query: NewsQuery) -> List[NewsArticle]:
        """
        Cerca notizie basate sulla query fornita
        
        Args:
            query: Configurazione della ricerca
            
        Returns:
            Lista di articoli trovati
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Verifica se la fonte è disponibile e configurata correttamente
        
        Returns:
            True se la fonte è disponibile
        """
        pass
    
    def to_documents(self, articles: List[NewsArticle]) -> List[Document]:
        """
        Converte gli articoli in oggetti Document di LangChain
        
        Args:
            articles: Lista di articoli
            
        Returns:
            Lista di documenti LangChain
        """
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
            
            documents.append(Document(
                page_content=content,
                metadata=metadata
            ))
        
        return documents

class TavilyNewsSource(NewsSource):
    """Implementazione per Tavily Search API"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Inizializza la fonte Tavily
        
        Args:
            config: Configurazione specifica per Tavily (opzionale, usa config globale se None)
        """
        if config is None:
            config = get_search_config()
        
        super().__init__(config)
        
        self.api_key = config.get('tavily_api_key')
        self.max_results = config.get('max_results', 10)
        self.search_depth = config.get('search_depth', 'advanced')
        self.include_answer = config.get('include_answer', True)
        self.include_raw_content = config.get('include_raw_content', True)
        
        self.tavily_search = None
        if self.is_available():
            self._init_tavily()
    
    def _init_tavily(self):
        """Inizializza il client Tavily"""
        try:
            os.environ["TAVILY_API_KEY"] = self.api_key
            self.tavily_search = TavilySearchResults(
                max_results=self.max_results,
                search_depth=self.search_depth,
                include_answer=self.include_answer,
                include_raw_content=self.include_raw_content
            )
            self.logger.info("Client Tavily inizializzato con successo")
        except Exception as e:
            self.logger.error(f"Errore nell'inizializzazione di Tavily: {e}")
            self.tavily_search = None
    
    def is_available(self) -> bool:
        """Verifica se Tavily è disponibile"""
        return bool(self.api_key)
    
    def search_news(self, query: NewsQuery) -> List[NewsArticle]:
        """
        Cerca notizie usando Tavily
        
        Args:
            query: Configurazione della ricerca
            
        Returns:
            Lista di articoli trovati
        """
        if not self.tavily_search:
            if not self.is_available():
                raise ValueError("Tavily API key non configurata")
            self._init_tavily()
        
        try:
            # Costruisci la query di ricerca
            search_query = self._build_search_query(query)
            
            self.logger.info(f"Ricerca Tavily: {search_query}")
            
            # Esegui la ricerca
            results = self.tavily_search.run(search_query)
            
            # Converti i risultati in NewsArticle
            articles = self._parse_tavily_results(results, query)
            
            self.logger.info(f"Trovati {len(articles)} articoli da Tavily")
            return articles
            
        except Exception as e:
            self.logger.error(f"Errore nella ricerca Tavily: {e}")
            return []
    
    def _build_search_query(self, query: NewsQuery) -> str:
        """
        Costruisce la query di ricerca per Tavily
        
        Args:
            query: Configurazione della ricerca
            
        Returns:
            Query di ricerca formattata
        """
        search_parts = []
        
        # Keywords principali
        if query.keywords:
            search_parts.extend(query.keywords)
        
        # Dominio specifico
        if query.domain:
            search_parts.append(query.domain)
        
        # Range temporale
        if query.time_range:
            time_filter = {
                '1d': 'ultime 24 ore',
                '1w': 'ultima settimana', 
                '1m': 'ultimo mese'
            }.get(query.time_range, '')
            if time_filter:
                search_parts.append(time_filter)
        
        return ' '.join(search_parts)
    
    def _parse_tavily_results(self, results: List[Dict], query: NewsQuery) -> List[NewsArticle]:
        """
        Converte i risultati Tavily in NewsArticle
        
        Args:
            results: Risultati grezzi da Tavily
            query: Query originale per contesto
            
        Returns:
            Lista di NewsArticle
        """
        articles = []
        
        for result in results:
            try:
                # Estrai informazioni base
                title = result.get('title', 'Titolo non disponibile')
                content = result.get('content', '')
                url = result.get('url', '')
                score = result.get('score', 0.0)
                raw_content = result.get('raw_content', '')
                
                # Metadati aggiuntivi
                metadata = {
                    'tavily_score': score,
                    'search_query': ' '.join(query.keywords),
                    'domain': query.domain,
                    'language': query.language
                }
                
                article = NewsArticle(
                    title=title,
                    content=content,
                    url=url,
                    score=score,
                    raw_content=raw_content,
                    source='tavily',
                    metadata=metadata
                )
                
                articles.append(article)
                
            except Exception as e:
                self.logger.warning(f"Errore nel parsing del risultato Tavily: {e}")
                continue
        
        return articles

class NewsSourceManager:
    """Gestore per multiple fonti di notizie"""
    
    def __init__(self):
        self.sources: Dict[str, NewsSource] = {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def add_source(self, name: str, source: NewsSource):
        """
        Aggiunge una fonte di notizie
        
        Args:
            name: Nome identificativo della fonte
            source: Istanza della fonte
        """
        self.sources[name] = source
        self.logger.info(f"Aggiunta fonte: {name}")
    
    def remove_source(self, name: str):
        """
        Rimuove una fonte di notizie
        
        Args:
            name: Nome della fonte da rimuovere
        """
        if name in self.sources:
            del self.sources[name]
            self.logger.info(f"Rimossa fonte: {name}")
    
    def get_available_sources(self) -> List[str]:
        """
        Ottiene l'elenco delle fonti disponibili
        
        Returns:
            Lista dei nomi delle fonti disponibili
        """
        return [name for name, source in self.sources.items() if source.is_available()]
    
    def search_all_sources(self, query: NewsQuery) -> Dict[str, List[NewsArticle]]:
        """
        Cerca notizie su tutte le fonti disponibili
        
        Args:
            query: Configurazione della ricerca
            
        Returns:
            Dizionario con risultati per ogni fonte
        """
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
    
    def search_best_source(self, query: NewsQuery) -> List[NewsArticle]:
        """
        Cerca notizie sulla migliore fonte disponibile
        
        Args:
            query: Configurazione della ricerca
            
        Returns:
            Lista di articoli dalla migliore fonte
        """
        available_sources = self.get_available_sources()
        
        if not available_sources:
            self.logger.warning("Nessuna fonte disponibile")
            return []
        
        # Per ora usa la prima fonte disponibile
        # In futuro si può implementare logica di priorità
        best_source_name = available_sources[0]
        best_source = self.sources[best_source_name]
        
        try:
            return best_source.search_news(query)
        except Exception as e:
            self.logger.error(f"Errore nella ricerca su {best_source_name}: {e}")
            return []

# Factory function per creare il manager con fonti predefinite
def create_default_news_manager() -> NewsSourceManager:
    """
    Crea un NewsSourceManager con le fonti predefinite
    
    Returns:
        Manager configurato con fonti disponibili
    """
    manager = NewsSourceManager()
    
    # Aggiungi Tavily se disponibile
    try:
        tavily_source = TavilyNewsSource()
        if tavily_source.is_available():
            manager.add_source('tavily', tavily_source)
    except Exception as e:
        logger.warning(f"Impossibile inizializzare Tavily: {e}")
    
    # Qui si possono aggiungere altre fonti future
    # manager.add_source('rss', RSSNewsSource())
    # manager.add_source('api', APINewsSource())
    
    return manager