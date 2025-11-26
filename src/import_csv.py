import pandas as pd
import json
import os
import sys
import re

def parse_mtu(mtu_str):
    """
    Parses the MTU string to extract the start timestamp.
    Format: "dd/mm/yyyy HH:MM:SS - dd/mm/yyyy HH:MM:SS"
    Handles optional timezone suffix like (CET) or (CEST).
    """
    try:
        start_str = mtu_str.split(' - ')[0]
        # Remove timezone info in parentheses if present, e.g. "30/03/2025 03:00:00 (CEST)" -> "30/03/2025 03:00:00"
        start_str = re.sub(r'\s*\([A-Z]+\)', '', start_str)
        return pd.to_datetime(start_str, dayfirst=True).tz_localize('Europe/Brussels', ambiguous='NaT', nonexistent='shift_forward')
    except Exception as e:
        print(f"Error parsing MTU '{mtu_str}': {e}")
        return None

def extract_country_code(area_str):
    """
    Extracts country code from area string like "BZN|RO".
    """
    if 'BZN|' in area_str:
        return area_str.split('|')[1]
    return area_str

def import_csv(csv_path):
    if not os.path.exists(csv_path):
        print(f"Error: File {csv_path} not found.")
        return

    print(f"Reading {csv_path}...")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    # Check columns
    required_columns = ["MTU", "Out Area", "In Area", "Physical Flow (MW)"]
    if not all(col in df.columns for col in required_columns):
        print(f"Error: CSV must contain columns: {required_columns}")
        return

    output_dir = 'data'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Pre-process data
    print("Processing data...")
    
    # Parse timestamps
    df['timestamp'] = df['MTU'].apply(parse_mtu)
    df = df.dropna(subset=['timestamp'])

    # Extract country codes
    df['from_code'] = df['Out Area'].apply(extract_country_code)
    df['to_code'] = df['In Area'].apply(extract_country_code)

    # Clean flow data
    # Replace 'n/e' or '-' with NaN and drop
    df['flow'] = pd.to_numeric(df['Physical Flow (MW)'], errors='coerce')
    df = df.dropna(subset=['flow'])

    # Group by country pair
    grouped = df.groupby(['from_code', 'to_code'])

    for (from_code, to_code), group in grouped:
        # Prepare new data
        new_data = group[['timestamp', 'flow']].copy()
        new_data.sort_values('timestamp', inplace=True)
        
        filename = f"{output_dir}/flow_{from_code}_{to_code}.json"
        
        combined_df = new_data
        
        # Load existing data if available
        if os.path.exists(filename):
            try:
                existing_df = pd.read_json(filename)
                if not existing_df.empty:
                    # Ensure timestamp is datetime
                    if 'timestamp' in existing_df.columns:
                        existing_df['timestamp'] = pd.to_datetime(existing_df['timestamp'])
                        # Combine
                        combined_df = pd.concat([existing_df, new_data])
                        # Drop duplicates (keep last/newest or first? Let's keep new one if overlap, but drop_duplicates keeps first by default. 
                        # If we want to overwrite, we should sort and keep last.
                        # Let's assume we want to merge and keep unique timestamps.
                        combined_df.drop_duplicates(subset=['timestamp'], keep='last', inplace=True)
                        combined_df.sort_values('timestamp', inplace=True)
            except ValueError:
                print(f"Warning: Could not read existing {filename}, overwriting.")

        # Save
        combined_df.to_json(filename, orient='records', date_format='iso')
        print(f"Updated {filename} with {len(new_data)} records (Total: {len(combined_df)})")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python src/import_csv.py <path_to_csv>")
    else:
        import_csv(sys.argv[1])
