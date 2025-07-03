#!/bin/bash
# ============================================================================
# load_news_scraping.sh - Carica notizie solo da web scraping
# ============================================================================

echo "📰 Caricamento notizie da web scraping..."
python3 src/scripts/load_news.py --scraping "$@"