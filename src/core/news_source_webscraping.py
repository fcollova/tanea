"""
Modulo Web Scraping migliorato per news_sources
Implementa scraping robusto con fallback selectors e validazione URL
"""

import os
import time
import yaml
import re
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

from .news_source_base import NewsSource, NewsQuery, NewsArticle, expand_keywords_for_domain, test_url_availability
from .domain_config import get_domain_config
from .log import get_news_logger

logger = get_news_logger(__name__)

class WebScrapingSource(NewsSource):
    """Implementazione Web Scraping migliorata con fallback e validazione"""
    
    def __init__(self, config: Dict[str, Any] = None):
        if config is None:
            config = {}
        super().__init__(config)
        
        # Carica configurazione scraping da YAML
        self.scraping_config_path = config.get('scraping_config_path', 
                                             os.path.join(os.path.dirname(__file__), '..', 'config', 'web_scraping.yaml'))
        self.scraping_config = self._load_scraping_config()
        
        # Aggiorna configurazioni da YAML
        if self.scraping_config and 'general' in self.scraping_config:
            yaml_config = self.scraping_config['general']
            self.base_rate_limit_delay = max(
                yaml_config.get('rate_limit_delay', self.base_rate_limit_delay),
                self.scraping_config.get('security', {}).get('min_delay', 1.0)
            )
            self.timeout = min(
                yaml_config.get('timeout', self.timeout),
                self.scraping_config.get('security', {}).get('max_timeout', 15)  # Ridotto da 30 a 15
            )
            self.max_retries = yaml_config.get('max_retries', self.max_retries)
            self.max_articles_per_site = yaml_config.get('max_articles_per_site', 10)
            
        # Configura headers da YAML
        if self.scraping_config and 'headers' in self.scraping_config:
            self.session.headers.update(self.scraping_config['headers'])
            
        # Cache per selettori funzionanti
        self.working_selectors = {}
        
        # Fallback selectors universali
        self.universal_fallbacks = {
            'article_links': [
                'a[href*="articolo"]', 'a[href*="news"]', 'a[href*="notizie"]',
                '.article-title a', '.news-title a', '.headline a',
                'h1 a', 'h2 a', 'h3 a', '.title a'
            ],
            'title': ['h1', '.title', '.article-title', '.news-title', '.headline'],
            'content': ['.article-content', '.news-content', '.article-text', '.news-text', 
                       '.content', '.text', 'p', '.article-body', '.news-body'],
            'date': ['time', '.date', '.article-date', '.news-date', '.published', '.timestamp']
        }
    
    @property
    def priority(self) -> int:
        return 2  # Media priorità
    
    def _load_scraping_config(self) -> Optional[Dict[str, Any]]:
        """Carica configurazione scraping da file YAML"""
        try:
            if os.path.exists(self.scraping_config_path):
                with open(self.scraping_config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    self.logger.info(f"Configurazione scraping caricata da {self.scraping_config_path}")
                    return config
            else:
                self.logger.warning(f"File configurazione scraping non trovato: {self.scraping_config_path}")
                return None
        except Exception as e:
            self.logger.error(f"Errore caricamento configurazione scraping: {e}")
            return None
    
    def is_available(self) -> bool:
        """Web scraping disponibile se configurazione presente e almeno una fonte attiva"""
        if not self.scraping_config:
            return False
        
        # Controlla se c'è almeno una fonte attiva
        sites = self.scraping_config.get('sites', {})
        for site_name, site_config in sites.items():
            if site_config.get('active', True):
                return True
        
        return False
    
    
    def validate_site_configuration(self, site_config: Dict[str, Any]) -> Dict[str, Any]:
        """Valida e corregge configurazione sito"""
        issues = []
        fixes = {}
        
        site_name = site_config.get('name', 'Unknown')
        
        # Testa URL base
        base_url = site_config.get('base_url', '')
        if base_url and not test_url_availability(base_url):
            issues.append(f"Base URL non raggiungibile: {base_url}")
        
        # Testa URL categorie
        categories = site_config.get('categories', {})
        for cat_name, cat_config in categories.items():
            cat_url = cat_config.get('url', '')
            if cat_url and not test_url_availability(cat_url):
                issues.append(f"URL categoria {cat_name} non raggiungibile: {cat_url}")
                
                # Suggerisci URL alternativi
                suggested_urls = self._suggest_alternative_urls(base_url, cat_name)
                for suggested_url in suggested_urls:
                    if test_url_availability(suggested_url):
                        fixes[f"{cat_name}_url"] = suggested_url
                        self.logger.info(f"URL alternativo trovato per {cat_name}: {suggested_url}")
                        break
        
        return {'issues': issues, 'fixes': fixes}
    
    def _suggest_alternative_urls(self, base_url: str, category: str) -> List[str]:
        """Suggerisce URL alternativi per una categoria"""
        if not base_url:
            return []
            
        suggestions = []
        category_variations = {
            'calcio': ['calcio', 'football', 'soccer', 'serie-a', 'sport/calcio'],
            'sport': ['sport', 'sports', 'sportivi'],
            'tecnologia': ['tecnologia', 'tech', 'technology', 'hi-tech'],
            'economia': ['economia', 'business', 'finanza', 'finance'],
            'general': ['news', 'notizie', 'attualita', 'cronaca']
        }
        
        variations = category_variations.get(category.lower(), [category])
        
        for variation in variations:
            suggestions.extend([
                f"{base_url}/{variation}/",
                f"{base_url}/{variation}",
                f"{base_url}/news/{variation}/",
                f"{base_url}/sezioni/{variation}/",
                f"{base_url}/categoria/{variation}/"
            ])
        
        return suggestions[:5]  # Limita a 5 suggerimenti
    
    def test_selectors_on_page(self, url: str, selectors: Dict[str, str]) -> Dict[str, Dict]:
        """Testa selettori su una pagina e suggerisce alternative"""
        try:
            response = self._make_request_with_retry(url)
            if not response:
                return {}
                
            soup = BeautifulSoup(response.text, 'html.parser')
            results = {}
            
            for selector_name, selector in selectors.items():
                elements = soup.select(selector)
                results[selector_name] = {
                    'working': len(elements) > 0,
                    'count': len(elements),
                    'original_selector': selector
                }
                
                # Se il selettore non funziona, prova i fallback
                if len(elements) == 0 and selector_name in self.universal_fallbacks:
                    for fallback_selector in self.universal_fallbacks[selector_name]:
                        fallback_elements = soup.select(fallback_selector)
                        if len(fallback_elements) > 0:
                            results[selector_name]['suggested_selector'] = fallback_selector
                            results[selector_name]['suggested_count'] = len(fallback_elements)
                            self.logger.info(f"Fallback selector trovato per {selector_name}: {fallback_selector}")
                            break
            
            return results
            
        except Exception as e:
            self.logger.error(f"Errore test selettori su {url}: {e}")
            return {}
    
    def search_news(self, query: NewsQuery) -> List[NewsArticle]:
        """Cerca notizie tramite web scraping migliorato"""
        if not self.is_available():
            self.logger.warning("Configurazione scraping non disponibile")
            return []
        
            
        try:
            # Espandi keywords per il dominio
            expanded_keywords = expand_keywords_for_domain(query.domain, query.keywords)
            query_with_expanded = NewsQuery(
                keywords=expanded_keywords,
                domain=query.domain,
                max_results=query.max_results,
                language=query.language,
                time_range=query.time_range
            )
            
            # Seleziona siti appropriati per il dominio
            sites = self._get_domain_sites(query.domain)
            
            if not sites:
                self.logger.warning(f"Nessun sito configurato per dominio: {query.domain}")
                return []
            
            all_articles = []
            
            for site_config in sites:
                try:
                    site_name = site_config['name']
                    
                    # Valida configurazione sito prima del scraping
                    validation = self.validate_site_configuration(site_config)
                    if validation['issues']:
                        self.logger.warning(f"Problemi validazione {site_name}: {validation['issues']}")
                        
                        # Applica fix se disponibili
                        if validation['fixes']:
                            for fix_key, fix_value in validation['fixes'].items():
                                if fix_key.endswith('_url'):
                                    category = fix_key.replace('_url', '')
                                    if category in site_config.get('categories', {}):
                                        site_config['categories'][category]['url'] = fix_value
                                        self.logger.info(f"Applicato fix per {site_name}: {fix_key} = {fix_value}")
                    
                    self.logger.info(f"Scraping da {site_name}...")
                    
                    articles = self._scrape_site(site_config, query_with_expanded)
                    all_articles.extend(articles)
                    
                    self.logger.info(f"Sito {site_name}: {len(articles)} articoli")
                    
                    if len(all_articles) >= query.max_results:
                        break
                        
                except Exception as e:
                    self.logger.error(f"Errore scraping sito {site_config.get('name', 'Unknown')}: {e}")
                    continue
            
            # Applica filtri globali
            all_articles = self._apply_scraping_filters(all_articles)
            
            # Ordina per data e score
            all_articles.sort(
                key=lambda x: (
                    x.score or 0.0,
                    x.published_date or datetime.min
                ),
                reverse=True
            )
            
            return all_articles[:query.max_results]
            
        except Exception as e:
            self.logger.error(f"Errore web scraping: {e}")
            return []
    
    def _get_domain_sites(self, domain: str) -> List[Dict[str, Any]]:
        """Seleziona siti appropriati per il dominio"""
        if not self.scraping_config:
            return []
            
        domain_lower = domain.lower()
        domain_mapping = self.scraping_config.get('domain_mapping', {})
        
        # Trova siti preferiti per il dominio
        preferred_sites = []
        for domain_key, site_names in domain_mapping.items():
            if domain_key in domain_lower:
                preferred_sites = site_names
                break
        
        # Fallback se nessun mapping trovato
        if not preferred_sites:
            if any(term in domain_lower for term in ['calcio']):
                preferred_sites = ['gazzetta', 'corriere_sport', 'tuttomercatoweb', 'calciomercato', 'ansa_sport']
            elif any(term in domain_lower for term in ['tecnologia']):
                preferred_sites = ['repubblica', 'corriere', 'ansa']
            elif any(term in domain_lower for term in ['finanza']):
                preferred_sites = ['sole24ore', 'corriere', 'ansa']
            elif any(term in domain_lower for term in ['salute']):
                preferred_sites = ['ansa', 'corriere', 'repubblica']
            elif any(term in domain_lower for term in ['ambiente']):
                preferred_sites = ['ansa', 'corriere', 'repubblica']
            else:
                preferred_sites = ['ansa', 'corriere', 'repubblica']
        
        # Costruisci configurazioni siti
        sites_config = self.scraping_config.get('sites', {})
        selected_sites = []
        
        for site_name in preferred_sites:
            if site_name in sites_config:
                site_config = sites_config[site_name].copy()
                
                # Controlla se la fonte è attiva
                if not site_config.get('active', True):
                    self.logger.debug(f"Sito {site_name} disattivato (active: false)")
                    continue
                
                site_config['site_key'] = site_name
                selected_sites.append(site_config)
        
        # Ordina per priorità e health score
        def site_sort_key(site_config):
            priority = site_config.get('priority', 999)
            # Considera health score se disponibile
            health = self.working_selectors.get(site_config['site_key'], {}).get('health', 0.5)
            return (priority, -health)
            
        selected_sites.sort(key=site_sort_key)
        return selected_sites[:5]  # Limita a 5 siti per performance
    
    def _scrape_site(self, site_config: Dict[str, Any], query: NewsQuery) -> List[NewsArticle]:
        """Scraping di un singolo sito con selettori adattivi"""
        articles = []
        site_name = site_config.get('name', 'Unknown')
        site_key = site_config.get('site_key', '')
        
        try:
            # Trova categoria appropriata
            categories = site_config.get('categories', {})
            category = self._select_category(categories, query.domain)
            
            if not category:
                self.logger.warning(f"Nessuna categoria trovata per {site_name}")
                return []
            
            category_config = categories[category]
            category_url = category_config['url']
            
            # Rate limiting adattivo per sito
            site_delay = max(
                site_config.get('rate_limit_delay', self.base_rate_limit_delay),
                self.metrics.adaptive_delay
            )
            time.sleep(site_delay)
            
            # Scarica pagina categoria
            response = self._make_request_with_retry(category_url)
            if not response:
                return []
            
            # Estrai link articoli con fallback
            article_links = self._extract_article_links_with_fallback(
                response.text, category_config, site_config, site_key
            )
            
            if not article_links:
                self.logger.warning(f"Nessun link articolo trovato per {site_name}")
                return []
            
            # Limita numero articoli
            max_articles = min(
                len(article_links),
                self.max_articles_per_site,
                query.max_results
            )
            
            # Scraping articoli individuali
            for i, link in enumerate(article_links[:max_articles]):
                try:
                    article = self._scrape_article_with_fallback(link, site_config, query, site_key)
                    if article:
                        articles.append(article)
                        
                    # Rate limiting tra articoli (progressivo)
                    if i < max_articles - 1:  # Non aspettare dopo l'ultimo
                        progressive_delay = site_delay * (1.0 + (i * 0.1))  # Aumenta delay gradualmente
                        time.sleep(min(progressive_delay, site_delay * 2))
                        
                except Exception as e:
                    self.logger.warning(f"Errore scraping articolo {link}: {e}")
                    continue
            
            # Aggiorna cache selettori se ha funzionato
            if articles:
                self._update_working_selectors(site_key, category_config, site_config, True)
            
            return articles
            
        except Exception as e:
            self.logger.error(f"Errore scraping sito {site_name}: {e}")
            self._update_working_selectors(site_key, {}, {}, False)
            return []
    
    def _extract_article_links_with_fallback(self, html: str, category_config: Dict[str, Any], 
                                           site_config: Dict[str, Any], site_key: str) -> List[str]:
        """Estrae link articoli con selettori fallback"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            selectors = category_config.get('selectors', {})
            link_selector = selectors.get('article_links')
            
            # Prova selettore originale
            links = []
            if link_selector:
                link_elements = soup.select(link_selector)
                links = self._extract_href_from_elements(link_elements, site_config.get('base_url', ''))
            
            # Se non ha trovato link, prova selettori fallback
            if not links and 'article_links' in self.universal_fallbacks:
                self.logger.info(f"Selettore originale fallito per {site_key}, provo fallback...")
                
                for fallback_selector in self.universal_fallbacks['article_links']:
                    fallback_elements = soup.select(fallback_selector)
                    if fallback_elements:
                        links = self._extract_href_from_elements(fallback_elements, site_config.get('base_url', ''))
                        if links:
                            self.logger.info(f"Fallback selector funzionante per {site_key}: {fallback_selector}")
                            # Aggiorna configurazione per il futuro
                            self._cache_working_selector(site_key, 'article_links', fallback_selector)
                            break
            
            return links[:20]  # Limita a 20 link
            
        except Exception as e:
            self.logger.error(f"Errore estrazione link: {e}")
            return []
    
    def _extract_href_from_elements(self, elements: List, base_url: str) -> List[str]:
        """Estrae href da elementi e converte in URL assoluti"""
        links = []
        seen = set()
        
        for element in elements:
            href = element.get('href')
            if href:
                # Converti URL relativo in assoluto
                if href.startswith('/'):
                    href = urljoin(base_url, href)
                elif not href.startswith('http'):
                    href = urljoin(base_url, href)
                
                # Filtra URL validi
                if href.startswith('http') and href not in seen:
                    # Evita URL di navigazione
                    if not any(skip in href.lower() for skip in ['#', 'javascript:', 'mailto:', '/tag/', '/category/']):
                        seen.add(href)
                        links.append(href)
        
        return links
    
    def _scrape_article_with_fallback(self, url: str, site_config: Dict[str, Any], 
                                    query: NewsQuery, site_key: str) -> Optional[NewsArticle]:
        """Scraping di un singolo articolo con selettori fallback"""
        try:
            response = self._make_request_with_retry(url)
            if not response:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            selectors = site_config.get('article_selectors', {})
            
            # Estrai contenuti con fallback
            title = self._extract_text_with_fallback(soup, selectors.get('title', 'h1'), 'title', site_key)
            content = self._extract_text_with_fallback(soup, selectors.get('content', 'p'), 'content', site_key)
            date_str = self._extract_text_with_fallback(soup, selectors.get('date', 'time'), 'date', site_key)
            author = self._extract_text_with_fallback(soup, selectors.get('author', ''), 'author', site_key)
            
            if not title or not content:
                self.logger.debug(f"Contenuto insufficiente per {url}")
                return None
            
            # Pulisci contenuto
            content = self._cleanup_content(content, site_config)
            
            # Parse data
            pub_date = self._parse_date(date_str)
            
            # Filtra per keywords espanse
            if query.keywords:
                text_to_check = f"{title} {content}".lower()
                if not any(keyword.lower() in text_to_check for keyword in query.keywords):
                    return None
            
            article = NewsArticle(
                title=title.strip(),
                content=content.strip(),
                url=url,
                published_date=pub_date,
                source=site_config.get('name', 'Web Scraping') or 'Web Scraping',
                score=0.8,  # Score migliorato per articoli che passano i filtri
                metadata={
                    'site': site_key,
                    'author': author,
                    'domain': query.domain,
                    'search_keywords': query.keywords,
                    'scraping_method': 'adaptive_selectors'
                }
            )
            
            return article
            
        except Exception as e:
            self.logger.warning(f"Errore scraping articolo {url}: {e}")
            return None
    
    def _extract_text_with_fallback(self, soup: BeautifulSoup, selector: str, 
                                  selector_type: str, site_key: str) -> str:
        """Estrae testo con selettori fallback"""
        if not selector:
            selector = ''
            
        # Prova selettore originale
        text = self._extract_text(soup, selector)
        
        # Se non ha trovato testo e abbiamo fallback, prova quelli
        if not text and selector_type in self.universal_fallbacks:
            for fallback_selector in self.universal_fallbacks[selector_type]:
                fallback_text = self._extract_text(soup, fallback_selector)
                if fallback_text:
                    self.logger.debug(f"Fallback selector per {selector_type} in {site_key}: {fallback_selector}")
                    self._cache_working_selector(site_key, selector_type, fallback_selector)
                    return fallback_text
        
        return text
    
    def _extract_text(self, soup: BeautifulSoup, selector: str) -> str:
        """Estrae testo usando selettore CSS"""
        if not selector:
            return ""
            
        try:
            elements = soup.select(selector)
            if elements:
                # Combina testo da tutti gli elementi trovati
                texts = []
                for elem in elements:
                    # Rimuovi script e style
                    for script in elem(["script", "style"]):
                        script.decompose()
                    text = elem.get_text(strip=True)
                    if text:
                        texts.append(text)
                return " ".join(texts)
            return ""
        except Exception as e:
            self.logger.warning(f"Errore estrazione testo con selettore {selector}: {e}")
            return ""
    
    def _cache_working_selector(self, site_key: str, selector_type: str, selector: str):
        """Caches selettore funzionante per uso futuro"""
        if site_key not in self.working_selectors:
            self.working_selectors[site_key] = {}
        self.working_selectors[site_key][selector_type] = selector
    
    def _update_working_selectors(self, site_key: str, category_config: Dict, 
                                site_config: Dict, success: bool):
        """Aggiorna cache selettori e health score"""
        if site_key not in self.working_selectors:
            self.working_selectors[site_key] = {'health': 0.5, 'last_test': datetime.now()}
        
        # Aggiorna health score
        current_health = self.working_selectors[site_key].get('health', 0.5)
        if success:
            new_health = min(1.0, current_health + 0.1)
        else:
            new_health = max(0.0, current_health - 0.2)
        
        self.working_selectors[site_key]['health'] = new_health
        self.working_selectors[site_key]['last_test'] = datetime.now()
    
    def _select_category(self, categories: Dict[str, Any], domain: str) -> Optional[str]:
        """Seleziona categoria appropriata per il dominio"""
        domain_lower = domain.lower()
        
        # Mapping specifico per domini
        if any(term in domain_lower for term in ['calcio']):
            for cat in ['calcio', 'serie_a', 'sport']:
                if cat in categories:
                    return cat
        elif any(term in domain_lower for term in ['finanza']):
            for cat in ['finanza', 'economia']:
                if cat in categories:
                    return cat
        elif any(term in domain_lower for term in ['tecnologia']):
            if 'tecnologia' in categories:
                return 'tecnologia'
        elif any(term in domain_lower for term in ['salute']):
            if 'salute' in categories:
                return 'salute'
        elif any(term in domain_lower for term in ['ambiente']):
            if 'ambiente' in categories:
                return 'ambiente'
        
        # Fallback a general o prima categoria disponibile
        if 'general' in categories:
            return 'general'
        elif categories:
            return list(categories.keys())[0]
        
        return None
    
    def _cleanup_content(self, content: str, site_config: Dict[str, Any]) -> str:
        """Pulisce contenuto rimuovendo pattern specifici del sito"""
        if not content:
            return ""
        
        # Pattern specifici del sito
        cleanup_patterns = site_config.get('cleanup_patterns', [])
        for pattern in cleanup_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # Pattern globali
        global_patterns = self.scraping_config.get('content_filters', {}).get('global_cleanup_patterns', [])
        for pattern in global_patterns:
            content = re.sub(pattern, ' ', content)
        
        return content.strip()
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse data da stringa con formati multipli"""
        if not date_str:
            return None
            
        try:
            # Estrai datetime da attributo datetime se presente
            datetime_match = re.search(r'datetime="([^"]+)"', date_str)
            if datetime_match:
                date_str = datetime_match.group(1)
            
            # Prova diversi parser
            try:
                from dateutil import parser as date_parser
                return date_parser.parse(date_str)
            except:
                # Fallback a formati comuni italiani
                italian_formats = [
                    '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d',
                    '%d/%m/%Y %H:%M', '%d-%m-%Y %H:%M',
                    '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'
                ]
                for fmt in italian_formats:
                    try:
                        return datetime.strptime(date_str[:len(fmt)], fmt)
                    except:
                        continue
            
        except Exception as e:
            self.logger.debug(f"Impossibile parsare data: {date_str} - {e}")
            
        return None
    
    def _apply_scraping_filters(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Applica filtri da configurazione scraping"""
        if not self.scraping_config or 'content_filters' not in self.scraping_config:
            return articles
            
        filters = self.scraping_config['content_filters']
        filtered = []
        
        for article in articles:
            try:
                # Filtra per lunghezza
                min_length = filters.get('min_content_length', 0)
                max_length = filters.get('max_content_length', float('inf'))
                
                if len(article.content) < min_length or len(article.content) > max_length:
                    continue
                
                # Filtra titoli da saltare
                skip_titles = filters.get('skip_titles', [])
                if any(skip_title.lower() in article.title.lower() for skip_title in skip_titles):
                    continue
                
                filtered.append(article)
                
            except Exception as e:
                self.logger.warning(f"Errore applicazione filtri scraping: {e}")
                filtered.append(article)  # Mantieni in caso di errore
        
        return filtered
    
    def get_scraping_health_report(self) -> Dict[str, Any]:
        """Genera report sulla salute del sistema di scraping"""
        report = {
            'total_sites': len(self.scraping_config.get('sites', {})) if self.scraping_config else 0,
            'working_sites': len([s for s in self.working_selectors.values() if s.get('health', 0) > 0.5]),
            'failing_sites': len([s for s in self.working_selectors.values() if s.get('health', 0) <= 0.3]),
            'adaptive_delay': self.metrics.adaptive_delay,
            'success_rate': self.reliability_score,
            'avg_response_time': self.metrics.avg_response_time,
            'last_success': self.metrics.last_success_time.isoformat() if self.metrics.last_success_time else None,
            'working_selectors': self.working_selectors
        }
        
        return report