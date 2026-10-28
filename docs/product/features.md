# Feature list

What exists, what each feature is built on, and where it lives in the code. Written so that
in the week-15 walkthrough any row can be opened and explained.

Legend: **Rule** = deterministic logic I wrote · **ML** = trained model · **Stat** =
statistics · **Sim** = simulation.

---

## Data

| # | Feature | Kind | Code | Notes |
|---|---|---|---|---|
| F-01 | CSV import with validation | Rule | `services/parser.py` | required/optional columns, ranges, ISO 8601, 10 MB cap |
| F-02 | Gap handling | Rule | `services/parser.py` | ≤ 3 min interpolated, longer rejected with the file line |
| F-03 | Resampling to 1-minute epochs | Rule | `services/parser.py` | one epoch = one minute everywhere in the system |
| F-04 | Night assembly and storage | Rule | `services/pipeline.py`, `repository.py` | one document per night, epochs embedded, unique by `night_date` |
| F-05 | Synthetic night generator | Sim | `services/synthetic.py` | AR(1) noise, hypnogram with cycles, day factors drive quality |
| F-06 | Daily context | Rule | `routers/context.py`, `models.py` | steps, caffeine, alcohol, stress, late workout |

## Sleep staging

| # | Feature | Kind | Code | Notes |
|---|---|---|---|---|
| F-07 | Feature extraction | Rule | `services/features.py` | 7 features: relative HR, HR variability over 5/15 min, relative HRV, movement over 5/15 min, position in the night |
| F-08 | Rule-based staging | Rule | `services/staging.py` | per-night percentile thresholds + mode smoothing; works with heart rate alone |
| F-09 | RandomForest staging | ML | `services/staging.py`, `services/training.py` | 100 trees, depth 12, balanced classes; used only when HR + HRV + movement are present |
| F-10 | Model transparency endpoint | — | `routers/analytics.py` | accuracy, κ, per-stage recall, feature list, sklearn version, and the warning that training data was simulated |

## Night analysis

| # | Feature | Kind | Code | Notes |
|---|---|---|---|---|
| F-11 | Sleep metrics | Rule | `services/metrics.py` | TST, latency, WASO, efficiency, awakenings (wake runs ≥ 2 min), stage minutes and shares |
| F-12 | Cardiac / respiratory metrics | Rule | `services/metrics.py` | average HR, lowest 5-minute HR, average HRV, respiratory rate |
| F-13 | Oxygen metrics | Rule | `services/metrics.py` | mean and minimum SpO2, desaturation events (≥ 3 points below the night's median, dips ≤ 2 min apart merged), ODI, T90 |
| F-14 | Sleep score 0–100 | Rule | `services/metrics.py` | six weighted components, trapezoid bands, visible breakdown |

## Insights and prediction

| # | Feature | Kind | Code | Notes |
|---|---|---|---|---|
| F-15 | Factor correlations | Stat | `services/insights.py` | Pearson r with p and n; *notable* only at \|r\| ≥ 0.4, p < 0.05, n ≥ 14 |
| F-16 | Rule-based recommendations | Rule | `services/insights.py` | 6 rules over the last 7 nights, each carrying its evidence |
| F-17 | Attention flag for repeated oxygen dips | Rule | `services/insights.py` | suggests a doctor; never names a condition |
| F-18 | Next-day energy forecast | Rule | `services/forecast.py` | weighted formula (0.55 / 0.25 / 0.20), components shown, declared uncalibrated |
| F-19 | Smart alarm | Rule | `services/alarm.py` | pure function, replays a recorded night, compares with a fixed alarm |

## Interface and operations

| # | Feature | Kind | Code | Notes |
|---|---|---|---|---|
| F-20 | Web interface | — | `frontend/` | plain HTML/CSS/JS, no build step, Chart.js vendored |
| F-21 | Charts | — | `frontend/app.js` | hypnogram, HR + SpO2, 14-night trend, score breakdown, alarm markers |
| F-22 | Dark mode | — | `frontend/styles.css` | follows the operating system |
| F-23 | Demo-data controls | — | `routers/demo.py` | seed and remove; removal never touches imported data |
| F-24 | Runs without MongoDB | — | `db.py`, `config.py` | `USE_MOCK_DB=1` for demos and tests |
| F-25 | Docker setup | — | `Dockerfile`, `docker-compose.yml` | app + MongoDB; model trained at build time |
| F-26 | Test suite | — | `backend/tests/` | 81 tests, no database and no network needed |

---

## Deliberately absent

| Feature | Why | When |
|---|---|---|
| Authentication / multiple users | Scope. It is the first thing the security pass must add — the data is health data. | Alpha |
| Live sync from a wearable | No server API exists (Apple Health, Health Connect are on-device); needs a companion app | Beta |
| Audio monitoring (snoring, apnoea-like events) | A second pipeline: capture, privacy, on-device processing | Final |
| Blood pressure | No reliable consumer sensor within reach | Final |
| Report export / sharing | Needs auth first; a shareable health report without accounts is a data leak | Beta |
| Deep learning for staging | 60 simulated nights cannot justify it, and I must be able to explain the model | — |
