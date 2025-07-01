#!/bin/bash

# Script per avviare il News Vector DB System
# Gestisce virtual environment, dipendenze e servizi

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
echo "      News Vector DB System Startup        "
echo "============================================="
echo -e "${NC}"

# Controlla se Docker è installato
if ! command -v docker &> /dev/null; then
    print_error "Docker non è installato. Installalo prima di continuare."
    exit 1
fi

# Controlla se Docker Compose è installato
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose non è installato. Installalo prima di continuare."
    exit 1
fi

# Controlla se Python è installato
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 non è installato. Installalo prima di continuare."
    exit 1
fi

print_status "Controlli preliminari completati"

# 1. Crea virtual environment se non esiste
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    print_status "Creazione virtual environment..."
    python3 -m venv $VENV_DIR
    print_success "Virtual environment creato"
else
    print_status "Virtual environment già esistente"
fi

# 2. Attiva virtual environment
print_status "Attivazione virtual environment..."
source $VENV_DIR/bin/activate
print_success "Virtual environment attivato"

# 3. Aggiorna pip
print_status "Aggiornamento pip..."
pip install --upgrade pip > /dev/null 2>&1

# 4. Installa dipendenze
print_status "Installazione dipendenze Python..."
if [ -f "requirement.txt" ]; then
    pip install -r requirement.txt
    print_success "Dipendenze installate"
else
    print_error "File requirement.txt non trovato"
    exit 1
fi

# 5. Controlla file .env
if [ ! -f ".env" ]; then
    print_warning "File .env non trovato. Creazione template..."
    cat > .env << 'EOF'
# Configurazione News Vector DB
WEAVIATE_URL=http://localhost:8080
TAVILY_API_KEY=your-tavily-api-key-here
EMBEDDING_MODEL=nickprock/multi-sentence-BERTino

# Opzionale: per istanze Weaviate remote
# WEAVIATE_API_KEY=your-weaviate-api-key
EOF
    print_warning "File .env creato. CONFIGURA TAVILY_API_KEY prima di continuare!"
    print_warning "Modifica il file .env con la tua API key di Tavily"
    
    # Chiedi se continuare
    read -p "Vuoi continuare senza configurare l'API key? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Configurazione interrotta. Modifica .env e riavvia lo script."
        exit 1
    fi
fi

# 6. Avvia Weaviate
print_status "Avvio Weaviate database..."
if docker-compose ps | grep -q "weaviate.*Up"; then
    print_success "Weaviate già in esecuzione"
else
    docker-compose up -d
    print_success "Weaviate avviato"
fi

# 7. Attendi che Weaviate sia pronto
print_status "Attesa che Weaviate sia pronto..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:8080/v1/meta > /dev/null 2>&1; then
        print_success "Weaviate è pronto"
        break
    fi
    attempt=$((attempt + 1))
    echo -n "."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    print_error "Timeout: Weaviate non è pronto dopo 60 secondi"
    exit 1
fi

# 8. Controlla se è il primo avvio (scarica modello)
print_status "Controllo modello di embedding..."
if [ ! -d "./fastembed_cache" ]; then
    print_warning "Primo avvio: download del modello FastEmbed (~150MB)"
    print_status "Questo potrebbe richiedere alcuni minuti..."
fi

# 9. Funzione per gestire l'arresto
cleanup() {
    print_status "Arresto applicazione in corso..."
    print_warning "Weaviate container rimane in esecuzione"
    print_status "Per fermarlo manualmente: docker-compose down"
    exit 0
}

# Intercetta CTRL+C
trap cleanup SIGINT SIGTERM

# 10. Avvia l'applicazione
print_success "Tutto pronto! Avvio dell'applicazione..."
echo -e "${GREEN}"
echo "============================================="
echo "      Sistema avviato con successo!        "
echo "============================================="
echo -e "${NC}"

print_status "Per fermare solo l'applicazione, premi CTRL+C"
print_status "Weaviate rimarrà in esecuzione in background"
print_status "Logs dell'applicazione:"
echo

# Avvia l'applicazione
python example_usage.py

# Se arriviamo qui, l'applicazione è terminata normalmente
print_success "Applicazione terminata"
print_status "Weaviate rimane in esecuzione per uso futuro"
print_status "Per fermarlo: docker-compose down"