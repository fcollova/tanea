#!/bin/bash
# ============================================================================
# load_news_newsapi.sh - Carica notizie solo da NewsAPI
# ============================================================================

echo "📰 Caricamento notizie da NewsAPI..."
python3 src/scripts/load_news.py --newsapi "$@"