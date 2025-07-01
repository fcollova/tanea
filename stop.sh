#!/bin/bash

# Script per fermare il News Vector DB System

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

echo -e "${RED}"
echo "============================================="
echo "      News Vector DB System Shutdown       "
echo "============================================="
echo -e "${NC}"

# Ferma Weaviate e rimuove i container
print_status "Fermando Weaviate database..."
docker-compose down

# Disattiva virtual environment se attivo
if [[ "$VIRTUAL_ENV" != "" ]]; then
    print_status "Disattivazione virtual environment..."
    deactivate 2>/dev/null || true
fi

print_success "Sistema fermato completamente"