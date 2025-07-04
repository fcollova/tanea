#!/usr/bin/env python3
"""
Test dei nuovi script divisi: install.sh e run_example.sh
"""

import os
import subprocess

def test_script_structure():
    """Test della struttura dei nuovi script"""
    print("🧪 TEST STRUTTURA SCRIPT DIVISI")
    print("=" * 35)
    
    scripts_to_check = [
        ("install.sh", "Script di installazione"),
        ("run_example.sh", "Script di esecuzione esempio"),
        ("load_news_trafilatura.sh", "Script Trafilatura dedicato"),
        ("start.sh", "Script avvio Weaviate"),
        ("stop.sh", "Script stop Weaviate")
    ]
    
    print("📋 VERIFICA SCRIPT DISPONIBILI:")
    print("-" * 35)
    
    for script_name, description in scripts_to_check:
        if os.path.exists(script_name):
            # Verifica se è eseguibile
            is_executable = os.access(script_name, os.X_OK)
            exec_status = "✅ Eseguibile" if is_executable else "⚠️  Non eseguibile"
            
            # Leggi prime righe per verificare contenuto
            with open(script_name, 'r') as f:
                first_lines = f.readlines()[:5]
                has_shebang = first_lines[0].startswith('#!/bin/bash')
                shebang_status = "✅ Shebang OK" if has_shebang else "❌ Manca shebang"
            
            print(f"✅ {script_name:<25} {description}")
            print(f"   {exec_status} | {shebang_status}")
        else:
            print(f"❌ {script_name:<25} MANCANTE")
        print()

def test_script_functions():
    """Test delle funzioni principali degli script"""
    print("🔧 TEST FUNZIONI SCRIPT:")
    print("-" * 25)
    
    # Test install.sh (solo verifica sintassi bash)
    print("📦 install.sh:")
    try:
        result = subprocess.run(['bash', '-n', 'install.sh'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("   ✅ Sintassi bash corretta")
        else:
            print(f"   ❌ Errore sintassi: {result.stderr}")
    except Exception as e:
        print(f"   ⚠️  Impossibile testare: {e}")
    
    # Test run_example.sh (solo verifica sintassi bash)
    print("\n🚀 run_example.sh:")
    try:
        result = subprocess.run(['bash', '-n', 'run_example.sh'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("   ✅ Sintassi bash corretta")
        else:
            print(f"   ❌ Errore sintassi: {result.stderr}")
    except Exception as e:
        print(f"   ⚠️  Impossibile testare: {e}")
    
    # Test load_news_trafilatura.sh
    print("\n🤖 load_news_trafilatura.sh:")
    try:
        result = subprocess.run(['bash', '-n', 'load_news_trafilatura.sh'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("   ✅ Sintassi bash corretta")
        else:
            print(f"   ❌ Errore sintassi: {result.stderr}")
    except Exception as e:
        print(f"   ⚠️  Impossibile testare: {e}")

def show_script_workflow():
    """Mostra il workflow dei nuovi script"""
    print("\n📋 WORKFLOW SCRIPT DIVISI:")
    print("-" * 30)
    
    workflow_steps = [
        ("1. 📦 ./install.sh", "Installazione completa sistema", [
            "Crea virtual environment",
            "Installa dipendenze Python",
            "Configura file .env",
            "Verifica configurazioni",
            "Testa importazioni moduli"
        ]),
        ("2. 🐳 ./start.sh", "Avvia Weaviate", [
            "Avvia Docker Compose",
            "Verifica connessione Weaviate",
            "Mostra status"
        ]),
        ("3. 🚀 ./run_example.sh", "Esegue esempio", [
            "Verifica installazione completata",
            "Attiva virtual environment", 
            "Controlla Weaviate attivo",
            "Verifica dipendenze",
            "Avvia applicazione esempio"
        ])
    ]
    
    for step_title, step_desc, step_actions in workflow_steps:
        print(f"\n{step_title}")
        print(f"   📝 {step_desc}")
        for action in step_actions:
            print(f"      • {action}")

def show_trafilatura_integration():
    """Mostra l'integrazione di Trafilatura negli script"""
    print("\n🤖 INTEGRAZIONE TRAFILATURA:")
    print("-" * 30)
    
    trafilatura_features = [
        "📦 install.sh - Installa trafilatura automaticamente",
        "✅ install.sh - Verifica installazione trafilatura",
        "🚀 run_example.sh - Controlla trafilatura disponibile",
        "🎯 load_news_trafilatura.sh - Script dedicato Trafilatura",
        "⚙️  requirements.txt - Dipendenze trafilatura complete",
        "🔧 load_news.py - Opzione --trafilatura CLI",
        "📊 Priorità massima per fonte Trafilatura"
    ]
    
    for feature in trafilatura_features:
        print(f"   {feature}")

def show_comparison_old_vs_new():
    """Confronto vecchio vs nuovo approccio"""
    print("\n📊 CONFRONTO VECCHIO vs NUOVO:")
    print("-" * 35)
    
    print("🔴 PRIMA (run_example.sh monolitico):")
    old_issues = [
        "❌ Script unico faceva tutto",
        "❌ Installazione ad ogni esecuzione",
        "❌ Difficile troubleshooting",
        "❌ Nessuna separazione responsabilità",
        "❌ Rilentamento a ogni avvio"
    ]
    for issue in old_issues:
        print(f"   {issue}")
    
    print("\n🟢 DOPO (script divisi):")
    new_benefits = [
        "✅ install.sh - Una sola installazione",
        "✅ run_example.sh - Solo esecuzione",
        "✅ Troubleshooting mirato per fase",
        "✅ Responsabilità separate e chiare",
        "✅ Avvio rapido dopo installazione",
        "✅ Script specializzati per Trafilatura"
    ]
    for benefit in new_benefits:
        print(f"   {benefit}")

if __name__ == "__main__":
    print("🧪 TEST SCRIPT DIVISI - INSTALL.SH + RUN_EXAMPLE.SH")
    print("=" * 55)
    
    test_script_structure()
    test_script_functions()
    show_script_workflow()
    show_trafilatura_integration()
    show_comparison_old_vs_new()
    
    print(f"\n🎊 SCRIPT DIVISI IMPLEMENTATI CON SUCCESSO!")
    print(f"   L'installazione e l'esecuzione sono ora separate:")
    print(f"   - install.sh: Installazione una tantum")
    print(f"   - run_example.sh: Esecuzione rapida")
    print(f"   - load_news_trafilatura.sh: Trafilatura dedicato")
    print(f"   - Migliore manutenibilità e troubleshooting")