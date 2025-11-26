import json
import os
import pandas as pd
import numpy as np

def generate_dummy_data():
    output_dir = 'data'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open('countries.json', 'r') as f:
        countries = json.load(f)

    start = pd.Timestamp('20230101', tz='Europe/Brussels')
    end = pd.Timestamp('20240101', tz='Europe/Brussels')
    dates = pd.date_range(start=start, end=end, freq='h')

    for country in countries:
        code_from = country['code']
        for code_to in country['neighbors']:
            # Generate random flow data
            flow = np.random.uniform(0, 1000, size=len(dates))
            df = pd.DataFrame({'timestamp': dates, 'flow': flow})
            
            filename = f"{output_dir}/flow_{code_from}_{code_to}.json"
            df.to_json(filename, orient='records', date_format='iso')
            print(f"Generated dummy data for {filename}")

if __name__ == "__main__":
    generate_dummy_data()
