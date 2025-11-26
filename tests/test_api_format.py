import sys
import os
import pandas as pd
from entsoe import EntsoePandasClient

# Add src to path to import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from config import ENTSOE_API_KEY

def test_single_call():
    if not ENTSOE_API_KEY:
        print("API Key missing")
        return

    client = EntsoePandasClient(api_key=ENTSOE_API_KEY)
    
    # Test parameters: Bulgaria to Romania for one day
    country_code_from = 'BG'
    country_code_to = 'RO'
    start = pd.Timestamp('20250101', tz='Europe/Brussels')
    end = pd.Timestamp('20251001', tz='Europe/Brussels')
    
    print(f"Querying {country_code_from} -> {country_code_to} for {start} to {end}")
    
    try:
        # query_crossborder_flows
        ts = client.query_crossborder_flows(country_code_from, country_code_to, start=start, end=end)
        
        print("\n--- Response Type ---")
        print(type(ts))
        
        print("\n--- Response Content ---")
        print(ts)
        
        print("\n--- Converted to DataFrame ---")
        if isinstance(ts, pd.Series):
            df = ts.to_frame(name='flow')
            print(df.head())
            print("\nDataFrame Info:")
            print(df.info())
        else:
            print("Response is not a Series, printing raw:")
            print(ts)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_single_call()
