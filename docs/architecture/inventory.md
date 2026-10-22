# Inventory of what exists

Week 6 of the course asks for an architecture diagram *and* a critique of the current design.
Both need an honest list of what is actually in the repository first — this is that list,
produced by reading the code, not by remembering what was planned.

Line counts are from 2026-10-15 and are there to show the shape of the system (where the
weight sits), not as a quality measure.

---

## Backend — `backend/app/`

| File | Lines | Responsibility | Depends on |
|---|---:|---|---|
| `main.py` | 54 | FastAPI app, lifespan (indexes + model), 503 handler, mounts the routers and the static frontend | routers, db, staging, config |
| `config.py` | 27 | Every setting, read from environment variables | — |
| `db.py` | 28 | MongoDB client (or `mongomock`), index creation | config |
| `models.py` | 26 | Request validation: `DailyContext`, `AlarmRequest`, `DemoRequest` | pydantic |
| `repository.py` | 65 | Every database query in the system | bson |

### Routers — HTTP only

| File | Lines | Endpoints |
|---|---:|---|
| `routers/nights.py` | 79 | import, list, get, delete, smart-alarm |
| `routers/context.py` | 25 | get all, put one day |
| `routers/analytics.py` | 29 | insights, forecast, model-info |
| `routers/demo.py` | 32 | seed, clear |

### Services — the logic

| File | Lines | Responsibility | Pure? |
|---|---:|---|---|
| `services/parser.py` | 108 | CSV → validated 1-minute DataFrame; raises `ParseError` | yes |
| `services/synthetic.py` | 200 | Simulated nights: day factors → sleep quality → hypnogram → signals | yes (seeded) |
| `services/features.py` | 56 | 7 features per epoch for the model | yes |
| `services/staging.py` | 130 | Rule-based staging, model loading/caching, `stage_night` dispatch | model cache is global state |
| `services/training.py` | 87 | Train the RandomForest on synthetic nights, save model + metrics | writes files |
| `services/metrics.py` | 130 | Every night metric and the 0–100 score | yes |
| `services/pipeline.py` | 59 | DataFrame + stages → the night document that gets stored | yes |
| `services/insights.py` | 180 | Night table, correlations, recommendation rules | yes |
| `services/forecast.py` | 62 | Next-day energy formula | yes |
| `services/alarm.py` | 56 | Smart-alarm simulation | yes |

Services never import FastAPI and never touch the database. That is what makes 9 of the 10
testable without any infrastructure.

### Tests — `backend/tests/` (711 lines, 81 tests)

| File | Covers |
|---|---|
| `conftest.py` | fake database, test client, 10 deterministic synthetic nights |
| `test_parser.py` | 12 parser cases incl. gaps, ranges, offsets, resampling |
| `test_synthetic_and_staging.py` | generator plausibility, smoothing, heuristic vs model, training |
| `test_metrics.py` | 13 hand-calculated metric cases incl. desaturation merging |
| `test_alarm_insights_forecast.py` | alarm choice rules, correlations, every recommendation rule, forecast |
| `test_api.py` | every endpoint, including failure paths (404, 413, 422) |

---

## Frontend — `frontend/`

| File | Lines | Responsibility |
|---|---:|---|
| `index.html` | 118 | Page structure: forecast, trend, night detail, alarm, insights, context |
| `app.js` | 345 | Fetches the API, renders tiles and 5 charts, handles the forms |
| `styles.css` | 144 | Layout and theming (light/dark via CSS variables) |
| `vendor/chart.umd.min.js` | — | Chart.js 4, MIT, vendored so the page works offline |

No framework and no build step: the page is served as written. `app.js` is one module with
named render functions and no global mutable state apart from the currently selected night.

---

## Infrastructure

| File | Purpose |
|---|---|
| `Dockerfile` | Python 3.12 image, trains the model at build time |
| `docker-compose.yml` | app + `mongo:7` with a health check |
| `.env.example` | every setting with its default |
| `scripts/make_sample_data.py` | regenerates `sample_data/sample_night.csv` |

---

## Data stored (MongoDB, database `sheepcounter`)

**`nights`** — one document per night, unique on `night_date`:

```
_id, night_date "2026-03-02", source "import"|"synthetic",
start, end                       ISO timestamps, local wall-clock
stage_method "ml"|"heuristic"
summary { ...every metric, score, score_breakdown }
epochs [ { t, stage, hr, hrv, spo2, mov, resp }, ... ]   one per minute
```

**`daily_context`** — one document per day, unique on `date`:

```
_id, date "2026-03-01", source "user"|"synthetic",
steps, caffeine_cups, alcohol_units, stress, late_workout
```

Epochs are embedded rather than stored in their own collection: a night is always read whole,
and `MAX_EPOCHS = 2000` keeps a document far below MongoDB's 16 MB limit.

---

## What is *not* here

No authentication, no users collection, no sessions, no migrations, no CI pipeline, no
logging configuration beyond the default, no rate limiting, no frontend tests. Each absence
is tracked in [../product/gap-map.md](../product/gap-map.md).
