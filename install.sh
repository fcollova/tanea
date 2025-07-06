#!/bin/bash

# Script per l'installazione del News Vector DB System
# Gestisce virtual environment, dipendenze e configurazione iniziale

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
echo "      News Vector DB System - Installer    "
echo "============================================="
echo -e "${NC}"

print_status "Avvio installazione sistema News Vector DB..."

# Controlla se Python è installato
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 non è installato. Installalo prima di continuare."
    print_status "Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip python3-venv"
    print_status "CentOS/RHEL: sudo yum install python3 python3-pip"
    print_status "macOS: brew install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
print_success "Python ${PYTHON_VERSION} trovato"

# Controlla se Docker è installato
if ! command -v docker &> /dev/null; then
    print_warning "Docker non è installato. È necessario per Weaviate."
    print_status "Installa Docker da: https://docs.docker.com/get-docker/"
    print_status "Oppure:"
    print_status "Ubuntu: sudo apt install docker.io docker-compose"
    print_status "CentOS: sudo yum install docker docker-compose"
    print_status "macOS: Installa Docker Desktop"
    
    read -p "Vuoi continuare senza Docker? (l'esempio non funzionerà) (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Installazione interrotta. Installa Docker e riavvia."
        exit 1
    fi
else
    print_success "Docker trovato"
fi

# 1. Crea virtual environment
VENV_DIR="venv"
if [ -d "$VENV_DIR" ]; then
    print_warning "Virtual environment già esistente. Rimuovere e ricreare? (y/N)"
    read -p "" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Rimozione virtual environment esistente..."
        rm -rf $VENV_DIR
    else
        print_status "Utilizzo virtual environment esistente"
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    print_status "Creazione virtual environment..."
    python3 -m venv $VENV_DIR
    print_success "Virtual environment creato in '$VENV_DIR'"
fi

# 2. Attiva virtual environment
print_status "Attivazione virtual environment..."
source $VENV_DIR/bin/activate
print_success "Virtual environment attivato"

# 3. Aggiorna pip
print_status "Aggiornamento pip..."
pip install --upgrade pip > /dev/null 2>&1
print_success "Pip aggiornato"

# 4. Installa dipendenze
print_status "Installazione dipendenze Python..."
if [ -f "requirements.txt" ]; then
    print_status "Installazione da requirements.txt (questo può richiedere alcuni minuti)..."
    
    # Installa le dipendenze principali
    pip install -r requirements.txt
    
    print_success "Dipendenze Python installate"
    
    # Verifica dipendenze critiche
    print_status "Verifica installazione dipendenze critiche..."
    
    python3 -c "import trafilatura; print('✅ Trafilatura:', trafilatura.__version__)" 2>/dev/null || print_warning "❌ Trafilatura non installata correttamente"
    python3 -c "import weaviate; print('✅ Weaviate client installato')" 2>/dev/null || print_warning "❌ Weaviate client non installato"
    python3 -c "import feedparser; print('✅ Feedparser installato')" 2>/dev/null || print_warning "❌ Feedparser non installato"
    python3 -c "import bs4; print('✅ BeautifulSoup installato')" 2>/dev/null || print_warning "❌ BeautifulSoup non installato"
    python3 -c "import yaml; print('✅ PyYAML installato')" 2>/dev/null || print_warning "❌ PyYAML non installato"
    python3 -c "import prisma; print('✅ Prisma installato')" 2>/dev/null || print_warning "❌ Prisma non installato"
    
else
    print_error "File requirements.txt non trovato"
    exit 1
fi

