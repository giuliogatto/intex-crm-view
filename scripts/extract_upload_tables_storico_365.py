import os
import csv
import oracledb
import paramiko
from datetime import date, datetime

# --- CONFIGURAZIONE ORACLE ---
# Equivalente sqlplus: INTEX2/SD@192.168.1.10:1521/INT2DB
ORACLE_USER = "INTEX2"
ORACLE_PASS = "SD"
ORACLE_DSN = "192.168.1.10:1521/INT2DB"

# --- CONFIGURAZIONE SERVER DEBIAN DESTINAZIONE ---
DEBIAN_HOST = "57.131.22.138"
DEBIAN_PORT = 22
DEBIAN_USER = "upload_intex"
DEBIAN_PASS = "Ncv13!AL"
# Path nel chroot SFTP (/var/data_imports -> /)
DEBIAN_REMOTE_DIR = "/intex/"

# Cartella locale temporanea su Windows
LOCAL_DIR = r"C:\Automazioni\export_temp"
os.makedirs(LOCAL_DIR, exist_ok=True)

# Finestra su data bolla cliente (filtro UI "Da/A Data Bolla").
# 14 giorni ≈ sync incrementale (come le offerte) → poche centinaia di testate.
# Per ricostruire lo storico UI alzare (es. 365) o None = export full (EW1 ~200k,
# STORICO ~670k: file grandi, upload lento).
LOOKBACK_DAYS = 365  # None = nessun filtro data (full dump)

# Anagrafica cicli: sempre full dump (come scripts/export_cicli_tables.txt).
# Non filtrare su data_ins: altrimenti i cicli "vecchi" spariscono dal DB.
EXPORT_CICLI = True


def _lookback_predicate(alias: str = "t") -> str:
    if LOOKBACK_DAYS is None:
        return "1=1"
    return f"{alias}.EW1_DATA_BOLLA_CLI >= TRUNC(SYSDATE) - {LOOKBACK_DAYS}"


