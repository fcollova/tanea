"""
Modulo centralizzato per la gestione del logging nell'applicazione News Vector DB

Fornisce:
- Configurazione standardizzata del logging
- Factory per logger specializzati
- Utilities per performance e error tracking
- Decoratori per logging automatico
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from functools import wraps
from datetime import datetime

# Configurazione di default
DEFAULT_LOG_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

class LoggerManager:
    """Gestore centralizzato per tutti i logger dell'applicazione"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggerManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not LoggerManager._initialized:
            self.loggers: Dict[str, logging.Logger] = {}
            self.config = self._load_config()
            self._setup_root_logger()
            LoggerManager._initialized = True
    
    def _load_config(self) -> Dict[str, Any]:
        """Carica configurazione logging da logging.conf"""
        # Determina ambiente
        env = os.getenv('ENV', 'dev').lower()
        is_production = env in ['prod', 'production']
        
        # Directory log
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Usa logging.conf se disponibile
        config_file = self._find_logging_config()
        if config_file:
            try:
                # Sostituisci placeholder %(env)s nel file di configurazione
                import tempfile
                import logging.config
                
                with open(config_file, 'r') as f:
                    content = f.read()
                
                # Sostituisci placeholder ambiente
                content = content.replace('%(env)s', env)
                
                # Crea file temporaneo con sostituzioni
                with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as tmp_file:
                    tmp_file.write(content)
                    tmp_config_file = tmp_file.name
                
                # Carica configurazione
                logging.config.fileConfig(tmp_config_file, disable_existing_loggers=False)
                
                # Rimuovi file temporaneo
                os.unlink(tmp_config_file)
                
                return {
                    'environment': env,
                    'is_production': is_production,
                    'config_source': 'logging.conf',
                    'config_file': config_file
                }
                
            except Exception as e:
                print(f"Errore caricamento logging.conf: {e}")
                # Fallback alla configurazione hardcoded
                pass
        
        # Configurazione fallback (come prima)
        return {
            'environment': env,
            'is_production': is_production,
            'log_level': logging.INFO if is_production else logging.DEBUG,
            'log_dir': log_dir,
            'log_file': log_dir / f"tanea_{env}.log",
            'error_log_file': log_dir / f"tanea_errors_{env}.log",
            'max_file_size': 10 * 1024 * 1024,  # 10MB
            'backup_count': 5,
            'console_logging': not is_production,  # Console solo in dev
            'file_logging': True,
            'format': DEFAULT_LOG_FORMAT,
            'date_format': DEFAULT_DATE_FORMAT,
            'config_source': 'hardcoded'
        }
    
    def _find_logging_config(self) -> Optional[str]:
        """Trova il file logging.conf"""
        possible_paths = [
            'src/config/logging.conf',
            'config/logging.conf',
            'logging.conf',
            os.path.join(os.path.dirname(__file__), '..', 'config', 'logging.conf')
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def _setup_root_logger(self):
        """Configura il logger root dell'applicazione"""
        # Se la configurazione viene da logging.conf, non fare nulla
        # perché è già stata configurata
        if self.config.get('config_source') == 'logging.conf':
            return
        
        # Configurazione fallback manuale
        root_logger = logging.getLogger()
        root_logger.setLevel(self.config['log_level'])
        
        # Rimuovi handler esistenti per evitare duplicati
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        formatter = logging.Formatter(
            self.config['format'],
            self.config['date_format']
        )
        
        # Handler per file principale
        if self.config['file_logging']:
            file_handler = logging.handlers.RotatingFileHandler(
                self.config['log_file'],
                maxBytes=self.config['max_file_size'],
                backupCount=self.config['backup_count'],
                encoding='utf-8'
            )
            file_handler.setLevel(self.config['log_level'])
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        
        # Handler per errori separato
        if self.config['file_logging']:
            error_handler = logging.handlers.RotatingFileHandler(
                self.config['error_log_file'],
                maxBytes=self.config['max_file_size'],
                backupCount=self.config['backup_count'],
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            root_logger.addHandler(error_handler)
        
        # Handler console (solo in sviluppo)
        if self.config['console_logging']:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.config['log_level'])
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
    
    def get_logger(self, name: str, specialized_type: Optional[str] = None) -> logging.Logger:
        """
        Factory method per ottenere logger standardizzati
        
        Args:
            name: Nome del logger (solitamente __name__)
            specialized_type: Tipo specializzato ('news', 'database', 'config', 'scripts')
            
        Returns:
            Logger configurato
        """
        # Normalizza il nome
        if name.startswith('src.'):
            name = name[4:]  # Rimuovi prefisso 'src.'
        
        # Aggiungi prefisso specializzato se specificato
        if specialized_type:
            logger_name = f"tanea.{specialized_type}.{name}"
        else:
            logger_name = f"tanea.{name}"
        
        # Riusa logger esistente se già creato
        if logger_name in self.loggers:
            return self.loggers[logger_name]
        
        # Crea nuovo logger
        logger = logging.getLogger(logger_name)
        
        # Non aggiungere handler qui, usa quelli del root logger
        # Questo evita duplicazioni
        
        # Cache il logger
        self.loggers[logger_name] = logger
        
        return logger
    
    def get_stats(self) -> Dict[str, Any]:
        """Ottiene statistiche sui logger attivi"""
        log_files = {}
        if 'log_file' in self.config:
            log_files['main'] = str(self.config['log_file'])
        if 'error_log_file' in self.config:
            log_files['errors'] = str(self.config['error_log_file'])
        
        return {
            'total_loggers': len(self.loggers),
            'logger_names': list(self.loggers.keys()),
            'config': self.config,
            'log_files': log_files
        }

# Istanza globale
_logger_manager = LoggerManager()

def get_logger(name: str, specialized_type: Optional[str] = None) -> logging.Logger:
    """
    Factory function per ottenere logger standardizzati
    
    Args:
        name: Nome del modulo (usa __name__)
        specialized_type: Tipo specializzato se necessario
        
    Returns:
        Logger configurato
        
    Example:
        logger = get_logger(__name__)
        news_logger = get_logger(__name__, 'news')
    """
    return _logger_manager.get_logger(name, specialized_type)

def setup_logging() -> None:
    """
    Inizializza il sistema di logging (legacy compatibility)
    Chiamata dai moduli esistenti che usano setup_logging()
    """
    # Il LoggerManager si auto-inizializza, questa funzione mantiene compatibilità
    _configure_main_functionality_loggers()

def _configure_main_functionality_loggers():
    """Configura livelli specifici per funzionalità principali dell'applicazione"""
    
    # Funzionalità principali: sempre INFO (mai DEBUG in produzione)
    main_loggers = [
        'tanea.news',       # Ricerca e gestione notizie
        'tanea.database',   # Vector DB operations
        'tanea.config',     # Configurazione sistema
        'tanea.scripts'     # Script principali
    ]
    
    env = os.getenv('ENV', 'dev').lower()
    is_production = env in ['prod', 'production']
    
    # In produzione: solo INFO per funzionalità principali
    # In sviluppo: DEBUG per funzionalità principali, INFO per il resto
    main_level = logging.INFO if is_production else logging.INFO  # Sempre INFO per chiarezza
    
    for logger_name in main_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(main_level)
    
    # Silenzia librerie esterne troppo verbose
    external_loggers = {
        'httpcore': logging.WARNING,
        'httpx': logging.INFO,  # Mantieni requests HTTP importanti
        'urllib3': logging.WARNING,
        'huggingface_hub': logging.WARNING,
        'requests': logging.WARNING,
        'boto3': logging.WARNING,
        'botocore': logging.WARNING,
        'openai': logging.WARNING,
        'langchain': logging.INFO
    }
    
    for logger_name, level in external_loggers.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)

