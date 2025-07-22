#!/usr/bin/env python3
"""
Script per pulire completamente i database PostgreSQL e Weaviate
Riporta il sistema ad uno stato clean per il crawler
"""

import sys
import os
import asyncio
from typing import List

# Aggiungi src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.config import get_database_config, get_weaviate_config
from core.domain_manager import DomainManager
from core.vector_db_manager import VectorDBManager
from core.storage.link_database import LinkDatabase
import weaviate

class DatabaseCleaner:
    """Classe per pulire completamente i database"""
    
    def __init__(self):
        self.domain_manager = DomainManager()
        self.link_db = LinkDatabase()
        self.weaviate_client = None
        
    async def clean_all(self, confirm: bool = False):
        """
        Pulisce completamente entrambi i database
        
        Args:
            confirm: Deve essere True per confermare l'operazione (IRREVERSIBILE!)
        """
        if not confirm:
            print("❌ ERRORE: Operazione di pulizia richiede confirm=True")
            print("   Questa operazione è IRREVERSIBILE e cancellerà TUTTI i dati!")
            return False
            
        print("🧹 INIZIO PULIZIA COMPLETA DATABASE")
        print("=" * 60)
        
        try:
            # 1. Pulisci PostgreSQL
            await self.clean_postgresql(confirm=True)
            
            # 2. Pulisci Weaviate
            await self.clean_weaviate(confirm=True)
            
            print("=" * 60)
            print("✅ PULIZIA COMPLETA TERMINATA CON SUCCESSO!")
            print("   I database sono ora in stato clean e pronti per il crawler")
            return True
            
        except Exception as e:
            print(f"❌ ERRORE durante la pulizia: {e}")
            return False
        finally:
            await self.cleanup()
    
    async def clean_postgresql(self, confirm: bool = False):
        """Pulisce completamente il database PostgreSQL"""
        if not confirm:
            print("❌ Pulizia PostgreSQL richiede confirm=True")
            return False
            
        print("🗄️  PULIZIA POSTGRESQL")
        print("-" * 40)
        
        try:
            await self.link_db.connect()
            
            # Conta record prima della pulizia
            sites_count = await self.link_db.db.site.count()
            links_count = await self.link_db.db.discoveredlink.count()
            
            print(f"📊 Stato attuale PostgreSQL:")
            print(f"   • Siti: {sites_count}")
            print(f"   • Link: {links_count}")
            
            if sites_count == 0 and links_count == 0:
                print("✅ PostgreSQL già pulito")
                return True
            
            # Pulizia in ordine (rispetta le foreign key)
            print("🗑️  Eliminazione dati...")
            
            # 1. Elimina tutti i link
            deleted_links = await self.link_db.db.discoveredlink.delete_many()
            print(f"   ✅ Eliminati {deleted_links} link")
            
            # 2. Elimina tutti i siti
            deleted_sites = await self.link_db.db.site.delete_many()
            print(f"   ✅ Eliminati {deleted_sites} siti")
            
            # 3. Reset sequenze auto-increment (opzionale)
            await self.link_db.db.execute_raw('ALTER SEQUENCE "Site_id_seq" RESTART WITH 1')
            await self.link_db.db.execute_raw('ALTER SEQUENCE "DiscoveredLink_id_seq" RESTART WITH 1')
            print("   ✅ Reset sequenze auto-increment")
            
            print("✅ PostgreSQL pulito completamente")
            return True
            
        except Exception as e:
            print(f"❌ Errore pulizia PostgreSQL: {e}")
            raise
    
    async def list_weaviate_collections(self):
        """Lista tutte le collezioni Weaviate disponibili"""
        print("🔍 COLLEZIONI WEAVIATE DISPONIBILI")
        print("-" * 40)
        
        vector_manager = None
        try:
            # Inizializza client Weaviate se non già fatto
            if not self.weaviate_client:
                vector_manager = VectorDBManager(environment='dev')
                vector_manager.init_weaviate_client()
                self.weaviate_client = vector_manager.weaviate_client
            
            # Ottieni tutte le collezioni esistenti
            all_collections = self.weaviate_client.collections.list_all()
            tanea_collections = [name for name in all_collections.keys() if name.startswith('Tanea_')]
            other_collections = [name for name in all_collections.keys() if not name.startswith('Tanea_')]
            
            print(f"📊 Stato attuale Weaviate:")
            print(f"   • Collezioni Tanea: {len(tanea_collections)}")
            print(f"   • Altre collezioni: {len(other_collections)}")
            print()
            
            all_collections_list = []
            
            if tanea_collections:
                print("🎯 Collezioni Tanea:")
                for collection_name in tanea_collections:
                    try:
                        collection = self.weaviate_client.collections.get(collection_name)
                        count = collection.aggregate.over_all(total_count=True).total_count
                        domain_id = self.domain_manager.get_domain_by_index(collection_name)
                        all_collections_list.append(collection_name)
                        current_num = len(all_collections_list)
                        print(f"   {current_num:2d}. {collection_name}: {count} documenti (dominio: {domain_id or 'unknown'})")
                    except Exception as e:
                        all_collections_list.append(collection_name)
                        current_num = len(all_collections_list)
                        print(f"   {current_num:2d}. {collection_name}: errore conteggio ({e})")
            
            if other_collections:
                print()
                print("📋 Altre collezioni:")
                for collection_name in other_collections:
                    try:
                        collection = self.weaviate_client.collections.get(collection_name)
                        count = collection.aggregate.over_all(total_count=True).total_count
                        all_collections_list.append(collection_name)
                        current_num = len(all_collections_list)
                        print(f"   {current_num:2d}. {collection_name}: {count} documenti")
                    except Exception as e:
                        all_collections_list.append(collection_name)
                        current_num = len(all_collections_list)
                        print(f"   {current_num:2d}. {collection_name}: errore conteggio ({e})")
            
            if not tanea_collections and not other_collections:
                print("✅ Nessuna collezione trovata in Weaviate")
            
            return all_collections_list
            
        except Exception as e:
            print(f"❌ Errore elenco collezioni Weaviate: {e}")
            return []
        finally:
            # Assicurati che il vector_manager venga pulito se creato localmente
            if vector_manager and hasattr(vector_manager, 'weaviate_client'):
                try:
                    vector_manager.weaviate_client.close()
                except:
                    pass
    
    async def delete_specific_collection(self, collection_name: str = None):
        """Elimina una collezione specifica di Weaviate"""
        print("🗑️  ELIMINAZIONE COLLEZIONE SPECIFICA")
        print("-" * 40)
        
        vector_manager = None
        try:
            # Inizializza client Weaviate se non già fatto
            if not self.weaviate_client:
                vector_manager = VectorDBManager(environment='dev')
                vector_manager.init_weaviate_client()
                self.weaviate_client = vector_manager.weaviate_client
            
            # Lista collezioni disponibili
            available_collections = await self.list_weaviate_collections()
            
            if not available_collections:
                print("❌ Nessuna collezione disponibile per l'eliminazione")
                return False
            
            # Se non specificata, chiedi quale collezione eliminare
            if not collection_name:
                print()
                print("🎯 Seleziona la collezione da eliminare:")
                print(f"   💡 Usa i numeri da 1 a {len(available_collections)} mostrati sopra")
                print("   ❌ Scrivi 0 per annullare")
                print()
                while True:
                    try:
                        choice = input("Inserisci il numero della collezione: ").strip()
                        if choice == "0":
                            print("❌ Operazione annullata")
                            return False
                        
                        choice_idx = int(choice) - 1
                        if 0 <= choice_idx < len(available_collections):
                            collection_name = available_collections[choice_idx]
                            print(f"✅ Selezionata collezione: {collection_name}")
                            break
                        else:
                            print(f"❌ Numero non valido. Inserisci un numero tra 1 e {len(available_collections)}")
                    except ValueError:
                        print("❌ Inserisci un numero valido")
            
            # Verifica che la collezione esista
            if collection_name not in available_collections:
                print(f"❌ Collezione '{collection_name}' non trovata")
                return False
            
            # Chiedi conferma
            try:
                collection = self.weaviate_client.collections.get(collection_name)
                count = collection.aggregate.over_all(total_count=True).total_count
                print(f"")
                print(f"⚠️  ATTENZIONE: Stai per eliminare la collezione:")
                print(f"   📝 Nome: {collection_name}")
                print(f"   📊 Documenti: {count}")
                print(f"   🗑️  Questa operazione è IRREVERSIBILE!")
                print()
                
                confirm = input("Conferma eliminazione? Scrivi 'DELETE' per confermare: ").strip()
                if confirm != "DELETE":
                    print("❌ Eliminazione annullata - conferma non valida")
                    return False
                
            except Exception as e:
                print(f"❌ Errore verifica collezione: {e}")
                return False
            
            # Elimina la collezione
            print(f"🗑️  Eliminazione collezione {collection_name}...")
            self.weaviate_client.collections.delete(collection_name)
            print(f"✅ Collezione '{collection_name}' eliminata con successo")
            return True
            
        except Exception as e:
            print(f"❌ Errore eliminazione collezione: {e}")
            return False
        finally:
            # Assicurati che il vector_manager venga pulito se creato localmente
            if vector_manager and hasattr(vector_manager, 'weaviate_client'):
                try:
                    vector_manager.weaviate_client.close()
                except:
                    pass
    
    async def clean_weaviate(self, confirm: bool = False):
        """Pulisce completamente Weaviate (tutti gli index domini)"""
        if not confirm:
            print("❌ Pulizia Weaviate richiede confirm=True")
            return False
            
        print("🔍 PULIZIA WEAVIATE")
        print("-" * 40)
        
        try:
            # Inizializza client Weaviate
            vector_manager = VectorDBManager(environment='dev')
            vector_manager.init_weaviate_client()
            self.weaviate_client = vector_manager.weaviate_client
            
            # Ottieni tutte le collezioni esistenti
            all_collections = self.weaviate_client.collections.list_all()
            tanea_collections = [name for name in all_collections.keys() if name.startswith('Tanea_')]
            
            print(f"📊 Stato attuale Weaviate:")
            print(f"   • Collezioni Tanea trovate: {len(tanea_collections)}")
            
            if not tanea_collections:
                print("✅ Weaviate già pulito (nessuna collezione Tanea)")
                return True
            
            # Mostra collezioni da eliminare
            for collection_name in tanea_collections:
                try:
                    collection = self.weaviate_client.collections.get(collection_name)
                    count = collection.aggregate.over_all(total_count=True).total_count
                    domain_id = self.domain_manager.get_domain_by_index(collection_name)
                    print(f"   • {collection_name}: {count} documenti (dominio: {domain_id or 'unknown'})")
                except Exception as e:
                    print(f"   • {collection_name}: errore conteggio ({e})")
            
            # Elimina tutte le collezioni Tanea
            print("🗑️  Eliminazione collezioni...")
            deleted_count = 0
            
            for collection_name in tanea_collections:
                try:
                    self.weaviate_client.collections.delete(collection_name)
                    print(f"   ✅ Eliminata collezione: {collection_name}")
                    deleted_count += 1
                except Exception as e:
                    print(f"   ❌ Errore eliminazione {collection_name}: {e}")
            
            print(f"✅ Weaviate pulito: {deleted_count}/{len(tanea_collections)} collezioni eliminate")
            return True
            
        except Exception as e:
            print(f"❌ Errore pulizia Weaviate: {e}")
            raise
    
    async def create_fresh_schemas(self):
        """Crea gli schemi Weaviate per tutti i domini attivi"""
        print("🏗️  CREAZIONE SCHEMI DOMINI ATTIVI")
        print("-" * 40)
        
        try:
            # Ottieni domini attivi
            active_domains = self.domain_manager.get_domain_list(active_only=True)
            print(f"📋 Domini attivi da configurare: {active_domains}")
            
            if not active_domains:
                print("⚠️  Nessun dominio attivo trovato")
                return False
            
            # Crea schemi per domini attivi
            vector_manager = VectorDBManager(environment='dev')
            if not vector_manager.weaviate_client:
                vector_manager.init_weaviate_client()
            
            created_count = 0
            for domain_id in active_domains:
                try:
                    vector_manager.create_domain_schema(domain_id)
                    index_name = self.domain_manager.get_weaviate_index(domain_id, 'dev')
                    print(f"   ✅ Creato schema per dominio '{domain_id}': {index_name}")
                    created_count += 1
                except Exception as e:
                    print(f"   ❌ Errore creazione schema per '{domain_id}': {e}")
            
            print(f"✅ Creati {created_count}/{len(active_domains)} schemi domini")
            return created_count > 0
            
        except Exception as e:
            print(f"❌ Errore creazione schemi: {e}")
            return False
    
    async def verify_clean_state(self):
        """Verifica che i database siano in stato clean"""
        print("🔍 VERIFICA STATO CLEAN")
        print("-" * 40)
        
        postgresql_clean = False
        weaviate_clean = False
        
        try:
            # Verifica PostgreSQL
            print("📊 PostgreSQL:")
            try:
                await self.link_db.connect()
                sites_count = await self.link_db.db.site.count()
                links_count = await self.link_db.db.discoveredlink.count()
                
                print(f"   • Siti: {sites_count}")
                print(f"   • Link: {links_count}")
                postgresql_clean = (sites_count == 0 and links_count == 0)
                
            except Exception as pg_error:
                print(f"   ❌ Errore connessione PostgreSQL: {pg_error}")
                print("   ℹ️  Assicurati che PostgreSQL sia in esecuzione e DATABASE_URL sia configurato")
                postgresql_clean = None
            
            # Verifica Weaviate
            print("📊 Weaviate:")
            try:
                if not self.weaviate_client:
                    vector_manager = VectorDBManager(environment='dev')
                    vector_manager.init_weaviate_client()
                    self.weaviate_client = vector_manager.weaviate_client
                
                all_collections = self.weaviate_client.collections.list_all()
                tanea_collections = [name for name in all_collections.keys() if name.startswith('Tanea_')]
                
                print(f"   • Collezioni Tanea: {len(tanea_collections)}")
                
                if tanea_collections:
                    for collection_name in tanea_collections:
                        try:
                            collection = self.weaviate_client.collections.get(collection_name)
                            count = collection.aggregate.over_all(total_count=True).total_count
                            print(f"     - {collection_name}: {count} documenti")
                        except:
                            print(f"     - {collection_name}: errore conteggio")
                
                # Stato clean = PostgreSQL vuoto E solo schemi vuoti in Weaviate per domini attivi
                active_domains = self.domain_manager.get_domain_list(active_only=True)
                expected_collections = {
                    self.domain_manager.get_weaviate_index(domain, 'dev') 
                    for domain in active_domains
                }
                
                weaviate_clean = set(tanea_collections) == expected_collections
                
            except Exception as wv_error:
                print(f"   ❌ Errore connessione Weaviate: {wv_error}")
                print("   ℹ️  Assicurati che Weaviate sia in esecuzione su http://localhost:8080")
                weaviate_clean = None
            
            # Valutazione finale
            if postgresql_clean is True and weaviate_clean is True:
                print("✅ STATO CLEAN VERIFICATO - Sistema pronto per il crawler")
                return True
            elif postgresql_clean is None or weaviate_clean is None:
                print("⚠️  VERIFICA INCOMPLETA - Alcuni servizi non disponibili")
                return False
            else:
                if not postgresql_clean:
                    print("❌ PostgreSQL non è clean")
                if not weaviate_clean:
                    print("❌ Weaviate non è in stato clean")
                return False
                
        except Exception as e:
            print(f"❌ Errore verifica stato: {e}")
            return False
    
    async def cleanup(self):
        """Chiude tutte le connessioni"""
        try:
            # Chiudi connessione PostgreSQL
            if hasattr(self, 'link_db') and self.link_db:
                try:
                    await self.link_db.disconnect()
                except Exception as e:
                    print(f"Errore chiusura PostgreSQL: {e}")
            
            # Chiudi connessione Weaviate
            if hasattr(self, 'weaviate_client') and self.weaviate_client:
                try:
                    self.weaviate_client.close()
                    self.weaviate_client = None
                except Exception as e:
                    print(f"Errore chiusura Weaviate: {e}")
                    
        except Exception as e:
            print(f"Errore durante cleanup: {e}")

