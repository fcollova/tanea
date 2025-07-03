#!/bin/bash

# Quick script per caricare notizie
# Uso: ./quick_load.sh

echo "🚀 Quick News Loader..."

# Attiva venv e esegue load_news.py
source venv/bin/activate && python src/scripts/load_news.py

echo "✅ Fatto!"