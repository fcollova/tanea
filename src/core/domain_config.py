"""
Utility per gestire la configurazione dei domini in modo centralizzato
"""
import os
import yaml
from typing import Dict, List, Optional, Set
from pathlib import Path
from .log import get_config_logger

logger = get_config_logger(__name__)

class DomainConfig:
    """Gestisce la configurazione centralizzata dei domini"""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'domains.yaml')
        
        self.config_path = config_path
        self._config_cache = None
        self._last_modified = None
        
    def _load_config(self) -> Dict:
        """Carica la configurazione dei domini da YAML"""
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"File configurazione domini non trovato: {self.config_path}")
                return {}
            
            # Controlla se il file è stato modificato
            current_modified = os.path.getmtime(self.config_path)
            if self._config_cache is None or current_modified != self._last_modified:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config_cache = yaml.safe_load(f) or {}
                    self._last_modified = current_modified
                    logger.info(f"Configurazione domini caricata da {self.config_path}")
            
            return self._config_cache
            
        except Exception as e:
            logger.error(f"Errore caricamento configurazione domini: {e}")
            return {}
    
    def get_all_domains(self) -> List[str]:
        """Ottiene tutti i domini definiti"""
        config = self._load_config()
        domains = config.get('domains', {})
        return list(domains.keys())
    
    def get_active_domains(self) -> List[str]:
        """Ottiene solo i domini attivi"""
        config = self._load_config()
        domains = config.get('domains', {})
        
        active_domains = []
        for domain_key, domain_config in domains.items():
            if domain_config.get('active', False):
                active_domains.append(domain_key)
        
        return active_domains
    
    def get_domain_info(self, domain: str) -> Optional[Dict]:
        """Ottiene informazioni complete su un dominio"""
        config = self._load_config()
        domains = config.get('domains', {})
        return domains.get(domain)
    
    def get_domain_keywords(self, domain: str) -> List[str]:
        """Ottiene le keywords per un dominio"""
        domain_info = self.get_domain_info(domain)
        if domain_info:
            return domain_info.get('keywords', [])
        return []
    
    def get_domain_max_results(self, domain: str, env: str = 'dev') -> int:
        """Ottiene il numero massimo di risultati per un dominio"""
        domain_info = self.get_domain_info(domain)
        if domain_info:
            max_results = domain_info.get('max_results', {})
            return max_results.get(env, max_results.get('dev', 10))
        return 10
    
    def is_domain_active(self, domain: str) -> bool:
        """Verifica se un dominio è attivo"""
        domain_info = self.get_domain_info(domain)
        if domain_info:
            return domain_info.get('active', False)
        return False
    
    def validate_domain(self, domain: str) -> bool:
        """Valida se un dominio esiste nella configurazione"""
        return domain in self.get_all_domains()
    
    def get_fallback_domains(self) -> List[str]:
        """Ottiene domini di fallback (tutti i domini attivi)"""
        return self.get_active_domains()

# Istanza globale per uso condiviso
_domain_config_instance = None

def get_domain_config(config_path: Optional[str] = None) -> DomainConfig:
    """
    Factory function per ottenere l'istanza di DomainConfig
    
    Args:
        config_path: Percorso alternativo al file di configurazione
        
    Returns:
        Istanza di DomainConfig
    """
    global _domain_config_instance
    
    if _domain_config_instance is None or config_path is not None:
        _domain_config_instance = DomainConfig(config_path)
    
    return _domain_config_instance

def get_active_domains() -> List[str]:
    """Shortcut per ottenere domini attivi"""
    return get_domain_config().get_active_domains()

def get_domain_keywords(domain: str) -> List[str]:
    """Shortcut per ottenere keywords di un dominio"""
    return get_domain_config().get_domain_keywords(domain)

def is_domain_active(domain: str) -> bool:
    """Shortcut per verificare se un dominio è attivo"""
    return get_domain_config().is_domain_active(domain)

def validate_domain(domain: str) -> bool:
    """Shortcut per validare un dominio"""
    return get_domain_config().validate_domain(domain)