#!/bin/bash
# Database Cleaner - Tanea News System
# Script di convenienza per pulire i database

set -e

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧹 Tanea Database Cleaner${NC}"
echo "=================================="

# Verifica se il virtual environment esiste
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment non trovato${NC}"
    echo "Esegui prima: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Attiva virtual environment
echo -e "${YELLOW}🐍 Attivazione virtual environment...${NC}"
source venv/bin/activate

# Menu di scelta
echo -e "${PURPLE}Seleziona un'opzione:${NC}"
echo "1. 🔍 Verifica stato database"
echo "2. 🧹 Menu completo (interattivo)"  
echo "3. 🚀 Reset rapido completo"
echo "4. 📋 Lista collezioni Weaviate"
echo "5. 🗑️  Elimina collezione specifica"
echo "0. ❌ Annulla"
echo ""

read -p "Opzione (0-5): " choice

case $choice in
    1)
        echo -e "${BLUE}🔍 Verifica stato database...${NC}"
        cd "$PWD" && python3 scripts/clean_databases.py <<< "1"
        ;;
    2)
        echo -e "${BLUE}🧹 Apertura menu completo...${NC}"
        python3 scripts/clean_databases.py
        ;;
    3)
        echo -e "${RED}⚠️  ATTENZIONE: Reset completo dei database!${NC}"
        echo "Questa operazione cancellerà TUTTI i dati esistenti."
        echo -e "${YELLOW}I database saranno riportati allo stato iniziale clean.${NC}"
        echo ""
        read -p "Sei sicuro? (scrivi 'RESET' per confermare): " confirm
        
        if [ "$confirm" = "RESET" ]; then
            echo -e "${GREEN}🚀 Esecuzione reset completo...${NC}"
            python3 scripts/quick_reset.py
        else
            echo -e "${RED}❌ Reset annullato${NC}"
        fi
        ;;
    4)
        echo -e "${BLUE}📋 Lista collezioni Weaviate...${NC}"
        python3 scripts/list_collections.py
        ;;
    5)
        echo -e "${YELLOW}🗑️  Eliminazione collezione specifica...${NC}"
        python3 scripts/delete_collection.py
        ;;
    0)
        echo -e "${RED}❌ Operazione annullata${NC}"
        ;;
    *)
        echo -e "${RED}❌ Opzione non valida${NC}"
        exit 1
        ;;
esac

echo -e "${GREEN}✅ Operazione completata${NC}"