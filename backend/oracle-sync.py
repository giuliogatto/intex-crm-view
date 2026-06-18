import os
import sys
import time
import argparse
from datetime import datetime
import psycopg2

# Ensure current directory is in path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import importlib
data_connector_module = importlib.import_module("data-connector")
IntexDataConnector = data_connector_module.IntexDataConnector

from database import DatabasePool
db_pool = DatabasePool()

class OracleSyncProcess:
    def __init__(self, limit=100, mode="full"):
        self.connector = IntexDataConnector()
        self.limit = limit
        self.mode = mode
        
    def fetch_all_paginated(self, endpoint, filters=None, mappings=None):
        """
        Generic ORDS pagination fetcher. Loop using limit and offset
        until no items are returned or hasMore is False.
        """
        all_items = []
        offset = 0
        
        # Build base ORDS query if filters are passed
        ords_q = None
        if filters and mappings:
            ords_q = self.connector.build_ords_query(filters, mappings)
            
        print(f"  Fetching from {endpoint} (limit={self.limit})...")
        
        while True:
            params = {"limit": self.limit, "offset": offset}
            if ords_q:
                params["q"] = ords_q
                
            try:
                data = self.connector.fetch_data(endpoint, params)
                items = data.get('items', [])
                if not items:
                    break
                    
                all_items.extend(items)
                print(f"    Fetched {len(all_items)} records so far...")
                
                # Check ORDS pagination flag
                if not data.get('hasMore', False):
                    break
                    
                offset += self.limit
                time.sleep(0.3) # Avoid hammering the remote API gateway
            except Exception as e:
                print(f"    Error during pagination at offset {offset}: {e}")
                break
                
        return all_items

    def sync_clienti(self):
        print("\n--- Syncing Clienti ---")
        items = self.fetch_all_paginated("/ords/intex2/R07_R0236_C012456789_001W/")
        if not items:
            print("  No customers returned.")
            return
            
        conn = db_pool.get_conn()
        cursor = conn.cursor()
        
        upsert_query = """
            INSERT INTO clienti (codice, ragione_sociale)
            VALUES (%s, %s)
            ON CONFLICT (codice) DO UPDATE SET
                ragione_sociale = EXCLUDED.ragione_sociale;
        """
        
        count = 0
        for item in items:
            code = item.get('r07_cd_cliente')
            name = item.get('r07_ragione_soc')
            if code and name:
                cursor.execute(upsert_query, (str(code).strip(), name.strip()))
                count += 1
                
        conn.commit()
        cursor.close()
        db_pool.release_conn(conn)
        print(f"  Synced {count} customers.")

    def sync_articoli(self):
        print("\n--- Syncing Articoli ---")
        items = self.fetch_all_paginated("/ords/intex2/CW1_ARTICOLI_FISCALI_001W/")
        if not items:
            print("  No articles returned.")
            return
            
        conn = db_pool.get_conn()
        cursor = conn.cursor()
        
        upsert_query = """
            INSERT INTO articoli (codice, descrizione, composizione)
            VALUES (%s, %s, %s)
            ON CONFLICT (codice) DO UPDATE SET
                descrizione = EXCLUDED.descrizione,
                composizione = EXCLUDED.composizione;
        """
        
        count = 0
        for item in items:
            code = item.get('cw1_cd_articolo_fiscale')
            desc = item.get('cw1_ds_articolo_fiscale')
            if code and desc:
                # Compositions will be loaded dynamically or left blank
                cursor.execute(upsert_query, (code.strip(), desc.strip(), desc.strip()))
                count += 1
                
        conn.commit()
        cursor.close()
        db_pool.release_conn(conn)
        print(f"  Synced {count} articles.")

    def sync_fatture_and_seasons(self):
        print("\n--- Syncing Invoices & Seasons ---")
        
        # Apply filters if incremental mode is requested
        filters = {}
        mappings = {}
        if self.mode == "incremental":
            # Sync only invoices from recent years / months
            filters = {"data_inizio": datetime.now().replace(month=1, day=1).strftime('%Y-%m-%d')}
            mappings = {"date_column": "data_bolla_iso"}
            
        items = self.fetch_all_paginated("/ords/intex2/F07_003W/", filters, mappings)
        if not items:
            print("  No invoices returned.")
            return
            
        conn = db_pool.get_conn()
        cursor = conn.cursor()
        
        # 1. First extract and upsert unique seasons
        seasons = set()
        for item in items:
            s_code = item.get('ew2_cd_stagione')
            if s_code:
                seasons.add(s_code.strip())
                
        season_query = """
            INSERT INTO stagioni (codice, descrizione)
            VALUES (%s, %s)
            ON CONFLICT (codice) DO NOTHING;
        """
        for season in seasons:
            cursor.execute(season_query, (season, f"Stagione {season}"))
            
        # 2. Sync invoice headers (aggregated by disposition number)
        disposizioni = {}
        for item in items:
            disp_num = item.get('ew2_nr_disposizione')
            if not disp_num:
                continue
            disp_num = str(disp_num)
            
            # Sum up row amounts to get document total
            importo = float(item.get('f07_importo_riga_euro') or item.get('f07_importo_riga') or 0.00)
            
            if disp_num not in disposizioni:
                # Extract invoice date from iso fields
                date_str = item.get('data_bolla_iso') or item.get('d02_dt_bolla')
                date_val = datetime.now().date()
                if date_str:
                    try:
                        date_val = datetime.strptime(date_str[:10], '%Y-%m-%d').date()
                    except ValueError:
                        pass
                
                disposizioni[disp_num] = {
                    "data": date_val,
                    "codice_cliente": str(item.get('ew2_cd_cliente') or 'XXX').strip(),
                    "codice_stagione": (item.get('ew2_cd_stagione') or 'PE 12').strip(),
                    "importo_totale": 0.0,
                }
            disposizioni[disp_num]["importo_totale"] += importo
            
        header_query = """
            INSERT INTO fatture_testate (numero_disposizione, data_fattura, codice_cliente, codice_stagione, importo_totale, stato_pagamento)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (numero_disposizione) DO UPDATE SET
                data_fattura = EXCLUDED.data_fattura,
                codice_cliente = EXCLUDED.codice_cliente,
                codice_stagione = EXCLUDED.codice_stagione,
                importo_totale = EXCLUDED.importo_totale;
        """
        
        for disp_num, header in disposizioni.items():
            cursor.execute(header_query, (
                disp_num,
                header["data"],
                header["codice_cliente"],
                header["codice_stagione"],
                header["importo_totale"],
                "Aperta" # Default status
            ))
            
        # 3. Sync invoice lines
        line_query = """
            INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (numero_disposizione, riga_disposizione) DO UPDATE SET
                numero_bolla = EXCLUDED.numero_bolla,
                codice_articolo = EXCLUDED.codice_articolo,
                colore = EXCLUDED.colore,
                kg_fatturati = EXCLUDED.kg_fatturati,
                capi_fatturati = EXCLUDED.capi_fatturati,
                importo_riga = EXCLUDED.importo_riga;
        """
        
        line_count = 0
        for item in items:
            disp_num = item.get('ew2_nr_disposizione')
            riga_disp = item.get('ew2_riga_disposizione')
            if not disp_num or not riga_disp:
                continue
                
            cursor.execute(line_query, (
                str(disp_num),
                int(riga_disp),
                str(item.get('d02_nr_bolla') or '').strip() or None,
                (item.get('ew2_cd_articolo_fiscale') or 'CAPI').strip(),
                (item.get('ew2_ds_colore') or 'TUTTI').strip(),
                float(item.get('f07_kg_fatturati') or 0.0),
                int(item.get('f07_nr_capi_fatturati') or 0),
                float(item.get('f07_importo_riga_euro') or item.get('f07_importo_riga') or 0.0)
            ))
            line_count += 1
            
        conn.commit()
        cursor.close()
        db_pool.release_conn(conn)
        print(f"  Synced {len(seasons)} seasons, {len(disposizioni)} invoice headers, and {line_count} detail lines.")

    def run_sync(self):
        print(f"Starting Intex API Database Sync Process (Mode: {self.mode.upper()})...")
        start_time = time.time()
        
        try:
            self.sync_clienti()
            self.sync_articoli()
            self.sync_fatture_and_seasons()
            # In a full ERP implementation, sync_ddt and sync_offerte would also run here.
            
            elapsed = time.time() - start_time
            print(f"\nDatabase Sync completed successfully in {elapsed:.2f} seconds.")
        except Exception as e:
            print(f"\nDatabase Sync process encountered a fatal error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync remote Intex ORDS data to local TimescaleDB cache.")
    parser.add_argument(
        "--mode", 
        choices=["full", "incremental"], 
        default="full", 
        help="Sync mode: 'full' downloads everything, 'incremental' fetches only recent records."
    )
    parser.add_argument(
        "--limit", 
        type=int, 
        default=100, 
        help="Pagination batch size limit (to avoid remote timeouts)."
    )
    
    args = parser.parse_args()
    
    sync_job = OracleSyncProcess(limit=args.limit, mode=args.mode)
    sync_job.run_sync()
