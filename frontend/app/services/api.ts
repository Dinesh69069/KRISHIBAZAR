// Define structure matching your FastAPI Pydantic request models
export interface RecommendationRequest {
  crop: string;
  location_name: string;
}

export interface MandiRecommendation {
  Market: string;
  District: string;
  "Distance (KM)": number;
  "Transport Cost (₹)": number;
  "Expected Net Price (₹/q)": number;
}

export type ForecastPoint = {
  date: string;
  price: number;
  low: number;
  high: number;
};

export type Advice = {
  action: 'hold' | 'sell_now';
  days: number;
  best_date: string;
  expected_gain_per_q: number;
  reason: string;
};

export interface RecommendationResponse {
  crop: string;
  predicted_base_price_per_q: number;
  recommendations: MandiRecommendation[];
  forecast?: ForecastPoint[];
  advice?: Advice | null;
  mae_by_horizon?: Record<string, number>;
  mandi_fee_per_q?: number;
}

type LegacyForecastPoint = {
  date: string;
  predicted_price: number;
  low?: number;
  high?: number;
};

type ApiRecommendationResponse = Omit<RecommendationResponse, 'forecast'> & {
  forecast?: ForecastPoint[];
  seven_day_forecast?: LegacyForecastPoint[];
  advice?: Advice | string | null;
};

function normalizeForecast(response: ApiRecommendationResponse): ForecastPoint[] | undefined {
  const points = response.forecast ?? response.seven_day_forecast;
  if (!points?.length) return undefined;

  return points.map((point) => {
    const price = 'price' in point ? point.price : point.predicted_price;
    const spread = Math.max(price * 0.08, 1);
    return {
      date: point.date,
      price,
      low: point.low ?? Number(Math.max(0, price - spread).toFixed(2)),
      high: point.high ?? Number((price + spread).toFixed(2)),
    };
  });
}

function normalizeAdvice(advice: Advice | string | null | undefined): Advice | null | undefined {
  return typeof advice === 'object' ? advice : advice ? null : undefined;
}

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

/**
 * Communicates safely with your FastAPI server engine to process time-series prices 
 * and logistics route calculations dynamically.
 */
export async function fetchMarketRecommendations(payload: RecommendationRequest): Promise<RecommendationResponse> {
  try {
    const response = await fetch(`${BASE_URL}/recommend-market`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Server responded with unexpected status code: ${response.status}`);
    }

    const body = await response.json() as ApiRecommendationResponse;
    return {
      ...body,
      forecast: normalizeForecast(body),
      advice: normalizeAdvice(body.advice),
    };
  } catch (error) {
    console.error("Network bridge breakdown:", error);
    throw error;
  }
}
