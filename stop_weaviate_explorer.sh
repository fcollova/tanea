#!/bin/bash

# Stop Weaviate Explorer Dashboard
# Ferma Weaviate e Streamlit Dashboard

set -e

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 Fermata Weaviate Explorer Dashboard${NC}"
echo "======================================="

# Ferma Streamlit se in esecuzione
echo -e "${YELLOW}🔄 Fermata Streamlit Dashboard...${NC}"
if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null ; then
    pkill -f "streamlit run" || true
    echo -e "${GREEN}✅ Streamlit fermato${NC}"
else
    echo -e "${BLUE}ℹ️  Streamlit non era in esecuzione${NC}"
fi

# Ferma Weaviate
echo -e "${YELLOW}🔄 Fermata Weaviate...${NC}"
if docker-compose ps | grep -q "weaviate"; then
    docker-compose down --remove-orphans
    echo -e "${GREEN}✅ Weaviate fermato${NC}"
else
    echo -e "${BLUE}ℹ️  Weaviate non era in esecuzione${NC}"
fi

# Pulizia finale
echo -e "${YELLOW}🧹 Pulizia container orfani...${NC}"
docker system prune -f --filter "label=com.docker.compose.project=tanea" > /dev/null 2>&1 || true

echo ""
echo -e "${GREEN}✅ Tutti i servizi sono stati fermati correttamente!${NC}"
echo ""
echo -e "${BLUE}📊 Per riavviare:${NC}"
echo -e "   ${YELLOW}./start_weaviate_explorer.sh${NC}"
echo ""