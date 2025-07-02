import os
import configparser
from typing import Dict, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)

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
        for config_file in config_files:
            if os.path.exists(config_file):
                try:
                    self.config.read(config_file, encoding='utf-8')
                    loaded_files.append(config_file)
                    logger.info(f"Caricato file di configurazione: {config_file}")
                except Exception as e:
                    logger.error(f"Errore nel caricamento di {config_file}: {e}")
            else:
                logger.warning(f"File di configurazione non trovato: {config_file}")
        
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
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione del logging"""
        return {
            'level': self.get('logging', 'level', 'INFO'),
            'format': self.get('logging', 'format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            'file': self.get('logging', 'file'),
            'max_bytes': self.get('logging', 'max_bytes', 10485760, int),  # 10MB
            'backup_count': self.get('logging', 'backup_count', 5, int)
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

def get_logging_config() -> Dict[str, Any]:
    """Accesso rapido alla configurazione logging"""
    return get_config().get_logging_config()

def get_scheduler_config() -> Dict[str, Any]:
    """Accesso rapido alla configurazione scheduler"""
    return get_config().get_scheduler_config()

# Funzione per configurare il logging basato sulla configurazione
def setup_logging():
    """Configura il logging basato sui parametri di configurazione"""
    config = get_logging_config()
    
    # Configura il formato
    formatter = logging.Formatter(config['format'])
    
    # Configura il livello
    level = getattr(logging, config['level'].upper(), logging.INFO)
    
    # Configura il root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Rimuovi handler esistenti
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Aggiungi console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Aggiungi file handler se specificato
    if config['file']:
        try:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                config['file'],
                maxBytes=config['max_bytes'],
                backupCount=config['backup_count']
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            logger.error(f"Errore nella configurazione del file logging: {e}")