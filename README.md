# KrishiBazar AI

KrishiBazar AI helps Odisha farmers make more informed selling decisions. It forecasts short-term crop prices and ranks nearby mandis by expected net price after transport and market fees.

**Live services:** [Web application](https://krishibazar-ai.vercel.app) · [API](https://krishibazar-api-xjxb.onrender.com/docs) · [GitHub repository](https://github.com/Dinesh69069/KRISHIBAZAR)

## What it does

- Forecasts seven-day prices for Tomato, Potato, and Onion.
- Recommends nearby mandis using geographic distance and estimated transport cost.
- Shows a clear hold-or-sell recommendation from the forecast trend.
- Refreshes price data and publishes updated models through a scheduled GitHub Actions workflow.

## Architecture

```text
Next.js frontend (Vercel)
        |
        v
FastAPI prediction API (Render) <--> Supabase Storage
        |
        v
Forecast models + Odisha mandi coordinate cache

GitHub Actions --> Data.gov.in --> Supabase Storage --> retrained models
```

## Repository structure

```text
api/                 FastAPI application and recommendation endpoint
app/                 Streamlit prototype
data/processed/      Deployable mandi coordinate cache and local generated data
frontend/            Next.js user interface
models/              Trained crop forecasting models
notebooks/           Data exploration and feature-engineering walkthroughs
src/                 Ingestion, preprocessing, features, training, and ranking logic
.github/workflows/   Daily data ingestion and model publishing workflow
```

## Run locally

### Backend

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python -m uvicorn api.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`, with interactive documentation at `/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` in your browser.

## Environment variables

Create a root `.env` file for local backend development. Never commit it.

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
DATA_GOV_IN_API_KEY=your_data_gov_in_api_key
FRONTEND_ORIGIN=http://localhost:3000
```

For the frontend, create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

## Data and machine learning workflow

1. Explore the cleaned Odisha mandi data in `notebooks/01_data_exploration.ipynb`.
2. Review leakage-safe calendar, lag, and rolling features in `notebooks/02_feature_engineering.ipynb`.
3. Build features:

   ```bash
   python -m src.features.engineering
   ```

4. Train and evaluate crop models with a chronological holdout:

   ```bash
   python -m src.models.train
   ```

5. Publish current models to Supabase Storage:

   ```bash
   python -m src.models.publish
   ```

## Deployment

### Backend on Render

- Runtime: Python 3
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/`

Set `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, and `FRONTEND_ORIGIN` in Render's Environment settings.

### Frontend on Vercel

- Root directory: `frontend`
- Environment variable: `NEXT_PUBLIC_API_URL=https://your-render-api.onrender.com`

Deploy the backend first, then use its public URL for `NEXT_PUBLIC_API_URL`. Add the resulting Vercel URL as `FRONTEND_ORIGIN` in Render and redeploy the API.

## Team

Built by the N.I.E.L.I.T. Department of AI team under the mentorship of Bijayalaxmi Behera.

- Dinesh Kumar Sahoo — Project Lead
- Satyajit Behera — Frontend
- Digal Dibyajyoti — ML and Data
- Harddik Srichandanray — Backend
- Subham Kumar Sahoo — System Architect
- Nikhilesh Behera — Deployment
