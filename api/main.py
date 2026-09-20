import os
import io
import numpy as np
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from supabase import create_client, Client
from src.recommendation.market_ranker import recommend_best_market_geopy

load_dotenv()

app = FastAPI(title="KrishiBazar AI - Enterprise Multi-Model Server Engine")

# Enable secure network access endpoints for your decoupled Next.js web application
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:3000"), "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global configuration pathways for your system assets
MODELS_DIR = "models"
GEO_CACHE_FILE = "data/processed/mandi_coordinates.csv"
LOCAL_DATA_FALLBACK = "data/processed/cleaned_orissa_mandi.csv"
MANDI_FEE_FILE = "data/processed/mandi_fees.csv"  # expected columns: market name, mandi_fee_per_q
FORECAST_HORIZON_DAYS = 7
LAG_WINDOW_SIZE = 30  # how much recent history we keep in memory for lag/rolling features

# Placeholder only -- I don't have a verified, current per-commodity mandi
# fee/cess schedule for Odisha APMCs (it's set by government notification
# and varies by market and commodity). Used only when a market isn't found
# in MANDI_FEE_FILE. Replace this and populate the CSV with real rates
# before trusting mandi_fee_per_q for actual selling decisions.
DEFAULT_MANDI_FEE_PER_Q = 20.0

_mandi_fee_cache: dict | None = None


def get_mandi_fee(market_name: str | None) -> float:
    """Looks up the mandi fee (₹ per quintal) for a market from
    MANDI_FEE_FILE, falling back to DEFAULT_MANDI_FEE_PER_Q if the file or
    the specific market isn't found. Cached in memory after first read."""
    global _mandi_fee_cache
    if _mandi_fee_cache is None:
        _mandi_fee_cache = {}
        if os.path.exists(MANDI_FEE_FILE):
            try:
                fee_df = pd.read_csv(MANDI_FEE_FILE)
                _mandi_fee_cache = dict(zip(fee_df["market name"], fee_df["mandi_fee_per_q"]))
            except Exception as fee_err:
                print(f"Could not read mandi fee file, using default fee: {fee_err}")
    return float(_mandi_fee_cache.get(market_name, DEFAULT_MANDI_FEE_PER_Q))


def generate_advice(forecast: list[dict], trend_direction: str,
                    price_change_pct: float) -> dict:
    """Build advice in the response shape consumed by the frontend."""
    first_price = forecast[0]["price"]
    last_price = forecast[-1]["price"]
    if trend_direction == "rising" and price_change_pct >= 3:
        best_index = max(range(len(forecast)), key=lambda index: forecast[index]["price"])
        action = "hold"
        days = best_index + 1
        reason = f"Prices are projected to rise about {price_change_pct}% over the next 7 days."
    else:
        best_index = 0
        action = "sell_now"
        days = 0
        reason = "Prices are not showing a strong enough upward trend to justify waiting."

    return {
        "action": action,
        "days": days,
        "best_date": forecast[best_index]["date"],
        "expected_gain_per_q": round(forecast[best_index]["price"] - first_price, 2),
        "reason": reason,
    }

# Cloud Storage variables loaded dynamically from secure environment memory
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
BUCKET_NAME = "mandi-vault"
FILE_NAME = "cleaned_orissa_mandi.csv"

# Request schema configuration matching text-location inputs precisely
class RecommendationRequest(BaseModel):
    crop: str
    location_name: str

geolocator = Nominatim(user_agent="krishibazar_ai_backend")


def load_crop_model(crop: str):
    """Load the newest cloud model when available, with a local development fallback."""
    model_filename = f"crop_model_{crop}.pkl"

    if SUPABASE_URL and SUPABASE_KEY:
        try:
            supabase_client = create_client(
                SUPABASE_URL,
                SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY,
            )
            model_bytes = supabase_client.storage.from_(BUCKET_NAME).download(model_filename)
            return joblib.load(io.BytesIO(model_bytes))
        except Exception as cloud_error:
            print(f"Supabase model lookup failed; using local model: {cloud_error}")

    target_model_path = os.path.join(MODELS_DIR, model_filename)
    if not os.path.exists(target_model_path):
        raise HTTPException(status_code=404, detail=f"No trained model is available for commodity: {crop}")
    return joblib.load(target_model_path)