# 4.5. Setup Prisma
print_status "Setup Prisma ORM..."
if [ -f "prisma/schema.prisma" ]; then
    print_status "Generazione client Prisma..."
    if prisma generate > /dev/null 2>&1; then
        print_success "✅ Prisma client generato"
    else
        print_error "❌ Errore nella generazione del client Prisma"
        print_status "Verifica che il file prisma/schema.prisma sia corretto"
        exit 1
    fi
    
    print_status "Setup database PostgreSQL..."
    
    # Verifica se PostgreSQL è installato
    if command -v psql &> /dev/null; then
        print_success "PostgreSQL trovato"
        
        # Verifica se PostgreSQL è in esecuzione
        if sudo systemctl is-active --quiet postgresql 2>/dev/null || sudo service postgresql status >/dev/null 2>&1; then
            print_success "PostgreSQL è in esecuzione"
            
            # Crea utente e database se non esistono
            print_status "Creazione utente e database PostgreSQL..."
            
            # Crea utente tanea_user se non esiste
            sudo -u postgres psql -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'tanea_user') THEN CREATE USER tanea_user WITH PASSWORD 'tanea_secure_2024!' CREATEDB; END IF; END \$\$;" 2>/dev/null || true
            
            # Crea database tanea_news se non esiste
            sudo -u postgres psql -c "CREATE DATABASE tanea_news OWNER tanea_user;" 2>/dev/null || true
            
            # Assegna privilegi
            sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE tanea_news TO tanea_user;" 2>/dev/null || true
            
            print_success "Database PostgreSQL configurato"
            
            # Ora esegui prisma db push
            print_status "Esecuzione Prisma DB push..."
            if prisma db push > /dev/null 2>&1; then
                print_success "✅ Schema database creato"
            else
                print_warning "❌ Errore creazione schema - eseguire manualmente: prisma db push"
            fi
            
        else
            print_warning "PostgreSQL non è in esecuzione"
            print_status "Avvia PostgreSQL con: sudo systemctl start postgresql"
            print_status "Poi esegui manualmente:"
            print_status "  sudo -u postgres psql -c \"CREATE USER tanea_user WITH PASSWORD 'tanea_secure_2024!' CREATEDB;\""
            print_status "  sudo -u postgres psql -c \"CREATE DATABASE tanea_news OWNER tanea_user;\""
            print_status "  prisma db push"
        fi
    else
        print_warning "PostgreSQL non installato"
        print_status "Installa PostgreSQL:"
        print_status "  Ubuntu/Debian: sudo apt install postgresql postgresql-contrib"
        print_status "  CentOS/RHEL: sudo yum install postgresql-server postgresql-contrib"
        print_status "  macOS: brew install postgresql"
    fi
else
    print_warning "❌ File prisma/schema.prisma non trovato"
    print_status "Prisma non verrà configurato"
fi

# 5. Crea file .env se non esiste
if [ ! -f ".env" ]; then
    print_status "Creazione file configurazione .env..."
    cat > .env << 'EOF'
# ============================================================================
# News Vector DB System - Configurazione
# ============================================================================

# === WEAVIATE DATABASE ===
WEAVIATE_URL=http://localhost:8080
# WEAVIATE_API_KEY=your-weaviate-api-key  # Solo per istanze remote

# === API KEYS ===
# API key per Tavily (ricerca notizie via API)
TAVILY_API_KEY=your-tavily-api-key-here

# API key per NewsAPI (opzionale)
# NEWSAPI_API_KEY=your-newsapi-key-here

# === EMBEDDING MODEL ===
# Modello per generazione embeddings (italiano)
EMBEDDING_MODEL=nickprock/multi-sentence-BERTino

# === LOGGING ===
LOG_LEVEL=INFO
LOG_TO_FILE=true

# === NEWS SOURCES ===
# Abilitazione fonti (true/false)
ENABLE_RSS=true
ENABLE_NEWSAPI=false
ENABLE_SCRAPING=true
ENABLE_TRAFILATURA=true
ENABLE_TAVILY=false

