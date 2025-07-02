#!/bin/bash

# =============================================================================
# load_news.sh - Script per caricare notizie su Weaviate
# =============================================================================

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configurazioni
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/venv"
PYTHON_SCRIPT="$SCRIPT_DIR/load_news.py"
LOG_FILE="$SCRIPT_DIR/logs/load_news_$(date +%Y%m%d_%H%M%S).log"

# Funzioni di utilità
print_header() {
    echo -e "${CYAN}=================================================${NC}"
    echo -e "${CYAN}          📰 NEWS LOADER SCRIPT 📰${NC}"
    echo -e "${CYAN}=================================================${NC}"
    echo ""
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_step() {
    echo -e "${PURPLE}🔄 $1${NC}"
}

# Controlla se file/directory esistono
check_prerequisites() {
    print_step "Controllo prerequisiti..."
    
    # Controlla se siamo nella directory corretta
    if [[ ! -f "$SCRIPT_DIR/load_news.py" ]]; then
        print_error "load_news.py non trovato in $SCRIPT_DIR"
        exit 1
    fi
    
    # Controlla virtual environment
    if [[ ! -d "$VENV_PATH" ]]; then
        print_error "Virtual environment non trovato in $VENV_PATH"
        print_info "Esegui: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
        exit 1
    fi
    
    # Controlla file di configurazione
    if [[ ! -f "$SCRIPT_DIR/config.conf" ]]; then
        print_error "File config.conf non trovato"
        exit 1
    fi
    
    # Crea directory logs se non esiste
    mkdir -p "$SCRIPT_DIR/logs"
    
    print_success "Prerequisiti verificati"
}

# Controlla se Weaviate è in esecuzione
check_weaviate() {
    print_step "Controllo connessione Weaviate..."
    
    # Leggi URL da config (default localhost:8080)
    WEAVIATE_URL="http://localhost:8080"
    
    if command -v curl > /dev/null 2>&1; then
        if curl -s "$WEAVIATE_URL/v1/meta" > /dev/null 2>&1; then
            print_success "Weaviate è raggiungibile su $WEAVIATE_URL"
            return 0
        else
            print_error "Weaviate non è raggiungibile su $WEAVIATE_URL"
            print_info "Assicurati che Weaviate sia in esecuzione:"
            print_info "  docker-compose up -d"
            return 1
        fi
    else
        print_warning "curl non disponibile, salto controllo Weaviate"
        return 0
    fi
}

# Attiva virtual environment
activate_venv() {
    print_step "Attivazione virtual environment..."
    
    # Source del virtual environment
    source "$VENV_PATH/bin/activate"
    
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        print_success "Virtual environment attivato: $VIRTUAL_ENV"
        return 0
    else
        print_error "Errore nell'attivazione del virtual environment"
        return 1
    fi
}

# Controlla chiave API Tavily
check_tavily_key() {
    print_step "Controllo configurazione Tavily..."
    
    # Controlla se la chiave è configurata nei file config
    if grep -q "tavily_api_key.*=" config.dev.conf 2>/dev/null || \
       grep -q "tavily_api_key.*=" config.prod.conf 2>/dev/null; then
        
        # Verifica che non sia commentata
        if grep -q "^[[:space:]]*tavily_api_key[[:space:]]*=" config.dev.conf 2>/dev/null || \
           grep -q "^[[:space:]]*tavily_api_key[[:space:]]*=" config.prod.conf 2>/dev/null; then
            print_success "Chiave API Tavily configurata"
            return 0
        else
            print_warning "Chiave API Tavily commentata nel file di configurazione"
            print_info "Decommentare e impostare tavily_api_key in config.dev.conf o config.prod.conf"
            return 1
        fi
    else
        print_warning "Chiave API Tavily non configurata"
        print_info "Aggiungere tavily_api_key nei file di configurazione"
        return 1
    fi
}

# Esegue il caricamento news
run_news_loader() {
    print_step "Avvio caricamento notizie..."
    echo ""
    
    # Determina ambiente
    ENV=${ENV:-dev}
    export ENV
    
    print_info "Ambiente: $ENV"
    print_info "Log file: $LOG_FILE"
    echo ""
    
    # Esegue lo script Python con logging
    if python "$PYTHON_SCRIPT" 2>&1 | tee "$LOG_FILE"; then
        echo ""
        print_success "Caricamento notizie completato con successo!"
        print_info "Log salvato in: $LOG_FILE"
        return 0
    else
        echo ""
        print_error "Errore durante il caricamento notizie"
        print_info "Controlla il log: $LOG_FILE"
        return 1
    fi
}

# Mostra statistiche finali
show_stats() {
    print_step "Recupero statistiche finali..."
    
    # Estrae statistiche dal log
    if [[ -f "$LOG_FILE" ]]; then
        echo ""
        print_info "Riepilogo dall'esecuzione:"
        
        # Cerca pattern specifici nel log
        if grep -q "Nuovi articoli:" "$LOG_FILE"; then
            grep "Nuovi articoli:" "$LOG_FILE" | tail -1 | sed 's/.*Nuovi articoli:/  📰 Nuovi articoli:/'
        fi
        
        if grep -q "Duplicati saltati:" "$LOG_FILE"; then
            grep "Duplicati saltati:" "$LOG_FILE" | tail -1 | sed 's/.*Duplicati saltati:/  🔄 Duplicati saltati:/'
        fi
        
        if grep -q "Totale articoli:" "$LOG_FILE"; then
            grep "Totale articoli:" "$LOG_FILE" | tail -1 | sed 's/.*Totale articoli:/  📊 Totale articoli:/'
        fi
    fi
}

# Cleanup function
cleanup() {
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        deactivate 2>/dev/null || true
    fi
}

# Funzione principale
main() {
    # Setup cleanup trap
    trap cleanup EXIT
    
    print_header
    
    # Controlli preliminari
    check_prerequisites || exit 1
    echo ""
    
    check_weaviate || {
        print_warning "Continuando senza verifica Weaviate..."
        echo ""
    }
    
    check_tavily_key || {
        print_warning "Continuando senza verifica chiave Tavily..."
        echo ""
    }
    
    # Attiva ambiente
    activate_venv || exit 1
    echo ""
    
    # Esegue caricamento
    if run_news_loader; then
        echo ""
        show_stats
        echo ""
        print_success "Processo completato! 🎉"
        
        # Suggerimenti finali
        echo ""
        print_info "Comandi utili:"
        print_info "  🔍 Test Q&A: python example_usage.py"
        print_info "  📊 Esplora DB: python explore_db.py"
        print_info "  📝 Log: tail -f $LOG_FILE"
        
    else
        echo ""
        print_error "Processo fallito! ❌"
        print_info "Controlla il log per dettagli: $LOG_FILE"
        exit 1
    fi
}

# Gestione parametri command line
case "${1:-}" in
    --help|-h)
        echo "Uso: $0 [opzioni]"
        echo ""
        echo "Opzioni:"
        echo "  --help, -h     Mostra questo aiuto"
        echo "  --dev          Usa ambiente development (default)"
        echo "  --prod         Usa ambiente production"
        echo "  --check        Solo controlli prerequisiti"
        echo ""
        echo "Variabili ambiente:"
        echo "  ENV            Ambiente (dev|prod) - default: dev"
        echo ""
        echo "Esempi:"
        echo "  $0              # Carica news in ambiente dev"
        echo "  $0 --prod       # Carica news in ambiente prod"
        echo "  ENV=prod $0     # Carica news in ambiente prod"
        exit 0
        ;;
    --dev)
        export ENV=dev
        ;;
    --prod)
        export ENV=prod
        ;;
    --check)
        print_header
        check_prerequisites
        check_weaviate
        check_tavily_key
        print_success "Controlli completati"
        exit 0
        ;;
    "")
        # Default: nessun parametro
        ;;
    *)
        print_error "Parametro sconosciuto: $1"
        print_info "Usa --help per vedere le opzioni disponibili"
        exit 1
        ;;
esac

# Esegue main
main