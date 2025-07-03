#!/usr/bin/env python3
"""
Script per analizzare l'uso del logging in tutti i moduli
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Set

def analyze_logging_patterns():
    """Analizza i pattern di logging in tutti i file Python"""
    print("🔍 Analisi pattern di logging...")
    
    # Trova tutti i file Python
    src_path = Path("src")
    py_files = list(src_path.rglob("*.py"))
    
    logging_analysis = {
        'files_with_logging': [],
        'logger_patterns': {},
        'log_levels_used': set(),
        'inconsistencies': [],
        'summary': {}
    }
    
    # Pattern da cercare
    patterns = {
        'import_logging': r'import logging',
        'logger_creation': r'logger = logging\.getLogger\((.*?)\)',
        'basic_config': r'logging\.basicConfig\(',
        'setup_logging': r'setup_logging\(',
        'log_calls': r'logger\.(debug|info|warning|error|critical)\(',
        'direct_logging': r'logging\.(debug|info|warning|error|critical)\(',
    }
    
    print(f"\n📁 Analizzando {len(py_files)} file Python...")
    
    for py_file in py_files:
        if py_file.name.startswith('__'):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            file_analysis = {
                'path': str(py_file),
                'has_logging': False,
                'logger_name': None,
                'log_levels': set(),
                'patterns_found': {},
                'lines_with_logging': []
            }
            
            # Analizza ogni pattern
            for pattern_name, pattern in patterns.items():
                matches = re.finditer(pattern, content)
                found_matches = list(matches)
                
                if found_matches:
                    file_analysis['has_logging'] = True
                    file_analysis['patterns_found'][pattern_name] = len(found_matches)
                    
                    if pattern_name == 'logger_creation':
                        for match in found_matches:
                            file_analysis['logger_name'] = match.group(1)
                    
                    elif pattern_name in ['log_calls', 'direct_logging']:
                        for match in found_matches:
                            level = match.group(1)
                            file_analysis['log_levels'].add(level)
                            logging_analysis['log_levels_used'].add(level)
            
            # Trova linee specifiche con logging
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if 'logger.' in line or 'logging.' in line:
                    file_analysis['lines_with_logging'].append((i, line.strip()))
            
            if file_analysis['has_logging']:
                logging_analysis['files_with_logging'].append(file_analysis)
                
                # Identifica pattern nel nome del logger
                logger_name = file_analysis['logger_name']
                if logger_name:
                    if logger_name not in logging_analysis['logger_patterns']:
                        logging_analysis['logger_patterns'][logger_name] = []
                    logging_analysis['logger_patterns'][logger_name].append(str(py_file))
                    
        except Exception as e:
            print(f"❌ Errore leggendo {py_file}: {e}")
    
    # Analizza inconsistenze
    _analyze_inconsistencies(logging_analysis)
    
    # Genera summary
    logging_analysis['summary'] = {
        'total_files': len(py_files),
        'files_with_logging': len(logging_analysis['files_with_logging']),
        'unique_logger_patterns': len(logging_analysis['logger_patterns']),
        'log_levels_count': len(logging_analysis['log_levels_used'])
    }
    
    return logging_analysis

def _analyze_inconsistencies(analysis):
    """Identifica inconsistenze nei pattern di logging"""
    inconsistencies = []
    
    # 1. Diversi pattern per logger names
    logger_patterns = analysis['logger_patterns']
    if len(logger_patterns) > 3:  # Troppi pattern diversi
        inconsistencies.append({
            'type': 'too_many_logger_patterns',
            'description': f"Trovati {len(logger_patterns)} pattern diversi per logger names",
            'details': list(logger_patterns.keys())
        })
    
    # 2. File senza logger ma con chiamate logging
    for file_info in analysis['files_with_logging']:
        has_logger_creation = 'logger_creation' in file_info['patterns_found']
        has_log_calls = 'log_calls' in file_info['patterns_found']
        has_direct_logging = 'direct_logging' in file_info['patterns_found']
        
        if has_log_calls and not has_logger_creation:
            inconsistencies.append({
                'type': 'missing_logger_creation',
                'description': f"File usa logger.* senza creare logger",
                'file': file_info['path']
            })
        
        if has_direct_logging:
            inconsistencies.append({
                'type': 'direct_logging_usage',
                'description': f"File usa logging.* direttamente invece di logger.*",
                'file': file_info['path']
            })
    
    analysis['inconsistencies'] = inconsistencies

def print_analysis_report(analysis):
    """Stampa report dell'analisi"""
    summary = analysis['summary']
    
    print(f"\n📊 REPORT ANALISI LOGGING")
    print(f"=" * 50)
    print(f"📁 File totali analizzati: {summary['total_files']}")
    print(f"📝 File con logging: {summary['files_with_logging']}")
    print(f"🏷️  Pattern logger diversi: {summary['unique_logger_patterns']}")
    print(f"📈 Livelli log usati: {', '.join(sorted(analysis['log_levels_used']))}")
    
    print(f"\n🏷️  PATTERN LOGGER NAMES:")
    for pattern, files in analysis['logger_patterns'].items():
        print(f"  • {pattern}: {len(files)} file(s)")
        for file_path in files[:3]:  # Mostra solo primi 3
            print(f"    - {file_path}")
        if len(files) > 3:
            print(f"    ... e altri {len(files) - 3}")
    
    print(f"\n📝 FILE CON LOGGING:")
    for file_info in analysis['files_with_logging']:
        print(f"  📄 {file_info['path']}")
        print(f"     Logger: {file_info['logger_name'] or 'N/A'}")
        print(f"     Livelli: {', '.join(sorted(file_info['log_levels'])) or 'nessuno'}")
        
        # Mostra prime righe con logging
        if file_info['lines_with_logging']:
            print(f"     Esempi:")
            for line_num, line_content in file_info['lines_with_logging'][:2]:
                print(f"       L{line_num}: {line_content}")
        print()
    
    if analysis['inconsistencies']:
        print(f"\n⚠️  INCONSISTENZE TROVATE:")
        for inconsistency in analysis['inconsistencies']:
            print(f"  🔸 {inconsistency['type']}: {inconsistency['description']}")
            if 'file' in inconsistency:
                print(f"     File: {inconsistency['file']}")
            if 'details' in inconsistency:
                print(f"     Dettagli: {inconsistency['details']}")
        print()
    
    print(f"\n💡 RACCOMANDAZIONI:")
    
    # Analizza se serve modulo centralizzato
    if summary['unique_logger_patterns'] > 2:
        print(f"  ✅ Creare modulo log.py centralizzato")
        print(f"     - Standardizzare configurazione logging")
        print(f"     - Unificare pattern logger names")
    
    if any(inc['type'] == 'direct_logging_usage' for inc in analysis['inconsistencies']):
        print(f"  ✅ Sostituire logging.* con logger.*")
    
    if any(inc['type'] == 'missing_logger_creation' for inc in analysis['inconsistencies']):
        print(f"  ✅ Aggiungere creazione logger mancanti")
    
    files_without_logging = summary['total_files'] - summary['files_with_logging']
    if files_without_logging > 0:
        print(f"  ✅ Considerare aggiungere logging a {files_without_logging} file(s)")

