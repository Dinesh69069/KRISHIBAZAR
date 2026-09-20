import os
import pandas as pd

def clean_orissa_data(raw_file_path, output_dir):
    print("⏳ [STEP 05] Starting data cleaning pipeline...")
    
    # 1. Read the massive Kaggle file
    if not os.path.exists(raw_file_path):
        raise FileNotFoundError(f"Missing raw file at: {raw_file_path}")
        
    df = pd.read_csv(raw_file_path)
    print(f" Raw All-India dataset shape: {df.shape}")
    
    # 2. Extract strictly Orissa rows (The dataset uses 'Orissa')
    df_orissa = df[df['STATE'].str.strip() == 'Orissa'].copy()
    print(f" Filtered for Orissa. Records found: {len(df_orissa)}")
    
    # 3. Clean up column headers to lowercase to avoid bugs
    df_orissa.columns = df_orissa.columns.str.strip().str.lower()
    
    # 4. Filter strictly for your 5 MVP Crops
    # (Note: Using 'Wheat' instead of 'Rice' if 'Rice' isn't explicitly in this file)
    mvp_crops = ['Tomato', 'Potato', 'Onion', 'Wheat', 'Rice']
    df_orissa['commodity'] = df_orissa['commodity'].str.strip().str.title()
    df_filtered = df_orissa[df_orissa['commodity'].isin(mvp_crops)].copy()
    print(f" Isolated 5 MVP crops. Remaining records: {len(df_filtered)}")
    
    # 5. Turn text dates into proper chronological Pandas Datetime format
    df_filtered['price date'] = pd.to_datetime(df_filtered['price date'], format='%m/%d/%Y', errors='coerce')
    df_filtered = df_filtered.dropna(subset=['price date'])
    
    # 6. Ensure price columns are treated as numbers
    price_cols = ['min_price', 'max_price', 'modal_price']
    for col in price_cols:
        df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce')
        
    # Drop rows missing the core target price or where price is 0
    df_filtered = df_filtered.dropna(subset=['modal_price'])
    df_filtered = df_filtered[df_filtered['modal_price'] > 0]
    
    # 7. Sort chronologically so time flows forward
    df_filtered = df_filtered.sort_values(by=['commodity', 'market name', 'price date']).reset_index(drop=True)
    
    # 8. Save the output
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, 'cleaned_orissa_mandi.csv')
    df_filtered.to_csv(output_file, index=False)
    
    print(f" Success! Cleaned dataset saved directly to: {output_file}")
    return df_filtered

if __name__ == "__main__":
    # Relative path paths from your project root
    RAW_PATH = "data/raw/Agriculture_price_dataset.csv"
    PROCESSED_DIR = "data/processed/"
    clean_orissa_data(RAW_PATH, PROCESSED_DIR)
