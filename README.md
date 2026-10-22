# Sheepcounter

A sleep-analysis prototype: import a night of wearable data (or generate a realistic one),
get your sleep stages, the metrics behind them, explainable insights, a next-day energy
forecast and a smart-alarm simulation.

> **Not a medical device.** Sheepcounter produces general wellness information. It cannot
> diagnose, treat or rule out any condition, including sleep apnoea. Talk to a doctor about
> health concerns.

Course: Advanced Software Engineering (8866357-02), Chungbuk National University.
Semester project, repository group-17.

---

## Product vision

**FOR** people who already own a sleep-tracking wearable
**WHO** get a single "sleep score" every morning and no idea what to do with it,
**THE** Sheepcounter platform **IS A** personal sleep-analysis web application
**THAT** turns a night of raw biometric data into sleep stages, explainable patterns
("your score is lower on days with alcohol"), a next-day energy forecast and a smart alarm.
**UNLIKE** the closed apps shipped with wearables, which show a number and keep the reasoning,
**OUR PRODUCT** shows the evidence behind every statement: which rule fired, which numbers
triggered it, how the model was trained and how reliable it is.

---

## Status: MVP (week 3)

What works end to end today:

| Area | Status |
|---|---|
| CSV import of one night (validation, gap filling, resampling to 1-minute epochs) | done |
| Synthetic night generator (demo data without a wearable) | done |
| Sleep staging: wake / light / deep / REM (rule-based + RandomForest) | done |
| Night metrics: TST, latency, WASO, efficiency, stage shares, HR, HRV, SpO2, ODI | done |
| Sleep score 0–100 with a visible breakdown | done |
| Daily context (steps, caffeine, alcohol, stress, late workout) | done |
| Insights: correlations + rule-based recommendations with evidence | done |
| Next-day energy forecast (transparent formula) | done |
| Smart alarm (replay of a recorded night) | done |
| Web interface (charts, forms, dark mode) | done |
| Tests (81) | done |
| Authentication, multi-user, live wearable sync, audio monitoring, blood pressure | **not built** — see [ROADMAP.md](ROADMAP.md) |

---

## How to run it

### Option A — Docker (recommended, includes MongoDB)

```bash
docker compose up --build
# open http://localhost:8000
```

### Option B — locally with MongoDB

```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export MONGO_URL=mongodb://localhost:27017            # Windows: set MONGO_URL=...
uvicorn app.main:app --reload
# open http://127.0.0.1:8000
```

### Option C — no database at all (quick demo)

```bash
cd backend
pip install -r requirements-dev.txt
USE_MOCK_DB=1 uvicorn app.main:app
```

`USE_MOCK_DB=1` runs the app against an in-memory fake MongoDB (`mongomock`). Everything
works; the data disappears when the process stops.

On first start the app trains the sleep-stage model on synthetic nights (a few seconds) and
saves it to `backend/app/model_store/`. The Docker image does this at build time.

### First steps in the interface

1. **Load demo data** — generates 28 synthetic nights with their daily context.
2. Pick a night in **Night detail** to see the hypnogram, vitals and the score breakdown.
3. Press **Simulate** under *Smart alarm*.
4. Look at **Insights** — correlations appear once there are at least 7 nights with context.
5. **Import CSV** with your own night, or with `sample_data/sample_night.csv`.
6. **Remove demo data** deletes only the synthetic records; imported nights stay.

---

## CSV format

One row per measurement, 10 seconds to 1 minute apart. Everything is resampled to
1-minute epochs. See `sample_data/sample_night.csv` (generate it with
`python scripts/make_sample_data.py`).

| Column | Required | Unit | Accepted range |
|---|---|---|---|
| `timestamp` | **yes** | ISO 8601 (`2026-03-02T23:14:00`) | a UTC offset is accepted and dropped — the app works in local wall-clock time |
| `heart_rate` | **yes** | bpm | 25–220 |
| `hrv_rmssd` | no | ms | 0–500 |
| `spo2` | no | % | 50–100 |
| `movement` | no | activity index | 0–100 |
| `resp_rate` | no | breaths per minute | 2–60 |

Ranges are in `VALID_RANGES` in `backend/app/services/parser.py`.

Rules the parser enforces:

- 60 to 2000 epochs (≈1 to 33 hours), file at most 10 MB;
- gaps up to 3 minutes are interpolated, a longer gap is rejected with the file line number;
- values outside the ranges above are dropped and interpolated, and reported as warnings;
- unknown columns are ignored with a warning;
- the file must contain one night; a second import with the same night date replaces the first.

