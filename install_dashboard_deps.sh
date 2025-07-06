#!/bin/bash

# Install Dashboard Dependencies
# Installa solo le dipendenze per la dashboard Streamlit

set -e

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📦 Installazione Dipendenze Dashboard${NC}"
echo "====================================="

# Attiva virtual environment se esiste
if [ -d "venv" ]; then
    echo -e "${YELLOW}🐍 Attivazione virtual environment...${NC}"
    source venv/bin/activate
    echo -e "${GREEN}✅ Virtual environment attivato${NC}"
else
    echo -e "${YELLOW}⚠️  Nessun virtual environment trovato${NC}"
    echo -e "${BLUE}💡 Creazione virtual environment consigliata:${NC}"
    echo -e "   ${YELLOW}python3 -m venv venv${NC}"
    echo -e "   ${YELLOW}source venv/bin/activate${NC}"
    echo ""
fi

# Verifica requirements.txt
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ File requirements.txt non trovato${NC}"
    exit 1
fi

# Installa dipendenze
echo -e "${YELLOW}📦 Installazione dipendenze da requirements.txt...${NC}"
pip install -r requirements.txt

# Verifica installazione delle dipendenze principali
echo -e "${YELLOW}🔍 Verifica installazione...${NC}"

dependencies=(
    "streamlit"
    "plotly" 
    "pandas"
    "numpy"
    "weaviate"
    "matplotlib"
    "seaborn"
    "wordcloud"
)

all_installed=true

for dep in "${dependencies[@]}"; do
    if python3 -c "import $dep" &> /dev/null; then
        echo -e "${GREEN}✅ $dep${NC}"
    else
        echo -e "${RED}❌ $dep${NC}"
        all_installed=false
    fi
done

echo ""
if [ "$all_installed" = true ]; then
    echo -e "${GREEN}🎉 Tutte le dipendenze installate correttamente!${NC}"
    echo ""
    echo -e "${BLUE}🚀 Ora puoi avviare la dashboard:${NC}"
    echo -e "   ${YELLOW}./start_weaviate_explorer.sh${NC}"
else
    echo -e "${RED}❌ Alcune dipendenze non sono state installate correttamente${NC}"
    echo -e "${YELLOW}💡 Prova a reinstallare:${NC}"
    echo -e "   ${YELLOW}pip install -r requirements.txt --force-reinstall${NC}"
fi

echo ""