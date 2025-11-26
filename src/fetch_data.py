import json
import os
import pandas as pd
from entsoe import EntsoePandasClient
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import ENTSOE_API_KEY
import time

def fetch_flow_for_month(code_from, code_to, start, end):
    """
    Fetches data for a single flow for a specific time range.
    Returns a tuple: (code_from, code_to, DataFrame or None)
    """
    try:
        # Create a new client per thread to be safe/clean
        client = EntsoePandasClient(api_key=ENTSOE_API_KEY)
        print(f"  [Thread] Fetching {code_from}->{code_to} for {start.date()} to {end.date()}...")
        ts = client.query_crossborder_flows(code_from, code_to, start=start, end=end)
        
        if ts is not None and not ts.empty:
            df = ts.to_frame(name='flow')
            df.index.name = 'timestamp'
            df.reset_index(inplace=True)
            return (code_from, code_to, df)
    except Exception as e:
        print(f"  [Error] Failed to fetch {code_from}->{code_to} for {start.date()}: {e}")
    
    return (code_from, code_to, None)

def fetch_data():
    if not ENTSOE_API_KEY:
        print("Error: API key is missing.")
        return

    # Load countries
    with open('countries.json', 'r') as f:
        countries = json.load(f)

    # Prepare output directory
    output_dir = 'data'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Define the full date range
    full_start = pd.Timestamp('20230101', tz='Europe/Brussels')
    full_end = pd.Timestamp('20251124', tz='Europe/Brussels')
    
    # Generate monthly periods
    # We want to iterate month by month.
    # pd.date_range with freq='MS' gives start of months.
    month_starts = pd.date_range(start=full_start, end=full_end, freq='MS')
    
    # Data store: key=(from, to), value=list of DataFrames
    data_store = {}

    # Initialize data store keys
    for country in countries:
        for neighbor in country['neighbors']:
            data_store[(country['code'], neighbor)] = []

    # Iterate through months
    # We need to handle the last partial month if full_end is not a month end.
    # Actually, let's just build a list of (start, end) tuples.
    periods = []
    current = full_start
    while current < full_end:
        next_month = current + pd.offsets.MonthBegin(1)
        if next_month > full_end:
            period_end = full_end
        else:
            period_end = next_month
        
        periods.append((current, period_end))
        current = next_month

    # Loop over periods
    for start, end in periods:
        print(f"\n=== Processing Month: {start.strftime('%Y-%m')} ===")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for country in countries:
                code_from = country['code']
                for code_to in country['neighbors']:
                    futures.append(
                        executor.submit(fetch_flow_for_month, code_from, code_to, start, end)
                    )
            
            # Collect results for this month
            for future in as_completed(futures):
                c_from, c_to, df = future.result()
                if df is not None:
                    data_store[(c_from, c_to)].append(df)

    # Consolidate and Save
    print("\n=== Saving Data ===")
    for (code_from, code_to), df_list in data_store.items():
        if df_list:
            full_df = pd.concat(df_list, ignore_index=True)
            # Sort just in case
            full_df.sort_values('timestamp', inplace=True)
            # Remove duplicates if any
            full_df.drop_duplicates(subset=['timestamp'], inplace=True)
            
            filename = f"{output_dir}/flow_{code_from}_{code_to}.json"
            full_df.to_json(filename, orient='records', date_format='iso')
            print(f"Saved {filename} ({len(full_df)} records)")
        else:
            print(f"No data found for {code_from}->{code_to}")

if __name__ == "__main__":
    fetch_data()
