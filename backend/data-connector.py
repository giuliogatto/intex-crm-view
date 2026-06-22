import os
import requests
import json
from dotenv import load_dotenv

# Load backend .env parameters
load_dotenv()

class IntexDataConnector:
    """
    A generic, data-agnostic connector to interface with the original Intex ORDS endpoints.
    Uses environment variables for base URL and basic authentication.
    """
    
    def __init__(self):
        # Base URL, e.g. "https://analisi.intexsrl.com"
        self.base_url = os.getenv("INTEX_BASE_URL", "https://analisi.intexsrl.com")
        self.user = os.getenv("INTEX_ENDPOINT_USER")
        self.password = os.getenv("INTEX_ENDPOINT_PASSWORD")
        
    def build_ords_query(self, filters, mappings):
        """
        Translates a dictionary of application-level search filters into an ORDS JSON query.
        
        Arguments:
        - filters: dict, containing keys like 'data_inizio', 'data_fine', 'codice_cliente', etc.
        - mappings: dict, specifying column names and query operators. E.g.:
            {
                'date_column': 'DATA_BOLLA_CLI_ISO',
                'columns': {
                    'codice_cliente': ('D02_CD_CLIENTE', 'eq'),
                    'ragione_sociale': ('RAGIONE_SOCIALE', 'like'),
                    'stagione': ('Z11_DS_STAGIONE', 'like')
                }
            }
            
        Operators supported: 'eq', 'like', 'like_prefix'
        """
        query_dict = {}
        
        # 1. Handle date range filters on the mapped date column
        date_col = mappings.get('date_column')
        iso_plain = mappings.get('iso_plain_dates', False)
        if date_col:
            start_val = filters.get('data_inizio')
            end_val = filters.get('data_fine')
            if start_val and end_val:
                if iso_plain:
                    query_dict[date_col] = {"$between": [start_val, end_val]}
                else:
                    query_dict[date_col] = {
                        "$between": [
                            {"$date": f"{start_val}T00:00:00Z"},
                            {"$date": f"{end_val}T23:59:59Z"}
                        ]
                    }
            elif start_val:
                query_dict[date_col] = {"$gte": start_val} if iso_plain else {"$gte": {"$date": f"{start_val}T00:00:00Z"}}
            elif end_val:
                query_dict[date_col] = {"$lte": end_val} if iso_plain else {"$lte": {"$date": f"{end_val}T23:59:59Z"}}
                
        # 2. Map standard filter properties to ORDS column filters
        col_mappings = mappings.get('columns', {})
        for filter_key, (col_name, op) in col_mappings.items():
            filter_val = filters.get(filter_key)
            if not filter_val or filter_val == '':
                continue
                
            if op == 'eq':
                query_dict[col_name] = filter_val
            elif op == 'like':
                query_dict[col_name] = {"$like": f"%{filter_val}%"}
            elif op == 'like_prefix':
                query_dict[col_name] = {"$like": f"{filter_val}%"}
                
        return json.dumps(query_dict) if query_dict else None

    def fetch_data(self, endpoint_path, query_params=None):
        """
        Executes a GET request to the target ORDS endpoint path, using configured auth.
        
        Arguments:
        - endpoint_path: str, e.g. "/ords/intex2/D03_DDT_RIGHE_002W/"
        - query_params: dict, optional query parameters to append (e.g. {"q": "..."})
        """
        # Construct full remote URL
        url = self.base_url.rstrip('/') + '/' + endpoint_path.lstrip('/')
        
        auth = None
        if self.user and self.password:
            auth = (self.user, self.password)
            
        try:
            response = requests.get(url, params=query_params, auth=auth, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # Raise exception with request details for easier troubleshooting
            raise RuntimeError(f"Error fetching data from remote endpoint ({url}): {e}")

# Simple CLI test runner (executes if script is run directly)
if __name__ == "__main__":
    print("Testing IntexDataConnector initialization...")
    connector = IntexDataConnector()
    print(f"Base URL: {connector.base_url}")
    print(f"Auth User: {connector.user}")
    
    # Test ORDS query compilation
    sample_filters = {
        "data_inizio": "2026-02-01",
        "data_fine": "2026-03-24",
        "codice_cliente": "64",
        "stagione": "AI"
    }
    
    sample_mappings = {
        "date_column": "DATA_BOLLA_CLI_ISO",
        "columns": {
            "codice_cliente": ("D02_CD_CLIENTE", "like_prefix"),
            "stagione": ("Z11_DS_STAGIONE", "like")
        }
    }
    
    compiled_q = connector.build_ords_query(sample_filters, sample_mappings)
    print(f"Compiled query parameter 'q': {compiled_q}")
