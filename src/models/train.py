"""
Mandi price forecasting - next-observation modal price per commodity.

Trains 10-feature XGBoost regression models directly compatible with
the FastAPI production inference engine (api/main.py).
"""

import os
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

BASE_FEATURES = [
    "month", "day_of_week", "quarter", "season",
    "lag_1", "lag_3", "lag_7",
    "rolling_mean_3", "rolling_mean_7", "rolling_std_7",
]

TARGET = "modal_price"
MIN_TRAIN_ROWS = 100


def load_features(feature_file: str) -> pd.DataFrame:
    if not os.path.exists(feature_file):
        raise FileNotFoundError(f"Feature matrix file missing at: {feature_file}")

    df = pd.read_csv(feature_file)
    df["price date"] = pd.to_datetime(df["price date"])
    df["commodity"] = df["commodity"].str.strip().str.title()
    return df


def build_model() -> XGBRegressor:
    return XGBRegressor(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=5,
        subsample=0.8,
        random_state=42,
    )


def evaluate(y_true, y_pred) -> dict:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mape": float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100),
    }


def train_and_evaluate(
    feature_file: str = "data/processed/ml_ready_features.csv",
    models_output_dir: str = "models",
    test_ratio: float = 0.2,
) -> pd.DataFrame:
    df = load_features(feature_file)
    print(f"Loaded {len(df):,} feature rows | {df['price date'].min().date()} -> {df['price date'].max().date()}")

    os.makedirs(models_output_dir, exist_ok=True)
    summary = []

    # Target MVP crops
    commodities = ["Potato", "Onion", "Tomato"]

    for crop in commodities:
        crop_clean = crop.lower()
        model_filename = f"crop_model_{crop_clean}.pkl"
        model_path = os.path.join(models_output_dir, model_filename)

        crop_df = df[df["commodity"].str.lower() == crop_clean].sort_values("price date").copy()

        if len(crop_df) < MIN_TRAIN_ROWS:
            if os.path.exists(model_path):
                print(f"  [Notice] Insufficient new observations for {crop} ({len(crop_df)} rows). Preserving existing model: {model_filename}")
            else:
                print(f"  [Warning] Insufficient rows for {crop} ({len(crop_df)} rows) and no existing model found.")
            continue

        split_idx = int(len(crop_df) * (1 - test_ratio))
        train_df = crop_df.iloc[:split_idx]
        test_df = crop_df.iloc[split_idx:]

        X_train, y_train = train_df[BASE_FEATURES], train_df[TARGET]
        X_test, y_test = test_df[BASE_FEATURES], test_df[TARGET].values

        model = build_model()
        model.fit(X_train, y_train)

        preds = model.predict(X_test)
        preds = np.clip(preds, a_min=crop_df[TARGET].min() * 0.5, a_max=None)

        model_metrics = evaluate(y_test, preds)
        naive_metrics = evaluate(y_test, test_df["lag_1"].values)

        payload = {
            "model": model,
            "features": BASE_FEATURES,
        }
        joblib.dump(payload, model_path)

        lift = naive_metrics["mae"] - model_metrics["mae"]
        summary.append({
            "Crop": crop,
            "Train rows": len(train_df),
            "Test rows": len(test_df),
            "Naive MAE": round(naive_metrics["mae"], 1),
            "Model MAE": round(model_metrics["mae"], 1),
            "Model RMSE": round(model_metrics["rmse"], 1),
            "Model MAPE": round(model_metrics["mape"], 1),
            "Lift (Rs)": round(lift, 1),
        })

    if not summary:
        print("\nNo crop models were retrained.")
        return pd.DataFrame()

    out = pd.DataFrame(summary)
    print("\nModel Evaluation Results (10-Feature XGBoost):")
    print(out.to_string(index=False))
    return out


def predict(model_path: str, rows: pd.DataFrame) -> np.ndarray:
    payload = joblib.load(model_path)
    return payload["model"].predict(rows[payload["features"]])


if __name__ == "__main__":
    train_and_evaluate(
        feature_file="data/processed/ml_ready_features.csv",
        models_output_dir="models",
    )