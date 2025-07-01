# config.py
"""
File di configurazione per il News Vector DB
"""

import os
from typing import List
from dotenv import load_dotenv
from news_vector_db import NewsConfig

# Carica le variabili d'ambiente dal file .env
load_dotenv()

# Configurazioni API
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")  # Opzionale per istanze locali
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")  # Richiesto

# Configurazione embeddings
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")

# Configurazioni domini di notizie
NEWS_DOMAINS = [
    # NewsConfig(
    #     domain="tecnologia",
    #     keywords=[
    #         "intelligenza artificiale", "AI", "machine learning", 
    #         "deep learning", "ChatGPT", "automazione", "robotica",
    #         "startup tecnologiche", "innovazione digitale"
    #     ],
    #     max_results=20,
    #     time_range="1d",
    #     language="it"
    # ),
    
    # NewsConfig(
    #     domain="finanza",
    #     keywords=[
    #         "borsa italiana", "FTSE MIB", "investimenti", 
    #         "economia italiana", "BCE", "inflazione", 
    #         "mercati finanziari", "criptovalute", "Bitcoin"
    #     ],
    #     max_results=15,
    #     time_range="1d",
    #     language="it"
    # ),
    
    # NewsConfig(
    #     domain="salute",
    #     keywords=[
    #         "medicina", "ricerca medica", "farmaci", 
    #         "vaccini", "salute pubblica", "COVID-19",
    #         "telemedicina", "biotecnologie"
    #     ],
    #     max_results=12,
    #     time_range="1d",
    #     language="it"
    # ),
    
    # NewsConfig(
    #     domain="ambiente",
    #     keywords=[
    #         "cambiamenti climatici", "sostenibilità", 
    #         "energie rinnovabili", "ambiente", "ecologia",
    #         "riscaldamento globale", "green economy"
    #     ],
    #     max_results=10,
    #     time_range="1d",
    #     language="it"
    # ),
    
    NewsConfig(
        domain="calcio",
        keywords=[
            "Serie A", "calcio italiano", "Juventus", "Inter", 
            "Milan", "Napoli", "Roma", "Lazio", "Atalanta",
            "Fiorentina", "campionato italiano", "classifica Serie A",
            "calciomercato", "risultati Serie A", "gol", "partite",
            "allenatori Serie A", "Champions League italiana",
            "Europa League italiana", "Coppa Italia"
        ],
        max_results=25,
        time_range="1d",
        language="it"
    )
]

# Configurazioni sistema
VECTOR_DB_CONFIG = {
    "index_name": "NewsArticles_IT",
    "update_time": "08:00",  # Ora aggiornamento giornaliero
    "cleanup_days": 30,      # Giorni dopo cui eliminare vecchi articoli
    "max_context_length": 4000,  # Lunghezza massima contesto
    "similarity_search_k": 5      # Numero documenti da recuperare
}