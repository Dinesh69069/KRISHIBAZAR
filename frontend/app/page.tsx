'use client';

import React, { useState } from 'react';
import ForecastPanel from './components/ForecastPanel';
import ResultsTabs from './components/ResultsTabs';
import { Advice, fetchMarketRecommendations, ForecastPoint, MandiRecommendation, RecommendationResponse } from './services/api';
import { buildMockForecast } from './services/mockForecast';

const ODISHA_LOCATIONS = [
  'Angul', 'Balasore', 'Bargarh', 'Baripada', 'Berhampur', 'Bhadrak',
  'Bhubaneswar', 'Bolangir', 'Cuttack', 'Dhenkanal', 'Jharsuguda',
  'Keonjhar', 'Koraput', 'Puri', 'Rourkela', 'Sambalpur', 'Rayagada',
];

/**
 * KrishiBazar AI — Mandi Rate Card UI
 *
 * Visual language: ledger / government mandi rate-card, not a generic SaaS dashboard.
 * Fonts: Zilla Slab (headings) + IBM Plex Sans (body) + IBM Plex Mono (numbers/labels).
 * Shared font loading and navigation live in app/layout.tsx.
 */

export default function Home() {
  // 1. UI Input States
  const [crop, setCrop] = useState('Tomato');
  const [locationName, setLocationName] = useState('');
  const [showLocationSuggestions, setShowLocationSuggestions] = useState(false);

  // 2. Data & Loading States
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<RecommendationResponse | null>(null);
  const [activeTab, setActiveTab] = useState<'mandis' | 'forecast'>('mandis');
  const [selectedDay, setSelectedDay] = useState(0);
  const [mockData, setMockData] = useState<ReturnType<typeof buildMockForecast> | null>(null);

  // 3. Execution Network Bridge Trigger
  const handleCalculate = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchMarketRecommendations({
        crop,
        location_name: locationName.trim(),
      });
      setData(response);
      setSelectedDay(0);
      setMockData(
        process.env.NEXT_PUBLIC_USE_MOCK_FORECAST === 'true' && !response.forecast?.length
          ? buildMockForecast(response.predicted_base_price_per_q, new Date())
          : null,
      );
    } catch {
      setError('Could not establish connection with FastAPI backend server.');
    } finally {
      setLoading(false);
    }
  };

  // Extract variables safely if data payload exists
  const topMandi: MandiRecommendation | null = data && data.recommendations.length > 0 ? data.recommendations[0] : null;
  const otherMandis: MandiRecommendation[] = data ? data.recommendations.slice(1, 4) : [];
  const forecast: ForecastPoint[] = data?.forecast?.length ? data.forecast : mockData?.forecast ?? [];
  const advice: Advice | null = data?.forecast?.length ? data.advice ?? null : mockData?.advice ?? null;
  const maeByHorizon = data?.forecast?.length ? data.mae_by_horizon : mockData?.mae_by_horizon ?? data?.mae_by_horizon;
  const fee = data?.mandi_fee_per_q ?? (topMandi
    ? Number(((data?.predicted_base_price_per_q ?? 0) - topMandi['Transport Cost (₹)'] - topMandi['Expected Net Price (₹/q)']).toFixed(2))
    : 0);
  const isMock = Boolean(mockData && !data?.forecast?.length);
  const headlinePrice = forecast[0]?.price ?? data?.predicted_base_price_per_q ?? 0;
  const firstForecast = forecast[0];
  const lastForecast = forecast[forecast.length - 1];
  const locationSuggestions = locationName.trim()
    ? ODISHA_LOCATIONS.filter((location) => location.toLowerCase().includes(locationName.trim().toLowerCase()))
    : ODISHA_LOCATIONS;

  return (
    <>
      <main
        className="kb kb-page min-h-screen"
        style={{ background: 'var(--bg)', color: 'var(--ink)' }}
      >
        {/* ================= MASTHEAD =================
        <div style={{ background: 'var(--nav)', color: 'var(--nav-ink)' }} className="px-6 py-7 md:px-12">
          <div className="max-w-7xl mx-auto flex items-baseline justify-between flex-wrap gap-2">
            <h1
              style={{ fontFamily: "'Zilla Slab', Georgia, serif", fontWeight: 600 }}
              className="text-3xl"
            >
              Krishi<span style={{ color: 'var(--nav-accent)' }}>Bazar</span> AI
            </h1>
            <p className="text-xs max-w-xs text-right" style={{ color: 'var(--nav-muted)' }}>
              Crop economics decision-support · Odisha mandis
            </p>
          </div>
          <div
            className="mt-4 h-[3px] max-w-7xl mx-auto"
            style={{ background: 'repeating-linear-gradient(90deg, var(--nav-accent) 0 10px, transparent 10px 16px)' }}
          />
        </div> */}

        <div className="max-w-7xl mx-auto p-6 md:p-12 grid grid-cols-1 lg:grid-cols-12 gap-8">

          {/* ================= LEFT: LEDGER INPUT CARD ================= */}
          <section
            className="lg:col-span-4 p-6 rounded-sm flex flex-col justify-between"
            style={{ background: 'var(--surface)', border: '1px solid var(--line)' }}
          >
            <div>
              <h2 style={{ fontFamily: "'Zilla Slab', Georgia, serif", fontWeight: 600 }} className="text-xl mb-1">
                Get today&apos;s rate card
              </h2>
              <p className="text-sm mb-6" style={{ color: 'var(--muted)' }}>
                Set your crop and location to forecast prices and rank nearby mandis.
              </p>

              <div className="space-y-5">
                <div>
                  <label className="block text-xs font-semibold mb-2" style={{ color: 'var(--muted)' }}>
                    Target commodity
                  </label>
                  <select
                    className="w-full rounded-sm px-4 py-3 focus:outline-none"
                    style={{ background: 'var(--bg)', border: '1px solid var(--line)', color: 'var(--ink)' }}
                    value={crop}
                    onChange={(e) => setCrop(e.target.value)}
                  >
                    {['Tomato', 'Potato', 'Onion'].map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>

                <div className="relative">
                  <label className="block text-xs font-semibold mb-2" style={{ color: 'var(--muted)' }}>
                    Your nearest town/city name
                  </label>
                  <input
                    type="text"
                    placeholder="e.g., Cuttack, Sambalpur, Bargarh"
                    className="w-full rounded-sm px-4 py-3 focus:outline-none"
                    style={{ background: 'var(--bg)', border: '1px solid var(--line)', color: 'var(--ink)' }}
                    value={locationName}
                    onChange={(e) => setLocationName(e.target.value)}
                    onFocus={() => setShowLocationSuggestions(true)}
                    onBlur={() => setShowLocationSuggestions(false)}
                    role="combobox"
                    aria-autocomplete="list"
                    aria-expanded={showLocationSuggestions && locationSuggestions.length > 0}
                    aria-controls="location-suggestions"
                  />
                  {showLocationSuggestions && locationSuggestions.length > 0 && (
                    <ul
                      id="location-suggestions"
                      role="listbox"
                      className="absolute z-10 mt-1 max-h-[132px] w-full overflow-y-auto rounded-sm"
                      style={{ background: 'var(--surface)', border: '1px solid var(--line)', boxShadow: '0 8px 18px rgba(18, 41, 28, .12)' }}
                    >
                      {locationSuggestions.map((location) => (
                        <li key={location} role="option" aria-selected={locationName === location}>
                          <button
                            type="button"
                            className="w-full px-4 py-2.5 text-left text-sm hover:bg-[var(--surface-2)] focus:bg-[var(--surface-2)] focus:outline-none"
                            onMouseDown={(event) => event.preventDefault()}
                            onClick={() => {
                              setLocationName(location);
                              setShowLocationSuggestions(false);
                            }}
                          >
                            {location}
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>

              <div
                className="inline-flex items-center gap-1.5 text-[11px] mt-6 px-2.5 py-1 rounded-sm"
                style={{
                  border: '1px solid var(--green)',
                  color: 'var(--green-t)',
                  fontFamily: "'IBM Plex Mono', monospace",
                  letterSpacing: '1px',
                  textTransform: 'uppercase',
                  transform: 'rotate(-1.5deg)',
                }}
              >
                ✓ Source: OGD mandi price data
              </div>
            </div>

            <button
              onClick={handleCalculate}
              disabled={loading}
              className="w-full mt-8 py-3.5 rounded-sm text-base"
              style={{
                fontFamily: "'Zilla Slab', Georgia, serif",
                fontWeight: 600,
                background: loading ? 'var(--line)' : 'var(--accent)',
                color: 'var(--on-accent)',
                border: 'none',
                cursor: loading ? 'default' : 'pointer',
              }}
            >
              {loading ? 'Calculating…' : 'Forecast price →'}
            </button>
          </section>

          {/* ================= RIGHT: ADVISOR & OUTPUT ================= */}
          <section className="lg:col-span-8 space-y-6">
            {error && (
              <div
                className="p-4 rounded-sm text-sm"
                style={{ background: 'var(--surface-2)', border: '1px solid var(--neg)', color: 'var(--neg)' }}
              >
                {error}
              </div>
            )}

            {!data && !loading && (
              <div
                className="h-full flex flex-col items-center justify-center p-12 rounded-sm text-center"
                style={{ border: '1px dashed var(--line)', color: 'var(--muted)' }}
              >
                <p style={{ fontFamily: "'Zilla Slab', Georgia, serif", fontWeight: 600 }} className="text-lg">
                  Awaiting your rate card
                </p>
                <p className="text-xs mt-1">Set the crop and location on the left, then run the forecast.</p>
              </div>
            )}

            {data && (
              <>
                <ResultsTabs activeTab={activeTab} onChange={setActiveTab} />

                {activeTab === 'mandis' && (
                  <div role="tabpanel" id="results-panel-mandis" aria-labelledby="results-tab-mandis" className="results-panel space-y-6">
                {/* AI MARKET ADVISOR TICKER CARD */}
                <div
                  className="p-6 rounded-sm relative"
                  style={{ background: 'var(--nav)', color: 'var(--nav-ink)', border: '1px solid var(--nav)' }}
                >
                  <div
                    className="absolute top-0 right-0 text-[10px] font-semibold px-3 py-1 rounded-bl-sm uppercase"
                    style={{ background: 'color-mix(in srgb, var(--nav-accent) 15%, transparent)', color: 'var(--nav-accent)', letterSpacing: '1.5px' }}
                  >
                    AI Advisor
                  </div>
                  <p className="text-[11px] uppercase mb-3" style={{ color: 'var(--nav-muted)', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '1.5px' }}>
                    {crop} · Today
                  </p>
                  <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                    <div>
                      <h3 style={{ fontFamily: "'IBM Plex Mono', monospace", color: 'var(--nav-accent)', fontWeight: 600 }} className="text-4xl leading-none">
                        ₹{headlinePrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        <span className="text-sm ml-2" style={{ color: 'var(--nav-muted)', fontFamily: "'IBM Plex Sans', sans-serif" }}>/quintal</span>
                      </h3>
                      {firstForecast && lastForecast && (
                        <p className="text-xs mt-2 flex items-center gap-1.5" style={{ color: 'var(--nav-muted)' }}>
                          Next 7 days:
                          <span style={{ color: lastForecast.price >= firstForecast.price ? 'var(--green-t)' : 'var(--neg)', fontWeight: 600 }}>
                            {lastForecast.price >= firstForecast.price ? '↑' : '↓'} ₹{firstForecast.price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} → ₹{lastForecast.price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </span>
                        </p>
                      )}
                    </div>
                    {advice && (
                      <div className={`px-5 py-3 rounded-sm text-center text-xs uppercase ${advice.action === 'sell_now' ? 'advice-sell' : ''}`}>
                        {advice.action === 'hold' ? `Hold for ${advice.days} days` : 'Sell today'}
                      </div>
                    )}
                  </div>
                  {advice && (
                    <div className="mt-5 pt-4 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs" style={{ borderTop: '1px solid color-mix(in srgb, var(--nav-muted) 20%, transparent)', color: 'var(--code-ink)' }}>
                      <div className="flex items-center gap-2"><span style={{ color: 'var(--green-t)' }}>●</span>{advice.reason}</div>
                      {maeByHorizon?.['7'] !== undefined && <div className="flex items-center gap-2"><span style={{ color: 'var(--nav-accent)' }}>●</span>Typical forecast error: about ±₹{maeByHorizon['7'].toLocaleString('en-IN', { maximumFractionDigits: 2 })} at 7 days</div>}
                    </div>
                  )}
                  {isMock && <span className="sample-badge advisor-sample">Sample data, not a real forecast</span>}
                </div>

                {/* TOP RECOMMENDED MARKET */}
                {topMandi && (
                  <div className="p-6 rounded-sm" style={{ background: 'var(--surface)', border: '1px solid var(--accent)', boxShadow: 'inset 3px 0 0 var(--accent)' }}>
                    <h3
                      className="text-[11px] uppercase mb-4"
                      style={{ color: 'var(--muted)', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '1px' }}
                    >
                      Best mandi · ranked by expected net price
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
                      <div>
                        <p className="text-[10px] uppercase mb-1" style={{ color: 'var(--muted)' }}>Mandi</p>
                        <p className="text-lg font-semibold capitalize">{topMandi.Market}</p>
                        <p className="text-[11px] capitalize" style={{ color: 'var(--muted)' }}>{topMandi.District} district</p>
                      </div>
                      <div>
                        <p className="text-[10px] uppercase mb-1" style={{ color: 'var(--muted)' }}>Distance</p>
                        <p className="text-lg font-semibold" style={{ fontFamily: "'IBM Plex Mono', monospace" }}>
                          {topMandi['Distance (KM)']} km
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] uppercase mb-1" style={{ color: 'var(--muted)' }}>Transport cost</p>
                        <p className="text-lg font-semibold" style={{ fontFamily: "'IBM Plex Mono', monospace", color: 'var(--neg)' }}>
                          ₹{topMandi['Transport Cost (₹)'].toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] uppercase mb-1" style={{ color: 'var(--green-t)' }}>Expected net</p>
                        <p className="text-lg font-bold" style={{ fontFamily: "'IBM Plex Mono', monospace", color: 'var(--green-t)' }}>
                          ₹{topMandi['Expected Net Price (₹/q)'].toLocaleString()}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* OTHER MANDIS */}
                {otherMandis.length > 0 && (
                  <div className="space-y-5">
                    <h3
                      className="text-[11px] uppercase pl-1"
                      style={{ color: 'var(--muted)', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '1px' }}
                    >
                      Other nearby mandis
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {otherMandis.map((mandi, idx) => (
                        <div
                          key={idx}
                          className="p-5 rounded-sm flex flex-col justify-between"
                          style={{ background: 'var(--surface)', border: '1px solid var(--line)' }}
                        >
                          <div>
                            <div className="flex justify-between items-start mb-2">
                              <span className="font-semibold text-sm capitalize">{mandi.Market}</span>
                              <span
                                className="text-[10px] px-1.5 py-0.5 rounded-sm"
                                style={{ background: 'var(--surface-2)', color: 'var(--ink)', fontFamily: "'IBM Plex Mono', monospace" }}
                              >
                                #{idx + 2}
                              </span>
                            </div>
                            <p className="text-[11px] capitalize mb-4" style={{ color: 'var(--muted)' }}>{mandi.District} district</p>
                          </div>
                          <div className="flex justify-between items-end gap-4 text-xs" style={{ fontFamily: "'IBM Plex Mono', monospace" }}>
                            <span style={{ color: 'var(--muted)' }}>{mandi['Distance (KM)']} km</span>
                            <span style={{ color: 'var(--green-t)', fontWeight: 600 }}>
                              ₹{mandi['Expected Net Price (₹/q)'].toLocaleString()} net
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                  </div>
                )}

                {activeTab === 'forecast' && (
                  <ForecastPanel
                    crop={crop}
                    forecast={forecast}
                    advice={advice}
                    maeByHorizon={maeByHorizon}
                    fee={fee}
                    bestMandi={topMandi}
                    isMock={isMock}
                    selectedDay={selectedDay}
                    onSelectedDayChange={setSelectedDay}
                  />
                )}
              </>
            )}
          </section>
        </div>

        <footer
          className="max-w-7xl mx-auto px-6 md:px-12 py-6 mt-2 text-xs flex justify-between flex-wrap gap-2"
          style={{ borderTop: '1px solid var(--line)', color: 'var(--muted)' }}
        >
          <span>KrishiBazar AI</span>
          <span>Data: Open Government Data Platform, Ministry of Agriculture</span>
        </footer>
      </main>
    </>
  );
}