def find_nearest_market(latitude: float, longitude: float) -> str | None:
    """Return the nearest cached mandi name for market-specific feature history."""
    if not os.path.exists(GEO_CACHE_FILE):
        return None

    geo_registry = pd.read_csv(GEO_CACHE_FILE).dropna(subset=['market name', 'latitude', 'longitude'])
    if geo_registry.empty:
        return None

    user_coords = (latitude, longitude)
    distances = geo_registry.apply(
        lambda row: geodesic(user_coords, (row['latitude'], row['longitude'])).km,
        axis=1,
    )
    return str(geo_registry.loc[distances.idxmin(), 'market name'])


def month_to_season(month: int) -> int:
    """Must match the season scheme baked into the training data / training
    script: months 6-9 -> 1 (monsoon), 10-12 & 1-2 -> 2 (winter), 3-5 -> 3 (summer)."""
    if month in (6, 7, 8, 9):
        return 1
    if month in (10, 11, 12, 1, 2):
        return 2
    return 3


def build_feature_row(forecast_date: pd.Timestamp, price_window: list[float],
                       price_spread: float, market_te_value: float | None,
                       use_advanced_features: bool) -> dict:
    """Builds one row of model input features for a given future date, using
    only prices known so far (real history + prior recursive predictions).
    Mirrors the feature engineering in the training script exactly, so a
    model trained there sees the same shape of input here."""
    s = pd.Series(price_window)
    month = forecast_date.month
    day_of_week = forecast_date.dayofweek
    season = month_to_season(month)

    row = {
        'month': month,
        'day_of_week': day_of_week,
        'quarter': (month - 1) // 3 + 1,
        'season': season,
        'lag_1': float(s.iloc[-1]),
        'lag_3': float(s.iloc[-3]) if len(s) >= 3 else float(s.iloc[-1]),
        'lag_7': float(s.iloc[-7]) if len(s) >= 7 else float(s.iloc[-1]),
        'rolling_mean_3': float(s.tail(3).mean()),
        'rolling_mean_7': float(s.tail(7).mean()),
        'rolling_std_7': float(s.tail(7).std()) if len(s) >= 2 else 10.0,
    }

    if use_advanced_features:
        row['lag_14'] = float(s.iloc[-14]) if len(s) >= 14 else float(s.iloc[-1])
        row['rolling_min_7'] = float(s.tail(7).min())
        row['rolling_max_7'] = float(s.tail(7).max())
        prev = float(s.iloc[-2]) if len(s) >= 2 else None
        row['pct_change_1'] = ((row['lag_1'] / prev) - 1) if prev else 0.0
        row['price_spread'] = price_spread
        row['month_sin'] = np.sin(2 * np.pi * month / 12)
        row['month_cos'] = np.cos(2 * np.pi * month / 12)
        row['dow_sin'] = np.sin(2 * np.pi * day_of_week / 7)
        row['dow_cos'] = np.cos(2 * np.pi * day_of_week / 7)
        row['season_sin'] = np.sin(2 * np.pi * season / 4)
        row['season_cos'] = np.cos(2 * np.pi * season / 4)
        row['market_te'] = market_te_value

    return row


