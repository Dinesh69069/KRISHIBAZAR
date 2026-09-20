import type { Metadata } from 'next';
import SideIndex from '../components/SideIndex';
import Footer from '../components/Footer';

export const metadata: Metadata = {
  title: 'About | KrishiBazar AI',
  description:
    'How KrishiBazar AI forecasts wholesale mandi prices in Odisha and ranks nearby mandis by expected net price.',
};

const SECTIONS = [
  { id: 'model', label: 'Model training' },
  { id: 'pipeline', label: 'Data pipeline' },
  { id: 'recommend', label: 'Recommendations' },
  { id: 'stack', label: 'Tech stack' },
  { id: 'deploy', label: 'Deployment' },
];

export default function AboutPage() {
  return (
    <div className="kb kb-page">
      <div className="wrap">
        {/* ---------- Header ---------- */}
        <div className="a-head">
          <div>
            <h1>How the forecast is built</h1>
            <p>
              From daily government price records to a ranked list of mandis: the model, the data pipeline and the
              recommendation flow behind every rate card.
            </p>
          </div>
          <dl className="spec">
            <div><dt>Model</dt><dd>XGBoost regression</dd></div>
            <div><dt>Predicts</dt><dd>Wholesale modal price</dd></div>
            <div><dt>Crops</dt><dd>Tomato, Potato, Onion, Rice</dd></div>
            <div><dt>Data refresh</dt><dd>Daily, 4:00 PM IST</dd></div>
            <div><dt>History kept</dt><dd>Rolling two years</dd></div>
          </dl>
        </div>

        <div className="a-body">
          <SideIndex items={SECTIONS} />

          <div className="stack">
            {/* ---------- Model training ---------- */}
            <article className="panel" id="model">
              <div className="panel-h">
                <h2>Model training</h2>
                <p>An XGBoost regressor learns from past prices and is tested on the most recent ones.</p>
              </div>
              <div className="panel-b">
                <div className="two">
                  <div>
                    <p className="sub">Time-based split, oldest to newest</p>
                    <div className="split" role="img" aria-label="85 percent training data, 15 percent future test data">
                      <div className="tr">85% train</div>
                      <div className="te">15%</div>
                    </div>
                    <div className="split-l">
                      <span>Oldest prices</span>
                      <span>Future test data</span>
                    </div>

                    <p className="sub" style={{ marginTop: 26 }}>10 input features</p>
                    <div className="feat">
                      <h4>Calendar</h4>
                      <div>
                        <span className="chip">Month</span>
                        <span className="chip">Day of week</span>
                        <span className="chip">Quarter</span>
                        <span className="chip">Season</span>
                      </div>
                    </div>
                    <div className="feat">
                      <h4>Price lags</h4>
                      <div>
                        <span className="chip g">1-day</span>
                        <span className="chip g">3-day</span>
                        <span className="chip g">7-day</span>
                      </div>
                    </div>
                    <div className="feat">
                      <h4>Rolling</h4>
                      <div>
                        <span className="chip a">3-day average</span>
                        <span className="chip a">7-day average</span>
                        <span className="chip a">7-day volatility</span>
                      </div>
                    </div>

                    <div className="eval">
                      <strong>How it is judged:</strong> predictions are compared with a naive baseline that repeats the
                      previous price, using MAE and RMSE. The model and feature list are saved together as{' '}
                      <code>crop_price_model.pkl</code>.
                    </div>
                  </div>

                  <div>
                    <p className="sub">Training workflow</p>
                    <ol className="tl">
                      <li>Clean and normalise historical mandi prices.</li>
                      <li>Sort the records in date order.</li>
                      <li>Split 85/15 by time, so testing only uses future data.</li>
                      <li>Build calendar, lag and rolling features.</li>
                      <li>Score XGBoost against the previous-price baseline.</li>
                      <li>Save the model and its feature list.</li>
                    </ol>
                  </div>
                </div>
              </div>
            </article>

            {/* ---------- Data pipeline ---------- */}
            <article className="panel" id="pipeline">
              <div className="panel-h">
                <h2>Automated data pipeline</h2>
                <p>A GitHub Actions workflow refreshes the price history every day.</p>
              </div>
              <div className="panel-b">
                <div className="cron">
                  <span className="mono">10:30 UTC</span>
                  <span>=</span>
                  <span className="mono">4:00 PM IST</span>
                  <span style={{ marginLeft: 'auto' }}>runs every day</span>
                </div>
                <div className="stages">
                  <div className="stage">
                    <h3>Fetch <small>Data.gov.in API</small></h3>
                    <ol className="tl" style={{ counterReset: 's 0' }}>
                      <li>Pull mandi price records from the Government of India API.</li>
                      <li>Query both <code>Orissa</code> and <code>Odisha</code> spellings.</li>
                      <li>Walk through every page of results.</li>
                    </ol>
                  </div>
                  <div className="stage">
                    <h3>Clean <small>Standardise</small></h3>
                    <ol className="tl" style={{ counterReset: 's 3' }}>
                      <li>Standardise dates, crop names and price columns.</li>
                      <li>Keep only the supported crops.</li>
                      <li>Drop duplicates and keep two years of history.</li>
                    </ol>
                  </div>
                  <div className="stage">
                    <h3>Store <small>Local or Supabase</small></h3>
                    <ol className="tl" style={{ counterReset: 's 6' }}>
                      <li>Save the dataset locally in development, or sync it to Supabase Storage in production.</li>
                      <li>Read API and Supabase credentials from GitHub Secrets.</li>
                    </ol>
                  </div>
                </div>
              </div>
            </article>

            {/* ---------- Recommendation workflow ---------- */}
            <article className="panel" id="recommend">
              <div className="panel-h">
                <h2>Recommendation workflow</h2>
                <p>What happens between pressing Forecast price and seeing your ranked mandis.</p>
              </div>
              <div className="panel-b">
                <div className="lane first">
                  <h3>Predict the price<small>Steps 1 to 4</small></h3>
                  <div className="tiles">
                    <div className="tile"><b>1</b>FastAPI receives the crop and <code>location_name</code>.</div>
                    <div className="tile"><b>2</b>OpenStreetMap Nominatim finds the location.</div>
                    <div className="tile"><b>3</b>Recent prices become the model&apos;s feature vector.</div>
                    <div className="tile"><b>4</b>XGBoost predicts the wholesale price.</div>
                  </div>
                </div>
                <div className="lane">
                  <h3>Rank the mandis<small>Steps 5 to 8</small></h3>
                  <div className="tiles">
                    <div className="tile"><b>5</b>Distance to each nearby mandi is calculated.</div>
                    <div className="tile"><b>6</b>Transport cost and mandi fees are deducted.</div>
                    <div className="tile"><b>7</b>Mandis are ranked by expected net price.</div>
                    <div className="tile"><b>8</b>Top picks go back to the frontend.</div>
                  </div>
                </div>

                <div className="receipt">
                  <h4>Example: tomato, Jatni (Khurda)</h4>
                  <div><span>Predicted price</span><span>₹2,761.91</span></div>
                  <div className="neg"><span>− Transport, 25.1 km</span><span>₹150.71</span></div>
                  <div className="neg"><span>− Mandi fees</span><span>₹20.00</span></div>
                  <div className="tot"><span>Expected net / quintal</span><span>₹2,591.20</span></div>
                </div>
              </div>
            </article>

            {/* ---------- Tech stack ---------- */}
            <article className="panel" id="stack">
              <div className="panel-h">
                <h2>Technology stack</h2>
                <p>Grouped by the job each tool does.</p>
              </div>
              <div className="panel-b">
                <div className="row"><h3>Frontend</h3><div><span className="chip">Next.js</span><span className="chip">React</span><span className="chip">TypeScript</span><span className="chip">Tailwind CSS</span></div></div>
                <div className="row"><h3>Backend API</h3><div><span className="chip">FastAPI</span><span className="chip">Pydantic</span><span className="chip">Uvicorn</span></div></div>
                <div className="row"><h3>Machine learning</h3><div><span className="chip g">XGBoost</span><span className="chip g">scikit-learn</span><span className="chip g">pandas</span><span className="chip g">NumPy</span><span className="chip g">Joblib</span></div></div>
                <div className="row"><h3>Location</h3><div><span className="chip">Geopy</span><span className="chip">OpenStreetMap Nominatim</span></div></div>
                <div className="row"><h3>Data source</h3><div><span className="chip a">Data.gov.in agricultural market data</span></div></div>
                <div className="row"><h3>Storage</h3><div><span className="chip">Local CSV (development)</span><span className="chip">Supabase Storage (cloud)</span></div></div>
                <div className="row"><h3>Automation</h3><div><span className="chip">GitHub Actions</span></div></div>
                <div className="row"><h3>Secondary UI</h3><div><span className="chip">Streamlit dashboard (legacy)</span></div></div>
              </div>
            </article>

            {/* ---------- Deployment ---------- */}
            <article className="panel" id="deploy">
              <div className="panel-h">
                <h2>Deployment</h2>
                <p>Runs locally today; the pipeline is ready for the cloud.</p>
              </div>
              <div className="panel-b">
                <div className="path">
                  <span className="node">Next.js frontend</span>
                  <span className="arrow">— /recommend-market →</span>
                  <span className="node">FastAPI backend</span>
                </div>
                <div className="two">
                  <div>
                    <p className="sub">Run locally</p>
                    <div className="term">
                      <div className="term-h">Terminal 1 · backend</div>
                      <pre><i>$</i> python -m uvicorn api.main:app --reload</pre>
                    </div>
                    <div className="term">
                      <div className="term-h">Terminal 2 · frontend</div>
                      <pre><i>$</i> cd frontend{'\n'}<i>$</i> npm run dev</pre>
                    </div>
                  </div>
                  <div>
                    <p className="sub">Typical production setup</p>
                    <div className="host first"><b>Next.js</b><span>Vercel or another frontend platform</span></div>
                    <div className="host"><b>FastAPI</b><span>Render, Railway or a container platform</span></div>
                    <div className="host"><b>Datasets</b><span>Processed data and generated assets in Supabase Storage</span></div>
                    <div className="host"><b>Ingestion</b><span>Daily GitHub Actions run</span></div>
                    <div className="host"><b>Credentials</b><span>Kept in deployment secrets</span></div>
                  </div>
                </div>
              </div>
            </article>
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}
