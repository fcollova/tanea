"""
Modulo RSS Feed per news_sources
"""

import os
import yaml
import feedparser
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from .news_source_base import NewsSource, NewsQuery, NewsArticle, expand_keywords_for_domain
from .domain_config import get_domain_config
from .log import get_news_logger

logger = get_news_logger(__name__)

class RSSFeedSource(NewsSource):
    """Implementazione per feed RSS italiani configurabili via YAML"""
    
    def __init__(self, config: Dict[str, Any] = None):
        if config is None:
            config = {}
        super().__init__(config)
        
        # Carica configurazione RSS da YAML
        self.rss_config_path = config.get('rss_config_path', 
                                        os.path.join(os.path.dirname(__file__), '..', 'config', 'rss_feeds.yaml'))
        self.rss_config = self._load_rss_config()
        
        # Aggiorna configurazioni da YAML
        if self.rss_config and 'general' in self.rss_config:
            yaml_config = self.rss_config['general']
            self.base_rate_limit_delay = yaml_config.get('rate_limit_delay', self.base_rate_limit_delay)
            self.timeout = yaml_config.get('timeout', self.timeout)
            self.max_retries = yaml_config.get('max_retries', self.max_retries)
    
    def _load_rss_config(self) -> Optional[Dict[str, Any]]:
        """Carica configurazione RSS da file YAML"""
        try:
            if os.path.exists(self.rss_config_path):
                with open(self.rss_config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    self.logger.info(f"Configurazione RSS caricata da {self.rss_config_path}")
                    return config
            else:
                self.logger.warning(f"File configurazione RSS non trovato: {self.rss_config_path}")
                return self._get_fallback_feeds()
        except Exception as e:
            self.logger.error(f"Errore caricamento configurazione RSS: {e}")
            return self._get_fallback_feeds()
    
    def _get_fallback_feeds(self) -> Dict[str, Any]:
        """Feed di fallback se YAML non disponibile"""
        domain_config = get_domain_config()
        all_domains = domain_config.get_all_domains()
        
        feeds = {
            'general': [
                {'url': 'https://www.ansa.it/sito/notizie/topnews/topnews_rss.xml', 'source': 'ANSA', 'priority': 1},
                {'url': 'https://www.corriere.it/rss/homepage.xml', 'source': 'Corriere', 'priority': 1}
            ]
        }
        
        # Aggiungi feeds specifici solo per domini definiti
        if 'calcio' in all_domains:
            feeds['calcio'] = [
                {'url': 'https://www.gazzetta.it/rss/calcio.xml', 'source': 'Gazzetta', 'priority': 1},
                {'url': 'https://www.corrieredellosport.it/rss/calcio.xml', 'source': 'CdS', 'priority': 1}
            ]
            feeds['sport'] = [
                {'url': 'https://www.ansa.it/sito/notizie/sport/sport_rss.xml', 'source': 'ANSA Sport', 'priority': 1},
                {'url': 'https://www.gazzetta.it/rss/home.xml', 'source': 'Gazzetta', 'priority': 1}
            ]
        
        if 'tecnologia' in all_domains:
            feeds['tecnologia'] = [
                {'url': 'https://www.ansa.it/sito/notizie/tecnologie/tecnologie_rss.xml', 'source': 'ANSA', 'priority': 1}
            ]
        
        if 'finanza' in all_domains:
            feeds['economia'] = [
                {'url': 'https://www.ilsole24ore.com/rss/economia.xml', 'source': 'Il Sole 24 Ore', 'priority': 1}
            ]
        
        if 'salute' in all_domains:
            feeds['salute'] = [
                {'url': 'https://www.ansa.it/canale_saluteebenessere/notizie/rss.xml', 'source': 'ANSA', 'priority': 1}
            ]
        
        if 'ambiente' in all_domains:
            feeds['ambiente'] = [
                {'url': 'https://www.ansa.it/canale_ambiente/notizie/rss.xml', 'source': 'ANSA', 'priority': 1}
            ]
        
        # Mapping dinamico basato su domini definiti
        domain_mapping = {}
        for domain in all_domains:
            if domain == 'calcio':
                domain_mapping[domain] = ['calcio', 'sport']
            elif domain == 'finanza':
                domain_mapping[domain] = ['economia']
            else:
                domain_mapping[domain] = [domain] if domain in feeds else ['general']
        
        return {
            'feeds': feeds,
            'domain_mapping': domain_mapping
        }
        
    @property
    def priority(self) -> int:
        return 1  # Alta priorità - sempre disponibile
        
    def is_available(self) -> bool:
        return True  # RSS sempre disponibile
    
    def search_news(self, query: NewsQuery) -> List[NewsArticle]:
        try:
            # Espandi keywords per il dominio
            expanded_keywords = expand_keywords_for_domain(query.domain, query.keywords)
            
            # Seleziona feed appropriati dalla configurazione YAML
            feed_configs = self._get_domain_feeds(query.domain)
            
            if not feed_configs:
                self.logger.warning(f"Nessun feed configurato per dominio: {query.domain}")
                return []
            
            all_articles = []
            max_feeds = min(3, len(feed_configs))  # Limita a 3 feed per performance
            
            for feed_config in feed_configs[:max_feeds]:
                feed_url = feed_config.get('url')
                feed_source = feed_config.get('source', 'RSS')
                
                if not feed_url:
                    continue
                    
                articles = self._parse_rss_feed(feed_url, query, feed_source)
                all_articles.extend(articles)
                
                self.logger.debug(f"Feed {feed_source}: {len(articles)} articoli")
                
                if len(all_articles) >= query.max_results * 1.5:  # Extra per deduplica
                    break
            
            # Filtra per keywords espanse
            if expanded_keywords:
                all_articles = self._filter_by_keywords(all_articles, expanded_keywords)
            
            # Applica filtri da configurazione
            all_articles = self._apply_content_filters(all_articles)
            
            # Ordina per data (più recenti prima)
            all_articles.sort(
                key=lambda x: x.published_date or datetime.min, 
                reverse=True
            )
            
            return all_articles[:query.max_results]
            
        except Exception as e:
            self.logger.error(f"Errore RSS: {e}")
            return []
    
    def _get_domain_feeds(self, domain: str) -> List[Dict[str, Any]]:
        """Seleziona feed appropriati per il dominio dalla configurazione YAML"""
        if not self.rss_config or 'feeds' not in self.rss_config:
            return []
            
        domain_lower = domain.lower()
        
        # Usa mapping domini da YAML se disponibile
        domain_mapping = self.rss_config.get('domain_mapping', {})
        
        # Trova categorie appropriate per il dominio
        categories = []
        for domain_key, mapped_categories in domain_mapping.items():
            if domain_key in domain_lower:
                categories.extend(mapped_categories)
                break
        
        # Fallback se nessun mapping trovato
        if not categories:
            if any(term in domain_lower for term in ['calcio']):
                categories = ['calcio', 'sport']
            elif any(term in domain_lower for term in ['tecnologia']):
                categories = ['tecnologia']
            elif any(term in domain_lower for term in ['finanza']):
                categories = ['economia', 'finanza']
            elif any(term in domain_lower for term in ['salute']):
                categories = ['salute', 'general']
            elif any(term in domain_lower for term in ['ambiente']):
                categories = ['ambiente', 'general']
            else:
                categories = ['general']
        
        # Raccogli feed dalle categorie
        feeds = []
        feeds_config = self.rss_config.get('feeds', {})
        
        for category in categories:
            if category in feeds_config:
                category_feeds = feeds_config[category]
                # Ordina per priorità
                sorted_feeds = sorted(category_feeds, key=lambda x: x.get('priority', 999))
                feeds.extend(sorted_feeds)
        
        return feeds
    
    def _parse_rss_feed(self, feed_url: str, query: NewsQuery, feed_source: str = None) -> List[NewsArticle]:
        """Parsing di un singolo feed RSS"""
        try:
            response = self._make_request_with_retry(feed_url)
            if not response:
                return []
                
            feed = feedparser.parse(response.content)
            articles = []
            
            # Calcola data limite
            date_limit = None
            if query.time_range:
                if query.time_range == '1d':
                    date_limit = datetime.now() - timedelta(days=1)
                elif query.time_range == '1w':
                    date_limit = datetime.now() - timedelta(weeks=1)
                elif query.time_range == '1m':
                    date_limit = datetime.now() - timedelta(days=30)
            
            for entry in feed.entries:
                try:
                    # Parse date
                    pub_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        pub_date = datetime(*entry.updated_parsed[:6])
                    
                    # Filtra per data se specificato
                    if date_limit and pub_date and pub_date < date_limit:
                        continue
                    
                    # Determina fonte dal feed o usa quella specificata
                    source_name = feed_source or getattr(feed.feed, 'title', None) or urlparse(feed_url).netloc or 'RSS Feed'
                    
                    # Assicurati che source_name non sia vuoto
                    if not source_name or (isinstance(source_name, str) and source_name.strip() == ''):
                        source_name = 'RSS Feed'
                    
                    # Contenuto
                    content = ''
                    if hasattr(entry, 'summary'):
                        content = entry.summary
                    elif hasattr(entry, 'description'):
                        content = entry.description
                    
                    # Rimuovi HTML tags
                    if content:
                        content = BeautifulSoup(content, 'html.parser').get_text()
                    
                    article = NewsArticle(
                        title=getattr(entry, 'title', ''),
                        content=content,
                        url=getattr(entry, 'link', ''),
                        published_date=pub_date,
                        source=source_name,
                        score=0.9,  # RSS ha alta affidabilità
                        metadata={
                            'feed_url': feed_url,
                            'entry_id': getattr(entry, 'id', ''),
                            'domain': query.domain,
                            'search_keywords': query.keywords
                        }
                    )
                    
                    articles.append(article)
                    
                except Exception as e:
                    self.logger.warning(f"Errore parsing entry RSS: {e}")
                    continue
            
            return articles
            
        except Exception as e:
            self.logger.error(f"Errore parsing feed {feed_url}: {e}")
            return []
    
    def _filter_by_keywords(self, articles: List[NewsArticle], keywords: List[str]) -> List[NewsArticle]:
        """Filtra articoli per keywords"""
        if not keywords:
            return articles
            
        filtered = []
        keywords_lower = [kw.lower() for kw in keywords]
        
        for article in articles:
            text = f"{article.title} {article.content}".lower()
            if any(keyword in text for keyword in keywords_lower):
                filtered.append(article)
                
        return filtered
    
    def _apply_content_filters(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Applica filtri di contenuto dalla configurazione YAML"""
        if not self.rss_config or 'content_filters' not in self.rss_config:
            return articles
            
        filters = self.rss_config['content_filters']
        filtered = []
        
        for article in articles:
            try:
                # Filtra titoli da saltare
                skip_titles = filters.get('skip_titles', [])
                if any(skip_title.lower() in article.title.lower() for skip_title in skip_titles):
                    continue
                
                # Filtra per lunghezza minima
                min_length = filters.get('min_content_length', 0)
                if len(article.content) < min_length:
                    continue
                
                # Pulisci contenuto dai pattern da rimuovere
                cleaned_content = article.content
                remove_patterns = filters.get('remove_patterns', [])
                for pattern in remove_patterns:
                    cleaned_content = cleaned_content.replace(pattern, '')
                
                # Crea nuovo articolo con contenuto pulito
                cleaned_article = NewsArticle(
                    title=article.title,
                    content=cleaned_content.strip(),
                    url=article.url,
                    published_date=article.published_date,
                    source=article.source,
                    score=article.score,
                    raw_content=article.raw_content,
                    metadata=article.metadata
                )
                
                filtered.append(cleaned_article)
                
            except Exception as e:
                self.logger.warning(f"Errore applicazione filtri: {e}")
                filtered.append(article)  # Mantieni articolo originale se filtro fallisce
                
        return filtered