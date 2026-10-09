#!/usr/bin/env python3
import json
import os
import sys
import urllib.request
import base64

API_URL = "https://analisi.intexsrl.com/ords/intex2/open-api-catalog/"
USER = "arcadia_user"
PASS = "kuru2387BECAMWQ!"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
KNOWN_ENDPOINTS_FILE = os.path.join(DATA_DIR, "known_endpoints.json")

def fetch_api_catalog():
    req = urllib.request.Request(API_URL)
    credentials = f"{USER}:{PASS}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    req.add_header("Authorization", f"Basic {encoded_credentials}")
    
    with urllib.request.urlopen(req) as response:
        if response.status == 200:
            data = json.loads(response.read().decode('utf-8'))
            return data
        else:
            raise Exception(f"HTTP Request failed with status code {response.status}")

def main():
    print("Fetching API catalog from Intex ORDS...")
    try:
        catalog = fetch_api_catalog()
    except Exception as e:
        print(f"ERROR: Failed to fetch API catalog: {e}", file=sys.stderr)
        sys.exit(1)

    items = catalog.get("items", [])
    current_endpoints = {item["name"]: item.get("links", [{}])[0].get("href", "") for item in items if "name" in item}
    current_names = set(current_endpoints.keys())

    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(KNOWN_ENDPOINTS_FILE):
        print(f"First run detected. Initializing baseline with {len(current_names)} endpoints.")
        with open(KNOWN_ENDPOINTS_FILE, "w", encoding="utf-8") as f:
            json.dump(current_endpoints, f, indent=2, sort_keys=True)
        print("Baseline saved to:", KNOWN_ENDPOINTS_FILE)
        print("\nCurrent Endpoints found:")
        for name in sorted(current_names):
            print(f"  - {name}")
        return

    with open(KNOWN_ENDPOINTS_FILE, "r", encoding="utf-8") as f:
        known_endpoints = json.load(f)

    known_names = set(known_endpoints.keys())

    new_endpoints = current_names - known_names
    removed_endpoints = known_names - current_names

    print(f"Check completed. Total current endpoints: {len(current_names)}.")
    
    if new_endpoints:
        print(f"\n🚨 ATTENZIONE: Rilevati {len(new_endpoints)} nuovi endpoint!")
        for name in sorted(new_endpoints):
            print(f"  + {name} -> {current_endpoints[name]}")
    else:
        print("Nessun nuovo endpoint rilevato.")

    if removed_endpoints:
        print(f"\nℹ️ Endpoint rimossi ({len(removed_endpoints)}):")
        for name in sorted(removed_endpoints):
            print(f"  - {name}")

    # Update known endpoints file to stay up-to-date
    if new_endpoints or removed_endpoints:
        with open(KNOWN_ENDPOINTS_FILE, "w", encoding="utf-8") as f:
            json.dump(current_endpoints, f, indent=2, sort_keys=True)
        print("\nElenco degli endpoint aggiornato in:", KNOWN_ENDPOINTS_FILE)

if __name__ == "__main__":
    main()
