#!/usr/bin/env python3
"""
Daemon crawler per automazione continua
"""

import asyncio
import sys
import os
import signal
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.crawler.crawl_scheduler import CrawlScheduler
from core.domain_manager import DomainManager

class CrawlerDaemon:
    def __init__(self):
        self.scheduler = None
        self.running = False
    
    async def start(self):
        """Avvia il daemon crawler"""
        print("🚀 Avvio Tanea Crawler Daemon...")
        print(f"📅 Timestamp: {datetime.now()}")
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Inizializza scheduler
        self.scheduler = CrawlScheduler()
        domain_manager = DomainManager()
        
        try:
            # Verifica domini attivi
            active_domains = domain_manager.get_domain_list(active_only=True)
            print(f"📂 Domini configurati: {active_domains}")
            
            if not active_domains:
                print("❌ Nessun dominio attivo. Controlla domains.yaml")
                return
            
            # Configura scheduling per domini attivi
            for domain in active_domains:
                # Scheduling ogni 2 ore per domini attivi
                await self.scheduler.schedule_domain_crawling(domain, interval_hours=2)
                print(f"⏰ Scheduling configurato per {domain}: ogni 2 ore")
            
            # Avvia daemon
            print("🔄 Avvio scheduling loop...")
            print("⏹️  Premi Ctrl+C per fermare")
            
            self.running = True
            await self.scheduler.start_daemon()
            
        except KeyboardInterrupt:
            print("\n⏹️  Fermata richiesta dall'utente")
        except Exception as e:
            print(f"❌ Errore daemon: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Ferma il daemon"""
        if self.scheduler:
            await self.scheduler.stop()
        self.running = False
        print("✅ Daemon fermato")
    
    def _signal_handler(self, signum, frame):
        """Handler per segnali di sistema"""
        print(f"\n📡 Ricevuto segnale {signum}")
        self.running = False

async def main():
    daemon = CrawlerDaemon()
    await daemon.start()

if __name__ == "__main__":
    asyncio.run(main())