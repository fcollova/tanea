"""
Modulo NewsAPI per news_sources
"""

import os
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

from .news_source_base import NewsSource, NewsQuery, NewsArticle, expand_keywords_for_domain
from .config import get_search_config
from .domain_config import get_domain_config
from .log import get_news_logger

logger = get_news_logger(__name__)

class NewsAPISource(NewsSource):
    """Implementazione per NewsAPI con fonti italiane verificate"""
    
    def __init__(self, config: Dict[str, Any] = None):
        if config is None:
            config = {}
        super().__init__(config)
        
        # Prova prima dalla configurazione passata, poi dal sistema di config, poi dalle variabili d'ambiente
        search_config = get_search_config()
        self.api_key = (
            config.get('newsapi_api_key') or 
            search_config.get('newsapi_api_key') or 
            os.getenv('NEWSAPI_API_KEY')
        )
        self.base_url = "https://newsapi.org/v2"
        
        # Domini italiani verificati (per /v2/everything)
        self.italian_domains = [
            'ansa.it', 'repubblica.it', 'corriere.it', 'ilsole24ore.com',
            'gazzetta.it', 'corrieredellosport.it', 'tuttosport.com'
        ]
        
    @property
    def priority(self) -> int:
        return 2  # Media priorità
        
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def search_news(self, query: NewsQuery) -> List[NewsArticle]:
        if not self.is_available():
            self.logger.warning("NewsAPI key non configurata")
            return []
            
        try:
            # Espandi keywords per il dominio
            expanded_keywords = expand_keywords_for_domain(query.domain, query.keywords)
            
            # Due strategie diverse per evitare errore 400
            articles = []
            
            # Strategia 1: Usa /v2/top-headlines con country=it (senza sources)
            if expanded_keywords:
                articles.extend(self._search_top_headlines(query, expanded_keywords))
            
            # Strategia 2: Usa /v2/everything solo con keywords (senza sources)
            if len(articles) < query.max_results:
                articles.extend(self._search_everything(query, expanded_keywords, len(articles)))
            
            return articles[:query.max_results]
            
        except Exception as e:
            self.logger.error(f"Errore NewsAPI: {e}")
            return []
    
    def _search_top_headlines(self, query: NewsQuery, keywords: List[str]) -> List[NewsArticle]:
        """Cerca using /v2/top-headlines endpoint"""
        try:
            params = {
                'apiKey': self.api_key,
                'country': 'it',
                'pageSize': min(query.max_results, 50),
                'category': self._get_newsapi_category(query.domain)
            }
            
            response = self._make_request_with_retry(
                f"{self.base_url}/top-headlines", 
                params=params
            )
            
            if not response:
                return []
                
            data = response.json()
            articles = data.get('articles', [])
            
            # Filtra per keywords espanse
            if keywords:
                articles = self._filter_by_keywords_newsapi(articles, keywords)
            
            return self._parse_newsapi_articles(articles, query)
            
        except Exception as e:
            self.logger.warning(f"Errore top-headlines: {e}")
            return []
    
    def _search_everything(self, query: NewsQuery, keywords: List[str], current_count: int) -> List[NewsArticle]:
        """Cerca using /v2/everything endpoint (solo keywords)"""
        try:
            remaining = query.max_results - current_count
            if remaining <= 0:
                return []
            
            params = {
                'apiKey': self.api_key,
                'language': 'it',
                'sortBy': 'publishedAt',
                'pageSize': min(remaining, 50),
                'domains': 'ansa.it,repubblica.it,corriere.it,gazzetta.it,corrieredellosport.it'
            }
            
            # Query keywords con priorità a quelle espanse
            if keywords:
                # Usa keywords più specifiche per ridurre rumore
                main_keywords = keywords[:3]  # Prendi solo le prime 3
                params['q'] = ' OR '.join(f'"{kw}"' for kw in main_keywords)
            else:
                # Default per domini attivi
                domain_config = get_domain_config()
                active_domains = domain_config.get_active_domains()
                if 'calcio' in active_domains:
                    params['q'] = 'calcio OR sport'
                else:
                    params['q'] = 'notizie'
            
            # Range temporale
            if query.time_range:
                from_date = self._get_from_date(query.time_range)
                if from_date:
                    params['from'] = from_date.isoformat()
            
            response = self._make_request_with_retry(
                f"{self.base_url}/everything", 
                params=params
            )
            
            if not response:
                return []
                
            data = response.json()
            articles = data.get('articles', [])
            
            return self._parse_newsapi_articles(articles, query)
            
        except Exception as e:
            self.logger.warning(f"Errore everything: {e}")
            return []
    
    def _get_newsapi_category(self, domain: str) -> str:
        """Mappa domini a categorie NewsAPI"""
        domain_lower = domain.lower()
        if any(term in domain_lower for term in ['calcio']):
            return 'sports'
        elif any(term in domain_lower for term in ['finanza']):
            return 'business'
        elif any(term in domain_lower for term in ['tecnologia']):
            return 'technology'
        elif any(term in domain_lower for term in ['salute']):
            return 'health'
        else:
            return 'general'
    
    def _filter_by_keywords_newsapi(self, articles: List[Dict], keywords: List[str]) -> List[Dict]:
        """Filtra articoli NewsAPI per keywords"""
        if not keywords:
            return articles
            
        filtered = []
        keywords_lower = [kw.lower() for kw in keywords]
        
        for article in articles:
            title = article.get('title', '').lower()
            description = article.get('description', '').lower()
            content = article.get('content', '').lower()
            
            text = f"{title} {description} {content}"
            
            if any(keyword in text for keyword in keywords_lower):
                filtered.append(article)
                
        return filtered
    
    def _get_from_date(self, time_range: str) -> Optional[datetime]:
        """Converte time_range in data"""
        now = datetime.now()
        if time_range == '1d':
            return now - timedelta(days=1)
        elif time_range == '1w':
            return now - timedelta(weeks=1) 
        elif time_range == '1m':
            return now - timedelta(days=30)
        return None
    
    def _parse_newsapi_articles(self, articles: List[Dict], query: NewsQuery) -> List[NewsArticle]:
        """Converte articoli NewsAPI in NewsArticle"""
        parsed = []
        
        for article in articles:
            try:
                # Parse date
                pub_date = None
                if article.get('publishedAt'):
                    pub_date = datetime.fromisoformat(
                        article['publishedAt'].replace('Z', '+00:00')
                    )
                
                # Determina fonte
                source_info = article.get('source', {})
                if isinstance(source_info, dict):
                    source_name = source_info.get('name', 'NewsAPI')
                else:
                    source_name = 'NewsAPI'
                
                # Assicurati che source_name non sia vuoto
                if not source_name or source_name.strip() == '':
                    source_name = 'NewsAPI'
                
                news_article = NewsArticle(
                    title=article.get('title', ''),
                    content=article.get('description', '') + '\n\n' + (article.get('content', '') or ''),
                    url=article.get('url', ''),
                    published_date=pub_date,
                    source=source_name,
                    score=1.0,  # NewsAPI non fornisce score
                    metadata={
                        'newsapi_source': article.get('source', {}),
                        'author': article.get('author'),
                        'urlToImage': article.get('urlToImage'),
                        'domain': query.domain,
                        'search_keywords': query.keywords
                    }
                )
                
                parsed.append(news_article)
                
            except Exception as e:
                self.logger.warning(f"Errore parsing articolo NewsAPI: {e}")
                continue
                
        return parsed