def run_recursive_forecast(xgb_model, feature_columns: list[str], model_payload: dict,
                            crop_history: pd.DataFrame, nearest_market: str | None,
                            horizon_days: int = FORECAST_HORIZON_DAYS) -> list[dict]:
    """Runs the model forward `horizon_days` steps. Each step's prediction
    is appended to the in-memory price window and becomes the new lag_1 /
    lag_3 / etc. for the next step -- the model itself only ever predicts
    one day ahead, this loop is what turns that into a 7-day curve."""
    # crop_history is sorted newest-first; flip to oldest-first ascending
    # so index [-1] is always "most recent" like a normal time series.
    ascending_prices = crop_history['modal_price'].values[:LAG_WINDOW_SIZE][::-1]
    price_window = list(ascending_prices)

    latest_row = crop_history.iloc[0]
    price_spread = float(latest_row.get('max_price', price_window[-1]) - latest_row.get('min_price', price_window[-1]))

    # New models (trained with the market-aware script) carry a market
    # target-encoding + log1p target; older models predict raw price with
    # the original 10 features. Support both so partially-retrained
    # deployments don't break.
    use_advanced_features = 'market_encoding' in model_payload
    predicts_log_target = use_advanced_features  # log1p target was introduced alongside these features

    market_te_value = None
    if use_advanced_features:
        market_encoding = model_payload.get('market_encoding', {})
        global_mean_price = model_payload.get('global_mean_price', float(np.mean(price_window)))
        market_te_value = market_encoding.get(nearest_market, global_mean_price)

    forecast = []
    current_date = pd.Timestamp.now().normalize()

    for step in range(1, horizon_days + 1):
        forecast_date = current_date + pd.Timedelta(days=step)
        row = build_feature_row(forecast_date, price_window, price_spread, market_te_value, use_advanced_features)

        X_pred = pd.DataFrame([row])[feature_columns].fillna(0)
        raw_prediction = float(xgb_model.predict(X_pred)[0])
        predicted_price = float(np.expm1(raw_prediction)) if predicts_log_target else raw_prediction

        forecast.append({
            "date": forecast_date.strftime("%Y-%m-%d"),
            "days_ahead": step,
            "predicted_price": round(predicted_price, 2),
        })

        price_window.append(predicted_price)  # feed this step's prediction into the next step's lags

    return forecast


@app.get("/")
def read_root():
    return {"status": "online", "message": "KrishiBazar AI Enterprise Multi-Model Engine is live."}


