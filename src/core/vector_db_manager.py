import os
from typing import Optional

import weaviate
from langchain_community.embeddings import FastEmbedEmbeddings

from .config import get_weaviate_config, get_embedding_config
from .log import get_database_logger

logger = get_database_logger(__name__)

class VectorDBManager:
    """
    Classe per gestire la creazione e configurazione del Vector Database
    """
    
    def __init__(self, environment: str = None):
        # Ottieni configurazioni
        weaviate_config = get_weaviate_config()
        embedding_config = get_embedding_config()
        
        self.weaviate_url = weaviate_config['url']
        self.weaviate_api_key = weaviate_config['api_key']
        self.index_name = weaviate_config['index_name']
        self.embedding_model = embedding_config['model_name']
        self.embedding_config = embedding_config
        
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
        logger.info("VectorDBManager completamente inizializzato")
        
        return self.weaviate_client, self.embeddings