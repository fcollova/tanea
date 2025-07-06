import os
import logging
import configparser
from typing import Dict, Any, Optional, Union

# Logger - usa naming convention centralizzata direttamente
logger = logging.getLogger('tanea.config.core.config')

class Config:
    """
    Classe per gestire la configurazione dell'applicazione.
    Legge da config.conf (comune), config.dev.conf (sviluppo) e config.prod.conf (produzione)
    """
    
    def __init__(self, environment: str = None):
        """
        Inizializza la configurazione
        
        Args:
            environment: 'dev' o 'prod'. Se None, determina automaticamente dall'ENV
        """
        self.environment = environment or self._determine_environment()
        self.config = configparser.ConfigParser()
        self._load_configs()
    
    def _determine_environment(self) -> str:
        """Determina l'ambiente dalla variabile ENV o default a 'dev'"""
        env = os.getenv('ENV', 'dev').lower()
        return 'dev' if env not in ['prod', 'production'] else 'prod'
    
    def _load_configs(self):
        """Carica i file di configurazione in ordine di priorità"""
        config_files = [
            'config.conf',  # Configurazione comune
            f'config.{self.environment}.conf'  # Configurazione specifica per ambiente
        ]
        
        loaded_files = []
        config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
        for config_file in config_files:
            config_path = os.path.join(config_dir, config_file)
            if os.path.exists(config_path):
                try:
                    self.config.read(config_path, encoding='utf-8')
                    loaded_files.append(config_file)
                    logger.info(f"Caricato file di configurazione: {config_file}")
                except Exception as e:
                    logger.error(f"Errore nel caricamento di {config_file}: {e}")
            else:
                logger.warning(f"File di configurazione non trovato: {config_path}")
        
        if not loaded_files:
            logger.warning("Nessun file di configurazione caricato")
        
        logger.info(f"Ambiente: {self.environment}")
        logger.info(f"File caricati: {loaded_files}")
    
    def get(self, section: str, key: str, default: Any = None, 
            cast_type: type = str) -> Any:
        """
        Ottiene un valore di configurazione
        
        Args:
            section: Sezione del file di configurazione
            key: Chiave di configurazione
            default: Valore di default se non trovato
            cast_type: Tipo a cui convertire il valore (str, int, float, bool)
            
        Returns:
            Valore di configurazione convertito al tipo specificato
        """
        try:
            if not self.config.has_section(section):
                logger.debug(f"Sezione '{section}' non trovata, usando default: {default}")
                return default
            
            if not self.config.has_option(section, key):
                logger.debug(f"Chiave '{key}' nella sezione '{section}' non trovata, usando default: {default}")
                return default
            
            value = self.config.get(section, key)
            
            # Conversione di tipo
            if cast_type == bool:
                return value.lower() in ('true', '1', 'yes', 'on')
            elif cast_type == int:
                return int(value)
            elif cast_type == float:
                return float(value)
            elif cast_type == list:
                # Supporta liste separate da virgola
                return [item.strip() for item in value.split(',') if item.strip()]
            else:
                return value
                
        except Exception as e:
            logger.error(f"Errore nel recupero di {section}.{key}: {e}")
            return default
    
    def get_section(self, section: str) -> Dict[str, str]:
        """
        Ottiene tutte le configurazioni di una sezione
        
        Args:
            section: Nome della sezione
            
        Returns:
            Dizionario con tutte le configurazioni della sezione
        """
        if not self.config.has_section(section):
            logger.warning(f"Sezione '{section}' non trovata")
            return {}
        
        return dict(self.config.items(section))
    
    def set(self, section: str, key: str, value: Any):
        """
        Imposta un valore di configurazione (solo in memoria)
        
        Args:
            section: Sezione del file di configurazione
            key: Chiave di configurazione
            value: Valore da impostare
        """
        if not self.config.has_section(section):
            self.config.add_section(section)
        
        self.config.set(section, key, str(value))
    
    # Metodi di convenienza per le configurazioni più comuni
    
    def get_weaviate_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione Weaviate"""
        return {
            'url': self.get('weaviate', 'url', 'http://localhost:8080'),
            'api_key': self.get('weaviate', 'api_key'),
            'index_name': self.get('weaviate', 'index_name', 'NewsArticles'),
            'timeout': self.get('weaviate', 'timeout', 30, int)
        }
    
    def get_embedding_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione del modello di embedding"""
        return {
            'model_name': self.get('embedding', 'model_name', 'intfloat/multilingual-e5-base'),
            'max_length': self.get('embedding', 'max_length', 512, int),
            'cache_dir': self.get('embedding', 'cache_dir', './fastembed_cache'),
            'custom_model': self.get('embedding', 'custom_model', 'nickprock/multi-sentence-BERTino'),
            'fallback_model': self.get('embedding', 'fallback_model', 'sentence-transformers/all-MiniLM-L6-v2')
        }
    
    def get_search_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione per la ricerca"""
        return {
            'tavily_api_key': self.get('search', 'tavily_api_key'),
            'newsapi_api_key': self.get('search', 'newsapi_api_key'),
            'max_results': self.get('search', 'max_results', 10, int),
            'search_depth': self.get('search', 'search_depth', 'advanced'),
            'include_answer': self.get('search', 'include_answer', True, bool),
            'include_raw_content': self.get('search', 'include_raw_content', True, bool)
        }
    
    def get_news_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione per le notizie"""
        return {
            'default_language': self.get('news', 'default_language', 'it'),
            'default_time_range': self.get('news', 'default_time_range', '1d'),
            'max_results': self.get('news', 'max_results', 10, int),
            'chunk_size': self.get('news', 'chunk_size', 1000, int),
            'chunk_overlap': self.get('news', 'chunk_overlap', 200, int)
        }
    
    def get_scheduler_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione dello scheduler"""
        return {
            'update_time': self.get('scheduler', 'update_time', '09:00'),
            'cleanup_day': self.get('scheduler', 'cleanup_day', 'sunday'),
            'cleanup_time': self.get('scheduler', 'cleanup_time', '02:00'),
            'cleanup_days_old': self.get('scheduler', 'cleanup_days_old', 30, int),
            'check_interval': self.get('scheduler', 'check_interval', 60, int)
        }
    
    def get_database_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione del database PostgreSQL"""
        return {
            'url': self.get('database', 'url', 'postgresql://postgres:password@localhost:5432/tanea_news'),
            'schema': self.get('database', 'schema', 'public'),
            'pool_size': self.get('database', 'pool_size', 5, int),
            'pool_timeout': self.get('database', 'pool_timeout', 10, int)
        }
    
    def get_crawler_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione del crawler"""
        return {
            'user_agent': self.get('crawler', 'user_agent', 'TaneaBot/1.0'),
            'rate_limit': self.get('crawler', 'rate_limit', 2.0, float),
            'max_concurrent': self.get('crawler', 'max_concurrent', 3, int),
            'timeout': self.get('crawler', 'timeout', 15, int),
            'max_retries': self.get('crawler', 'max_retries', 3, int),
            
            # Rate limiting avanzato
            'rate_limit_enabled': self.get('crawler', 'rate_limit_enabled', True, bool),
            'rate_limit_default_rps': self.get('crawler', 'rate_limit_default_rps', 0.5, float),
            'rate_limit_max_concurrent': self.get('crawler', 'rate_limit_max_concurrent', 2, int),
            'rate_limit_back_off_factor': self.get('crawler', 'rate_limit_back_off_factor', 2.0, float),
            'rate_limit_max_back_off': self.get('crawler', 'rate_limit_max_back_off', 300.0, float),
            'robots_txt_enabled': self.get('crawler', 'robots_txt_enabled', True, bool),
            'robots_txt_cache_hours': self.get('crawler', 'robots_txt_cache_hours', 24, int)
        }
    
    def get_web_crawling_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione web crawling (config + YAML)"""
        import yaml
        
        # Configurazione base dai file config.*
        base_config = {
            'config_file': self.get('web_crawling', 'config_file', 'web_crawling.yaml'),
            'rate_limit_delay': self.get('web_crawling', 'rate_limit_delay', 2.0, float),
            'max_links_per_site': self.get('web_crawling', 'max_links_per_site', 25, int),
            'min_quality_score': self.get('web_crawling', 'min_quality_score', 0.3, float),
            'max_concurrent_requests': self.get('web_crawling', 'max_concurrent_requests', 5, int),
            'respect_robots_txt': self.get('web_crawling', 'respect_robots_txt', True, bool),
            'follow_redirects': self.get('web_crawling', 'follow_redirects', True, bool),
            'verify_ssl': self.get('web_crawling', 'verify_ssl', True, bool),
            'enable_deduplication': self.get('web_crawling', 'enable_deduplication', True, bool),
            'extract_metadata': self.get('web_crawling', 'extract_metadata', True, bool),
            'extract_keywords': self.get('web_crawling', 'extract_keywords', True, bool),
            
            # Parametri spider Trafilatura
            'spider_max_depth': self.get('web_crawling', 'spider_max_depth', 2, int),
            'spider_max_pages': self.get('web_crawling', 'spider_max_pages', 50, int),
            'spider_max_known_urls': self.get('web_crawling', 'spider_max_known_urls', 150, int),
            'spider_language': self.get('web_crawling', 'spider_language', 'it')
        }
        
        # Carica configurazione YAML
        yaml_file = base_config['config_file']
        yaml_path = os.path.join(os.path.dirname(__file__), '..', 'config', yaml_file)
        
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                yaml_config = yaml.safe_load(f) or {}
            
            # Combina configurazioni (YAML ha precedenza sui dettagli)
            combined_config = base_config.copy()
            combined_config.update(yaml_config)
            
            return combined_config
            
        except Exception as e:
            logger.error(f"Errore caricamento {yaml_file}: {e}")
            return base_config

