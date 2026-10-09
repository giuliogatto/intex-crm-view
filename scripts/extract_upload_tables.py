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
DEBIAN_HOST = "100.a.b.c"  # IP Tailscale del tuo server Debian
DEBIAN_PORT = 22
DEBIAN_USER = "upload_intex"
DEBIAN_PASS = "Ncv13!AL"
# Path nel chroot SFTP (/var/data_imports -> /)
DEBIAN_REMOTE_DIR = "/intex/"

# Cartella locale temporanea su Windows
LOCAL_DIR = r"C:\Automazioni\export_temp"
os.makedirs(LOCAL_DIR, exist_ok=True)

# Finestra incrementale (giorni). Vedi documentation/analisi-export-offerte.md
LOOKBACK_DAYS = 14

# Offerte commerciali Wi@sh3: testate (C37_001W, cliente incluso) + righe fasi (C38+Z08+Z02)
QUERIES = {
    "c37_offerte_testate.csv": f"""
        SELECT v.*
        FROM INTEX2.C37_001W v
        WHERE v.C37_PRG IS NOT NULL
          AND v.C37_CD_STAGIONE NOT IN ('pe/ai', '*')
          AND v.Z09_DATA_INS >= TRUNC(SYSDATE) - {LOOKBACK_DAYS}
    """,
    "c38_offerte_righe.csv": f"""
        SELECT r.*,
               z8.Z08_CD_FASE,
               z2.Z02_DS_FASE,
               z8.Z08_CD_UNITA_MIS
        FROM INTEX2.C37_TESTATA_LISTINI t
        JOIN INTEX2.C38_RIGHE_LISTINI r
          ON  r.C38_CD_CLIENTE      = t.C37_CD_CLIENTE
          AND r.C38_CD_LINEA        = t.C37_CD_LINEA
          AND r.C38_CD_STAGIONE     = t.C37_CD_STAGIONE
          AND r.C38_CD_COMPOSIZIONE = t.C37_CD_COMPOSIZIONE
          AND r.C38_CD_ARTICOLO     = t.C37_CD_ARTICOLO
          AND r.C38_CD_CICLO        = t.C37_CD_CICLO
          AND r.C38_CD_VALUTA       = t.C37_CD_VALUTA
        LEFT JOIN INTEX2.Z08_CICLI_LAVORAZIONE z8
          ON  z8.Z08_CD_CLIENTE          = t.C37_CD_CLIENTE
          AND z8.Z08_CD_ARTICOLO_CLIENTE = t.C37_CD_ARTICOLO
          AND z8.Z08_CD_CICLO            = t.C37_CD_CICLO
          AND z8.Z08_CD_LINEA            = t.C37_CD_LINEA
          AND z8.Z08_CD_STAGIONE         = t.C37_CD_STAGIONE
          AND z8.Z08_CD_COMPOSIZIONE     = t.C37_CD_COMPOSIZIONE
          AND z8.Z08_SEQUENZA            = r.C38_SEQUENZA
        LEFT JOIN INTEX2.Z02_FASI_DI_LAVORO z2
          ON z2.Z02_CD_FASE = z8.Z08_CD_FASE
        WHERE t.C37_PRG IS NOT NULL
          AND t.C37_CD_STAGIONE NOT IN ('pe/ai', '*')
          AND EXISTS (
                SELECT 1 FROM INTEX2.C37_001W v
                WHERE v.C37_CD_CLIENTE      = t.C37_CD_CLIENTE
                  AND v.C37_CD_LINEA        = t.C37_CD_LINEA
                  AND v.C37_CD_STAGIONE     = t.C37_CD_STAGIONE
                  AND v.C37_CD_COMPOSIZIONE = t.C37_CD_COMPOSIZIONE
                  AND v.C37_CD_ARTICOLO     = t.C37_CD_ARTICOLO
                  AND v.C37_CD_CICLO        = t.C37_CD_CICLO
                  AND v.C37_CD_VALUTA       = t.C37_CD_VALUTA
                  AND v.Z09_DATA_INS >= TRUNC(SYSDATE) - {LOOKBACK_DAYS}
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
            writer.writerow(columns) # Intestazioni colonne
            writer.writerows(rows)

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
    print("Sincronizzazione completata con successo!")

if __name__ == "__main__":
    export_and_send()