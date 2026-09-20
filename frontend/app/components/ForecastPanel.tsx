'use client';

import type { Advice, ForecastPoint, MandiRecommendation } from '../services/api';

type ForecastPanelProps = {
  crop: string;
  forecast: ForecastPoint[];
  advice?: Advice | null;
  maeByHorizon?: Record<string, number>;
  fee: number;
  bestMandi: MandiRecommendation | null;
  isMock: boolean;
  selectedDay: number;
  onSelectedDayChange: (day: number) => void;
};

const dateForDisplay = (iso: string) => new Date(`${iso.slice(0, 10)}T00:00:00`);
const formatDate = (iso: string, options: Intl.DateTimeFormatOptions) =>
  dateForDisplay(iso).toLocaleDateString('en-IN', options);
const money = (value: number, decimals = 2) => `₹${value.toLocaleString('en-IN', {
  minimumFractionDigits: decimals,
  maximumFractionDigits: decimals,
})}`;

export default function ForecastPanel({ crop, forecast, advice, maeByHorizon, fee, bestMandi, isMock, selectedDay, onSelectedDayChange }: ForecastPanelProps) {
  const selected = forecast[selectedDay];

  if (!forecast.length) {
    return (
      <div className="forecast-card" role="tabpanel" id="results-panel-forecast" aria-labelledby="results-tab-forecast">
        <div className="forecast-empty">
          <h3>The 7-day forecast isn&apos;t available yet.</h3>
          <p>Recommended mandis are still shown on the other tab.</p>
        </div>
      </div>
    );
  }

  const prices = forecast.flatMap((point) => [point.low, point.high]);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const range = Math.max(maxPrice - minPrice, 1);
  const x = (index: number) => 38 + (index * 564) / Math.max(forecast.length - 1, 1);
  const y = (price: number) => 198 - ((price - minPrice) / range) * 164;
  const linePath = forecast.map((point, index) => `${index === 0 ? 'M' : 'L'} ${x(index)} ${y(point.price)}`).join(' ');
  const bandPath = `${forecast.map((point, index) => `${index === 0 ? 'M' : 'L'} ${x(index)} ${y(point.high)}`).join(' ')} ${forecast.slice().reverse().map((point, reverseIndex) => `L ${x(forecast.length - 1 - reverseIndex)} ${y(point.low)}`).join(' ')} Z`;
  const ticks = [maxPrice, minPrice + range / 2, minPrice];
  const bestDay = advice?.action === 'hold' ? forecast.findIndex((point) => point.date === advice.best_date) : -1;
  const difference = selected.price - forecast[0].price;
  const netPrice = bestMandi ? selected.price - bestMandi['Transport Cost (₹)'] - fee : null;

  return (
    <div className="forecast-card results-panel" role="tabpanel" id="results-panel-forecast" aria-labelledby="results-tab-forecast">
      <div className="forecast-header">
        <div>
          <h3>{crop} · price outlook, next 7 days</h3>
          <p>Tap a day on the chart or the buttons below.</p>
        </div>
        <div className="forecast-legend" aria-label="Chart legend">
          <span><i className="legend-line" />Forecast</span>
          <span><i className="legend-band" />Likely range</span>
          {isMock && <span className="sample-badge">Sample data, not a real forecast</span>}
        </div>
      </div>

      <div className="forecast-body">
        <svg className="forecast-chart" viewBox="0 0 640 240" role="img" aria-label={`${crop} seven-day price forecast chart`}>
          {ticks.map((tick) => (
            <g key={tick}>
              <line x1="38" x2="602" y1={y(tick)} y2={y(tick)} className="chart-grid" />
              <text x="0" y={y(tick) + 4} className="chart-label">{money(tick, 0)}</text>
            </g>
          ))}
          <path d={bandPath} className="chart-band" />
          {bestDay >= 0 && <circle cx={x(bestDay)} cy={y(forecast[bestDay].price)} r="12" className="best-ring" />}
          <path d={linePath} className="chart-line" />
          <line x1={x(selectedDay)} x2={x(selectedDay)} y1="18" y2="202" className="selected-line" />
          {forecast.map((point, index) => (
            <circle key={point.date} cx={x(index)} cy={y(point.price)} r={index === selectedDay ? 7 : 4} className={index === selectedDay ? 'selected-dot' : 'chart-dot'} />
          ))}
        </svg>

        <div className="forecast-days" role="group" aria-label="Select forecast day">
          {forecast.map((point, index) => (
            <button key={point.date} type="button" className={index === selectedDay ? 'selected' : ''} onClick={() => onSelectedDayChange(index)}>
              <span>{formatDate(point.date, { weekday: 'short' })} {dateForDisplay(point.date).getDate()}</span>
              <strong>{money(point.price, 0)}</strong>
            </button>
          ))}
        </div>

        <div className="forecast-readout">
          <div>
            <p className="readout-date">{formatDate(selected.date, { weekday: 'long', day: 'numeric', month: 'long' })}</p>
            <p className="readout-price">{money(selected.price)} <span>/quintal</span></p>
            <p className={difference >= 0 ? 'difference up' : 'difference down'}>
              {selectedDay === 0 ? 'First forecast day' : `${difference >= 0 ? '↑' : '↓'} ${money(Math.abs(difference))} against day 1`}
            </p>
          </div>
          <div className="readout-range">
            <span>Likely range</span>
            <strong>{money(selected.low)} – {money(selected.high)}</strong>
          </div>
        </div>

        {bestMandi && netPrice !== null && (
          <div className="net-strip">
            <span>Net at best mandi ({bestMandi.Market}) on this day</span>
            <strong>{money(netPrice)}</strong>
          </div>
        )}

        <p className="forecast-footnote">
          The shaded band shows where past forecasts landed 8 times out of 10.
          {maeByHorizon?.[String(selectedDay + 1)] !== undefined && ` Typical miss for this day: about ±${money(maeByHorizon[String(selectedDay + 1)])}.`}
          {' '}Forecasts get less certain further out.
        </p>
      </div>
    </div>
  );
}