The optional columns change what the app can do: without `hrv_rmssd` and `movement` the
machine-learning model is not used and staging falls back to the rule-based method; without
`spo2` the oxygen metrics are empty.

---

## API

Interactive documentation while the app runs: <http://localhost:8000/docs>.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness check |
| POST | `/api/nights/import` | upload one CSV night (multipart `file`) |
| GET | `/api/nights?limit=90` | night summaries, oldest first, without per-minute data |
| GET | `/api/nights/{id}` | one night including every epoch |
| DELETE | `/api/nights/{id}` | delete a night |
| POST | `/api/nights/{id}/smart-alarm` | replay the alarm (optional `window_start`, `window_end`) |
| GET | `/api/context` | all daily-context records |
| PUT | `/api/context/{YYYY-MM-DD}` | save the context for one day |
| GET | `/api/insights` | correlations + recommendations |
| GET | `/api/forecast` | next-day energy forecast |
| GET | `/api/model-info` | how the staging model was trained and how it scored |
| POST | `/api/demo/seed` | generate synthetic nights (`nights`, `seed`) |
| DELETE | `/api/demo` | delete synthetic data only |

---

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

81 tests, no MongoDB needed (they run against `mongomock`). They cover the CSV parser,
the generator, staging, every night metric computed by hand, the smart alarm, the insight
rules, the forecast and the HTTP API.

---

## How honest is the output?

This matters more than the feature list, so it is stated here rather than hidden in the code.

- **The staging model has never seen a real night.** It is a RandomForest trained on nights
  from this project's own simulator. On held-out *simulated* nights it reaches about 0.90
  accuracy (Cohen's κ ≈ 0.84) — that number says the model learned the simulator, not that it
  would work on you. `/api/model-info` repeats this warning. Validating against real
  polysomnography or a wearable's own labels is on the roadmap.
- **The demo data has relationships planted in it** (caffeine, alcohol, stress and a late
  workout all worsen simulated sleep). Correlations found in demo data are therefore
  guaranteed to exist — they demonstrate the feature, they are not a finding.
- **The energy forecast is a fixed weighted formula**, not a trained model, and nothing has
  been calibrated against how anyone actually felt the next day.
- **The sleep score is this project's own definition** (weights in
  `backend/app/services/metrics.py`), not a clinical standard.
- **SpO2 and the desaturation index are not a sleep-apnoea test.** A wearable's optical
  sensor is not an oximeter used for diagnosis.
- **There is no authentication**, so anyone who can reach the server can read the data in it.
  Run it locally. This is the first item in the security roadmap.

---

## Repository layout

```
backend/
  app/
    main.py            FastAPI application, routers, static files
    config.py          all settings, read from environment variables
    db.py              MongoDB connection (or the in-memory fake)
    models.py          request validation (Pydantic)
    repository.py      every database query lives here
    routers/           HTTP endpoints: nights, context, analytics, demo
    services/          the actual logic (see docs/CODE_WALKTHROUGH.md)
  tests/               81 tests
frontend/              plain HTML/CSS/JS, Chart.js vendored locally
docs/                  product, architecture, ADRs, code walkthrough
sample_data/           an example CSV
scripts/               helper scripts
```

A module-by-module explanation is in [docs/CODE_WALKTHROUGH.md](docs/CODE_WALKTHROUGH.md).
Architecture diagrams and the critique of the current design are in
[docs/architecture/](docs/architecture/).

---

## Third-party code

| What | Version | Licence | Why |
|---|---|---|---|
| FastAPI, Uvicorn, Pydantic | see `backend/requirements.txt` | MIT / BSD | HTTP API |
| pandas, NumPy, SciPy | see `backend/requirements.txt` | BSD | time series, statistics |
| scikit-learn, joblib | see `backend/requirements.txt` | BSD | sleep-stage model |
| PyMongo | see `backend/requirements.txt` | Apache-2.0 | MongoDB driver |
| mongomock | dev only | BSD | tests without a database |
| Chart.js 4 | `frontend/vendor/chart.umd.min.js` | MIT (`frontend/vendor/LICENSE-chartjs.md`) | charts, vendored so the page works offline |

---

## AI assistance

This project is built with AI assistance, as the course allows and requires to be disclosed.
Every session is logged in [AI_LOG.md](AI_LOG.md), and the conventions given to AI tools are
in [AGENTS.md](AGENTS.md).
