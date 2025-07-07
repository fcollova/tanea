#!/bin/bash

# Start Weaviate Explorer Dashboard
# Avvia Weaviate + Streamlit Dashboard per esplorare il database

set -e

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Avvio Weaviate Explorer Dashboard${NC}"
echo "======================================="

# Verifica se docker-compose è disponibile
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ docker-compose non trovato${NC}"
    exit 1
fi

# Verifica se il file docker-compose.yml esiste
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ File docker-compose.yml non trovato${NC}"
    exit 1
fi

# Attiva virtual environment se esiste
if [ -d "venv" ]; then
    echo -e "${YELLOW}🐍 Attivazione virtual environment...${NC}"
    source venv/bin/activate
fi

# Verifica e installa dipendenze Python
if ! python3 -c "import streamlit" &> /dev/null; then
    echo -e "${YELLOW}📦 Installazione dipendenze da requirements.txt...${NC}"
    pip install -r requirements.txt
else
    echo -e "${GREEN}✅ Dipendenze già installate${NC}"
fi

echo -e "${YELLOW}📦 Avvio Weaviate...${NC}"

# Avvia solo Weaviate (pulisce eventuali container orfani)
docker-compose up -d weaviate --remove-orphans

# Attendi che Weaviate sia pronto
echo -e "${YELLOW}⏳ Attendo che Weaviate sia pronto...${NC}"
sleep 10

# Verifica stato Weaviate
if docker-compose ps | grep "weaviate" | grep -q "Up"; then
    echo -e "${GREEN}✅ Weaviate avviato correttamente${NC}"
else
    echo -e "${RED}❌ Problema con Weaviate${NC}"
    exit 1
fi

# Avvia Streamlit in background
echo -e "${YELLOW}🚀 Avvio Streamlit Dashboard...${NC}"
cd src/weaviate_navigator

# Verifica se Streamlit è già in esecuzione
if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Streamlit già in esecuzione su porta 8501${NC}"
    echo -e "${BLUE}🔗 Dashboard già disponibile: ${YELLOW}http://localhost:8501${NC}"
else
    # Attiva venv anche qui se necessario
    if [ -d "../../venv" ]; then
        source ../../venv/bin/activate
    fi
    
    # Avvia Streamlit con output su file di log
    echo -e "${YELLOW}📝 Log Streamlit: ../../logs/streamlit.log${NC}"
    nohup streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true > ../../logs/streamlit.log 2>&1 &
    STREAMLIT_PID=$!
    
    # Attendi che Streamlit sia pronto
    echo -e "${YELLOW}⏳ Attendo che Streamlit sia pronto...${NC}"
    sleep 8
    
    # Verifica se Streamlit è attivo
    if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null 2>/dev/null; then
        echo -e "${GREEN}✅ Streamlit Dashboard avviato correttamente${NC}"
    else
        echo -e "${RED}❌ Problema con Streamlit Dashboard${NC}"
        echo -e "${YELLOW}📋 Controllare ../../logs/streamlit.log per dettagli${NC}"
        exit 1
    fi
fi

cd ../..

echo ""
echo -e "${GREEN}🎉 Weaviate Explorer Dashboard pronto!${NC}"
echo ""
echo -e "${BLUE}📊 Accesso Dashboard:${NC}"
echo -e "   🔗 Streamlit Dashboard: ${YELLOW}http://localhost:8501${NC}"
echo -e "   📊 Explorer Semantico: ${YELLOW}http://localhost:8501/🔍_Explorer${NC}"
echo -e "   📈 Analytics Avanzate: ${YELLOW}http://localhost:8501/📈_Analytics${NC}"
echo ""
echo -e "${BLUE}🔧 Servizi Disponibili:${NC}"
echo -e "   📊 Weaviate Database: ${YELLOW}http://localhost:8080${NC}"
echo -e "   🖥️  Streamlit Dashboard: ${YELLOW}http://localhost:8501${NC}"
echo ""
echo -e "${BLUE}✨ Features Dashboard:${NC}"
echo -e "   🏠 Home: Panoramica generale e statistiche"
echo -e "   🔍 Explorer: Ricerca semantica avanzata"
echo -e "   📈 Analytics: Visualizzazioni e analisi"
echo ""
echo -e "${BLUE}🛑 Per fermare i servizi:${NC}"
echo -e "   ${YELLOW}docker-compose down${NC}"
echo -e "   ${YELLOW}pkill -f streamlit${NC} (per fermare Streamlit)"
echo ""
echo -e "${GREEN}Buona esplorazione! 🚀${NC}"