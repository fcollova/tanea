#!/bin/bash

# Script per avviare Weaviate Explorer
# Utilizza Streamlit per eseguire weviate_explorer.py

echo "🔍 Avvio Weaviate Explorer..."

# Attiva virtual environment se esiste
VENV_DIR="venv"
if [ -d "$VENV_DIR" ]; then
    echo "📦 Attivazione virtual environment..."
    source $VENV_DIR/bin/activate
fi

# Verifica che il file Python esista
if [ ! -f "weviate_explorer.py" ]; then
    echo "❌ Errore: File weviate_explorer.py non trovato"
    exit 1
fi

# Verifica che streamlit sia installato
if ! command -v streamlit &> /dev/null; then
    echo "❌ Errore: Streamlit non installato"
    echo "💡 Installa le dipendenze con: pip install -r requirements.txt"
    exit 1
fi

# Avvia Streamlit
streamlit run weviate_explorer.py --server.port 8501 --server.address 0.0.0.0

echo "✅ Weaviate Explorer terminato"