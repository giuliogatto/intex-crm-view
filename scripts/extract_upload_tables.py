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

# Elenco tabelle da esportare con query per estrarre le modifiche recenti/ultimi record
QUERIES = {
    "c30_listino_clienti.csv": """
        SELECT * FROM (
            SELECT * FROM INTEX2.C30_LISTINO_CLIENTI 
            ORDER BY ROWNUM DESC
        ) WHERE ROWNUM <= 2000
    """,
    "c33_listino_cicli.csv": """
        SELECT * FROM (
            SELECT * FROM INTEX2.C33_LISTINO_CLIENTI_CICLI 
            ORDER BY ROWNUM DESC
        ) WHERE ROWNUM <= 2000
    """,
    "storico_disposizioni.csv": """
        SELECT * FROM (
            SELECT * FROM INTEX2.STORICO_DISPOSIZIONI 
            ORDER BY ROWNUM DESC
        ) WHERE ROWNUM <= 2000
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