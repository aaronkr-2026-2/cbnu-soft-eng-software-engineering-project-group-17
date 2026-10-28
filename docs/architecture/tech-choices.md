# Technology choices

Five decisions that shaped the system, each with the alternatives that were considered and
what the choice costs. The course guide's quick self-check — *which language can I read and
debug, not just generate?* — decided more of this than anything else.

| # | Decision | Alternatives considered | Why this one | What it costs |
|---|---|---|---|---|
| 1 | **Python + FastAPI** for the backend | Next.js (the guide's default), Flask, Django | The product is a data pipeline with a thin HTTP layer on top: pandas, NumPy, SciPy and scikit-learn do the work, and all four are Python. FastAPI adds request validation through Pydantic and generates the `/docs` page for free. It is also the stack I already read and debug fluently, which the course requires for the live walkthrough. | Not the stack with the fastest path to a public URL; hosting a Python service is more work than deploying to Vercel. |
| 2 | **MongoDB** for storage | PostgreSQL, SQLite | A night is one nested object — summary plus several hundred epochs — and it is always read whole. That is a document, and storing it as one avoids a join per chart. The daily-context records are sparse (every field optional), which a schemaless store handles without migrations. I also already work with MongoDB. | No schema enforcement: the document shape lives in `pipeline.py` and nothing stops a bad write. No foreign keys. A relational store would have caught #8 in the critique for me. |
| 3 | **Plain HTML/CSS/JS + vendored Chart.js** for the interface | React, Next.js, Vue, a charting service | There is no client-side state worth a framework: pick a night, draw five charts, submit two forms. No build step means no toolchain to explain in the walkthrough and no `node_modules` in the repository. Chart.js is vendored so the page works offline and has no third-party request. | No component reuse, no type checking, and `app.js` will need splitting as it grows (critique #9). |
| 4 | **scikit-learn RandomForest** for sleep staging, with a rule-based fallback | A neural network (LSTM/CNN on raw signals), rules only, a cloud ML service | 60 simulated nights cannot justify a neural network, and I have to explain every line in week 15 — I can explain seven named features and a forest of decision trees. The rules are not a leftover: they are the only path that works when a file has heart rate alone, and they are the baseline the model is measured against (≈0.68 vs ≈0.90 on simulated nights). | Two staging paths to test and keep consistent (critique #5), and a ceiling on accuracy that a model trained on real polysomnography would not have. |
| 5 | **A synthetic data generator** as a first-class part of the system | Public sleep datasets (PhysioNet/Sleep-EDF), waiting for my own wearable data, a fixed sample file | It makes the product demonstrable with no hardware, testable with deterministic seeds, and gives the model something to train on in seconds. Public polysomnography datasets are EEG-based: they do not contain the wrist signals this product consumes, so they would not have trained this model either. | The model knows my simulator, not sleep (critique #2) — the single largest limitation in the project, and the reason the roadmap puts real-data validation in Alpha. |

---

## Decisions that were close

**Postgres with a JSONB column** would have given schema enforcement for the summary and
flexibility for the epochs. It lost on familiarity and on the fact that nothing in this
product needs a join. If the Alpha release adds users and relationships between them, this
should be re-opened rather than defended.

**Two processes (API + static frontend)** was rejected because it adds CORS, a second thing to
deploy and a second origin to secure, for no benefit at this size. It becomes right as soon as
the frontend wants a CDN.

**SQLite** would have removed the database dependency entirely. `USE_MOCK_DB=1` solved the
same problem (run with no infrastructure) without giving up the document model.

---

## Full dependency list

Versions are pinned in `backend/requirements.txt`; licences are in the README's third-party
table. Every one of them is there for a reason that can be named in one line:

| Package | What it does here |
|---|---|
| fastapi, uvicorn | HTTP layer and server |
| pydantic (via fastapi) | validates request bodies; rejects stress 9 before any code runs |
| pymongo | MongoDB driver |
| python-multipart | required by FastAPI to accept the uploaded CSV |
| pandas | the 1-minute epoch grid: resampling, interpolation, rolling windows |
| numpy | the signal generation and every array calculation |
| scipy | `pearsonr` for the correlations (r **and** p) |
| scikit-learn | the RandomForest and its metrics |
| joblib | saves and loads the trained model |
| pytest, httpx, mongomock | development only: test runner, test client, fake database |

Nothing was added for convenience alone. The rule in `AGENTS.md` is that a new dependency
needs a line in the README table and, if it changes the architecture, an ADR.
