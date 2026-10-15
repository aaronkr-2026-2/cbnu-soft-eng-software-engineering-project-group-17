# ADR 001 — Python/FastAPI + MongoDB + a no-build frontend

- **Status:** accepted
- **Date:** 2026-10-15
- **Deciders:** Charlie (solo project)

## Context

The semester project is a working prototype of a sleep-analysis application, built fast in
weeks 1–3 and then improved for twelve more weeks under course milestones (architecture,
security, testing, documentation, deployment). Two constraints shape the choice more than
anything technical:

1. In week 15 I have to open any file and explain it, unscripted. Code I can generate but not
   read is worthless here.
2. The product is a data pipeline: parse a time series, derive features, run a model, compute
   metrics, run statistics. The HTTP layer is thin by comparison.

The course guide suggests Next.js on Vercel as the default fastest path to a public URL, and
lists Flask/Django as the Python option for "data-heavy backends".

## Decision

- **Backend: Python 3.12 + FastAPI**, with pandas/NumPy/SciPy/scikit-learn doing the work.
- **Database: MongoDB**, one document per night with epochs embedded, accessed only through
  `repository.py`.
- **Frontend: plain HTML/CSS/JS**, no framework and no build step, with Chart.js vendored
  into the repository.
- One process serves both the API (`/api/...`) and the static files (`/`).

## Alternatives considered

| Option | Why not |
|---|---|
| Next.js / React on Vercel (the guide's default) | The analysis would have to live somewhere else anyway — the scientific stack is Python. A JS frontend plus a Python service is two deployments and a CORS boundary for a single-user prototype. |
| Flask instead of FastAPI | Would work, but Pydantic validation and the generated `/docs` page are exactly what a prototype whose main risk is bad input data needs. |
| Django | Brings an ORM, admin and auth that this MVP does not use, and a lot of structure to explain in a walkthrough. |
| PostgreSQL | Real schema enforcement, which this project misses (see the critique). Lost because a night is one nested object always read whole, the context records are sparse, and nothing needs a join. Should be re-opened if users and relationships arrive. |
| SQLite | Removes the database dependency, but gives up the document model. `USE_MOCK_DB=1` solves the same "run with nothing installed" problem. |
| React for the frontend | No client-side state worth a framework: select a night, draw charts, submit two forms. |

## Consequences

**Good**

- One language from the CSV parser to the HTTP response; no serialisation boundary in the
  middle of the analysis.
- Services stay plain functions with no framework imports, so 81 tests run with no database
  and no network.
- No `node_modules`, no build step: what is in the repository is what runs in the browser.
- The `/docs` page is generated from the code, so API documentation cannot drift.

**Bad**

- Deploying a Python service is more work than pushing to Vercel; the week-7 hosting
  milestone will cost more than it would have with the guide's default.
- No schema enforcement in the database. The document shape lives in `pipeline.py` and
  nothing stops a bad write — this directly causes the "no schema version" gap.
- No type checking or component model in the frontend; `app.js` will need splitting as it
  grows.

**Neutral**

- Serving the frontend from the API process means no CORS and nothing to deploy twice, but
  the frontend cannot move to a CDN without revisiting this.

## Revisit when

Users and authentication arrive (Alpha), or the frontend outgrows one file.