def set_debug_mode(enabled: bool = True):
    """
    Abilita/disabilita modalità debug per funzionalità principali
    
    Args:
        enabled: True per abilitare DEBUG, False per tornare a INFO
    """
    main_loggers = [
        'tanea.news',
        'tanea.database', 
        'tanea.config',
        'tanea.scripts'
    ]
    
    level = logging.DEBUG if enabled else logging.INFO
    
    for logger_name in main_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
    
    # Log del cambio
    logger = get_logger(__name__)
    logger.info(f"Modalità debug {'abilitata' if enabled else 'disabilitata'} per funzionalità principali")

# Logger specializzati per aree funzionali specifiche

def get_news_logger(name: str) -> logging.Logger:
    """Logger specializzato per gestione notizie"""
    return get_logger(name, 'news')

def get_database_logger(name: str) -> logging.Logger:
    """Logger specializzato per operazioni database/vector store"""
    return get_logger(name, 'database')

def get_config_logger(name: str) -> logging.Logger:
    """Logger specializzato per configurazione"""
    return get_logger(name, 'config')

def get_scripts_logger(name: str) -> logging.Logger:
    """Logger specializzato per script"""
    return get_logger(name, 'scripts')

# Decoratori per logging automatico

def log_function_call(logger: Optional[logging.Logger] = None, level: int = logging.DEBUG):
    """
    Decoratore per loggare chiamate a funzioni
    
    Args:
        logger: Logger da usare (se None, usa logger del modulo)
        level: Livello di log
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_logger = logger or get_logger(func.__module__)
            
            # Log chiamata
            func_name = f"{func.__module__}.{func.__name__}"
            func_logger.log(level, f"Chiamata {func_name}")
            
            try:
                result = func(*args, **kwargs)
                func_logger.log(level, f"Completata {func_name}")
                return result
            except Exception as e:
                func_logger.error(f"Errore in {func_name}: {e}")
                raise
        
        return wrapper
    return decorator

def log_performance(logger: Optional[logging.Logger] = None, level: int = logging.INFO):
    """
    Decoratore per loggare performance di funzioni
    
    Args:
        logger: Logger da usare
        level: Livello di log
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_logger = logger or get_logger(func.__module__)
            
            start_time = datetime.now()
            func_name = f"{func.__module__}.{func.__name__}"
            
            try:
                result = func(*args, **kwargs)
                
                duration = (datetime.now() - start_time).total_seconds()
                func_logger.log(level, f"Performance {func_name}: {duration:.3f}s")
                
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                func_logger.error(f"Errore in {func_name} dopo {duration:.3f}s: {e}")
                raise
        
        return wrapper
    return decorator

