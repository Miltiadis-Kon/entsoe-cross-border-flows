import os
from dotenv import load_dotenv

load_dotenv()

ENTSOE_API_KEY = os.getenv("ENTSOE_API_KEY")

if not ENTSOE_API_KEY:
    print("WARNING: ENTSOE_API_KEY not found in environment variables. Data fetching will fail.")
