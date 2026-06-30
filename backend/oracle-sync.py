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
from analytics import refresh_analytics_layer

db_pool = DatabasePool()

SYNC_TARGETS = ("clienti", "articoli", "fatture", "bolle", "offerte")
SYNC_METHODS = {
    "clienti": "sync_clienti",
    "articoli": "sync_articoli",
    "fatture": "sync_fatture_and_seasons",
    "bolle": "sync_ddts",
    "offerte": "sync_offerte",
}

class OracleSyncProcess:
    FATTURE_LIMIT = 100

    def __init__(self, limit=100, mode="full", start_date=None, end_date=None, sync_targets=None, skip_analytics=False):
        self.connector = IntexDataConnector()
        self.limit = limit
        self.mode = mode
        self.start_date = start_date
        self.end_date = end_date
        self.sync_targets = sync_targets or SYNC_TARGETS
        self.skip_analytics = skip_analytics

    def _incremental_start_date(self):
        if self.start_date:
            return self.start_date
        if self.mode == "incremental":
            return datetime.now().replace(month=1, day=1).strftime('%Y-%m-%d')
        return None

    def _resolve_end_date(self):
        if self.end_date:
            return self.end_date
        return datetime.now().strftime('%Y-%m-%d')

    def _build_date_filters(self, date_column, iso_plain=False):
        start_date_val = self._incremental_start_date()
        if not start_date_val:
            return {}, {}
        end_date_val = self._resolve_end_date()
        print(f"  Filtering records from {start_date_val} to {end_date_val} ({date_column})")
        mappings = {"date_column": date_column}
        if iso_plain:
            mappings["iso_plain_dates"] = True
        return (
            {"data_inizio": start_date_val, "data_fine": end_date_val},
            mappings,
        )

    @staticmethod
    def _parse_iso_date(date_str):
        if not date_str:
            return datetime.now().date()
        try:
            return datetime.strptime(str(date_str)[:10], '%Y-%m-%d').date()
        except ValueError:
            return datetime.now().date()

    @staticmethod
    def _build_numero_offerta(item):
        anno = item.get('d03_anno_cartellino')
        nr = item.get('d03_nr_cartellino')
        if anno is None or nr is None:
            return None
        try:
            anno_i = int(anno)
            nr_i = int(nr)
        except (TypeError, ValueError):
            return None
        if nr_i <= 0:
            return None
        return f"{anno_i}-{nr_i}"

    @staticmethod
    def _resolve_bolla_number(item, header_map):
        key_d02 = item.get('d03_key_d02')
        nr_bolla = header_map.get(key_d02)
        if nr_bolla:
            return nr_bolla
        nr_bolla_cli = str(item.get('ew1_nr_bolla_cli') or '').strip()
        return nr_bolla_cli or None

    @staticmethod
    def _extract_stagione_code(item):
        for key in ('ew2_cd_stagione', 'ew1_cd_stagione'):
            val = item.get(key)
            if val:
                code = str(val).strip()
                if code:
                    return code
        return None

    @staticmethod
    def _extract_stagione_descrizione(item, codice):
        desc = item.get('z11_ds_stagione')
        if desc:
            text = str(desc).strip()
            if text:
                return text
        return f"Stagione {codice}"

    def _upsert_stagione(self, cursor, codice, descrizione=None):
        if not codice:
            return
        desc = descrizione or f"Stagione {codice}"
        cursor.execute(
            """
            INSERT INTO stagioni (codice, descrizione)
            VALUES (%s, %s)
            ON CONFLICT (codice) DO UPDATE SET
                descrizione = CASE
                    WHEN stagioni.descrizione LIKE 'Stagione %%' THEN EXCLUDED.descrizione
                    ELSE stagioni.descrizione
                END
            """,
            (codice, desc),
        )

    def _apply_bolla_stagioni(self, cursor, bolla_stagioni):
        if not bolla_stagioni:
            return
        update_query = """
            UPDATE ddt_testate
            SET codice_stagione = %s
            WHERE numero_bolla = %s AND codice_stagione IS NULL
        """
        for numero_bolla, codice in bolla_stagioni.items():
            self._upsert_stagione(cursor, codice)
            cursor.execute(update_query, (codice, numero_bolla))
        bolla_stagioni.clear()

    def _backfill_stagione_codes(self):
        """
        D03_DDT_RIGHE_002W does not expose season fields; propagate codice_stagione
        from fatture -> bolle -> offerte using local link tables.
        """
        print("\n--- Backfilling stagione on bolle and offerte ---")
        conn = db_pool.get_conn()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE ddt_testate d
            SET codice_stagione = sub.codice_stagione
            FROM (
                SELECT fr.numero_bolla,
                       MIN(f.codice_stagione) AS codice_stagione
                FROM fatture_righe fr
                JOIN fatture_testate f ON f.codice_cliente = fr.codice_cliente
                                      AND f.numero_disposizione = fr.numero_disposizione
                WHERE fr.numero_bolla IS NOT NULL
                  AND f.codice_stagione IS NOT NULL
                GROUP BY fr.numero_bolla
            ) sub
            WHERE d.numero_bolla = sub.numero_bolla
              AND d.codice_stagione IS NULL
            """
        )
        bolle_updated = cursor.rowcount

        cursor.execute(
            """
            UPDATE offerte_testate o
            SET codice_stagione = sub.codice_stagione
            FROM (
                SELECT dr.numero_offerta,
                       MIN(d.codice_stagione) AS codice_stagione
                FROM ddt_righe dr
                JOIN ddt_testate d ON d.numero_bolla = dr.numero_bolla
                WHERE dr.numero_offerta IS NOT NULL
                  AND d.codice_stagione IS NOT NULL
                GROUP BY dr.numero_offerta
            ) sub
            WHERE o.numero_offerta = sub.numero_offerta
              AND o.codice_stagione IS NULL
            """
        )
        offerte_updated = cursor.rowcount

        conn.commit()
        cursor.close()
        db_pool.release_conn(conn)
        print(f"  Backfilled codice_stagione on {bolle_updated} bolle and {offerte_updated} offerte.")

    def _upsert_offerte_batch(self, cursor, offerte_headers, offerte_lines):
        if not offerte_headers and not offerte_lines:
            return

        header_query = """
            INSERT INTO offerte_testate (numero_offerta, data_offerta, codice_cliente, codice_stagione, importo_totale)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (numero_offerta) DO UPDATE SET
                data_offerta = LEAST(offerte_testate.data_offerta, EXCLUDED.data_offerta),
                codice_cliente = EXCLUDED.codice_cliente,
                codice_stagione = COALESCE(EXCLUDED.codice_stagione, offerte_testate.codice_stagione),
                importo_totale = EXCLUDED.importo_totale;
        """
        for numero_offerta, header in offerte_headers.items():
            cursor.execute(header_query, (
                numero_offerta,
                header["data_offerta"],
                header["codice_cliente"],
                header.get("codice_stagione"),
                header["importo_totale"],
            ))

        line_query = """
            INSERT INTO offerte_righe (numero_offerta, riga_num, codice_articolo, colore, quantita, prezzo_unitario, importo_riga)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (numero_offerta, riga_num) DO UPDATE SET
                codice_articolo = EXCLUDED.codice_articolo,
                colore = EXCLUDED.colore,
                quantita = GREATEST(offerte_righe.quantita, EXCLUDED.quantita),
                prezzo_unitario = EXCLUDED.prezzo_unitario,
                importo_riga = GREATEST(offerte_righe.importo_riga, EXCLUDED.importo_riga);
        """
        for line in offerte_lines.values():
            cursor.execute(line_query, (
                line["numero_offerta"],
                line["riga_num"],
                line["codice_articolo"],
                line["colore"],
                line["quantita"],
                line["prezzo_unitario"],
                line["importo_riga"],
            ))

        touched = list(offerte_headers.keys())
        if touched:
            cursor.execute(
                """
                UPDATE offerte_testate o
                SET importo_totale = COALESCE(s.totale, 0)
                FROM (
                    SELECT numero_offerta, SUM(importo_riga) AS totale
                    FROM offerte_righe
                    WHERE numero_offerta = ANY(%s)
                    GROUP BY numero_offerta
                ) s
                WHERE o.numero_offerta = s.numero_offerta
                """,
                (touched,),
            )

        offerte_headers.clear()
        offerte_lines.clear()

    def _collect_offerta_from_ddt_line(self, item, offerte_headers, offerte_lines):
        numero_offerta = self._build_numero_offerta(item)
        if not numero_offerta:
            return

        codice_cliente = str(item.get('d02_cd_cliente') or item.get('ew1_cd_cliente') or '').strip()
        if not codice_cliente:
            return

        codice_stagione = self._extract_stagione_code(item)

        data_offerta = self._parse_iso_date(
            item.get('data_bolla_cli_iso') or item.get('data_bolla_iso') or item.get('ew1_data_bolla_cli')
        )

        codice_articolo = (item.get('d03_cd_articolo') or 'CAPI').strip()
        colore = (item.get('ew2_ds_colore') or 'TUTTI').strip()
        quantita = float(
            item.get('ew2_nr_capi_caricati')
            or item.get('ew2_capi_evasi')
            or item.get('d03_capi_in_uscita')
            or 0
        )
        prezzo_unitario = float(item.get('d03_prezzo_uni_euro') or item.get('d03_prezzo_uni') or 0)
        importo_riga = float(prezzo_unitario * quantita) if prezzo_unitario else 0.0

        riga_num = item.get('d03_riga_disp_cli') or item.get('d03_riga')
        if riga_num is None:
            return
        riga_num = int(riga_num)
        line_key = (numero_offerta, riga_num)

        existing_header = offerte_headers.get(numero_offerta)
        if not existing_header:
            offerte_headers[numero_offerta] = {
                "data_offerta": data_offerta,
                "codice_cliente": codice_cliente,
                "codice_stagione": codice_stagione,
                "importo_totale": importo_riga,
            }
        else:
            if data_offerta < existing_header["data_offerta"]:
                existing_header["data_offerta"] = data_offerta
            if codice_stagione and not existing_header.get("codice_stagione"):
                existing_header["codice_stagione"] = codice_stagione
            existing_header["importo_totale"] += importo_riga

        existing_line = offerte_lines.get(line_key)
        if not existing_line:
            offerte_lines[line_key] = {
                "numero_offerta": numero_offerta,
                "riga_num": riga_num,
                "codice_articolo": codice_articolo,
                "colore": colore,
                "quantita": quantita,
                "prezzo_unitario": prezzo_unitario,
                "importo_riga": importo_riga,
            }
            return

        existing_line["quantita"] = max(existing_line["quantita"], quantita)
        existing_line["importo_riga"] = max(existing_line["importo_riga"], importo_riga)
        if prezzo_unitario:
            existing_line["prezzo_unitario"] = prezzo_unitario

    def _offerte_incremental_filters(self):
        start_date_val = self._incremental_start_date()
        if not start_date_val:
            return None, {}, {}
        filters, mappings = self._build_date_filters("EW1_DATA_BOLLA_CLI")
        return start_date_val, filters, mappings

    def sync_offerte(self):
        """
        Sync offerte_testate and offerte_righe from Oracle cartellini on DDT lines.
        In the ERP, commercial offers map to d03_anno_cartellino + d03_nr_cartellino.
        Uses the same incremental date window as DDT lines (EW1_DATA_BOLLA_CLI).
        """
        print("\n--- Syncing Offerte (Cartellini) ---")

        start_date_val, filters, mappings = self._offerte_incremental_filters()
        endpoint = "/ords/intex2/D03_DDT_RIGHE_002W/"
        ords_q = None
        if filters and mappings:
            ords_q = self.connector.build_ords_query(filters, mappings)

        conn = db_pool.get_conn()
        cursor = conn.cursor()

        offerte_headers = {}
        offerte_lines = {}
        offset = 0
        total_cartellini = 0
        uncommitted = 0

        while True:
            params = {"limit": self.limit, "offset": offset}
            if ords_q:
                params["q"] = ords_q

            try:
                data = self.connector.fetch_data(endpoint, params)
                items = data.get('items', [])
                if not items:
                    break

                latest_date = None
                for item in items:
                    if not self._build_numero_offerta(item):
                        continue

                    total_cartellini += 1
                    stagione = self._extract_stagione_code(item)
                    if stagione:
                        self._upsert_stagione(
                            cursor,
                            stagione,
                            self._extract_stagione_descrizione(item, stagione),
                        )

                    date_str = (
                        item.get('data_bolla_cli_iso')
                        or item.get('data_bolla_iso')
                        or item.get('ew1_data_bolla_cli')
                    )
                    if date_str:
                        date_str = str(date_str)[:10]
                        if not latest_date or date_str > latest_date:
                            latest_date = date_str

                    self._collect_offerta_from_ddt_line(item, offerte_headers, offerte_lines)
                    uncommitted += 1
                    if uncommitted >= 1000:
                        self._upsert_offerte_batch(cursor, offerte_headers, offerte_lines)
                        conn.commit()
                        print(f"      [Database] Committed {uncommitted} offerte records to local cache.")
                        uncommitted = 0

                date_log = f" [Latest date: {latest_date}]" if latest_date else ""
                print(f"    Processed {total_cartellini} cartellino-linked lines so far...{date_log}")

                if not data.get('hasMore', False):
                    break
                offset += self.limit
                time.sleep(0.2)
            except Exception as e:
                print(f"    Error during offerte sync at offset {offset}: {e}")
                break

        if uncommitted > 0 or offerte_headers or offerte_lines:
            self._upsert_offerte_batch(cursor, offerte_headers, offerte_lines)
            conn.commit()
            if uncommitted > 0:
                print(f"      [Database] Final Commit: {uncommitted} offerte records.")

        cursor.close()
        db_pool.release_conn(conn)
        print(f"  Synced offerte from {total_cartellini} cartellino-linked DDT lines.")
        self._backfill_stagione_codes()

    def fetch_all_paginated(self, endpoint, filters=None, mappings=None):
        """
        Generic ORDS pagination fetcher. Used for smaller tables.
        """
        all_items = []
        offset = 0
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
                
                # Log date if available
                latest_date = None
                for item in items:
                    date_str = item.get('d02_dt_bolla') or item.get('data_bolla_iso')
                    if date_str:
                        date_str = date_str[:10]
                        if not latest_date or date_str > latest_date:
                            latest_date = date_str
                            
                date_log = f" [Date: {latest_date}]" if latest_date else ""
                print(f"    Fetched {len(all_items)} records so far...{date_log}")
                
                if not data.get('hasMore', False):
                    break
                    
                offset += self.limit
                time.sleep(0.2)
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
        uncommitted = 0
        for item in items:
            code = item.get('r07_cd_cliente')
            name = item.get('r07_ragione_soc')
            if code and name:
                cursor.execute(upsert_query, (str(code).strip(), name.strip()))
                count += 1
                uncommitted += 1
                if uncommitted >= 1000:
                    conn.commit()
                    print(f"    [Database] Committed {uncommitted} customers.")
                    uncommitted = 0
                    
        if uncommitted > 0:
            conn.commit()
            print(f"    [Database] Final Commit: {uncommitted} customers.")
            
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
                cursor.execute(upsert_query, (code.strip(), desc.strip(), desc.strip()))
                count += 1
                
        conn.commit()
        cursor.close()
        db_pool.release_conn(conn)
        print(f"  Synced {count} articles.")

    def sync_fatture_and_seasons(self):
        print("\n--- Syncing Invoices & Seasons ---")
        limit = self.FATTURE_LIMIT
        print(f"  Using page size {limit} for F07_003W (DATA_BOLLA_ISO filter).")
        
        start_date_val = self._incremental_start_date()
        filters, mappings = self._build_date_filters("DATA_BOLLA_ISO", iso_plain=True) if start_date_val else ({}, {})
            
        endpoint = "/ords/intex2/F07_003W/"
        ords_q = None
        if filters and mappings:
            ords_q = self.connector.build_ords_query(filters, mappings)
            
        conn = db_pool.get_conn()
        cursor = conn.cursor()
        
        offset = 0
        total_fetched = 0
        uncommitted_count = 0
        
        disposizioni = {} # Keep running totals in memory to prevent overwrite anomalies
        
        while True:
            params = {"limit": limit, "offset": offset}
            if ords_q:
                params["q"] = ords_q
                
            try:
                data = self.connector.fetch_data(endpoint, params)
                items = data.get('items', [])
                if not items:
                    break
                    
                total_fetched += len(items)
                
                # Find the latest date in this batch
                latest_date = None
                for item in items:
                    date_str = item.get('data_bolla_iso') or item.get('d02_dt_bolla')
                    if date_str:
                        date_str = date_str[:10]
                        if not latest_date or date_str > latest_date:
                            latest_date = date_str
                
                # Log date and progress
                date_log = f" [Latest date: {latest_date}]" if latest_date else ""
                print(f"    Fetched {total_fetched} records so far...{date_log}")
                
                # 1. Sync unique seasons
                season_meta = {}
                for item in items:
                    s_code = self._extract_stagione_code(item)
                    if s_code:
                        season_meta.setdefault(
                            s_code,
                            self._extract_stagione_descrizione(item, s_code),
                        )

                for season, descrizione in season_meta.items():
                    self._upsert_stagione(cursor, season, descrizione)
                
                # 2. Update disposizioni headers running values (keyed by cliente + disposizione)
                for item in items:
                    disp_num = item.get('ew2_nr_disposizione')
                    if not disp_num:
                        continue
                    disp_num = str(disp_num)
                    codice_cliente = str(item.get('ew2_cd_cliente') or 'XXX').strip()
                    disp_key = (codice_cliente, disp_num)
                    importo = float(item.get('f07_importo_riga_euro') or item.get('f07_importo_riga') or 0.00)

                    if disp_key not in disposizioni:
                        date_str = item.get('data_bolla_iso') or item.get('d02_dt_bolla')
                        date_val = datetime.now().date()
                        if date_str:
                            try:
                                date_val = datetime.strptime(date_str[:10], '%Y-%m-%d').date()
                            except ValueError:
                                pass

                        disposizioni[disp_key] = {
                            "data": date_val,
                            "codice_cliente": codice_cliente,
                            "codice_stagione": self._extract_stagione_code(item),
                            "importo_totale": 0.0
                        }
                    elif not disposizioni[disp_key].get("codice_stagione"):
                        stagione = self._extract_stagione_code(item)
                        if stagione:
                            disposizioni[disp_key]["codice_stagione"] = stagione
                    disposizioni[disp_key]["importo_totale"] += importo

                # Upsert headers in this batch
                header_query = """
                    INSERT INTO fatture_testate (codice_cliente, numero_disposizione, data_fattura, codice_stagione, importo_totale)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (codice_cliente, numero_disposizione) DO UPDATE SET
                        data_fattura = EXCLUDED.data_fattura,
                        codice_stagione = EXCLUDED.codice_stagione,
                        importo_totale = EXCLUDED.importo_totale;
                """
                batch_keys = set()
                for item in items:
                    disp_num = item.get('ew2_nr_disposizione')
                    if not disp_num:
                        continue
                    codice_cliente = str(item.get('ew2_cd_cliente') or 'XXX').strip()
                    batch_keys.add((codice_cliente, str(disp_num)))
                for codice_cliente, disp_num in batch_keys:
                    h = disposizioni[(codice_cliente, disp_num)]
                    cursor.execute(header_query, (
                        codice_cliente,
                        disp_num,
                        h["data"],
                        h["codice_stagione"],
                        h["importo_totale"],
                    ))

                # 3. Sync invoice lines
                line_query = """
                    INSERT INTO fatture_righe (codice_cliente, numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (codice_cliente, numero_disposizione, riga_disposizione) DO UPDATE SET
                        numero_bolla = EXCLUDED.numero_bolla,
                        codice_articolo = EXCLUDED.codice_articolo,
                        colore = EXCLUDED.colore,
                        kg_fatturati = EXCLUDED.kg_fatturati,
                        capi_fatturati = EXCLUDED.capi_fatturati,
                        importo_riga = EXCLUDED.importo_riga;
                """
                for item in items:
                    disp_num = item.get('ew2_nr_disposizione')
                    riga_disp = item.get('ew2_riga_disposizione')
                    if not disp_num or not riga_disp:
                        continue

                    cursor.execute(line_query, (
                        str(item.get('ew2_cd_cliente') or 'XXX').strip(),
                        str(disp_num),
                        int(riga_disp),
                        str(item.get('d02_nr_bolla') or '').strip() or None,
                        (item.get('ew2_cd_articolo_fiscale') or 'CAPI').strip(),
                        (item.get('ew2_ds_colore') or 'TUTTI').strip(),
                        float(item.get('f07_kg_fatturati') or 0.0),
                        int(item.get('f07_nr_capi_fatturati') or 0),
                        float(item.get('f07_importo_riga_euro') or item.get('f07_importo_riga') or 0.0)
                    ))
                
                uncommitted_count += len(items)
                
                # Commit every 1000 records
                if uncommitted_count >= 1000:
                    conn.commit()
                    print(f"      [Database] Committed {uncommitted_count} records to local cache.")
                    uncommitted_count = 0
                
                if not data.get('hasMore', False):
                    break
                    
                offset += limit
                time.sleep(0.2)
            except Exception as e:
                print(f"    Error during pagination at offset {offset}: {e}")
                break
                
        # Final commit for remaining rows
        if uncommitted_count > 0:
            conn.commit()
            print(f"      [Database] Final Commit: {uncommitted_count} records committed.")
            
        cursor.close()
        db_pool.release_conn(conn)
        print(f"  Synced invoice headers and detail lines.")

    def sync_ddts(self):
        print("\n--- Syncing DDTs (Delivery Notes) ---")
        
        # 1. Fetch headers
        start_date_val = self._incremental_start_date()
        filters_h, mappings_h = self._build_date_filters("D02_DT_BOLLA") if start_date_val else ({}, {})
            
        header_map = {} # {d02_key: numero_bolla}
        
        endpoint_h = "/ords/intex2/D02_DDT_TESTATA_001W/"
        ords_q_h = None
        if filters_h and mappings_h:
            ords_q_h = self.connector.build_ords_query(filters_h, mappings_h)
            
        conn = db_pool.get_conn()
        cursor = conn.cursor()
        
        upsert_header = """
            INSERT INTO ddt_testate (numero_bolla, data_bolla, codice_cliente, codice_stagione)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (numero_bolla) DO UPDATE SET
                data_bolla = EXCLUDED.data_bolla,
                codice_cliente = EXCLUDED.codice_cliente,
                codice_stagione = COALESCE(EXCLUDED.codice_stagione, ddt_testate.codice_stagione);
        """
        
        offset = 0
        total_headers = 0
        uncommitted_h = 0
        
        while True:
            params = {"limit": self.limit, "offset": offset}
            if ords_q_h:
                params["q"] = ords_q_h
                
            try:
                data = self.connector.fetch_data(endpoint_h, params)
                items = data.get('items', [])
                if not items:
                    break
                    
                total_headers += len(items)
                print(f"    Fetched {total_headers} DDT headers so far...")
                
                for item in items:
                    key = item.get('d02_key')
                    nr_bolla = item.get('d02_nr_bolla')
                    if key is not None and nr_bolla is not None:
                        nr_bolla_str = str(nr_bolla).strip()
                        header_map[key] = nr_bolla_str
                        
                        date_str = item.get('d02_dt_bolla')
                        date_val = datetime.now().date()
                        if date_str:
                            try:
                                date_val = datetime.strptime(date_str[:10], '%Y-%m-%d').date()
                            except ValueError:
                                pass
                                
                        cursor.execute(upsert_header, (
                            nr_bolla_str,
                            date_val,
                            str(item.get('d02_cd_cliente') or 'XXX').strip(),
                            None
                        ))
                        uncommitted_h += 1
                        if uncommitted_h >= 1000:
                            conn.commit()
                            print(f"      [Database] Committed {uncommitted_h} DDT headers to local cache.")
                            uncommitted_h = 0
                            
                if not data.get('hasMore', False):
                    break
                offset += self.limit
                time.sleep(0.2)
            except Exception as e:
                print(f"    Error during DDT headers sync at offset {offset}: {e}")
                break
                
        if uncommitted_h > 0:
            conn.commit()
            print(f"      [Database] Final Commit: {uncommitted_h} DDT headers.")
            
        print(f"  Synced {total_headers} DDT headers.")
        
        # 2. Fetch lines
        if not header_map:
            print("  No DDT headers synced, skipping DDT lines.")
            cursor.close()
            db_pool.release_conn(conn)
            return
            
        print("\n  Syncing DDT Detail Lines...")
        filters_l, mappings_l = self._build_date_filters("EW1_DATA_BOLLA_CLI") if start_date_val else ({}, {})
            
        endpoint_l = "/ords/intex2/D03_DDT_RIGHE_002W/"
        ords_q_l = None
        if filters_l and mappings_l:
            ords_q_l = self.connector.build_ords_query(filters_l, mappings_l)
            
        upsert_line = """
            INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (numero_bolla, riga_num) DO UPDATE SET
                numero_disposizione = EXCLUDED.numero_disposizione,
                riga_disposizione = EXCLUDED.riga_disposizione,
                numero_offerta = EXCLUDED.numero_offerta,
                codice_articolo = EXCLUDED.codice_articolo,
                colore = EXCLUDED.colore,
                kg_consegnati = EXCLUDED.kg_consegnati,
                capi_consegnati = EXCLUDED.capi_consegnati,
                importo_riga = EXCLUDED.importo_riga;
        """
        
        offset = 0
        total_lines = 0
        uncommitted_l = 0
        bolla_stagioni = {}
        
        while True:
            params = {"limit": self.limit, "offset": offset}
            if ords_q_l:
                params["q"] = ords_q_l
                
            try:
                data = self.connector.fetch_data(endpoint_l, params)
                items = data.get('items', [])
                if not items:
                    break
                    
                total_lines += len(items)
                print(f"    Fetched {total_lines} DDT lines so far...")
                
                for item in items:
                    nr_bolla = self._resolve_bolla_number(item, header_map)
                    riga_num = item.get('d03_riga')
                    
                    if nr_bolla and riga_num is not None:
                        price = item.get('d03_prezzo_uni_euro') or item.get('d03_prezzo_uni') or 0.00
                        qty = item.get('d03_capi_in_uscita') or item.get('d03_kg_in_uscita') or 0
                        importo = float(price) * float(qty)
                        numero_offerta = self._build_numero_offerta(item)
                        stagione = self._extract_stagione_code(item)
                        if stagione and nr_bolla not in bolla_stagioni:
                            bolla_stagioni[nr_bolla] = stagione
                        
                        cursor.execute(upsert_line, (
                            nr_bolla,
                            int(riga_num),
                            str(item.get('d03_nr_disp_cli') or '').strip() or None,
                            item.get('d03_riga_disp_cli'),
                            numero_offerta,
                            (item.get('d03_cd_articolo') or 'CAPI').strip(),
                            (item.get('ew2_ds_colore') or 'TUTTI').strip(),
                            float(item.get('d03_kg_in_uscita') or 0.0),
                            int(item.get('d03_capi_in_uscita') or 0),
                            importo
                        ))
                        uncommitted_l += 1
                        if uncommitted_l >= 1000:
                            self._apply_bolla_stagioni(cursor, bolla_stagioni)
                            conn.commit()
                            print(f"      [Database] Committed {uncommitted_l} DDT lines to local cache.")
                            uncommitted_l = 0
                            
                if not data.get('hasMore', False):
                    break
                offset += self.limit
                time.sleep(0.2)
            except Exception as e:
                print(f"    Error during DDT lines sync at offset {offset}: {e}")
                break
                
        if uncommitted_l > 0 or bolla_stagioni:
            self._apply_bolla_stagioni(cursor, bolla_stagioni)
            conn.commit()
            if uncommitted_l > 0:
                print(f"      [Database] Final Commit: {uncommitted_l} DDT lines.")
            
        print(f"  Synced {total_lines} DDT detail lines.")
        cursor.close()
        db_pool.release_conn(conn)

        self._backfill_stagione_codes()

    def run_sync(self):
        targets_label = ", ".join(self.sync_targets)
        print(f"Starting Intex API Database Sync Process (Mode: {self.mode.upper()}, Targets: {targets_label})...")
        start_time = time.time()
        backfill_targets = {"fatture", "bolle", "offerte"}
        
        try:
            for target in self.sync_targets:
                getattr(self, SYNC_METHODS[target])()

            if backfill_targets.intersection(self.sync_targets):
                if "bolle" not in self.sync_targets and "offerte" not in self.sync_targets:
                    self._backfill_stagione_codes()

            if not self.skip_analytics:
                try:
                    refresh_analytics_layer(db_pool)
                except Exception as analytics_err:
                    print(f"\nWarning: analytics refresh failed: {analytics_err}")
                    print("  Apply migration: python apply_migrations.py create-analytics.sql")

            elapsed = time.time() - start_time
            print(f"\nDatabase Sync completed successfully in {elapsed:.2f} seconds.")
        except Exception as e:
            print(f"\nDatabase Sync process encountered a fatal error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sync remote Intex ORDS data to local TimescaleDB cache.",
        epilog=(
            "Examples:\n"
            "  # Sync only delivery notes (bolle) for calendar year 2026\n"
            "  python oracle-sync.py --only bolle --start-date 2026-01-01 --end-date 2026-12-31\n"
            "\n"
            "  # Incremental sync of invoices and offers only\n"
            "  python oracle-sync.py --mode incremental --only fatture offerte"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--only",
        nargs="+",
        choices=SYNC_TARGETS,
        metavar="TARGET",
        help=(
            "Sync only the listed targets (default: all). "
            "Choices: clienti, articoli, fatture (invoices + seasons), bolle (DDTs), offerte."
        ),
    )
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
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Optional start date (YYYY-MM-DD) to fetch records starting from this date. Overrides incremental default."
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="Optional end date (YYYY-MM-DD) to fetch records up to this date. Defaults to today."
    )
    parser.add_argument(
        "--skip-analytics",
        action="store_true",
        help="Skip post-sync analytics materialized view refresh.",
    )

    args = parser.parse_args()
    
    for date_arg, flag in ((args.start_date, "--start-date"), (args.end_date, "--end-date")):
        if date_arg:
            try:
                datetime.strptime(date_arg, '%Y-%m-%d')
            except ValueError:
                print(f"Error: {flag} must be in YYYY-MM-DD format.")
                sys.exit(1)
            
    sync_job = OracleSyncProcess(
        limit=args.limit,
        mode=args.mode,
        start_date=args.start_date,
        end_date=args.end_date,
        sync_targets=args.only,
        skip_analytics=args.skip_analytics,
    )
    sync_job.run_sync()
