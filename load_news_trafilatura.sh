#!/bin/bash
# ============================================================================
# load_news_trafilatura.sh
# Script per caricare notizie usando solo Trafilatura (AI-powered web scraping)
# ============================================================================

echo "🚀 News Loader - Solo Trafilatura (AI-powered scraping)"
echo "======================================================="

# Cambia nella directory dello script
cd "$(dirname "$0")"

# Attiva l'ambiente virtuale se esiste
if [ -d "venv" ]; then
    echo "📦 Attivazione ambiente virtuale..."
    source venv/bin/activate
fi

# Verifica che trafilatura sia installato
python3 -c "import trafilatura" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Trafilatura non installato!"
    echo "   Installa con: pip install trafilatura"
    exit 1
fi

echo "✅ Trafilatura disponibile"
echo ""

# Passa tutti gli argomenti al comando Python
python3 src/scripts/load_news.py --trafilatura "$@"

# Controlla il risultato
if [ $? -eq 0 ]; then
    echo ""
    echo "🎊 Caricamento con Trafilatura completato con successo!"
    echo "   Le notizie sono state estratte usando tecnologia AI-powered"
    echo "   per una maggiore accuratezza e robustezza."
else
    echo ""
    echo "❌ Errore durante il caricamento con Trafilatura"
    exit 1
fi