"""
Modulo Tavily per news_sources
"""

import os
from typing import List, Dict, Optional, Any

# from langchain_community.tools import TavilySearchResults  # Commentato per testing

from .news_source_base import NewsSource, NewsQuery, NewsArticle, expand_keywords_for_domain
from .config import get_search_config
from .domain_config import get_domain_config
from .log import get_news_logger

logger = get_news_logger(__name__)

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
    
    @property
    def priority(self) -> int:
        return 3  # Bassa priorità - fallback
    
    def _init_tavily(self):
        """Inizializza il client Tavily (simulato per testing)"""
        try:
            os.environ["TAVILY_API_KEY"] = self.api_key
            # Simulazione per testing senza LangChain
            self.tavily_search = {"mock": True}
            self.logger.info("Client Tavily inizializzato con successo (modalità test)")
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
            # Espandi keywords per il dominio
            expanded_keywords = expand_keywords_for_domain(query.domain, query.keywords)
            
            # Costruisci la query di ricerca
            search_query = self._build_search_query(query, expanded_keywords)
            
            self.logger.info(f"Ricerca Tavily: {search_query}")
            
            # Esegui la ricerca (simulata per testing)
            results = [
                {
                    'title': f'Articolo test Tavily per {search_query}',
                    'content': f'Contenuto simulato per query: {search_query}',
                    'url': 'https://example.com/test',
                    'score': 0.9
                }
            ]
            
            # Converti i risultati in NewsArticle
            articles = self._parse_tavily_results(results, query)
            
            self.logger.info(f"Trovati {len(articles)} articoli da Tavily")
            return articles
            
        except Exception as e:
            self.logger.error(f"Errore nella ricerca Tavily: {e}")
            return []
    
    def _build_search_query(self, query: NewsQuery, expanded_keywords: List[str]) -> str:
        """
        Costruisce la query di ricerca per Tavily
        
        Args:
            query: Configurazione della ricerca
            expanded_keywords: Keywords espanse per il dominio
            
        Returns:
            Query di ricerca formattata
        """
        search_parts = []
        
        # Usa keywords espanse come priorità
        if expanded_keywords:
            # Usa le prime 4 keywords più rilevanti per evitare query troppo lunghe
            search_parts.extend(expanded_keywords[:4])
        elif query.keywords:
            search_parts.extend(query.keywords[:4])
        
        # Aggiungi specificità dominio se non già presente
        domain_config = get_domain_config()
        if query.domain and domain_config.validate_domain(query.domain):
            domain_keywords = domain_config.get_domain_keywords(query.domain)
            if domain_keywords:
                for kw in domain_keywords[:2]:  # Solo prime 2
                    if kw not in search_parts:
                        search_parts.append(kw)
        
        # Range temporale
        if query.time_range:
            time_filter = {
                '1d': 'ultime 24 ore',
                '1w': 'ultima settimana', 
                '1m': 'ultimo mese'
            }.get(query.time_range, '')
            if time_filter:
                search_parts.append(time_filter)
        
        # Aggiungi contesto italiano
        search_parts.append('Italia')
        
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
                    'search_query': ' '.join(query.keywords) if query.keywords else '',
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