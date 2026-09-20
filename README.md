# KrishiBazar AI

Starter structure for exploring agricultural market data and building market recommendations.

## Setup

```bash
python -m venv .venv
python -m pip install -r requirements.txt
```

Place the downloaded Kaggle CSV in `data/raw/`, then use the notebooks for exploration and feature engineering.

For Supabase ingestion and model publishing, configure `SUPABASE_URL` and the server-only `SUPABASE_SERVICE_ROLE_KEY` in your local `.env` or GitHub Actions secrets. Keep the service-role key out of frontend code.

## Run the applications

```bash
python -m uvicorn api.main:app --reload
python -m streamlit run app/streamlit_app.py
```
