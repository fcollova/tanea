#!/bin/bash

# Script per fermare solo Weaviate Vector DB

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
echo "       Weaviate Vector DB Shutdown         "
echo "============================================="
echo -e "${NC}"

# Ferma Weaviate e rimuove i container
print_status "Fermando Weaviate database..."
docker-compose down

print_success "Weaviate Vector DB fermato completamente"