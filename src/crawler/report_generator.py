"""
Report Generator - Generazione report Excel e PDF per operazioni crawler
"""

import os
import csv
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

# Try to import pandas for Excel generation
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# PDF generation
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from core.log import get_scripts_logger
from core.config import get_config

logger = get_scripts_logger(__name__)

class ReportGenerator:
    """Genera report tabellari Excel e PDF per operazioni crawler"""
    
    def __init__(self, output_dir: str = None):
        # Ottieni configurazione se non specificata
        if output_dir is None:
            config = get_config()
            output_dir = config.get('logging', 'crawler_report_dir', 'logs/crawler_report')
        
        # Converti in path assoluto se è relativo
        if not os.path.isabs(output_dir):
            # Trova la root del progetto cercando il file caratteristico
            current_dir = Path.cwd()
            project_root = None
            
            # Cerca verso l'alto fino a trovare requirements.txt o run_crawler.sh
            search_dir = current_dir
            for _ in range(5):  # Limite di sicurezza
                if (search_dir / 'requirements.txt').exists() or (search_dir / 'run_crawler.sh').exists():
                    project_root = search_dir
                    break
                search_dir = search_dir.parent
            
            # Se non trova la root, usa la current directory
            if project_root is None:
                project_root = current_dir
                
            self.output_dir = project_root / output_dir
        else:
            self.output_dir = Path(output_dir)
            
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Carica configurazione report
        config = get_config()
        self.report_enabled = config.get('logging', 'enable_report_generation', True, bool)
        report_formats = config.get('logging', 'report_formats', 'csv,json,excel,pdf')
        self.enabled_formats = [fmt.strip() for fmt in report_formats.split(',')]
        self.cleanup_days = config.get('logging', 'report_cleanup_days', 30, int)
        
        # Verifica dipendenze
        if not PANDAS_AVAILABLE:
            logger.warning("Pandas non disponibile, usando fallback CSV per Excel")
            if 'excel' in self.enabled_formats:
                self.enabled_formats.remove('excel')
                self.enabled_formats.append('csv')  # Fallback
        
        if not REPORTLAB_AVAILABLE:
            logger.warning("ReportLab non disponibile, report PDF disabilitati")
            if 'pdf' in self.enabled_formats:
                self.enabled_formats.remove('pdf')
        
        logger.info(f"ReportGenerator inizializzato:")
        logger.info(f"  • Output: {self.output_dir}")
        logger.info(f"  • Formati abilitati: {', '.join(self.enabled_formats)}")
        logger.info(f"  • Cleanup dopo: {self.cleanup_days} giorni")
    
    def generate_discovery_report(self, results: Dict, operation_type: str = "discovery") -> Dict[str, str]:
        """
        Genera report per operazione discovery
        
        Args:
            results: Risultati discovery da crawler_exec
            operation_type: Tipo operazione (discovery/crawl)
            
        Returns:
            dict: Path dei file generati
        """
        if not self.report_enabled:
            logger.info("Generazione report disabilitata dalla configurazione")
            return {}
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        operation_name = f"{operation_type}_{timestamp}"
        
        # Prepara dati per report
        summary_data = self._prepare_discovery_summary(results, operation_type)
        sites_data = self._prepare_sites_details(results)
        
        report_files = {}
        
        # Genera CSV (preferito) o Excel come fallback
        if 'csv' in self.enabled_formats:
            try:
                csv_path = self._generate_csv_report(
                    summary_data, sites_data, operation_name, operation_type
                )
                report_files['csv'] = str(csv_path)
                logger.info(f"Report CSV generato: {csv_path}")
            except Exception as e:
                logger.error(f"Errore generazione CSV: {e}")
        elif 'excel' in self.enabled_formats:
            try:
                excel_path = self._generate_excel_report(
                    summary_data, sites_data, operation_name, operation_type
                )
                report_files['excel'] = str(excel_path)
                logger.info(f"Report Excel generato: {excel_path}")
            except Exception as e:
                logger.error(f"Errore generazione Excel: {e}")
        
        # Genera JSON
        if 'json' in self.enabled_formats:
            try:
                json_path = self._generate_json_report(
                    summary_data, sites_data, operation_name, operation_type
                )
                report_files['json'] = str(json_path)
                logger.info(f"Report JSON generato: {json_path}")
            except Exception as e:
                logger.error(f"Errore generazione JSON: {e}")
        
        # Genera PDF se disponibile e abilitato
        if 'pdf' in self.enabled_formats and REPORTLAB_AVAILABLE:
            try:
                pdf_path = self._generate_pdf_report(
                    summary_data, sites_data, operation_name, operation_type
                )
                report_files['pdf'] = str(pdf_path)
                logger.info(f"Report PDF generato: {pdf_path}")
            except Exception as e:
                logger.error(f"Errore generazione PDF: {e}")
        
        return report_files
    
    def generate_crawl_report(self, results: Dict, operation_type: str = "crawl") -> Dict[str, str]:
        """
        Genera report per operazione crawl completo
        
        Args:
            results: Risultati crawl da crawler_exec
            operation_type: Tipo operazione
            
        Returns:
            dict: Path dei file generati
        """
        if not self.report_enabled:
            logger.info("Generazione report disabilitata dalla configurazione")
            return {}
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        operation_name = f"{operation_type}_{timestamp}"
        
        # Prepara dati per report
        summary_data = self._prepare_crawl_summary(results, operation_type)
        sites_data = self._prepare_crawl_sites_details(results)
        
        report_files = {}
        
        # Genera CSV (preferito) o Excel come fallback
        if 'csv' in self.enabled_formats:
            try:
                csv_path = self._generate_csv_report(
                    summary_data, sites_data, operation_name, operation_type
                )
                report_files['csv'] = str(csv_path)
                logger.info(f"Report CSV generato: {csv_path}")
            except Exception as e:
                logger.error(f"Errore generazione CSV: {e}")
        elif 'excel' in self.enabled_formats:
            try:
                excel_path = self._generate_excel_report(
                    summary_data, sites_data, operation_name, operation_type
                )
                report_files['excel'] = str(excel_path)
                logger.info(f"Report Excel generato: {excel_path}")
            except Exception as e:
                logger.error(f"Errore generazione Excel: {e}")
        
        # Genera JSON
        if 'json' in self.enabled_formats:
            try:
                json_path = self._generate_json_report(
                    summary_data, sites_data, operation_name, operation_type
                )
                report_files['json'] = str(json_path)
                logger.info(f"Report JSON generato: {json_path}")
            except Exception as e:
                logger.error(f"Errore generazione JSON: {e}")
        
        # Genera PDF se disponibile e abilitato
        if 'pdf' in self.enabled_formats and REPORTLAB_AVAILABLE:
            try:
                pdf_path = self._generate_pdf_report(
                    summary_data, sites_data, operation_name, operation_type
                )
                report_files['pdf'] = str(pdf_path)
                logger.info(f"Report PDF generato: {pdf_path}")
            except Exception as e:
                logger.error(f"Errore generazione PDF: {e}")
        
        return report_files
    
    def _prepare_discovery_summary(self, results: Dict, operation_type: str) -> Dict[str, Any]:
        """Prepara dati summary per discovery"""
        return {
            'operation_type': operation_type.upper(),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'total_sites_processed': results.get('total_sites_processed', 0),
            'total_links_discovered': results.get('total_links_discovered', 0),
            'domains_processed': len(results.get('domains_processed', [])),
            'domain_list': ', '.join(results.get('domains_processed', [])),
            'errors_count': len(results.get('errors', [])),
            'success_rate': self._calculate_success_rate(results),
            'avg_links_per_site': self._calculate_avg_links_per_site(results)
        }
    
    def _prepare_crawl_summary(self, results: Dict, operation_type: str) -> Dict[str, Any]:
        """Prepara dati summary per crawl"""
        duration = results.get('duration', 0)
        return {
            'operation_type': operation_type.upper(),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'start_time': results.get('start_time', '').strftime("%Y-%m-%d %H:%M:%S") if results.get('start_time') else '',
            'end_time': results.get('end_time', '').strftime("%Y-%m-%d %H:%M:%S") if results.get('end_time') else '',
            'duration_seconds': duration,
            'duration_formatted': f"{duration:.1f}s",
            'sites_processed': results.get('sites_processed', 0),
            'links_discovered': results.get('links_discovered', 0),
            'links_crawled': results.get('links_crawled', 0),
            'articles_extracted': results.get('articles_extracted', 0),
            'errors_count': results.get('errors', 0),
            'success_rate': self._calculate_crawl_success_rate(results),
            'extraction_rate': self._calculate_extraction_rate(results),
            'avg_articles_per_site': self._calculate_avg_articles_per_site(results)
        }
    
    def _prepare_sites_details(self, results: Dict) -> List[Dict]:
        """Prepara dettagli siti per discovery"""
        sites_details = []
        sites_results = results.get('sites_results', {})
        
        for site_key, site_data in sites_results.items():
            details = {
                'site_key': site_key,
                'site_name': site_data.get('site', site_key),
                'domain': site_data.get('domain', ''),
                'links_discovered': site_data.get('links_discovered', 0),
                'pages_processed': site_data.get('pages_processed', 0),
                'status': 'SUCCESS' if site_data.get('links_discovered', 0) > 0 else 'FAILED'
            }
            
            # Aggiungi dettagli pagine se disponibili
            page_details = site_data.get('page_details', {})
            if page_details:
                details['pages_detail'] = json.dumps(page_details, indent=2)
            
            sites_details.append(details)
        
        return sites_details
    
    def _prepare_crawl_sites_details(self, results: Dict) -> List[Dict]:
        """Prepara dettagli siti per crawl"""
        sites_details = []
        sites_results = results.get('sites_details', {})
        
        for site_key, site_data in sites_results.items():
            details = {
                'site_key': site_key,
                'links_discovered': site_data.get('links_discovered', 0),
                'links_crawled': site_data.get('links_crawled', 0),
                'articles_extracted': site_data.get('articles_extracted', 0),
                'errors': site_data.get('errors', 0),
                'success_rate': f"{(site_data.get('articles_extracted', 0) / max(site_data.get('links_discovered', 1), 1) * 100):.1f}%",
                'status': 'SUCCESS' if site_data.get('articles_extracted', 0) > 0 else 'FAILED'
            }
            sites_details.append(details)
        
        return sites_details
    
    def _generate_excel_report(self, summary_data: Dict, sites_data: List[Dict], 
                              operation_name: str, operation_type: str) -> Path:
        """Genera report Excel o CSV se pandas non disponibile"""
        
        if PANDAS_AVAILABLE:
            # Usa pandas per Excel
            excel_path = self.output_dir / f"{operation_name}_report.xlsx"
            
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                # Sheet 1: Summary
                summary_df = pd.DataFrame([summary_data])
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                # Sheet 2: Sites Details
                if sites_data:
                    sites_df = pd.DataFrame(sites_data)
                    sites_df.to_excel(writer, sheet_name='Sites_Details', index=False)
                
                # Sheet 3: Metadata
                metadata = {
                    'report_generated': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'operation_type': operation_type.upper(),
                    'generator': 'TaneaCrawler ReportGenerator',
                    'version': '1.0'
                }
                metadata_df = pd.DataFrame([metadata])
                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
            
            return excel_path
        else:
            # Fallback: genera CSV multipli
            return self._generate_csv_fallback(summary_data, sites_data, operation_name, operation_type)
    
    def _generate_csv_fallback(self, summary_data: Dict, sites_data: List[Dict], 
                              operation_name: str, operation_type: str) -> Path:
        """Genera report CSV come fallback quando pandas non è disponibile"""
        
        # File principale summary
        csv_path = self.output_dir / f"{operation_name}_report.csv"
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow(['# CRAWLER REPORT - ' + operation_type.upper()])
            writer.writerow(['# Generated:', datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            writer.writerow([])
            
            # Summary section
            writer.writerow(['=== SUMMARY ==='])
            writer.writerow(['Parameter', 'Value'])
            for key, value in summary_data.items():
                writer.writerow([key.replace('_', ' ').title(), str(value)])
            
            writer.writerow([])
            
            # Sites details section
            if sites_data:
                writer.writerow(['=== SITES DETAILS ==='])
                if sites_data:
                    # Header
                    headers = list(sites_data[0].keys())
                    writer.writerow(headers)
                    
                    # Data
                    for site in sites_data:
                        row = [str(site.get(key, '')) for key in headers]
                        writer.writerow(row)
        
        # Genera anche JSON per dati strutturati
        json_path = self.output_dir / f"{operation_name}_report.json"
        report_data = {
            'metadata': {
                'report_generated': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'operation_type': operation_type.upper(),
                'generator': 'TaneaCrawler ReportGenerator',
                'version': '1.0'
            },
            'summary': summary_data,
            'sites_details': sites_data
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        logger.info(f"CSV/JSON fallback generato: {csv_path}, {json_path}")
        return csv_path
    
    def _generate_json_report(self, summary_data: Dict, sites_data: List[Dict], 
                             operation_name: str, operation_type: str) -> Path:
        """Genera report JSON separato"""
        json_path = self.output_dir / f"{operation_name}_report.json"
        
        report_data = {
            'metadata': {
                'report_generated': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'operation_type': operation_type.upper(),
                'generator': 'TaneaCrawler ReportGenerator',
                'version': '1.0'
            },
            'summary': summary_data,
            'sites_details': sites_data
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        return json_path
    
    def _generate_csv_report(self, summary_data: Dict, sites_data: List[Dict], 
                            operation_name: str, operation_type: str) -> Path:
        """Genera report CSV dedicato (formato preferito)"""
        csv_path = self.output_dir / f"{operation_name}_report.csv"
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header del report
            writer.writerow(['# TANEA CRAWLER REPORT'])
            writer.writerow(['# Operation:', operation_type.upper()])
            writer.writerow(['# Generated:', datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            writer.writerow(['# Generator:', 'TaneaCrawler ReportGenerator v1.0'])
            writer.writerow([])
            
            # === SEZIONE SUMMARY ===
            writer.writerow(['=== OPERATION SUMMARY ==='])
            writer.writerow(['Metric', 'Value', 'Description'])
            
            # Dati base
            writer.writerow(['Operation Type', summary_data.get('operation_type', ''), 'Type of crawler operation'])
            writer.writerow(['Execution Time', summary_data.get('timestamp', ''), 'When the operation was executed'])
            
            if 'duration_formatted' in summary_data:
                writer.writerow(['Duration', summary_data.get('duration_formatted', ''), 'Total execution time'])
            
            writer.writerow(['Sites Processed', summary_data.get('total_sites_processed', summary_data.get('sites_processed', 0)), 'Number of sites processed'])
            writer.writerow(['Domains Processed', summary_data.get('domains_processed', ''), 'Number of domains involved'])
            
            if 'domain_list' in summary_data:
                writer.writerow(['Domain List', summary_data.get('domain_list', ''), 'List of processed domains'])
            
            # Statistiche link
            writer.writerow(['Links Discovered', summary_data.get('total_links_discovered', summary_data.get('links_discovered', 0)), 'Total links found during discovery'])
            
            if 'links_crawled' in summary_data:
                writer.writerow(['Links Crawled', summary_data.get('links_crawled', 0), 'Links actually processed'])
            
            if 'articles_extracted' in summary_data:
                writer.writerow(['Articles Extracted', summary_data.get('articles_extracted', 0), 'Successfully extracted articles'])
            
            # Statistiche qualità
            writer.writerow(['Errors Count', summary_data.get('errors_count', 0), 'Number of errors encountered'])
            writer.writerow(['Success Rate', summary_data.get('success_rate', ''), 'Percentage of successful operations'])
            
            if 'extraction_rate' in summary_data:
                writer.writerow(['Extraction Rate', summary_data.get('extraction_rate', ''), 'Percentage of successful extractions'])
            
            writer.writerow(['Avg Links Per Site', summary_data.get('avg_links_per_site', ''), 'Average links discovered per site'])
            
            if 'avg_articles_per_site' in summary_data:
                writer.writerow(['Avg Articles Per Site', summary_data.get('avg_articles_per_site', ''), 'Average articles extracted per site'])
            
            writer.writerow([])
            
            # === SEZIONE SITES DETAILS ===
            if sites_data:
                writer.writerow(['=== SITES DETAILS ==='])
                
                # Header dinamico basato sui dati disponibili
                if sites_data:
                    headers = list(sites_data[0].keys())
                    # Traduci headers in italiano/inglese più leggibili
                    header_translations = {
                        'site_key': 'Site Key',
                        'site_name': 'Site Name', 
                        'domain': 'Domain',
                        'links_discovered': 'Links Found',
                        'links_crawled': 'Links Processed',
                        'articles_extracted': 'Articles Extracted',
                        'pages_processed': 'Pages Processed',
                        'errors': 'Errors',
                        'success_rate': 'Success Rate',
                        'status': 'Status'
                    }
                    
                    translated_headers = [header_translations.get(h, h.replace('_', ' ').title()) for h in headers]
                    writer.writerow(translated_headers)
                    
                    # Dati dei siti
                    for site in sites_data:
                        row = []
                        for key in headers:
                            value = site.get(key, '')
                            # Non include dettagli JSON lunghi nel CSV principale
                            if key == 'pages_detail' and isinstance(value, str) and len(value) > 100:
                                row.append('[Details in JSON report]')
                            else:
                                row.append(str(value))
                        writer.writerow(row)
            
            writer.writerow([])
            
            # === FOOTER ===
            writer.writerow(['=== REPORT INFO ==='])
            writer.writerow(['Generated By', 'Tanea Crawler System'])
            writer.writerow(['Report Format', 'CSV (Comma Separated Values)'])
            writer.writerow(['For detailed data', 'See accompanying JSON report'])
            writer.writerow(['Contact', 'Generated automatically by TaneaCrawler'])
        
        return csv_path
    
    def _generate_pdf_report(self, summary_data: Dict, sites_data: List[Dict], 
                            operation_name: str, operation_type: str) -> Path:
        """Genera report PDF"""
        pdf_path = self.output_dir / f"{operation_name}_report.pdf"
        
        # Crea documento PDF
        doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
        story = []
        
        # Stili
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            alignment=TA_CENTER,
            fontSize=16,
            spaceAfter=30,
            textColor=colors.darkblue
        )
        
        # Titolo
        title = Paragraph(f"🕷️ Crawler Report - {operation_type.upper()}", title_style)
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Summary Section
        story.append(Paragraph("📊 Riepilogo Operazione", styles['Heading2']))
        story.append(Spacer(1, 12))
        
        # Tabella summary
        summary_table_data = [['Parametro', 'Valore']]
        for key, value in summary_data.items():
            if key != 'operation_type':  # Già nel titolo
                formatted_key = key.replace('_', ' ').title()
                summary_table_data.append([formatted_key, str(value)])
        
        summary_table = Table(summary_table_data, colWidths=[3*inch, 3*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Statistiche aggiuntive se disponibili
        if sites_data:
            story.append(Paragraph("📊 Statistiche Generali", styles['Heading2']))
            story.append(Spacer(1, 12))
            
            # Crea statistiche aggregate invece del dettaglio per sito
            total_sites = len(sites_data)
            successful_sites = sum(1 for site in sites_data if site.get('status') == 'SUCCESS')
            total_links = sum(site.get('links_discovered', 0) for site in sites_data)
            
            stats_data = [
                ['Statistica', 'Valore'],
                ['Siti Totali', str(total_sites)],
                ['Siti Riusciti', str(successful_sites)],
                ['Siti Falliti', str(total_sites - successful_sites)],
                ['Link Totali Scoperti', str(total_links)],
                ['Media Link per Sito', f"{total_links/total_sites:.1f}" if total_sites > 0 else "0"],
            ]
            
            # Aggiungi statistiche sui crawling se disponibili
            if any('articles_extracted' in site for site in sites_data):
                total_articles = sum(site.get('articles_extracted', 0) for site in sites_data)
                stats_data.extend([
                    ['Articoli Totali Estratti', str(total_articles)],
                    ['Media Articoli per Sito', f"{total_articles/total_sites:.1f}" if total_sites > 0 else "0"]
                ])
            
            stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(stats_table)
        
        story.append(Spacer(1, 20))
        
        # Footer
        footer_text = f"Generato il {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} da TaneaCrawler"
        footer = Paragraph(footer_text, styles['Normal'])
        story.append(footer)
        
        # Costruisci PDF
        doc.build(story)
        
        return pdf_path
    
    def _calculate_success_rate(self, results: Dict) -> str:
        """Calcola success rate per discovery"""
        total_sites = results.get('total_sites_processed', 0)
        successful_sites = sum(1 for site_data in results.get('sites_results', {}).values() 
                              if site_data.get('links_discovered', 0) > 0)
        
        if total_sites > 0:
            rate = (successful_sites / total_sites) * 100
            return f"{rate:.1f}%"
        return "0.0%"
    
    def _calculate_crawl_success_rate(self, results: Dict) -> str:
        """Calcola success rate per crawl"""
        links_discovered = results.get('links_discovered', 0)
        articles_extracted = results.get('articles_extracted', 0)
        
        if links_discovered > 0:
            rate = (articles_extracted / links_discovered) * 100
            return f"{rate:.1f}%"
        return "0.0%"
    
    def _calculate_extraction_rate(self, results: Dict) -> str:
        """Calcola extraction rate"""
        links_crawled = results.get('links_crawled', 0)
        articles_extracted = results.get('articles_extracted', 0)
        
        if links_crawled > 0:
            rate = (articles_extracted / links_crawled) * 100
            return f"{rate:.1f}%"
        return "0.0%"
    
    def _calculate_avg_links_per_site(self, results: Dict) -> str:
        """Calcola media link per sito"""
        total_sites = results.get('total_sites_processed', 0)
        total_links = results.get('total_links_discovered', 0)
        
        if total_sites > 0:
            avg = total_links / total_sites
            return f"{avg:.1f}"
        return "0.0"
    
    def _calculate_avg_articles_per_site(self, results: Dict) -> str:
        """Calcola media articoli per sito"""
        sites_processed = results.get('sites_processed', 0)
        articles_extracted = results.get('articles_extracted', 0)
        
        if sites_processed > 0:
            avg = articles_extracted / sites_processed
            return f"{avg:.1f}"
        return "0.0"
    
    def clean_old_reports(self, days_old: int = 30):
        """Pulisce report vecchi di più di N giorni"""
        import time
        current_time = time.time()
        
        cleaned_count = 0
        for file_path in self.output_dir.glob("*_report.*"):
            file_age = current_time - file_path.stat().st_mtime
            if file_age > (days_old * 24 * 60 * 60):  # Converti giorni in secondi
                try:
                    file_path.unlink()
                    cleaned_count += 1
                    logger.info(f"Rimosso report vecchio: {file_path.name}")
                except Exception as e:
                    logger.error(f"Errore rimozione {file_path.name}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Pulizia completata: {cleaned_count} report rimossi")
        else:
            logger.debug("Nessun report da pulire")