"""
Mandi price forecasting - next-observation modal price per (market, commodity).

Key design choices, each validated against a naive lag_1 baseline:
  1. Target is the CHANGE from lag_1, not the raw price. Trees cannot
     extrapolate past training values, and 52% of observations are unchanged
     from lag_1, so the change is the learnable part.
  2. Market/district/variety/grade passed as native categoricals. Price levels
     differ by thousands of rupees across markets; without these the model is
     averaging incompatible regimes.
  3. objective='reg:absoluteerror' because MAE is the reported metric and the
     series is spike-heavy.
  4. One global chronological cutoff, not a per-market percentile split.
"""

import os
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import mean_absolute_error, mean_squared_error

from xgboost import XGBRegressor

GROUP_KEYS = ["market name", "commodity", "variety", "grade"]

BASE_FEATURES = [
    "month", "day_of_week", "quarter", "season",
    "lag_1", "lag_3", "lag_7",
    "rolling_mean_3", "rolling_mean_7", "rolling_std_7",
]

# All derived from lagged columns only - nothing here sees the current row's price.
DERIVED_FEATURES = [
    "days_since_last",   # lag_1 can be a year stale; the model should know
    "prev_spread",       # previous max-min, a proxy for arrival quality spread
    "prev_spread_pct",
    "mom_1_3",           # short-horizon momentum
    "mom_1_7",
    "dev_rm7",           # how far the last price sits from its own 7-obs mean
    "dev_rm7_pct",
    "vol_pct",           # coefficient of variation
    "rm3_over_rm7",      # short vs long trend ratio
]

CATEGORICAL_FEATURES = ["market_cat", "district_cat", "variety_cat", "grade_cat"]

FEATURES = BASE_FEATURES + DERIVED_FEATURES + CATEGORICAL_FEATURES
TARGET = "modal_price"

MIN_TRAIN_ROWS = 200
MIN_TEST_ROWS = 50


def load_features(feature_file: str) -> pd.DataFrame:
    if not os.path.exists(feature_file):
        raise FileNotFoundError(f"Feature matrix file missing at: {feature_file}")

    df = pd.read_csv(feature_file)
    df["price date"] = pd.to_datetime(df["price date"])
    df["commodity"] = df["commodity"].str.strip().str.title()
    return df


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build lag-only derived features. Must be called before splitting."""
    d = df.sort_values(GROUP_KEYS + ["price date"]).copy()
    g = d.groupby(GROUP_KEYS, observed=True)

    d["days_since_last"] = g["price date"].diff().dt.days.fillna(999)
    d["prev_spread"] = g["max_price"].shift(1) - g["min_price"].shift(1)
    d["prev_spread_pct"] = d["prev_spread"] / d["lag_1"]
    d["mom_1_3"] = d["lag_1"] - d["lag_3"]
    d["mom_1_7"] = d["lag_1"] - d["lag_7"]
    d["dev_rm7"] = d["lag_1"] - d["rolling_mean_7"]
    d["dev_rm7_pct"] = d["dev_rm7"] / d["rolling_mean_7"]
    d["vol_pct"] = d["rolling_std_7"] / d["rolling_mean_7"]
    d["rm3_over_rm7"] = d["rolling_mean_3"] / d["rolling_mean_7"]

    d["market_cat"] = d["market name"].astype("category")
    d["district_cat"] = d["district name"].astype("category")
    d["variety_cat"] = d["variety"].astype("category")
    d["grade_cat"] = d["grade"].astype("category")

    return d.replace([np.inf, -np.inf], np.nan)


def build_model() -> XGBRegressor:
    return XGBRegressor(
        n_estimators=600,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=10,
        reg_lambda=2.0,
        objective="reg:absoluteerror",
        tree_method="hist",
        enable_categorical=True,
        random_state=42,
    )


def evaluate(y_true, y_pred) -> dict:
    return {
        "mae": mean_absolute_error(y_true, y_pred),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mape": float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100),
    }


def train_and_evaluate(feature_file: str, models_output_dir: str,
                       cutoff_date: str = "2025-03-01") -> pd.DataFrame:
    df = add_derived_features(load_features(feature_file))
    cutoff = pd.Timestamp(cutoff_date)

    print(f"Loaded {len(df):,} rows | {df['price date'].min().date()} -> "
          f"{df['price date'].max().date()}")
    print(f"Holdout cutoff: {cutoff.date()}\n")

    os.makedirs(models_output_dir, exist_ok=True)
    summary = []

    # Train whatever is actually present, rather than a hardcoded wishlist.
    for crop, crop_df in df.groupby("commodity", observed=True):
        train_df = crop_df[crop_df["price date"] < cutoff]
        test_df = crop_df[crop_df["price date"] >= cutoff]

        if len(train_df) < MIN_TRAIN_ROWS:
            print(f"  skip {crop}: only {len(train_df)} training rows")
            continue
        if len(test_df) < MIN_TEST_ROWS:
            print(f"  skip {crop}: only {len(test_df)} rows after cutoff "
                  f"(series ends {crop_df['price date'].max().date()})")
            continue

        X_train, X_test = train_df[FEATURES], test_df[FEATURES]
        # Learn the change from lag_1, not the level.
        y_train_delta = train_df[TARGET] - train_df["lag_1"]
        y_test = test_df[TARGET].values

        model = build_model()
        model.fit(X_train, y_train_delta)

        preds = model.predict(X_test) + test_df["lag_1"].values
        # A negative price is never a valid forecast.
        preds = np.clip(preds, a_min=df[TARGET].min() * 0.5, a_max=None)

        model_metrics = evaluate(y_test, preds)
        naive_metrics = evaluate(y_test, test_df["lag_1"].values)

        joblib.dump(
            {
                "model": model,
                "features": FEATURES,
                "target_is_delta_from_lag1": True,
                "categorical_features": CATEGORICAL_FEATURES,
                "trained_through": str(cutoff.date()),
            },
            os.path.join(models_output_dir, f"crop_model_{crop.lower()}.pkl"),
        )

        lift = naive_metrics["mae"] - model_metrics["mae"]
        summary.append({
            "Crop": crop,
            "Test rows": len(test_df),
            "Naive MAE": round(naive_metrics["mae"], 1),
            "Model MAE": round(model_metrics["mae"], 1),
            "Lift (Rs)": round(lift, 1),
            "Lift (%)": round(100 * lift / naive_metrics["mae"], 1),
            "Model MAPE": round(model_metrics["mape"], 1),
            "Beats naive": "yes" if lift > 0 else "NO",
        })

    if not summary:
        print("\nNo crop had enough data to train and evaluate.")
        return pd.DataFrame()

    out = pd.DataFrame(summary).sort_values("Lift (%)", ascending=False)
    print("\nHoldout results vs naive (carry-forward lag_1) baseline")
    print(out.to_string(index=False))
    print("\nA lift under ~2% is not a real improvement - treat it as a tie "
          "and ship the naive baseline for that crop.")
    return out


def predict(model_path: str, rows: pd.DataFrame) -> np.ndarray:
    """Rows must already have been passed through add_derived_features()."""
    payload = joblib.load(model_path)
    delta = payload["model"].predict(rows[payload["features"]])
    return delta + rows["lag_1"].values


if __name__ == "__main__":
    train_and_evaluate(
        feature_file="data/processed/ml_ready_features.csv",
        models_output_dir="models/",
        cutoff_date="2025-03-01",
    )