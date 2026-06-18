import os
import requests
from dotenv import load_dotenv

load_dotenv()

base_url = os.getenv("INTEX_BASE_URL", "https://analisi.intexsrl.com").rstrip('/')
user = os.getenv("INTEX_ENDPOINT_USER")
password = os.getenv("INTEX_ENDPOINT_PASSWORD")
auth = (user, password) if user and password else None

urls = {
    "Clienti": f"{base_url}/ords/intex2/R07_R0236_C012456789_001W/?limit=1",
    "Articoli": f"{base_url}/ords/intex2/CW1_ARTICOLI_FISCALI_001W/?limit=1",
    "DDT": f"{base_url}/ords/intex2/D02_DDT_TESTATA_001W/?limit=1"
}

for name, url in urls.items():
    try:
        response = requests.get(url, auth=auth, timeout=15)
        print(f"\n--- {name} View (Status: {response.status_code}) ---")
        if response.status_code == 200:
            items = response.json().get('items', [])
            if items:
                for k, v in items[0].items():
                    print(f"  {k}: {v}")
            else:
                print("  No items returned.")
    except Exception as e:
        print(f"Error for {name}: {e}")
