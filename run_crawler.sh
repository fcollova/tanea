#!/bin/bash
# Crawler Runner Script
# Esegue il crawler Trafilatura con configurazione unificata

set -e

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🕷️ Tanea Crawler Runner${NC}"
echo "================================"

# Verifica se il virtual environment esiste
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment non trovato${NC}"
    echo "Esegui prima: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Attiva virtual environment
echo -e "${YELLOW}🐍 Attivazione virtual environment...${NC}"
source venv/bin/activate

# Verifica se le dipendenze sono installate
if ! python -c "import trafilatura" &> /dev/null; then
    echo -e "${YELLOW}📦 Installazione dipendenze...${NC}"
    pip install -r requirements.txt
else
    echo -e "${GREEN}✅ Dipendenze già installate${NC}"
fi

# Imposta variabile DATABASE_URL da configurazione
echo -e "${YELLOW}⚙️ Configurazione database...${NC}"
DATABASE_URL=$(python -c "
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from core.config import get_database_config
config = get_database_config()
print(config.get('url', ''))
")
export DATABASE_URL

# Esegui il crawler dalla directory root per evitare cache duplicate
echo -e "${YELLOW}🚀 Esecuzione crawler...${NC}"
python src/crawler/crawler_exec.py "$@"

echo -e "${GREEN}✅ Crawler terminato${NC}"