def log_method_entry_exit(logger: Optional[logging.Logger] = None, level: int = logging.DEBUG):
    """
    Decoratore per loggare ingresso/uscita da metodi di classe
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            func_logger = logger or get_logger(func.__module__)
            
            class_name = self.__class__.__name__
            method_name = func.__name__
            full_name = f"{class_name}.{method_name}"
            
            func_logger.log(level, f">>> {full_name}")
            
            try:
                result = func(self, *args, **kwargs)
                func_logger.log(level, f"<<< {full_name}")
                return result
            except Exception as e:
                func_logger.error(f"!!! {full_name}: {e}")
                raise
        
        return wrapper
    return decorator

# Utilities

def get_logging_stats() -> Dict[str, Any]:
    """Ottiene statistiche del sistema di logging"""
    return _logger_manager.get_stats()

def flush_logs():
    """Forza il flush di tutti i log handlers"""
    for handler in logging.getLogger().handlers:
        handler.flush()

# Context manager per logging temporaneo

class temporary_log_level:
    """Context manager per cambiare temporaneamente il livello di log"""
    
    def __init__(self, logger_name: str, level: int):
        self.logger = logging.getLogger(logger_name)
        self.original_level = self.logger.level
        self.new_level = level
    
    def __enter__(self):
        self.logger.setLevel(self.new_level)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.setLevel(self.original_level)

# Inizializzazione automatica
if __name__ != "__main__":
    # Inizializza automaticamente quando il modulo viene importato
    pass