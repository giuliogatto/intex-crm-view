import os
import requests
import json
from dotenv import load_dotenv

load_dotenv(".env")

base_url = os.getenv("INTEX_BASE_URL", "https://analisi.intexsrl.com").rstrip('/')
user = os.getenv("INTEX_ENDPOINT_USER")
password = os.getenv("INTEX_ENDPOINT_PASSWORD")
auth = (user, password) if user and password else None

url = f"{base_url}/ords/intex2/open-api-catalog/"

print(f"Connecting to: {url}")
try:
    response = requests.get(url, auth=auth, timeout=20)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        catalog = response.json()
        print("Catalog JSON top-level keys:", list(catalog.keys()))
        # Print a small part of the catalog JSON to see the structure
        print(json.dumps(catalog, indent=2)[:1000])
    else:
        print(response.text)
except Exception as e:
    print(f"Error: {e}")