# === PERFORMANCE ===
MAX_ARTICLES_PER_DOMAIN=25
EMBEDDING_BATCH_SIZE=10
EOF
    print_success "File .env creato"
    print_warning "IMPORTANTE: Configura le API keys nel file .env prima di eseguire l'esempio!"
    print_status "API keys opzionali per funzionalità aggiuntive:"
    print_status "  - TAVILY_API_KEY: per ricerca via API (gratuita)"
    print_status "  - NEWSAPI_API_KEY: per NewsAPI (gratuita)"
else
    print_status "File .env già esistente"
fi

# 6. Crea directory logs se non esiste
if [ ! -d "logs" ]; then
    print_status "Creazione directory logs..."
    mkdir -p logs
    print_success "Directory logs creata"
fi

# 7. Verifica configurazioni
print_status "Verifica configurazioni sistema..."

# Verifica configurazione domini
if [ -f "src/config/domains.yaml" ]; then
    print_success "✅ Configurazione domini trovata"
else
    print_warning "❌ Configurazione domini non trovata"
fi

# Verifica configurazione web scraping
if [ -f "src/config/web_scraping.yaml" ]; then
    print_success "✅ Configurazione web scraping trovata"
else
    print_warning "❌ Configurazione web scraping non trovata"
fi

# Verifica configurazione RSS
if [ -f "src/config/rss_feeds.yaml" ]; then
    print_success "✅ Configurazione RSS feeds trovata"
else
    print_warning "❌ Configurazione RSS feeds non trovata"
fi

# 8. Test importazioni Python
print_status "Test importazioni moduli principali..."
cd src && python3 -c "
try:
    from core.news_sources import create_default_news_manager, NewsQuery
    from core.news_source_trafilatura import TrafilaturaWebScrapingSource
    print('✅ Moduli news sources: OK')
except Exception as e:
    print(f'❌ Moduli news sources: {e}')

try:
    from core.config import get_config
    print('✅ Modulo configurazione: OK')
except Exception as e:
    print(f'❌ Modulo configurazione: {e}')

try:
    from core.log import get_news_logger
    print('✅ Sistema logging: OK')
except Exception as e:
    print(f'❌ Sistema logging: {e}')
" 2>/dev/null
cd ..

# 9. Rendi eseguibili gli script
print_status "Configurazione permessi script..."
chmod +x start.sh stop.sh run_example.sh load_news_*.sh 2>/dev/null || true
print_success "Permessi script configurati"

# 10. Mostra istruzioni finali
echo
echo -e "${GREEN}"
echo "============================================="
echo "      Installazione completata!            "
echo "============================================="
echo -e "${NC}"

print_success "Il sistema News Vector DB è stato installato con successo!"
echo
print_status "PROSSIMI PASSI:"
print_status "1. Configura le API keys nel file .env (opzionale ma raccomandato)"
print_status "2. Avvia Weaviate: ./start.sh"
print_status "3. Esegui l'esempio: ./run_example.sh"
echo
print_status "SCRIPT DISPONIBILI:"
print_status "  ./start.sh                    - Avvia Weaviate"
print_status "  ./stop.sh                     - Ferma Weaviate"
print_status "  ./run_example.sh              - Esegue l'esempio"
print_status "  ./load_news_trafilatura.sh    - Carica notizie con Trafilatura"
print_status "  python src/scripts/load_news.py --help  - Opzioni caricamento"
echo
print_status "FONTI DI NOTIZIE CONFIGURATE:"
print_status "  🥇 Trafilatura (AI-powered scraping) - Priorità massima"
print_status "  🥈 RSS Feeds - Sempre disponibile"
print_status "  🥉 Web Scraping (BeautifulSoup) - Fallback"
print_status "  🔑 NewsAPI - Richiede API key"
print_status "  🔑 Tavily - Richiede API key"
echo
print_warning "NOTA: Per il primo avvio, il download del modello FastEmbed (~150MB)"
print_warning "      potrebbe richiedere alcuni minuti."

# Disattiva virtual environment
deactivate 2>/dev/null || true