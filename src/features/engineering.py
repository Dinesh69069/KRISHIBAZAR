import os
import pandas as pd
import numpy as np

def build_time_series_features(input_file, output_file):
    print(" [STEP 07] Constructing time-series features...")
    
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Cleaned data missing at: {input_file}")
        
    # 1. Load the cleaned Orissa dataset
    df = pd.read_csv(input_file)
    df['price date'] = pd.to_datetime(df['price date'])
    
    # Keep every market series independent before calculating time-series features.
    df = df.sort_values(by=['commodity', 'market name', 'price date']).reset_index(drop=True)

    # 2. Extract Calendar & Seasonality Components
    df['month'] = df['price date'].dt.month
    df['day_of_week'] = df['price date'].dt.dayofweek
    df['quarter'] = df['price date'].dt.quarter
    
    # Define an agricultural season mapping for India
    # 1: Kharif (Monsoon), 2: Rabi (Winter), 3: Zaid (Summer)
    def get_season(month):
        if month in [6, 7, 8, 9]: return 1  # Kharif
        elif month in [10, 11, 12, 1, 2]: return 2 # Rabi
        else: return 3 # Zaid
    df['season'] = df['month'].apply(get_season)

    # 3. Create Grouped Time Lags & Moving Averages
    # Grouping ensures a Tomato trend in Bhubaneswar doesn't mix with a Potato trend in Cuttack
    grouped = df.groupby(['commodity', 'market name'])
    
    # Historical Lags (Looking back to capture current baseline prices)
    df['lag_1'] = grouped['modal_price'].shift(1)  # Price from previous entry
    df['lag_3'] = grouped['modal_price'].shift(3)  # Price 3 entries ago
    df['lag_7'] = grouped['modal_price'].shift(7)  # Price 7 entries ago
    
    # Rolling Moving Averages (Smooths noise and shows local momentum)
    # We shift(1) first so the model doesn't "cheat" by looking at today's final price
    df['rolling_mean_3'] = grouped['modal_price'].transform(lambda x: x.shift(1).rolling(3).mean())
    df['rolling_mean_7'] = grouped['modal_price'].transform(lambda x: x.shift(1).rolling(7).mean())
    df['rolling_std_7']  = grouped['modal_price'].transform(lambda x: x.shift(1).rolling(7).std())

    # 4. Drop Empty Setup Rows
    # The first few rows of each group won't have 7 days of past history, so lags will be empty (NaN)
    df_ml_ready = df.dropna(subset=['lag_1', 'rolling_mean_7']).copy()
    
    # 5. Save the final ML-ready matrix
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df_ml_ready.to_csv(output_file, index=False)
    
    print(f"✅ Success! Feature matrix shape: {df_ml_ready.shape}")
    print(f" Engineered data saved to: {output_file}")
    return df_ml_ready

if __name__ == "__main__":
    CLEANED_DATA = "data/processed/cleaned_orissa_mandi.csv"
    ML_READY_DATA = "data/processed/ml_ready_features.csv"
    build_time_series_features(CLEANED_DATA, ML_READY_DATA)
