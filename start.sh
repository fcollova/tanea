#!/bin/bash

# Script per avviare solo Weaviate Vector DB
# Per gestire l'ambiente Python e eseguire l'app, usa run_example.sh

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
echo "        Weaviate Vector DB Startup          "
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

print_status "Controlli preliminari completati"

# Avvia Weaviate
print_status "Avvio Weaviate database..."
if docker-compose ps | grep -q "weaviate.*Up"; then
    print_success "Weaviate già in esecuzione"
else
    docker-compose up -d
    print_success "Weaviate avviato"
fi

# Attendi che Weaviate sia pronto
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

print_success "Weaviate Vector DB avviato con successo!"
echo -e "${GREEN}"
echo "============================================="
echo "         Weaviate è pronto per l'uso        "
echo "============================================="
echo -e "${NC}"

print_status "URL Weaviate: http://localhost:8080"
print_status "Per fermare Weaviate: ./stop.sh"
print_status "Per eseguire l'esempio: ./run_example.sh"
print_status "Per caricare notizie: ./load_news_scraping.sh"