#!/bin/bash
# ============================================================================
# load_news_rss.sh - Carica notizie solo da feed RSS
# ============================================================================

echo "📰 Caricamento notizie da feed RSS..."
python3 src/scripts/load_news.py --rss "$@"