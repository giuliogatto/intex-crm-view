import importlib
import os
import sys

# Ensure current directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Dynamically import data-connector (due to hyphen in name)
data_connector_module = importlib.import_module("data-connector")
IntexDataConnector = data_connector_module.IntexDataConnector

def main():
    connector = IntexDataConnector()
    
    # Query F07_003W which has season fields, since Z11_STAGIONI is no longer exposed directly
    endpoint_path = "/ords/intex2/F07_003W/"
    query_params = {"limit": 100}
    
    print(f"Connecting to: {connector.base_url.rstrip('/') + endpoint_path}")
    print("Querying remote invoice records to extract active seasons...")
    
    try:
        response_data = connector.fetch_data(endpoint_path, query_params)
        items = response_data.get('items', [])
        
        # Extract unique seasons
        seasons = set()
        for item in items:
            season_code = item.get('ew2_cd_stagione')
            if season_code:
                seasons.add(season_code.strip())
                
        sorted_seasons = sorted(list(seasons))
        
        print("\n--- Query Successful ---")
        print(f"Total Unique Seasons Extracted: {len(sorted_seasons)}")
        print("\nList of Seasons:")
        for idx, season in enumerate(sorted_seasons, start=1):
            print(f" {idx}. {season}")
            
    except Exception as e:
        print(f"\nFailed to query endpoint: {e}")

if __name__ == "__main__":
    main()
