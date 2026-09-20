import type { Advice, ForecastPoint } from './api';

export type MockForecast = {
  forecast: ForecastPoint[];
  advice: Advice;
  mae_by_horizon: Record<string, number>;
};

export function buildMockForecast(basePrice: number, startDate: Date): MockForecast {
  const changes = [0, 35, 72, 58, 96, 48, 18];
  const forecast = changes.map((change, index) => {
    const date = new Date(startDate);
    date.setDate(date.getDate() + index + 1);
    const price = Number((basePrice + change).toFixed(2));
    const spread = 32 + index * 8;

    return {
      date: date.toISOString().slice(0, 10),
      price,
      low: Number((price - spread).toFixed(2)),
      high: Number((price + spread).toFixed(2)),
    };
  });

  return {
    forecast,
    advice: {
      action: 'hold',
      days: 4,
      best_date: forecast[4].date,
      expected_gain_per_q: Number((forecast[4].price - forecast[0].price).toFixed(2)),
      reason: 'Prices are expected to strengthen before easing later in the outlook.',
    },
    mae_by_horizon: {
      '1': 42,
      '2': 51,
      '3': 63,
      '4': 76,
      '5': 89,
      '6': 103,
      '7': 118,
    },
  };
}
