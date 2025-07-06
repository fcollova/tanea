"""
Content Extractor - Estrazione contenuto articoli con trafilatura
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Optional, List
from datetime import datetime
from urllib.parse import urlparse

try:
    import trafilatura
    from trafilatura.settings import use_config
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False

from ..config import get_crawler_config
from ..log import get_news_logger
from .rate_limiter import AdvancedRateLimiter

logger = get_news_logger(__name__)

class ContentExtractor:
    """Estrae contenuto articoli usando trafilatura"""
    
    def __init__(self):
        if not TRAFILATURA_AVAILABLE:
            raise ImportError("Trafilatura richiesta per ContentExtractor")
        
        self.config = get_crawler_config()
        self.session = None
        self.rate_limiter = AdvancedRateLimiter()
        
        # Configurazione trafilatura ottimizzata
        self._setup_trafilatura()
        
        # Stats estrazione
        self.extraction_stats = {
            'total_attempts': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'avg_content_length': 0,
            'total_content_length': 0
        }
    
    def _setup_trafilatura(self):
        """Configura trafilatura per performance ottimale"""
        try:
            config = trafilatura.settings.use_config()
            
            # Ottimizzazioni per articoli di notizie
            config.set('DEFAULT', 'EXTRACTION_TIMEOUT', str(self.config['timeout']))
            config.set('DEFAULT', 'MIN_EXTRACTED_SIZE', '200')  # Almeno 200 caratteri
            config.set('DEFAULT', 'MIN_OUTPUT_SIZE', '100')
            config.set('DEFAULT', 'MAX_OUTPUT_SIZE', '50000')   # Max 50k caratteri
            
            # Focus su contenuto principale
            config.set('DEFAULT', 'FAVOR_PRECISION', 'True')
            config.set('DEFAULT', 'INCLUDE_COMMENTS', 'False')
            config.set('DEFAULT', 'INCLUDE_TABLES', 'True')     # Utili per sport/statistiche
            config.set('DEFAULT', 'INCLUDE_FORMATTING', 'True')
            
            self.trafilatura_config = config
            logger.info("Trafilatura configurata per estrazione news")
            
        except Exception as e:
            logger.warning(f"Errore configurazione trafilatura: {e}")
            self.trafilatura_config = None
    
    async def __aenter__(self):
        """Context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config['timeout']),
            headers={
                'User-Agent': self.config['user_agent'],
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            await self.session.close()
    
    async def extract_article(self, url: str, domain: str = "general", 
                            keywords: List[str] = None) -> Optional[Dict]:
        """
        Estrae contenuto articolo da URL
        
        Args:
            url: URL articolo da estrarre
            domain: Dominio di appartenenza (calcio, tecnologia, etc.)
            keywords: Keywords per validazione relevanza
            
        Returns:
            dict: Dati articolo estratto o None se fallito
        """
        self.extraction_stats['total_attempts'] += 1
        logger.info(f"[EXTRACTION DEBUG] Inizio estrazione per: {url}")
        
        try:
            # 1. Scarica pagina
            logger.info(f"[EXTRACTION DEBUG] Step 1: Fetch pagina")
            html = await self._fetch_article_page(url)
            if not html:
                logger.info(f"[EXTRACTION DEBUG] FALLIMENTO Step 1: HTML non ottenuto")
                self.extraction_stats['failed_extractions'] += 1
                return None
            logger.info(f"[EXTRACTION DEBUG] Step 1 OK: HTML ottenuto ({len(html)} caratteri)")
            
            # 2. Estrai contenuto con trafilatura  
            logger.info(f"[EXTRACTION DEBUG] Step 2: Estrazione Trafilatura")
            extracted_data = self._extract_with_trafilatura(html, url)
            if not extracted_data:
                logger.info(f"[EXTRACTION DEBUG] FALLIMENTO Step 2: Trafilatura non ha estratto dati")
                self.extraction_stats['failed_extractions'] += 1
                return None
            logger.info(f"[EXTRACTION DEBUG] Step 2 OK: Dati estratti = {list(extracted_data.keys())}")
            # logger.info(f"[EXTRACTION DEBUG] Dati estratti completi: {extracted_data}")  # Commentato per ridurre log
            
            # 3. Valida e enrichment
            logger.info(f"[EXTRACTION DEBUG] Step 3: Validazione")
            article_data = self._validate_and_enrich(extracted_data, url, domain, keywords)
            if not article_data:
                logger.info(f"[EXTRACTION DEBUG] FALLIMENTO Step 3: Validazione fallita")
                self.extraction_stats['failed_extractions'] += 1
                return None
            logger.info(f"[EXTRACTION DEBUG] Step 3 OK: Articolo validato")
            
            # 4. Aggiorna statistiche
            self._update_stats(article_data)
            
            logger.info(f"[EXTRACTION DEBUG] SUCCESSO: {article_data['title'][:50]}...")
            return article_data
            
        except Exception as e:
            logger.error(f"[EXTRACTION DEBUG] ERRORE ECCEZIONE: {url}: {e}")
            self.extraction_stats['failed_extractions'] += 1
            return None
    
    async def _fetch_article_page(self, url: str) -> Optional[str]:
        """Scarica pagina articolo con rate limiting"""
        try:
            # Applica rate limiting
            if not await self.rate_limiter.acquire_for_url(url):
                logger.warning(f"Rate limiter ha bloccato {url}")
                return None
            
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        self.rate_limiter.release_for_url(url, success=True)
                        return content
                    else:
                        logger.warning(f"HTTP {response.status} per {url}")
                        self.rate_limiter.release_for_url(url, success=False)
                        return None
                        
            except asyncio.TimeoutError:
                logger.warning(f"Timeout per {url}")
                self.rate_limiter.release_for_url(url, success=False)
                return None
            except Exception as e:
                logger.error(f"Errore fetch {url}: {e}")
                self.rate_limiter.release_for_url(url, success=False)
                return None
                
        except Exception as e:
            logger.error(f"Errore rate limiting per {url}: {e}")
            return None
    
    def _extract_with_trafilatura(self, html: str, url: str) -> Optional[Dict]:
        """Estrae contenuto usando trafilatura"""
        try:
            # Estrazione separata per contenuto e metadati
            content = trafilatura.extract(
                html,
                config=self.trafilatura_config,
                include_comments=False,
                include_tables=True,
                include_formatting=True,
                favor_precision=True
            )
            
            if not content:
                return None
            
            # Estrazione metadati separata
            metadata = trafilatura.extract_metadata(html)
            
            # Costruisci dizionario dati
            data = {
                'text': content,
                'title': metadata.title if metadata else '',
                'author': metadata.author if metadata else '',
                'date': metadata.date if metadata else None,
                'description': metadata.description if metadata else '',
                'sitename': metadata.sitename if metadata else '',
                'language': metadata.language if metadata else 'it'
            }
            
            return data
            
        except Exception as e:
            logger.debug(f"Errore trafilatura per {url}: {e}")
            return None
    
    def _validate_and_enrich(self, extracted_data: Dict, url: str, 
                           domain: str, keywords: List[str] = None) -> Optional[Dict]:
        """Valida e arricchisce dati estratti"""
        try:
            title = extracted_data.get('title', '').strip()
            content = extracted_data.get('text', '').strip()
            
            logger.info(f"[VALIDATION DEBUG] Titolo: '{title}' (len={len(title)})")
            logger.info(f"[VALIDATION DEBUG] Contenuto: {len(content)} caratteri")
            logger.info(f"[VALIDATION DEBUG] Primi 200 char: {content[:200]}...")
            
            # Validazioni base
            if not title or len(title) < 10:
                logger.info(f"[VALIDATION DEBUG] FALLIMENTO: Titolo troppo corto o assente: {url}")
                return None
            
            if not content or len(content) < 200:
                logger.info(f"[VALIDATION DEBUG] FALLIMENTO: Contenuto troppo corto: {url} ({len(content)} caratteri)")
                return None
            
            # Filtra per keywords se specificate
            if keywords:
                text_to_check = f"{title} {content}".lower()
                if not any(keyword.lower() in text_to_check for keyword in keywords):
                    logger.debug(f"Keywords non trovate in {url}")
                    return None
            
            # Parse data pubblicazione
            published_date = self._parse_publication_date(extracted_data.get('date'))
            
            # Calcola quality score
            quality_score = self._calculate_quality_score(title, content, extracted_data)
            
            # Estrai keywords dal contenuto
            found_keywords = self._extract_content_keywords(content, domain)
            
            # Costruisci articolo finale
            article_data = {
                'title': title,
                'content': content,
                'url': url,
                'published_date': published_date,
                'author': extracted_data.get('author', ''),
                'source': self._extract_source_name(url, extracted_data),
                'domain': domain,
                'quality_score': quality_score,
                'keywords': found_keywords,
                'metadata': {
                    'extraction_method': 'trafilatura',
                    'extraction_date': datetime.now().isoformat(),
                    'content_length': len(content),
                    'description': extracted_data.get('description', ''),
                    'sitename': extracted_data.get('sitename', ''),
                    'language': extracted_data.get('language', 'it'),
                    'url_parsed': urlparse(url)._asdict()
                }
            }
            
            return article_data
            
        except Exception as e:
            logger.error(f"Errore validazione/enrichment {url}: {e}")
            return None
    
    def _parse_publication_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse data pubblicazione con formato RFC3339 per Weaviate"""
        if not date_str:
            return None
        
        try:
            # Trafilatura normalizza già le date
            if 'T' in date_str:
                # Formato ISO già presente
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                # Formato data semplice - aggiungi orario per RFC3339
                dt = datetime.fromisoformat(date_str + 'T06:00:00')
            
            # Assicura timezone UTC per RFC3339
            if dt.tzinfo is None:
                from datetime import timezone
                dt = dt.replace(tzinfo=timezone.utc)  # Aggiungi timezone UTC
                
            return dt
                
        except Exception:
            # Fallback con dateutil se disponibile
            try:
                from dateutil import parser as date_parser
                dt = date_parser.parse(date_str)
                if dt.tzinfo is None:
                    from datetime import timezone
                    dt = dt.replace(tzinfo=timezone.utc)  # Aggiungi timezone UTC
                return dt
            except:
                logger.debug(f"Impossibile parsare data: {date_str}")
                return None
    
    def _calculate_quality_score(self, title: str, content: str, data: Dict) -> float:
        """Calcola score qualità contenuto"""
        score = 0.5  # Base score
        
        # Bonus per metadati completi
        if data.get('author'):
            score += 0.15
        if data.get('date'):
            score += 0.15
        if data.get('description'):
            score += 0.1
        
        # Bonus per lunghezza contenuto appropriata
        content_length = len(content)
        if 1000 <= content_length <= 8000:  # Lunghezza ideale
            score += 0.2
        elif 500 <= content_length <= 15000:  # Accettabile
            score += 0.1
        elif content_length < 200:  # Troppo corto
            score -= 0.2
        
        # Bonus per titolo informativo
        if 20 <= len(title) <= 150:
            score += 0.1
        
        # Bonus per struttura contenuto
        if content.count('\n') > 3:  # Paragrafi multipli
            score += 0.05
        
        return min(1.0, max(0.0, score))
    
    def _extract_source_name(self, url: str, data: Dict) -> str:
        """Estrae nome fonte"""
        # Prima prova sitename da trafilatura
        sitename = data.get('sitename', '')
        if sitename:
            return sitename
        
        # Fallback dal dominio URL
        try:
            domain = urlparse(url).netloc
            # Rimuovi www. e estrai nome principale
            domain = domain.replace('www.', '')
            domain_parts = domain.split('.')
            if domain_parts:
                return domain_parts[0].title()
        except:
            pass
        
        return 'Unknown Source'
    
    def _extract_content_keywords(self, content: str, domain: str) -> List[str]:
        """Estrae keywords rilevanti dal contenuto"""
        keywords = []
        content_lower = content.lower()
        
        # Keywords per dominio calcio
        if domain == 'calcio':
            calcio_keywords = [
                'serie a', 'juventus', 'inter', 'milan', 'napoli', 'roma', 'lazio',
                'atalanta', 'fiorentina', 'champions league', 'europa league',
                'coppa italia', 'calciomercato', 'gol', 'partita', 'allenatore',
                'giocatore', 'stadio', 'classifica'
            ]
            keywords.extend([kw for kw in calcio_keywords if kw in content_lower])
        
        # Keywords per tecnologia
        elif domain == 'tecnologia':
            tech_keywords = [
                'intelligenza artificiale', 'ai', 'machine learning', 'chatgpt',
                'openai', 'google', 'microsoft', 'apple', 'startup', 'innovation',
                'robotica', 'automazione', 'blockchain', 'crypto'
            ]
            keywords.extend([kw for kw in tech_keywords if kw in content_lower])
        
        # Keywords per finanza
        elif domain == 'finanza':
            finance_keywords = [
                'borsa italiana', 'ftse mib', 'investimenti', 'bce', 'euro',
                'inflazione', 'mercati finanziari', 'bitcoin', 'criptovalute',
                'banche', 'economia italiana'
            ]
            keywords.extend([kw for kw in finance_keywords if kw in content_lower])
        
        return keywords[:10]  # Limita numero keywords
    
    def _update_stats(self, article_data: Dict):
        """Aggiorna statistiche estrazione"""
        self.extraction_stats['successful_extractions'] += 1
        
        content_length = len(article_data['content'])
        self.extraction_stats['total_content_length'] += content_length
        
        # Calcola media lunghezza
        successful = self.extraction_stats['successful_extractions']
        self.extraction_stats['avg_content_length'] = (
            self.extraction_stats['total_content_length'] / successful
        )
    
    async def batch_extract_articles(self, urls: List[str], domain: str = "general",
                                   keywords: List[str] = None, 
                                   max_concurrent: int = 3) -> List[Dict]:
        """
        Estrae articoli in batch con concorrenza limitata
        
        Args:
            urls: Lista URL da estrarre
            domain: Dominio di appartenenza
            keywords: Keywords per validazione
            max_concurrent: Massimo estrattori concorrenti
            
        Returns:
            list: Lista articoli estratti con successo
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def extract_with_semaphore(url):
            async with semaphore:
                # Rate limiting
                await asyncio.sleep(self.config['rate_limit'])
                return await self.extract_article(url, domain, keywords)
        
        # Esegui estrazione concorrente
        tasks = [extract_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filtra risultati validi
        articles = []
        for i, result in enumerate(results):
            if isinstance(result, dict):
                articles.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Errore estrazione {urls[i]}: {result}")
        
        logger.info(f"Batch extraction: {len(articles)}/{len(urls)} successi")
        return articles
    
    def get_extraction_stats(self) -> Dict[str, any]:
        """Statistiche estrazione"""
        total = self.extraction_stats['total_attempts']
        success_rate = (
            self.extraction_stats['successful_extractions'] / total 
            if total > 0 else 0
        )
        
        return {
            **self.extraction_stats,
            'success_rate': success_rate,
            'failure_rate': 1 - success_rate
        }