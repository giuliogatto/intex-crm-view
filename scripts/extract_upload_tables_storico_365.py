import os
import csv
import oracledb
import paramiko
from datetime import datetime

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

def _lookback_predicate(alias: str = "t") -> str:
    if LOOKBACK_DAYS is None:
        return "1=1"
    return f"{alias}.EW1_DATA_BOLLA_CLI >= TRUNC(SYSDATE) - {LOOKBACK_DAYS}"

# Storico Disposizioni Completo (Wi@sh3):
#   STORICO_DISPOSIZIONI = griglia denormalizzata (filtri + colonne + note/descrizioni)
#   EW1 / EW2            = testata e righe sorgente (più aggiornate di STORICO)
#
# Nota: STORICO può restare indietro rispetto a EW1/EW2 (solo poche bolle recenti).
# Per questo si filtra STORICO sulle *chiavi* EW1 in finestra, non solo sulla sua
# EW1_DATA_BOLLA_CLI (spesso NULL o non allineata sulle disposizioni aperte).
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
}

def export_and_send():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    files_to_upload = []

    # 1. Estrazione dati da Oracle
    print("Connessione ad Oracle in corso...")
    conn = oracledb.connect(user=ORACLE_USER, password=ORACLE_PASS, dsn=ORACLE_DSN)
    cursor = conn.cursor()

    for filename, query in QUERIES.items():
        local_filepath = os.path.join(LOCAL_DIR, f"{timestamp}_{filename}")
        print(f"Esportazione: {filename}...")

        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        with open(local_filepath, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)  # Intestazioni colonne
            writer.writerows(rows)

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
        remote_path = os.path.join(DEBIAN_REMOTE_DIR, remote_file).replace('\\', '/')
        sftp.put(local_path, remote_path)
        print(f"Caricato: {remote_file}")
        # Opzionale: pulizia locale
        os.remove(local_path)

    sftp.close()
    ssh.close()
    print("Sincronizzazione storico disposizioni completata con successo!")

if __name__ == "__main__":
    export_and_send()
