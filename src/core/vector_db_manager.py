import os
from typing import Optional, Dict

import weaviate
from langchain_community.embeddings import FastEmbedEmbeddings

from .config import get_weaviate_config, get_embedding_config
from .domain_manager import DomainManager
from .log import get_database_logger

logger = get_database_logger(__name__)

class VectorDBManager:
    """
    Classe per gestire la creazione e configurazione del Vector Database
    """
    
    def __init__(self, environment: str = None, domain: str = None):
        # Ottieni configurazioni
        weaviate_config = get_weaviate_config()
        embedding_config = get_embedding_config()
        
        self.environment = environment or 'dev'
        self.domain = domain
        self.weaviate_url = weaviate_config['url']
        self.weaviate_api_key = weaviate_config['api_key']
        self.embedding_model = embedding_config['model_name']
        self.embedding_config = embedding_config
        
        # Inizializza DomainManager per gestione index
        self.domain_manager = DomainManager()
        
        # Index name dipende dal dominio (se specificato)
        if self.domain:
            self.index_name = self.domain_manager.get_weaviate_index(self.domain, self.environment)
        else:
            # Fallback al vecchio comportamento per compatibilità
            self.index_name = weaviate_config.get('index_name', f'Tanea_General_{self.environment.upper()}')
        
        self.weaviate_client = None
        self.embeddings = None
    
    def close(self):
        """Chiude le connessioni per evitare memory leaks"""
        try:
            if self.weaviate_client:
                self.weaviate_client.close()
                logger.info("VectorDBManager: Connessione Weaviate chiusa")
        except Exception as e:
            logger.error(f"VectorDBManager: Errore nella chiusura delle connessioni: {e}")
    
    def __enter__(self):
        """Support for context manager"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup when exiting context manager"""
        self.close()
    
    def init_weaviate_client(self):
        """Inizializza il client Weaviate"""
        try:
            auth_config = None
            if self.weaviate_api_key:
                auth_config = weaviate.auth.AuthApiKey(api_key=self.weaviate_api_key)
            
            self.weaviate_client = weaviate.connect_to_local(
                auth_credentials=auth_config
            )
            
            # Crea lo schema se non esiste
            self.create_schema()
            logger.info("Client Weaviate inizializzato con successo")
            
        except Exception as e:
            logger.error(f"Errore nell'inizializzazione di Weaviate: {e}")
            raise
    
    def init_embeddings(self):
        """Inizializza il modello di embedding"""
        logger.info("Inizializzazione FastEmbed con modello BERTino italiano")
        
        try:
            # Importa le classi necessarie per il modello custom
            from fastembed import TextEmbedding
            from fastembed.common.model_description import PoolingType, ModelSource
            
            # Aggiunge il modello BERTino custom
            TextEmbedding.add_custom_model(
                model=self.embedding_config['custom_model'],
                pooling=PoolingType.MEAN,
                normalization=True,
                sources=ModelSource(hf=self.embedding_config['custom_model']),
                dim=768,
                model_file="onnx/model_qint8_avx512_vnni.onnx",
            )
            
            self.embeddings = FastEmbedEmbeddings(
                model_name=self.embedding_config['custom_model'],
                max_length=self.embedding_config['max_length'],
                cache_dir=self.embedding_config['cache_dir']
            )
            logger.info("FastEmbed BERTino inizializzato con successo")
            
        except Exception as e:
            logger.error(f"Errore nell'inizializzazione di BERTino: {e}")
            logger.info("Tentativo con modello di fallback...")
            
            # Fallback a modello supportato
            self.embeddings = FastEmbedEmbeddings(
                model_name=self.embedding_config['fallback_model'],
                max_length=self.embedding_config['max_length'],
                cache_dir=self.embedding_config['cache_dir']
            )
            logger.info("Modello di fallback inizializzato")
    
    def create_schema(self):
        """Crea lo schema Weaviate se non esiste"""
        if not self.weaviate_client:
            raise ValueError("Client Weaviate non inizializzato")
            
        try:
            # Controlla se la collezione esiste già
            if self.weaviate_client.collections.exists(self.index_name):
                logger.info(f"Collezione {self.index_name} già esistente")
                return
            
            # Crea la collezione con il nuovo schema v4
            self.weaviate_client.collections.create(
                name=self.index_name,
                description="Articoli di notizie per dominio specifico",
                vectorizer_config=weaviate.classes.config.Configure.Vectorizer.none(),
                properties=[
                    weaviate.classes.config.Property(
                        name="content",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Contenuto dell'articolo"
                    ),
                    weaviate.classes.config.Property(
                        name="title",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Titolo dell'articolo"
                    ),
                    weaviate.classes.config.Property(
                        name="url",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="URL dell'articolo"
                    ),
                    weaviate.classes.config.Property(
                        name="domain",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Dominio di appartenenza"
                    ),
                    weaviate.classes.config.Property(
                        name="published_date",
                        data_type=weaviate.classes.config.DataType.DATE,
                        description="Data di pubblicazione"
                    ),
                    weaviate.classes.config.Property(
                        name="keywords",
                        data_type=weaviate.classes.config.DataType.TEXT_ARRAY,
                        description="Parole chiave associate"
                    ),
                    weaviate.classes.config.Property(
                        name="source",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Fonte dell'articolo"
                    ),
                    weaviate.classes.config.Property(
                        name="content_hash",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Hash per deduplicazione"
                    )
                ]
            )
            logger.info(f"Collezione {self.index_name} creata")
                
        except Exception as e:
            logger.error(f"Errore nella creazione dello schema: {e}")
            raise
    
    def initialize_all(self):
        """Inizializza tutti i componenti del vector database"""
        self.init_weaviate_client()
        self.init_embeddings()
        logger.info(f"VectorDBManager completamente inizializzato per dominio '{self.domain or 'General'}' (index: {self.index_name})")
        
        return self.weaviate_client, self.embeddings
    
    # ========================================================================
    # METODI PER GESTIONE MULTI-DOMAIN
    # ========================================================================
    
    def create_domain_schema(self, domain_id: str):
        """
        Crea lo schema Weaviate per un dominio specifico
        
        Args:
            domain_id: ID del dominio
        """
        if not self.weaviate_client:
            raise ValueError("Client Weaviate non inizializzato")
            
        domain_index = self.domain_manager.get_weaviate_index(domain_id, self.environment)
        
        try:
            # Controlla se la collezione esiste già
            if self.weaviate_client.collections.exists(domain_index):
                logger.info(f"Collezione {domain_index} per dominio '{domain_id}' già esistente")
                return
            
            # Crea la collezione con il nuovo schema v4
            self.weaviate_client.collections.create(
                name=domain_index,
                description=f"Articoli di notizie per dominio {domain_id}",
                vectorizer_config=weaviate.classes.config.Configure.Vectorizer.none(),
                properties=[
                    weaviate.classes.config.Property(
                        name="content",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Contenuto dell'articolo"
                    ),
                    weaviate.classes.config.Property(
                        name="title",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Titolo dell'articolo"
                    ),
                    weaviate.classes.config.Property(
                        name="url",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="URL dell'articolo"
                    ),
                    weaviate.classes.config.Property(
                        name="domain",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Dominio di appartenenza"
                    ),
                    weaviate.classes.config.Property(
                        name="published_date",
                        data_type=weaviate.classes.config.DataType.DATE,
                        description="Data di pubblicazione"
                    ),
                    weaviate.classes.config.Property(
                        name="keywords",
                        data_type=weaviate.classes.config.DataType.TEXT_ARRAY,
                        description="Parole chiave associate"
                    ),
                    weaviate.classes.config.Property(
                        name="source",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Fonte dell'articolo"
                    ),
                    weaviate.classes.config.Property(
                        name="content_hash",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Hash per deduplicazione"
                    )
                ]
            )
            logger.info(f"Collezione {domain_index} per dominio '{domain_id}' creata")
                
        except Exception as e:
            logger.error(f"Errore nella creazione dello schema per dominio {domain_id}: {e}")
            raise
    
    def create_all_domain_schemas(self, active_only: bool = True):
        """
        Crea gli schemi Weaviate per tutti i domini configurati
        
        Args:
            active_only: Se True, crea schemi solo per domini attivi
        """
        if not self.weaviate_client:
            self.init_weaviate_client()
            
        domains = self.domain_manager.get_domain_list(active_only)
        created_count = 0
        
        for domain_id in domains:
            try:
                self.create_domain_schema(domain_id)
                created_count += 1
            except Exception as e:
                logger.error(f"Errore creazione schema per dominio {domain_id}: {e}")
                
        logger.info(f"Creati/Verificati {created_count} schemi domini su {len(domains)} totali")
    
    def get_domain_collection(self, domain_id: str):
        """
        Ottiene la collezione Weaviate per un dominio specifico
        
        Args:
            domain_id: ID del dominio
            
        Returns:
            Collezione Weaviate
        """
        if not self.weaviate_client:
            raise ValueError("Client Weaviate non inizializzato")
            
        domain_index = self.domain_manager.get_weaviate_index(domain_id, self.environment)
        
        # Crea schema se non esiste
        if not self.weaviate_client.collections.exists(domain_index):
            self.create_domain_schema(domain_id)
            
        return self.weaviate_client.collections.get(domain_index)
    
    def list_domain_collections(self) -> Dict[str, str]:
        """
        Lista tutte le collezioni Weaviate esistenti per domini
        
        Returns:
            Dizionario {domain_id: collection_name} per domini riconosciuti
        """
        if not self.weaviate_client:
            raise ValueError("Client Weaviate non inizializzato")
            
        try:
            all_collections = self.weaviate_client.collections.list_all()
            domain_collections = {}
            
            for collection_name in all_collections.keys():
                if collection_name.startswith('Tanea_'):
                    domain_id = self.domain_manager.get_domain_by_index(collection_name)
                    if domain_id:
                        domain_collections[domain_id] = collection_name
                        
            return domain_collections
            
        except Exception as e:
            logger.error(f"Errore nel listing delle collezioni domini: {e}")
            return {}
    
    def delete_domain_collection(self, domain_id: str, confirm: bool = False):
        """
        Elimina la collezione Weaviate per un dominio (ATTENZIONE: operazione irreversibile!)
        
        Args:
            domain_id: ID del dominio
            confirm: Deve essere True per confermare l'eliminazione
        """
        if not confirm:
            logger.error("Eliminazione collezione richiede confirm=True")
            return False
            
        if not self.weaviate_client:
            raise ValueError("Client Weaviate non inizializzato")
            
        domain_index = self.domain_manager.get_weaviate_index(domain_id, self.environment)
        
        try:
            if self.weaviate_client.collections.exists(domain_index):
                self.weaviate_client.collections.delete(domain_index)
                logger.warning(f"Collezione {domain_index} per dominio '{domain_id}' ELIMINATA")
                return True
            else:
                logger.info(f"Collezione {domain_index} per dominio '{domain_id}' non esiste")
                return False
                
        except Exception as e:
            logger.error(f"Errore nell'eliminazione collezione per dominio {domain_id}: {e}")
            return False