def suggest_log_module_design(analysis):
    """Suggerisce design per modulo log.py"""
    print(f"\n🏗️  DESIGN SUGGERITO PER log.py:")
    print(f"=" * 50)
    
    print(f"1. 📋 Configurazione centralizzata")
    print(f"   - Formato log standardizzato")
    print(f"   - Livelli per ambiente (dev/prod)")
    print(f"   - Output file + console")
    
    print(f"\n2. 🏭 Factory per logger")
    print(f"   - get_logger(name) standardizzato")
    print(f"   - Naming convention automatica")
    print(f"   - Context-aware logging")
    
    print(f"\n3. 🎯 Logger specializzati")
    specialized_loggers = []
    for file_info in analysis['files_with_logging']:
        if 'news' in file_info['path'].lower():
            specialized_loggers.append('news')
        elif 'db' in file_info['path'].lower() or 'vector' in file_info['path'].lower():
            specialized_loggers.append('database')
        elif 'config' in file_info['path'].lower():
            specialized_loggers.append('config')
        elif 'script' in file_info['path'].lower():
            specialized_loggers.append('scripts')
    
    specialized_loggers = list(set(specialized_loggers))
    for logger_type in specialized_loggers:
        print(f"   - {logger_type}_logger()")
    
    print(f"\n4. 🔧 Utilities")
    print(f"   - Log decorators per funzioni")
    print(f"   - Performance logging")
    print(f"   - Error tracking")

if __name__ == "__main__":
    analysis = analyze_logging_patterns()
    print_analysis_report(analysis)
    suggest_log_module_design(analysis)