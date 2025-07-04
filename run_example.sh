#!/bin/bash

# Script per eseguire l'esempio del News Vector DB System
# Presuppone che l'installazione sia già stata completata

set -e  # Esci in caso di errore

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funzione per stampare messaggi colorati
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
echo -e "${BLUE}"
echo "============================================="
echo "      News Vector DB Example Runner        "
echo "============================================="
echo -e "${NC}"

# Verifica se l'installazione è stata completata
if [ ! -d "venv" ]; then
    print_error "Virtual environment non trovato!"
    print_status "Esegui prima l'installazione: ./install.sh"
    exit 1
fi

if [ ! -f "requirements.txt" ]; then
    print_error "Sistema non installato correttamente!"
    print_status "Esegui prima l'installazione: ./install.sh"
    exit 1
fi

# Controlla se Weaviate è in esecuzione
print_status "Controllo stato Weaviate..."
if ! curl -s http://localhost:8080/v1/meta > /dev/null 2>&1; then
    print_error "Weaviate non è in esecuzione!"
    print_status "Avvialo prima con: ./start.sh"
    print_status "Oppure avvia Docker e poi: ./start.sh"
    exit 1
fi
print_success "Weaviate è attivo e raggiungibile"

# Attiva virtual environment
print_status "Attivazione virtual environment..."
source venv/bin/activate
print_success "Virtual environment attivato"

# Controlla dipendenze critiche
print_status "Verifica dipendenze critiche..."
python3 -c "import trafilatura" 2>/dev/null || {
    print_error "Trafilatura non installato!"
    print_status "Esegui: ./install.sh per completare l'installazione"
    exit 1
}

python3 -c "import weaviate" 2>/dev/null || {
    print_error "Weaviate client non installato!"
    print_status "Esegui: ./install.sh per completare l'installazione"
    exit 1
}

print_success "Dipendenze verificate"

# Controlla file .env
if [ ! -f ".env" ]; then
    print_warning "File .env non trovato!"
    print_status "Creazione .env di default..."
    cp .env.example .env 2>/dev/null || {
        print_warning "Alcune funzionalità potrebbero non essere disponibili"
        print_status "Esegui ./install.sh per creare la configurazione completa"
    }
fi

# Controlla se è il primo avvio (scarica modello)
if [ ! -d "fastembed_cache" ]; then
    print_warning "Primo avvio: download del modello FastEmbed (~150MB)"
    print_status "Questo potrebbe richiedere alcuni minuti..."
    print_status "Il modello verrà scaricato automaticamente durante l'esecuzione"
fi

# Funzione per gestire l'arresto
cleanup() {
    print_status "Arresto applicazione in corso..."
    print_status "Weaviate rimane in esecuzione per uso futuro"
    print_status "Per fermarlo: ./stop.sh"
    exit 0
}

# Intercetta CTRL+C
trap cleanup SIGINT SIGTERM

# Mostra informazioni sistema
print_status "Informazioni sistema:"
print_status "  • Python: $(python3 --version)"
print_status "  • Virtual environment: attivo"
print_status "  • Weaviate: http://localhost:8080"
print_status "  • Logs: directory logs/"

# Verifica stato fonti di notizie
print_status "Verifica fonti di notizie disponibili..."
python3 -c "
import sys
import os
sys.path.append('src')

try:
    from core.news_sources import create_default_news_manager
    manager = create_default_news_manager()
    sources = manager.get_available_sources()
    print(f'✅ Fonti disponibili: {len(sources)}')
    for source in sources[:3]:  # Mostra prime 3
        print(f'   • {source}')
    if len(sources) > 3:
        print(f'   • ... e altre {len(sources)-3}')
except Exception as e:
    print(f'⚠️  Errore verifica fonti: {e}')
" 2>/dev/null

echo
print_success "Tutto pronto! Avvio dell'applicazione di esempio..."
echo -e "${GREEN}"
echo "============================================="
echo "      Applicazione avviata con successo!   "
echo "============================================="
echo -e "${NC}"

print_status "COMANDI UTILI DURANTE L'ESECUZIONE:"
print_status "  • CTRL+C: Ferma l'applicazione"
print_status "  • Logs: tail -f logs/tanea_dev.log"
print_status "  • Stato Weaviate: curl http://localhost:8080/v1/meta"
echo

print_status "Per fermare l'applicazione, premi CTRL+C"
print_status "Weaviate rimarrà in esecuzione in background"
print_status "Logs dell'applicazione:"
echo

# Avvia l'applicazione
python src/scripts/example_usage.py

# Se arriviamo qui, l'applicazione è terminata normalmente
print_success "Applicazione terminata correttamente"
print_status "Weaviate rimane in esecuzione per uso futuro"
print_status "Per fermarlo: ./stop.sh"
print_status "Per riavviare: ./run_example.sh"