@app.post("/recommend-market")
def get_market_recommendations(request: RecommendationRequest):
    try:
        # 1. DYNAMIC GEOCODING: Resolve text inputs into map coordinates automatically
        search_query = f"{request.location_name}, Odisha, India"
        try:
            geo_location = geolocator.geocode(search_query, timeout=10)
            user_lat = geo_location.latitude if geo_location else 20.2961
            user_lon = geo_location.longitude if geo_location else 85.8245
        except Exception:
            user_lat, user_lon = 20.2961, 85.8245

        # 2. DYNAMIC CROP SUB-MODEL SWITCHING
        crop_clean = request.crop.strip().lower()
        model_payload = load_crop_model(crop_clean)
        xgb_model = model_payload['model']
        feature_columns = model_payload['features']

        # 3. LIVE CLOUD DATA STREAM EXTRACTION WITH LOCAL DEV FALLBACK
        df_history = None

        if SUPABASE_URL and SUPABASE_KEY:
            try:
                print("Production Mode: Fetching real-time database from Supabase Storage...")
                supabase_client = create_client(
                    SUPABASE_URL,
                    SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY,
                )
                cloud_bytes = supabase_client.storage.from_(BUCKET_NAME).download(FILE_NAME)
                df_history = pd.read_csv(io.BytesIO(cloud_bytes))
            except Exception as cloud_err:
                print(f"Supabase stream error ({str(cloud_err)}). Checking local machine files...")

        if df_history is None:
            print("Local Development Mode: Fetching data directly from hard drive files...")
            if not os.path.exists(LOCAL_DATA_FALLBACK):
                raise HTTPException(status_code=500, detail="Operational data history files missing from storage tracker variables.")
            df_history = pd.read_csv(LOCAL_DATA_FALLBACK)

        df_history['price date'] = pd.to_datetime(df_history['price date'])

        # Use the nearest market series, matching the market-specific training groups.
        nearest_market = find_nearest_market(user_lat, user_lon)
        crop_history = df_history[df_history['commodity'].str.lower() == crop_clean].copy()
        if nearest_market and 'market name' in crop_history.columns:
            market_history = crop_history[crop_history['market name'] == nearest_market]
            if len(market_history) >= 7:
                crop_history = market_history
        crop_history = crop_history.sort_values(by='price date', ascending=False)

        if len(crop_history) < 7:
            raise HTTPException(status_code=400, detail=f"Insufficient current price observations to generate time variables for {request.crop}.")

        # 4. RECURSIVE 7-DAY FORECAST
        # The model only ever predicts one day ahead (it needs lag_1 = "yesterday's"
        # price). To get a 7-day curve without training 7 separate models, each
        # step's prediction is fed back in as the next step's lag_1/lag_3/etc.
        seven_day_forecast = run_recursive_forecast(
            xgb_model=xgb_model,
            feature_columns=feature_columns,
            model_payload=model_payload,
            crop_history=crop_history,
            nearest_market=nearest_market,
        )

        # Normalize the backend forecast to the frontend contract and derive
        # conservative uncertainty bands from recent observed volatility.
        recent_prices = crop_history['modal_price'].astype(float).head(7)
        forecast_error = float(recent_prices.std()) if len(recent_prices) > 1 else 0.0
        forecast = [
            {
                "date": point["date"],
                "price": point["predicted_price"],
                "low": round(max(0.0, point["predicted_price"] - forecast_error), 2),
                "high": round(point["predicted_price"] + forecast_error, 2),
            }
            for point in seven_day_forecast
        ]

        predicted_wholesale_price = forecast[0]["price"]  # Day 1, for downstream ranking
        day7_price = forecast[-1]["price"]
        price_change_pct = round(((day7_price - predicted_wholesale_price) / predicted_wholesale_price) * 100, 2) if predicted_wholesale_price else 0.0
        trend_direction = "rising" if day7_price > predicted_wholesale_price else "falling" if day7_price < predicted_wholesale_price else "stable"

        # 5. EXECUTE REGIONAL PROXIMITY LOGISTICS COST CALCULATIONS
        rankings_df = recommend_best_market_geopy(
            user_lat=user_lat,
            user_lon=user_lon,
            predicted_price=predicted_wholesale_price,
            cache_file=GEO_CACHE_FILE
        )

        recommendations_list = rankings_df.head(10).to_dict(orient="records")
        # Attach mandi fee to each recommended market (accepts either key
        # style the ranker might use).
        for rec in recommendations_list:
            rec_market = rec.get("Market") or rec.get("market name") or rec.get("market_name")
            rec["mandi_fee_per_q"] = get_mandi_fee(rec_market)

        top_recommendation = recommendations_list[0] if recommendations_list else None
        mandi_fee_per_q = top_recommendation["mandi_fee_per_q"] if top_recommendation else get_mandi_fee(nearest_market)

        # mae_by_horizon only exists on models retrained with the
        # market-aware script's backtest step; older models simply won't
        # have it, so this degrades to an empty dict rather than erroring.
        mae_by_horizon = model_payload.get("mae_by_horizon", {})

        advice = generate_advice(forecast, trend_direction, price_change_pct)

        return {
            "crop": request.crop,
            "resolved_location": request.location_name,
            "predicted_base_price_per_q": round(predicted_wholesale_price, 2),
            "forecast": forecast,
            "trend": {
                "direction": trend_direction,
                "change_pct": price_change_pct,
            },
            "advice": advice,
            "mae_by_horizon": mae_by_horizon,
            "mandi_fee_per_q": mandi_fee_per_q,
            "recommendations": recommendations_list
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)