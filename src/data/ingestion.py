import os
import io
import time
import pandas as pd
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv() # Extract credentials from secure local system .env configurations

DATA_GOV_IN_RESOURCE_ID = os.getenv(
    "DATA_GOV_IN_RESOURCE_ID",
    "9ef84268-d588-465a-a308-a864a43d0070",
)
DATA_GOV_IN_URL = f"https://api.data.gov.in/resource/{DATA_GOV_IN_RESOURCE_ID}"
API_KEY = os.getenv("DATA_GOV_IN_API_KEY")
DATA_GOV_HEADERS = {
    "User-Agent": "Mozilla/5.0 (KrishiBazar-AI data client)",
    "Accept": "application/json",
}

# Supabase Storage Configuration Elements
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
BUCKET_NAME = "mandi-vault"
FILE_NAME = "cleaned_orissa_mandi.csv"

def get_supabase_client() -> Client:
    """Initializes the live web connection channel link to Supabase Cloud infrastructure."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for ingestion writes.")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def fetch_paginated_records_for_state(state_name: str) -> pd.DataFrame:
    """Executes a pagination loop over the Data.gov.in REST gateway to capture all day records."""
    if not API_KEY:
        raise ValueError("DATA_GOV_IN_API_KEY is not configured.")

    all_records = []
    limit = 1000
    offset = 0
    total_records = None

    print(f"📡 Querying government network streams for state entry: '{state_name}'...")

    while total_records is None or offset < total_records:
        params = {
            "api-key": API_KEY, "format": "json", "offset": offset, "limit": limit, "filters[state.keyword]": state_name
        }
        for attempt in range(1, 4):
            try:
                response = requests.get(
                    DATA_GOV_IN_URL,
                    params=params,
                    headers=DATA_GOV_HEADERS,
                    timeout=(10, 60),
                )
                if response.status_code != 200:
                    if response.status_code in {429, 500, 502, 503, 504} and attempt < 3:
                        time.sleep(attempt * 2)
                        continue
                    raise RuntimeError(
                        f"Data.gov.in request failed for {state_name}: "
                        f"HTTP {response.status_code} - {response.text[:300]}"
                    )
                payload = response.json()
                if not isinstance(payload, dict) or "records" not in payload:
                    raise RuntimeError(
                        f"Data.gov.in returned an unexpected response for {state_name}."
                    )
                if total_records is None:
                    total_records = int(payload.get("total", 0))
                    print(f"📊 Total dynamic records detected for '{state_name}': {total_records}")
                records = payload.get("records", [])
                if not records:
                    return pd.DataFrame(all_records)
                all_records.extend(records)
                offset += limit
                time.sleep(0.5)
                break
            except (requests.RequestException, ValueError) as error:
                if attempt == 3:
                    raise RuntimeError(
                        f"Data.gov.in request failed for {state_name} after 3 attempts: {error}"
                    ) from error
                time.sleep(attempt * 2)
    return pd.DataFrame(all_records)

def run_production_ingestion():
    print("⏳ [SUPABASE PRODUCTION MODE] Triggering Cloud Ingestion Pipeline Lifecycle...")
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise SystemExit(
            "Supabase ingestion writes require SUPABASE_URL and "
            "SUPABASE_SERVICE_ROLE_KEY in .env or GitHub Actions secrets."
        )
    
    df_orissa = fetch_paginated_records_for_state("Orissa")
    df_odisha = fetch_paginated_records_for_state("Odisha")
    df_new = pd.concat([df_orissa, df_odisha], ignore_index=True)
    
    if df_new.empty:
        print("📅 Info: No new mandi records published today. Cloud storage matrix preserved.")
        return

    # Normalize the API's lowercase response fields into the canonical schema.
    column_mapping = {
        "state": "state", "district": "district name", "market": "market name",
        "commodity": "commodity", "arrival_date": "price date", 
        "min_price": "min_price", "max_price": "max_price", "modal_price": "modal_price"
    }
    df_new.columns = [str(column).strip().lower().replace(" ", "_") for column in df_new.columns]
    available_cols = [c for c in column_mapping.keys() if c in df_new.columns]
    df_new = df_new[available_cols].rename(columns={k: v for k, v in column_mapping.items() if k in available_cols})

    required_columns = {'state', 'district name', 'market name', 'commodity', 'price date', 'modal_price'}
    missing_columns = required_columns - set(df_new.columns)
    if missing_columns:
        raise ValueError(f"Data.gov.in response is missing required columns: {sorted(missing_columns)}")
    
    # Enforce precise day-first Indian calendar sequence format conversion
    df_new['price date'] = pd.to_datetime(df_new['price date'], dayfirst=True, errors='coerce')
    df_new = df_new.dropna(subset=['price date'])

    for col in ['min_price', 'max_price', 'modal_price']:
        if col in df_new.columns:
            df_new[col] = pd.to_numeric(df_new[col], errors='coerce')
            
    df_new['commodity'] = df_new['commodity'].str.strip().str.title()
    mvp_crops = ['Potato', 'Tomato', 'Onion', 'Wheat', 'Maize']
    print(f"📦 Raw Odisha records received: {len(df_new)}")
    df_new = df_new[df_new['commodity'].isin(mvp_crops)].dropna(subset=['modal_price'])
    print(f"🌾 MVP crop records retained: {len(df_new)}")

    # --- SUPABASE CLOUD STREAM INGESTION INTERFACE ---
    supabase = get_supabase_client()
    cloud_history_loaded = False
    try:
        print("☁️ Streaming existing master data log down from Supabase Storage bucket...")
        # Download file data stream natively from cloud memory bytes arrays
        res = supabase.storage.from_(BUCKET_NAME).download(FILE_NAME)
        df_existing = pd.read_csv(io.BytesIO(res))
        
        df_existing['price date'] = pd.to_datetime(
            df_existing['price date'], format='mixed', dayfirst=True, errors='coerce'
        )
        local_path = "data/processed/cleaned_orissa_mandi.csv"
        if os.path.exists(local_path):
            df_local = pd.read_csv(local_path)
            df_local['price date'] = pd.to_datetime(
                df_local['price date'], format='mixed', dayfirst=True, errors='coerce'
            )
            df_existing = pd.concat([df_existing, df_local], ignore_index=True)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        cloud_history_loaded = len(df_existing) >= 100
    except Exception as cloud_error:
        local_path = "data/processed/cleaned_orissa_mandi.csv"
        if not os.path.exists(local_path):
            print("ℹ️ No previous cloud master file found. Initializing new repository base registry...")
            df_combined = df_new
        else:
            print(f"ℹ️ Cloud master file unavailable ({cloud_error}). Preserving local history for initialization.")
            df_existing = pd.read_csv(local_path)
            df_existing['price date'] = pd.to_datetime(
                df_existing['price date'], format='mixed', dayfirst=True, errors='coerce'
            )
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)

    # Deduplicate matching nodes. Preserve the local historical base during the
    # first cloud bootstrap; apply retention after a cloud master exists.
    df_combined = df_combined.drop_duplicates(subset=['market name', 'commodity', 'price date'])
    if cloud_history_loaded:
        two_years_ago = datetime.now() - timedelta(days=730)
        df_rolling = df_combined[df_combined['price date'] >= two_years_ago].copy()
    else:
        df_rolling = df_combined.copy()
    df_rolling = df_rolling.sort_values(by='price date').reset_index(drop=True)

    # Convert table dataframe back into clean in-memory string arrays to write over the web
    csv_data = df_rolling.to_csv(index=False)
    csv_bytes = csv_data.encode('utf-8')

    print("📤 Uploading synchronized rolling data matrix back to Supabase Cloud vault...")
    # Overwrite-update the object cloud file storage container target instantly
    supabase.storage.from_(BUCKET_NAME).upload(
        path=FILE_NAME,
        file=csv_bytes,
        file_options={"content-type": "text/csv", "upsert": "true"}
    )
    os.makedirs("data/processed", exist_ok=True)
    df_rolling.to_csv("data/processed/cleaned_orissa_mandi.csv", index=False)
    print(f"💾 Success! Cloud repository up to date. Active dataset size: {len(df_rolling)} rows.")

if __name__ == "__main__":
    run_production_ingestion()
