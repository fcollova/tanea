"""
Modulo Web Scraping con Trafilatura per news_sources
Versione avanzata che usa trafilatura per estrazione intelligente
"""

import os
import time
import yaml
import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin

try:
    import trafilatura
    from trafilatura.settings import use_config
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False

from .news_source_base import NewsSource, NewsQuery, NewsArticle, expand_keywords_for_domain, test_url_availability
from .domain_config import get_domain_config
from .log import get_news_logger

logger = get_news_logger(__name__)

class TrafilaturaWebScrapingSource(NewsSource):
    """Implementazione Web Scraping con Trafilatura - Molto più robusta"""
    
    def __init__(self, config: Dict[str, Any] = None):
        if config is None:
            config = {}
        super().__init__(config)
        
        if not TRAFILATURA_AVAILABLE:
            raise ImportError("Trafilatura non disponibile. Installa con: pip install trafilatura")
        
        # Carica configurazione scraping da YAML
        self.scraping_config_path = config.get('scraping_config_path', 
                                             os.path.join(os.path.dirname(__file__), '..', 'config', 'web_scraping.yaml'))
        self.scraping_config = self._load_scraping_config()
        
        # Configurazione trafilatura
        self._setup_trafilatura_config()
        
        # Aggiorna configurazioni da YAML
        if self.scraping_config and 'general' in self.scraping_config:
            yaml_config = self.scraping_config['general']
            self.base_rate_limit_delay = max(
                yaml_config.get('rate_limit_delay', self.base_rate_limit_delay),
                1.0  # Minimo 1 secondo
            )
            self.timeout = min(yaml_config.get('timeout', self.timeout), 15)
            self.max_retries = yaml_config.get('max_retries', self.max_retries)
            self.max_articles_per_site = yaml_config.get('max_articles_per_site', 15)
        
        # Statistiche specifiche trafilatura
        self.extraction_stats = {
            'successful_extractions': 0,
            'failed_extractions': 0,
            'metadata_found': 0,
            'avg_content_length': 0
        }
    
    @property
    def priority(self) -> int:
        return 1  # Alta priorità - trafilatura è molto efficace
    
    def _setup_trafilatura_config(self):
        """Configura trafilatura per performance ottimale"""
        try:
            # Configurazione personalizzata per news
            trafilatura_config = trafilatura.settings.use_config()
            
            # Ottimizzazioni per articoli di notizie
            trafilatura_config.set('DEFAULT', 'EXTRACTION_TIMEOUT', '30')
            trafilatura_config.set('DEFAULT', 'MIN_EXTRACTED_SIZE', '200')  # Minimo 200 caratteri
            trafilatura_config.set('DEFAULT', 'MIN_OUTPUT_SIZE', '100')
            trafilatura_config.set('DEFAULT', 'MAX_OUTPUT_SIZE', '20000')  # Max 20k caratteri
            
            # Focus su contenuto principale
            trafilatura_config.set('DEFAULT', 'FAVOR_PRECISION', 'True')  # Preferisci qualità a quantità
            trafilatura_config.set('DEFAULT', 'INCLUDE_COMMENTS', 'False')  # Escludi commenti
            trafilatura_config.set('DEFAULT', 'INCLUDE_TABLES', 'True')  # Includi tabelle (utili per sport)
            
            self.trafilatura_config = trafilatura_config
            self.logger.info("Configurazione Trafilatura ottimizzata per news")
            
        except Exception as e:
            self.logger.warning(f"Impossibile configurare trafilatura: {e}")
            self.trafilatura_config = None
    
    def _load_scraping_config(self) -> Optional[Dict[str, Any]]:
        """Carica configurazione per siti e URL di partenza"""
        try:
            if os.path.exists(self.scraping_config_path):
                with open(self.scraping_config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    self.logger.info(f"Configurazione trafilatura caricata da {self.scraping_config_path}")
                    return config
            else:
                self.logger.warning(f"File configurazione non trovato: {self.scraping_config_path}")
                return self._get_default_sites()
        except Exception as e:
            self.logger.error(f"Errore caricamento configurazione: {e}")
            return self._get_default_sites()
    
    def _get_default_sites(self) -> Dict[str, Any]:
        """Configurazione siti di default ottimizzata per trafilatura"""
        return {
            'sites': {
                'ansa': {
                    'name': 'ANSA',
                    'base_url': 'https://www.ansa.it',
                    'categories': {
                        'calcio': 'https://www.ansa.it/sito/notizie/sport/',
                        'general': 'https://www.ansa.it/sito/notizie/topnews/'
                    }
                },
                'gazzetta': {
                    'name': 'Gazzetta dello Sport', 
                    'base_url': 'https://www.gazzetta.it',
                    'categories': {
                        'calcio': 'https://www.gazzetta.it/Calcio/',
                        'sport': 'https://www.gazzetta.it/'
                    }
                },
                'corriere': {
                    'name': 'Corriere della Sera',
                    'base_url': 'https://www.corriere.it',
                    'categories': {
                        'general': 'https://www.corriere.it/',
                        'sport': 'https://www.corriere.it/sport/'
                    }
                }
            },
            'domain_mapping': {
                'calcio': ['gazzetta', 'ansa'],
                'general': ['ansa', 'corriere']
            }
        }
    
    def is_available(self) -> bool:
        """Trafilatura disponibile se installata"""
        return TRAFILATURA_AVAILABLE
    
    def search_news(self, query: NewsQuery) -> List[NewsArticle]:
        """Cerca notizie usando trafilatura - molto più semplice e robusto"""
        if not self.is_available():
            self.logger.warning("Trafilatura non disponibile")
            return []
            
        try:
            # Espandi keywords per il dominio
            expanded_keywords = expand_keywords_for_domain(query.domain, query.keywords)
            
            # Seleziona siti appropriati per il dominio
            sites = self._get_domain_sites(query.domain)
            
            if not sites:
                self.logger.warning(f"Nessun sito configurato per dominio: {query.domain}")
                return []
            
            all_articles = []
            
            for site_config in sites:
                try:
                    site_name = site_config['name']
                    self.logger.info(f"Scraping trafilatura da {site_name}...")
                    
                    articles = self._scrape_site_trafilatura(site_config, query, expanded_keywords)
                    all_articles.extend(articles)
                    
                    self.logger.info(f"Sito {site_name}: {len(articles)} articoli estratti")
                    
                    if len(all_articles) >= query.max_results:
                        break
                        
                except Exception as e:
                    self.logger.error(f"Errore scraping trafilatura {site_config.get('name', 'Unknown')}: {e}")
                    continue
            
            # Filtra per keywords e qualità
            filtered_articles = self._filter_and_rank_articles(all_articles, expanded_keywords)
            
            # Ordina per score e data
            filtered_articles.sort(
                key=lambda x: (
                    x.score or 0.0,
                    x.published_date or datetime.min
                ),
                reverse=True
            )
            
            self.logger.info(f"Totale articoli estratti: {len(filtered_articles)}")
            return filtered_articles[:query.max_results]
            
        except Exception as e:
            self.logger.error(f"Errore web scraping trafilatura: {e}")
            return []
    
    def _scrape_site_trafilatura(self, site_config: Dict[str, Any], query: NewsQuery, 
                                keywords: List[str]) -> List[NewsArticle]:
        """Scraping di un sito usando trafilatura"""
        articles = []
        site_name = site_config.get('name', 'Unknown')
        
        try:
            # Trova categoria appropriata
            categories = site_config.get('categories', {})
            category_url = self._select_category_url(categories, query.domain)
            
            if not category_url:
                self.logger.warning(f"Nessuna categoria trovata per {site_name}")
                return []
            
            self.logger.info(f"Categoria URL: {category_url}")
            
            # Rate limiting
            time.sleep(self.metrics.adaptive_delay)
            
            # Scarica pagina categoria
            response = self._make_request_with_retry(category_url)
            if not response:
                return []
            
            # Estrai link articoli usando trafilatura (molto più robusta)
            article_links = self._extract_links_trafilatura(response.text, site_config)
            
            if not article_links:
                self.logger.warning(f"Nessun link trovato per {site_name}")
                return []
            
            self.logger.info(f"Trovati {len(article_links)} link da {site_name}")
            
            # Limita numero articoli
            max_articles = min(len(article_links), self.max_articles_per_site, query.max_results)
            
            # Scraping articoli individuali con trafilatura
            for i, link in enumerate(article_links[:max_articles]):
                try:
                    article = self._extract_article_trafilatura(link, site_config, keywords)
                    if article:
                        articles.append(article)
                    
                    # Rate limiting progressivo
                    if i < max_articles - 1:
                        progressive_delay = self.metrics.adaptive_delay * (1.0 + (i * 0.05))
                        time.sleep(min(progressive_delay, self.metrics.adaptive_delay * 1.5))
                        
                except Exception as e:
                    self.logger.warning(f"Errore estrazione articolo {link}: {e}")
                    continue
            
            return articles
            
        except Exception as e:
            self.logger.error(f"Errore scraping sito {site_name}: {e}")
            return []
    
    def _extract_links_trafilatura(self, html: str, site_config: Dict[str, Any]) -> List[str]:
        """Estrae link usando trafilatura + pattern recognition"""
        try:
            # Usa trafilatura per trovare tutti i link
            links = trafilatura.extract_links(html)
            
            if not links:
                # Fallback con pattern generici per articoli news
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                
                # Pattern generici per articoli di notizie
                selectors = [
                    'a[href*="/article"]', 'a[href*="/news"]', 'a[href*="/articolo"]',
                    'a[href*="/sport"]', 'a[href*="/calcio"]', 'a[href*="/notizie"]',
                    '.article-title a', '.news-title a', '.headline a',
                    'h1 a', 'h2 a', 'h3 a'
                ]
                
                link_elements = []
                for selector in selectors:
                    elements = soup.select(selector)
                    if elements:
                        link_elements.extend(elements)
                        break
                
                base_url = site_config.get('base_url', '')
                links = []
                for elem in link_elements:
                    href = elem.get('href')
                    if href:
                        if href.startswith('/'):
                            href = urljoin(base_url, href)
                        elif not href.startswith('http'):
                            href = urljoin(base_url, href)
                        if href.startswith('http'):
                            links.append(href)
            
            # Filtra link articoli (rimuovi nav, footer, etc.)
            article_links = []
            for link in links:
                if self._is_article_link(link):
                    article_links.append(link)
            
            # Rimuovi duplicati
            seen = set()
            unique_links = []
            for link in article_links:
                if link not in seen:
                    seen.add(link)
                    unique_links.append(link)
            
            return unique_links[:20]  # Max 20 link per sito
            
        except Exception as e:
            self.logger.error(f"Errore estrazione link trafilatura: {e}")
            return []
    
    def _is_article_link(self, url: str) -> bool:
        """Determina se un URL è probabilmente un articolo"""
        url_lower = url.lower()
        
        # Pattern positivi (indicano articoli)
        article_patterns = [
            '/articolo', '/article', '/news', '/notizie', '/sport', '/calcio',
            '/cronaca', '/politica', '/economia', '/tecnologia'
        ]
        
        # Pattern negativi (navigazione, non articoli)
        nav_patterns = [
            '/tag/', '/category/', '/author/', '/search/', '/page/',
            '?', '#', 'javascript:', 'mailto:', '/rss', '/feed',
            '/home', '/contact', '/about', '/privacy', '/cookie'
        ]
        
        # Check pattern positivi
        has_article_pattern = any(pattern in url_lower for pattern in article_patterns)
        
        # Check pattern negativi
        has_nav_pattern = any(pattern in url_lower for pattern in nav_patterns)
        
        return has_article_pattern and not has_nav_pattern
    
    def _extract_article_trafilatura(self, url: str, site_config: Dict[str, Any], 
                                   keywords: List[str]) -> Optional[NewsArticle]:
        """Estrae un singolo articolo usando trafilatura - MOLTO PIÙ SEMPLICE"""
        try:
            # Scarica pagina articolo
            response = self._make_request_with_retry(url)
            if not response:
                return None
            
            # MAGIA TRAFILATURA: Estrazione intelligente in 1 riga!
            extracted_data = trafilatura.extract(
                response.text,
                output_format='json',
                config=self.trafilatura_config,
                include_comments=False,
                include_tables=True,
                include_formatting=True
            )
            
            if not extracted_data:
                self.extraction_stats['failed_extractions'] += 1
                return None
            
            # Parse JSON result
            data = json.loads(extracted_data) if isinstance(extracted_data, str) else extracted_data
            
            title = data.get('title', '')
            content = data.get('text', '')
            
            if not title or not content or len(content) < 100:
                self.extraction_stats['failed_extractions'] += 1
                return None
            
            # Estrai metadati automaticamente
            metadata_dict = {
                'author': data.get('author', ''),
                'date': data.get('date', ''),
                'description': data.get('description', ''),
                'site_name': data.get('sitename', site_config.get('name', '')),
                'url': url,
                'extraction_method': 'trafilatura'
            }
            
            # Parse data pubblicazione
            pub_date = self._parse_date_trafilatura(data.get('date'))
            
            # Filtra per keywords se specificate
            if keywords:
                text_to_check = f"{title} {content}".lower()
                if not any(keyword.lower() in text_to_check for keyword in keywords):
                    return None
            
            # Calcola score basato su qualità contenuto
            score = self._calculate_content_score(title, content, data)
            
            article = NewsArticle(
                title=title.strip(),
                content=content.strip(),
                url=url,
                published_date=pub_date,
                source=site_config.get('name', 'Trafilatura Scraping'),
                score=score,
                raw_content=data.get('raw_text', ''),
                metadata=metadata_dict
            )
            
            # Aggiorna statistiche
            self.extraction_stats['successful_extractions'] += 1
            if data.get('author') or data.get('date'):
                self.extraction_stats['metadata_found'] += 1
            
            # Aggiorna lunghezza media contenuto
            current_avg = self.extraction_stats['avg_content_length']
            total_extractions = self.extraction_stats['successful_extractions']
            self.extraction_stats['avg_content_length'] = (
                (current_avg * (total_extractions - 1) + len(content)) / total_extractions
            )
            
            return article
            
        except Exception as e:
            self.logger.warning(f"Errore estrazione trafilatura {url}: {e}")
            self.extraction_stats['failed_extractions'] += 1
            return None
    
    def _parse_date_trafilatura(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse data estratta da trafilatura"""
        if not date_str:
            return None
        
        try:
            # Trafilatura normalizza già le date in formato ISO
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                # Formato data semplice
                return datetime.fromisoformat(date_str)
        except:
            # Fallback con parser generico
            try:
                from dateutil import parser as date_parser
                return date_parser.parse(date_str)
            except:
                return None
    
    def _calculate_content_score(self, title: str, content: str, data: Dict) -> float:
        """Calcola score qualità basato su indicatori trafilatura"""
        score = 0.7  # Base score
        
        # Bonus per metadata completi
        if data.get('author'):
            score += 0.1
        if data.get('date'):
            score += 0.1
        if data.get('description'):
            score += 0.05
        
        # Bonus per lunghezza contenuto appropriata
        content_length = len(content)
        if 500 <= content_length <= 5000:  # Lunghezza ideale per notizie
            score += 0.1
        elif content_length > 200:  # Almeno qualche contenuto
            score += 0.05
        
        # Bonus per titolo informativo
        if len(title) > 30:
            score += 0.05
        
        return min(1.0, score)
    
    def _select_category_url(self, categories: Dict[str, str], domain: str) -> Optional[str]:
        """Seleziona URL categoria appropriato per il dominio"""
        domain_lower = domain.lower()
        
        # Mapping domini → categorie
        if any(term in domain_lower for term in ['calcio']):
            for cat in ['calcio', 'sport']:
                if cat in categories:
                    return categories[cat]
        elif any(term in domain_lower for term in ['tecnologia']):
            if 'tecnologia' in categories:
                return categories['tecnologia']
        elif any(term in domain_lower for term in ['finanza']):
            for cat in ['finanza', 'economia']:
                if cat in categories:
                    return categories[cat]
        
        # Fallback a general o prima categoria
        if 'general' in categories:
            return categories['general']
        elif categories:
            return list(categories.values())[0]
        
        return None
    
    def _get_domain_sites(self, domain: str) -> List[Dict[str, Any]]:
        """Seleziona siti appropriati per il dominio"""
        if not self.scraping_config:
            return []
            
        domain_lower = domain.lower()
        domain_mapping = self.scraping_config.get('domain_mapping', {})
        
        # Trova siti preferiti per il dominio
        preferred_sites = domain_mapping.get(domain_lower, [])
        
        # Fallback se nessun mapping trovato
        if not preferred_sites:
            if any(term in domain_lower for term in ['calcio']):
                preferred_sites = ['gazzetta', 'ansa']
            else:
                preferred_sites = ['ansa', 'corriere']
        
        # Costruisci configurazioni siti
        sites_config = self.scraping_config.get('sites', {})
        selected_sites = []
        
        for site_name in preferred_sites:
            if site_name in sites_config:
                site_config = sites_config[site_name].copy()
                site_config['site_key'] = site_name
                selected_sites.append(site_config)
        
        return selected_sites[:3]  # Max 3 siti per performance
    
    def _filter_and_rank_articles(self, articles: List[NewsArticle], keywords: List[str]) -> List[NewsArticle]:
        """Filtra e rank articoli per qualità e rilevanza"""
        if not articles:
            return []
        
        filtered = []
        
        for article in articles:
            try:
                # Filtri qualità base
                if len(article.content) < 100:  # Troppo corto
                    continue
                    
                if len(article.content) > 20000:  # Troppo lungo (probabilmente non è un articolo)
                    continue
                
                # Boost score per keywords match
                if keywords:
                    text_to_check = f"{article.title} {article.content}".lower()
                    keyword_matches = sum(1 for kw in keywords if kw.lower() in text_to_check)
                    if keyword_matches > 0:
                        # Bonus score basato su numero keyword trovate
                        keyword_bonus = min(0.3, keyword_matches * 0.1)
                        article.score = min(1.0, (article.score or 0.7) + keyword_bonus)
                
                filtered.append(article)
                
            except Exception as e:
                self.logger.warning(f"Errore filtraggio articolo: {e}")
                continue
        
        return filtered
    
    def get_trafilatura_stats(self) -> Dict[str, Any]:
        """Statistiche specifiche trafilatura"""
        total_attempts = self.extraction_stats['successful_extractions'] + self.extraction_stats['failed_extractions']
        
        return {
            'total_extraction_attempts': total_attempts,
            'successful_extractions': self.extraction_stats['successful_extractions'],
            'failed_extractions': self.extraction_stats['failed_extractions'],
            'success_rate': self.extraction_stats['successful_extractions'] / total_attempts if total_attempts > 0 else 0,
            'metadata_found_rate': self.extraction_stats['metadata_found'] / self.extraction_stats['successful_extractions'] if self.extraction_stats['successful_extractions'] > 0 else 0,
            'avg_content_length': int(self.extraction_stats['avg_content_length']),
            'trafilatura_version': trafilatura.__version__ if TRAFILATURA_AVAILABLE else 'N/A'
        }