def _cell(value):
    """Normalizza celle per CSV Postgres (date ISO, None → vuoto)."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.isoformat()
    return value


# Storico Disposizioni Completo (Wi@sh3):
#   STORICO_DISPOSIZIONI = griglia denormalizzata (filtri + colonne + note/descrizioni)
#   EW1 / EW2            = testata e righe sorgente (più aggiornate di STORICO)
#
# Nota: STORICO può restare indietro rispetto a EW1/EW2 (solo poche bolle recenti).
# Per questo si filtra STORICO sulle *chiavi* EW1 in finestra, non solo sulla sua
# EW1_DATA_BOLLA_CLI (spesso NULL o non allineata sulle disposizioni aperte).
#
# Offerte / Cod. Univoco (C37_PRG): full dump (~34k), indipendente dal lookback bolle.
QUERIES = {
    "ew1_testata_disposizioni.csv": f"""
        SELECT t.*
        FROM INTEX2.EW1_TESTATA_DISPOSIZIONI t
        WHERE {_lookback_predicate("t")}
    """,
    "ew2_righe_disposizioni.csv": f"""
        SELECT r.*
        FROM INTEX2.EW2_RIGHE_DISPOSIZIONI r
        WHERE EXISTS (
            SELECT 1
            FROM INTEX2.EW1_TESTATA_DISPOSIZIONI t
            WHERE t.EW1_ANNO_DISPOSIZIONE = r.EW2_ANNO_DISPOSIZIONE
              AND t.EW1_NR_DISPOSIZIONE   = r.EW2_NR_DISPOSIZIONE
              AND {_lookback_predicate("t")}
        )
    """,
    "storico_disposizioni.csv": f"""
        SELECT s.*
        FROM INTEX2.STORICO_DISPOSIZIONI s
        WHERE EXISTS (
            SELECT 1
            FROM INTEX2.EW1_TESTATA_DISPOSIZIONI t
            WHERE t.EW1_ANNO_DISPOSIZIONE = s.EW2_ANNO_DISPOSIZIONE
              AND t.EW1_NR_DISPOSIZIONE   = s.EW2_NR_DISPOSIZIONE
              AND {_lookback_predicate("t")}
        )
    """,
    "c37_testata_listini.csv": """
        SELECT t.*
        FROM INTEX2.C37_TESTATA_LISTINI t
    """,
}

# Cicli di lavorazione → Postgres (create-cicli-tables.sql).
# Header = nomi colonna Postgres (come export_cicli_tables.txt).
CICLI_QUERIES = {
    "z09_cicli_testate.csv": """
        SELECT
          Z09_CD_CLIENTE          AS codice_cliente,
          Z09_CD_ARTICOLO_CLIENTE AS codice_articolo,
          Z09_CD_CICLO            AS codice_ciclo,
          Z09_CD_CICLO_CLI        AS codice_ciclo_cli,
          Z09_CD_LINEA            AS codice_linea,
          Z09_CD_STAGIONE         AS codice_stagione,
          Z09_CD_COMPOSIZIONE     AS codice_composizione,
          Z09_ST_RECORD           AS st_record,
          Z09_DS_CICLO            AS ds_ciclo,
          Z09_DS_CICLO_BOLLE_FAT  AS ds_ciclo_bolle_fat,
          Z09_DS_APPLICAZIONE     AS ds_applicazione,
          Z09_DS_RICAMO           AS ds_ricamo,
          Z09_DS_STAMPA           AS ds_stampa,
          Z09_NOTE                AS note,
          Z09_CD_REPARTO_STAT     AS codice_reparto,
          Z09_CD_GRUPPO           AS codice_gruppo,
          Z09_NR_REVISIONE        AS nr_revisione,
          Z09_PERC_FALLOSITA      AS perc_fallosita,
          Z09_DATA_INS            AS data_ins,
          Z09_DATA_VALIDITA       AS data_validita,
          Z09_FLAG_VISIBILE       AS flag_visibile,
          Z09_FLAG_PROTOTIPO      AS flag_prototipo,
          Z09_UTENTE_INSERIMENTO  AS utente_inserimento
        FROM INTEX2.Z09_TESTATE_CICLI_LAVORAZIONE
    """,
    "z08_cicli_fasi.csv": """
        SELECT
          z8.Z08_CD_CLIENTE          AS codice_cliente,
          z8.Z08_CD_ARTICOLO_CLIENTE AS codice_articolo,
          z8.Z08_CD_CICLO            AS codice_ciclo,
          z8.Z08_CD_LINEA            AS codice_linea,
          z8.Z08_CD_STAGIONE         AS codice_stagione,
          z8.Z08_CD_COMPOSIZIONE     AS codice_composizione,
          z8.Z08_SEQUENZA            AS sequenza,
          z8.Z08_CD_FASE             AS codice_fase,
          z8.Z08_CD_MACROFASE        AS codice_macrofase,
          z8.Z08_CD_UNITA_MIS        AS codice_unita_mis,
          z8.Z08_NOTE                AS note,
          z8.Z08_ST_RECORD           AS st_record
        FROM INTEX2.Z08_CICLI_LAVORAZIONE z8
        WHERE EXISTS (
          SELECT 1
          FROM INTEX2.Z09_TESTATE_CICLI_LAVORAZIONE z9
          WHERE z9.Z09_CD_CLIENTE          = z8.Z08_CD_CLIENTE
            AND z9.Z09_CD_ARTICOLO_CLIENTE = z8.Z08_CD_ARTICOLO_CLIENTE
            AND z9.Z09_CD_CICLO            = z8.Z08_CD_CICLO
            AND z9.Z09_CD_LINEA            = z8.Z08_CD_LINEA
            AND z9.Z09_CD_STAGIONE         = z8.Z08_CD_STAGIONE
            AND z9.Z09_CD_COMPOSIZIONE     = z8.Z08_CD_COMPOSIZIONE
        )
    """,
    "z02_fasi.csv": """
        SELECT
          z2.Z02_CD_FASE AS codice_fase,
          z2.Z02_DS_FASE AS ds_fase
        FROM INTEX2.Z02_FASI_DI_LAVORO z2
        WHERE EXISTS (
          SELECT 1
          FROM INTEX2.Z08_CICLI_LAVORAZIONE z8
          WHERE z8.Z08_CD_FASE = z2.Z02_CD_FASE
            AND EXISTS (
              SELECT 1
              FROM INTEX2.Z09_TESTATE_CICLI_LAVORAZIONE z9
              WHERE z9.Z09_CD_CLIENTE          = z8.Z08_CD_CLIENTE
                AND z9.Z09_CD_ARTICOLO_CLIENTE = z8.Z08_CD_ARTICOLO_CLIENTE
                AND z9.Z09_CD_CICLO            = z8.Z08_CD_CICLO
                AND z9.Z09_CD_LINEA            = z8.Z08_CD_LINEA
                AND z9.Z09_CD_STAGIONE         = z8.Z08_CD_STAGIONE
                AND z9.Z09_CD_COMPOSIZIONE     = z8.Z08_CD_COMPOSIZIONE
            )
        )
    """,
    "r07_clienti.csv": """
        SELECT
          r.R07_CD_CLIENTE AS codice_cliente,
          r.R07_RAGIONE_SOC AS ragione_sociale
        FROM INTEX2.R07_CLIENTI r
        WHERE EXISTS (
          SELECT 1
          FROM INTEX2.Z09_TESTATE_CICLI_LAVORAZIONE z9
          WHERE z9.Z09_CD_CLIENTE = r.R07_CD_CLIENTE
        )
    """,
    "z11_stagioni.csv": """
        SELECT
          z.Z11_CD_STAGIONE AS codice_stagione,
          z.Z11_DS_STAGIONE AS ds_stagione
        FROM INTEX2.Z11_STAGIONI z
        WHERE EXISTS (
          SELECT 1
          FROM INTEX2.Z09_TESTATE_CICLI_LAVORAZIONE z9
          WHERE z9.Z09_CD_STAGIONE = z.Z11_CD_STAGIONE
        )
    """,
    "cw4_composizioni.csv": """
        SELECT
          c.CW4_CD_COMPOSIZIONE AS codice_composizione,
          c.CW4_DS_COMPOSIZIONE AS ds_composizione
        FROM INTEX2.CW4_COMPOSIZIONI c
        WHERE EXISTS (
          SELECT 1
          FROM INTEX2.Z09_TESTATE_CICLI_LAVORAZIONE z9
          WHERE z9.Z09_CD_COMPOSIZIONE = c.CW4_CD_COMPOSIZIONE
        )
    """,
    "cwa_articoli_cliente.csv": """
        SELECT
          a.CWA_CD_CLIENTE          AS codice_cliente,
          a.CWA_CD_ARTICOLO_CLIENTE AS codice_articolo,
          a.CWA_DS_ARTICOLO_CLIENTE AS ds_articolo
        FROM INTEX2.CWA_ARTICOLI_CLIENTE a
        WHERE EXISTS (
          SELECT 1
          FROM INTEX2.Z09_TESTATE_CICLI_LAVORAZIONE z9
          WHERE z9.Z09_CD_CLIENTE          = a.CWA_CD_CLIENTE
            AND z9.Z09_CD_ARTICOLO_CLIENTE = a.CWA_CD_ARTICOLO_CLIENTE
        )
    """,
    "cw0_linee.csv": """
        SELECT DISTINCT
          l.CW0_CD_CLIENTE AS codice_cliente,
          l.CW0_CD_LINEA   AS codice_linea,
          l.CW0_DS_LINEA   AS ds_linea
        FROM INTEX2.CW0_LINEA_TINTORIA l
        WHERE EXISTS (
          SELECT 1
          FROM INTEX2.Z09_TESTATE_CICLI_LAVORAZIONE z9
          WHERE z9.Z09_CD_CLIENTE = l.CW0_CD_CLIENTE
            AND z9.Z09_CD_LINEA   = l.CW0_CD_LINEA
        )
    """,
}


def export_and_send():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    files_to_upload = []

    queries = dict(QUERIES)
    if EXPORT_CICLI:
        queries.update(CICLI_QUERIES)

    # 1. Estrazione dati da Oracle
    print("Connessione ad Oracle in corso...")
    conn = oracledb.connect(user=ORACLE_USER, password=ORACLE_PASS, dsn=ORACLE_DSN)
    cursor = conn.cursor()

    for filename, query in queries.items():
        local_filepath = os.path.join(LOCAL_DIR, f"{timestamp}_{filename}")
        print(f"Esportazione: {filename}...")

        cursor.execute(query)
        # Oracle uppercasa gli alias non quotati → lowercase come header Postgres
        columns = [desc[0].lower() for desc in cursor.description]
        rows = cursor.fetchall()

        with open(local_filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            for row in rows:
                writer.writerow([_cell(v) for v in row])

        print(f"  → {len(rows)} righe")
        files_to_upload.append((local_filepath, f"{timestamp}_{filename}"))

    cursor.close()
    conn.close()

    # 2. Upload sul server Debian via SFTP
    print("Invio file al server Debian...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(DEBIAN_HOST, port=DEBIAN_PORT, username=DEBIAN_USER, password=DEBIAN_PASS)

    sftp = ssh.open_sftp()
    for local_path, remote_file in files_to_upload:
        remote_path = os.path.join(DEBIAN_REMOTE_DIR, remote_file).replace("\\", "/")
        sftp.put(local_path, remote_path)
        print(f"Caricato: {remote_file}")
        os.remove(local_path)

    sftp.close()
    ssh.close()
    print(
        "Sincronizzazione completata "
        f"(storico + c37 + {'cicli' if EXPORT_CICLI else 'senza cicli'}, timestamp={timestamp})"
    )


if __name__ == "__main__":
    export_and_send()