async def main():
    """Funzione principale con menu interattivo"""
    cleaner = DatabaseCleaner()
    
    print("🧹 DATABASE CLEANER - Tanea News System")
    print("=" * 60)
    print()
    print("ATTENZIONE: Questa operazione è IRREVERSIBILE!")
    print("Cancellerà TUTTI i dati dai database PostgreSQL e Weaviate")
    print()
    
    # Menu opzioni
    print("Opzioni disponibili:")
    print("1. 🔍 Verifica stato attuale database")
    print("2. 🧹 Pulizia COMPLETA (PostgreSQL + Weaviate)")
    print("3. 🗄️  Pulizia solo PostgreSQL")
    print("4. 🔍 Pulizia solo Weaviate")
    print("5. 🏗️  Crea schemi domini attivi (dopo pulizia)")
    print("6. ✅ Procedura completa (pulizia + schemi)")
    print("7. 📋 Lista collezioni Weaviate")
    print("8. 🗑️  Elimina collezione specifica Weaviate")
    print("0. ❌ Annulla")
    print()
    
    try:
        choice = input("Seleziona un'opzione (0-8): ").strip()
        
        if choice == "0":
            print("❌ Operazione annullata")
            return
        
        elif choice == "1":
            await cleaner.verify_clean_state()
        
        elif choice == "2":
            confirm = input("⚠️  CONFERMA pulizia COMPLETA? Scrivi 'CLEAN' per confermare: ").strip()
            if confirm == "CLEAN":
                await cleaner.clean_all(confirm=True)
            else:
                print("❌ Pulizia annullata - conferma non valida")
        
        elif choice == "3":
            confirm = input("⚠️  CONFERMA pulizia PostgreSQL? Scrivi 'CLEAN' per confermare: ").strip()
            if confirm == "CLEAN":
                await cleaner.clean_postgresql(confirm=True)
            else:
                print("❌ Pulizia PostgreSQL annullata")
        
        elif choice == "4":
            confirm = input("⚠️  CONFERMA pulizia Weaviate? Scrivi 'CLEAN' per confermare: ").strip()
            if confirm == "CLEAN":
                await cleaner.clean_weaviate(confirm=True)
            else:
                print("❌ Pulizia Weaviate annullata")
        
        elif choice == "5":
            await cleaner.create_fresh_schemas()
        
        elif choice == "6":
            confirm = input("⚠️  CONFERMA procedura COMPLETA (pulizia + schemi)? Scrivi 'RESET' per confermare: ").strip()
            if confirm == "RESET":
                print("🚀 INIZIO PROCEDURA COMPLETA")
                success = await cleaner.clean_all(confirm=True)
                if success:
                    print("\n🏗️  Creazione schemi per domini attivi...")
                    await cleaner.create_fresh_schemas()
                    print("\n🔍 Verifica finale...")
                    await cleaner.verify_clean_state()
            else:
                print("❌ Procedura completa annullata")
        
        elif choice == "7":
            await cleaner.list_weaviate_collections()
        
        elif choice == "8":
            await cleaner.delete_specific_collection()
        
        else:
            print("❌ Opzione non valida")
    
    except KeyboardInterrupt:
        print("\n❌ Operazione interrotta dall'utente")
    except Exception as e:
        print(f"❌ Errore: {e}")
    finally:
        await cleaner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())