# Istanza globale di configurazione
_config_instance = None

def get_config(environment: str = None) -> Config:
    """
    Ottiene l'istanza singleton della configurazione
    
    Args:
        environment: Ambiente ('dev' o 'prod'). Usato solo alla prima chiamata.
        
    Returns:
        Istanza della configurazione
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(environment)
    return _config_instance

def reload_config(environment: str = None):
    """
    Ricarica la configurazione (utile per test o cambio ambiente)
    
    Args:
        environment: Nuovo ambiente da caricare
    """
    global _config_instance
    _config_instance = Config(environment)

# Funzioni di convenienza per accesso rapido
def get_weaviate_config() -> Dict[str, Any]:
    """Accesso rapido alla configurazione Weaviate"""
    return get_config().get_weaviate_config()

def get_embedding_config() -> Dict[str, Any]:
    """Accesso rapido alla configurazione embedding"""
    return get_config().get_embedding_config()

def get_search_config() -> Dict[str, Any]:
    """Accesso rapido alla configurazione ricerca"""
    return get_config().get_search_config()

def get_news_config() -> Dict[str, Any]:
    """Accesso rapido alla configurazione notizie"""
    return get_config().get_news_config()

def get_scheduler_config() -> Dict[str, Any]:
    """Accesso rapido alla configurazione scheduler"""
    return get_config().get_scheduler_config()

def get_database_config() -> Dict[str, Any]:
    """Accesso rapido alla configurazione database"""
    return get_config().get_database_config()

def get_crawler_config() -> Dict[str, Any]:
    """Accesso rapido alla configurazione crawler"""
    return get_config().get_crawler_config()

def get_web_crawling_config() -> Dict[str, Any]:
    """Accesso rapido alla configurazione web crawling"""
    return get_config().get_web_crawling_config()

# Funzione per configurare il logging basato sulla configurazione
def setup_logging():
    """
    Configura il logging basato sui parametri di configurazione.
    Se il nuovo sistema centralizzato è disponibile, viene usato quello.
    Altrimenti fallback al sistema legacy.
    """
    try:
        # Prova a usare il nuovo sistema centralizzato
        from .log import LoggerManager, _configure_main_functionality_loggers
        # Il LoggerManager si auto-inizializza, quindi basta importarlo
        
        # Configura livelli per funzionalità principali
        _configure_main_functionality_loggers()
        
        logger.info("Logging configurato tramite sistema centralizzato")
        return
    except ImportError:
        # Fallback al sistema legacy se il nuovo non è disponibile
        pass
    
    # Sistema legacy fallback minimale
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        # Solo se non ci sono handler, aggiungi console handler minimale
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        root_logger.setLevel(logging.INFO)
    
    logger.info("Logging configurato (legacy fallback)")