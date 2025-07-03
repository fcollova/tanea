import os
import yaml
from typing import Dict, List, Optional
from dataclasses import dataclass
from .log import get_config_logger

logger = get_config_logger(__name__)

@dataclass
class DomainConfig:
    """Configurazione di un dominio"""
    id: str
    name: str
    description: str
    active: bool
    keywords: List[str]
    max_results: Dict[str, int]

class DomainManager:
    """
    Manager per la gestione dei domini di notizie
    """
    
    def __init__(self, config_path: str = None):
        """
        Inizializza il DomainManager
        
        Args:
            config_path: Percorso al file di configurazione domains.yaml
        """
        if config_path is None:
            # Percorso di default
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                'config', 
                'domains.yaml'
            )
        
        self.config_path = config_path
        self.domains = {}
        self.load_domains()
    
    def load_domains(self):
        """Carica i domini dal file YAML"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
                
            for domain_id, domain_config in config['domains'].items():
                self.domains[domain_id] = DomainConfig(
                    id=domain_id,
                    name=domain_config['name'],
                    description=domain_config['description'],
                    active=domain_config.get('active', True),  # Default True per backward compatibility
                    keywords=domain_config['keywords'],
                    max_results=domain_config['max_results']
                )
                
            active_domains = [d_id for d_id, d in self.domains.items() if d.active]
            inactive_domains = [d_id for d_id, d in self.domains.items() if not d.active]
            
            logger.info(f"Caricati {len(self.domains)} domini totali")
            logger.info(f"Domini attivi ({len(active_domains)}): {active_domains}")
            logger.info(f"Domini inattivi ({len(inactive_domains)}): {inactive_domains}")
            
        except FileNotFoundError:
            logger.error(f"File di configurazione domini non trovato: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Errore nel parsing del file YAML: {e}")
            raise
        except Exception as e:
            logger.error(f"Errore nel caricamento dei domini: {e}")
            raise
    
    def get_domain(self, domain_id: str) -> Optional[DomainConfig]:
        """
        Ottiene la configurazione di un dominio
        
        Args:
            domain_id: ID del dominio
            
        Returns:
            DomainConfig o None se non trovato
        """
        return self.domains.get(domain_id)
    
    def get_all_domains(self, active_only: bool = True) -> Dict[str, DomainConfig]:
        """
        Ottiene tutti i domini configurati
        
        Args:
            active_only: Se True, restituisce solo domini attivi
        
        Returns:
            Dizionario con tutti i domini
        """
        if active_only:
            return {domain_id: domain for domain_id, domain in self.domains.items() if domain.active}
        return self.domains.copy()
    
    def get_domain_list(self, active_only: bool = True) -> List[str]:
        """
        Ottiene la lista degli ID dei domini
        
        Args:
            active_only: Se True, restituisce solo domini attivi
            
        Returns:
            Lista degli ID dei domini
        """
        if active_only:
            return [domain_id for domain_id, domain in self.domains.items() if domain.active]
        return list(self.domains.keys())
    
    def get_keywords(self, domain_id: str) -> List[str]:
        """
        Ottiene le keywords di un dominio
        
        Args:
            domain_id: ID del dominio
            
        Returns:
            Lista delle keywords o lista vuota se dominio non trovato
        """
        domain = self.get_domain(domain_id)
        return domain.keywords if domain else []
    
    def get_keywords_string(self, domain_id: str) -> str:
        """
        Ottiene le keywords di un dominio come stringa separata da virgole
        
        Args:
            domain_id: ID del dominio
            
        Returns:
            Stringa con keywords separate da virgole
        """
        keywords = self.get_keywords(domain_id)
        return ', '.join(keywords)
    
    def get_max_results(self, domain_id: str, environment: str = 'dev') -> int:
        """
        Ottiene il numero massimo di risultati per un dominio in un ambiente
        
        Args:
            domain_id: ID del dominio
            environment: Ambiente (dev/prod)
            
        Returns:
            Numero massimo di risultati o 5 come default
        """
        domain = self.get_domain(domain_id)
        if not domain:
            return 5
            
        return domain.max_results.get(environment, 5)
    
    def get_domain_name(self, domain_id: str) -> str:
        """
        Ottiene il nome di un dominio
        
        Args:
            domain_id: ID del dominio
            
        Returns:
            Nome del dominio o l'ID se non trovato
        """
        domain = self.get_domain(domain_id)
        return domain.name if domain else domain_id
    
    def get_domain_description(self, domain_id: str) -> str:
        """
        Ottiene la descrizione di un dominio
        
        Args:
            domain_id: ID del dominio
            
        Returns:
            Descrizione del dominio o stringa vuota se non trovato
        """
        domain = self.get_domain(domain_id)
        return domain.description if domain else ""
    
    def domain_exists(self, domain_id: str, active_only: bool = True) -> bool:
        """
        Verifica se un dominio esiste
        
        Args:
            domain_id: ID del dominio
            active_only: Se True, verifica solo domini attivi
            
        Returns:
            True se il dominio esiste (e se richiesto è attivo), False altrimenti
        """
        if domain_id not in self.domains:
            return False
        if active_only:
            return self.domains[domain_id].active
        return True
    
    def reload_domains(self):
        """Ricarica i domini dal file di configurazione"""
        self.domains.clear()
        self.load_domains()
        logger.info("Domini ricaricati")
    
    def validate_domain_config(self) -> bool:
        """
        Valida la configurazione dei domini
        
        Returns:
            True se la configurazione è valida, False altrimenti
        """
        try:
            for domain_id, domain in self.domains.items():
                if not domain.name:
                    logger.error(f"Dominio {domain_id}: nome mancante")
                    return False
                    
                if not domain.keywords:
                    logger.error(f"Dominio {domain_id}: keywords mancanti")
                    return False
                    
                if not domain.max_results:
                    logger.error(f"Dominio {domain_id}: max_results mancante")
                    return False
                    
                # Verifica che ci siano configurazioni per dev e prod
                if 'dev' not in domain.max_results or 'prod' not in domain.max_results:
                    logger.error(f"Dominio {domain_id}: mancano configurazioni dev/prod")
                    return False
                    
                # Verifica che il campo active sia presente
                if not hasattr(domain, 'active'):
                    logger.error(f"Dominio {domain_id}: campo active mancante")
                    return False
                    
            logger.info("Configurazione domini validata con successo")
            return True
            
        except Exception as e:
            logger.error(f"Errore nella validazione dei domini: {e}")
            return False
    
    def is_domain_active(self, domain_id: str) -> bool:
        """
        Verifica se un dominio è attivo
        
        Args:
            domain_id: ID del dominio
            
        Returns:
            True se il dominio è attivo, False altrimenti
        """
        domain = self.get_domain(domain_id)
        return domain.active if domain else False
    
    def get_active_domains(self) -> Dict[str, DomainConfig]:
        """
        Ottiene solo i domini attivi
        
        Returns:
            Dizionario con i domini attivi
        """
        return self.get_all_domains(active_only=True)
    
    def get_inactive_domains(self) -> Dict[str, DomainConfig]:
        """
        Ottiene solo i domini inattivi
        
        Returns:
            Dizionario con i domini inattivi
        """
        return {domain_id: domain for domain_id, domain in self.domains.items() if not domain.active}
    
    def set_domain_active(self, domain_id: str, active: bool) -> bool:
        """
        Attiva o disattiva un dominio (solo in memoria)
        
        Args:
            domain_id: ID del dominio
            active: True per attivare, False per disattivare
            
        Returns:
            True se operazione riuscita, False altrimenti
        """
        if domain_id not in self.domains:
            logger.error(f"Dominio {domain_id} non trovato")
            return False
            
        self.domains[domain_id].active = active
        logger.info(f"Dominio {domain_id} {'attivato' if active else 'disattivato'}")
        return True
    
    def get_domain_stats(self) -> Dict[str, int]:
        """
        Ottiene statistiche sui domini
        
        Returns:
            Dizionario con conteggi domini attivi/inattivi
        """
        active_count = len(self.get_active_domains())
        inactive_count = len(self.get_inactive_domains())
        
        return {
            "total": len(self.domains),
            "active": active_count,
            "inactive": inactive_count
        }