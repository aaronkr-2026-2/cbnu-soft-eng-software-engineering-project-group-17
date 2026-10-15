# Architecture

SleepInsight is a layered monolith: one FastAPI process that serves both the JSON API and the
static web interface, with MongoDB behind it. The layering is the only structural rule, and
it is enforced by a convention that is easy to check: **routers do HTTP, services do logic,
`repository.py` does the database, and nothing skips a layer.**

---

## Layers

```mermaid
flowchart TB
    subgraph browser["Browser"]
        UI["index.html · app.js · styles.css<br/>Chart.js (vendored)"]
    end

    subgraph api["FastAPI process"]
        direction TB
        subgraph routers["Routers — HTTP only"]
            RN["nights.py"]
            RC["context.py"]
            RA["analytics.py"]
            RD["demo.py"]
        end
        subgraph services["Services — logic, no I/O"]
            PARSE["parser.py"]
            SYN["synthetic.py"]
            FEAT["features.py"]
            STAGE["staging.py"]
            PIPE["pipeline.py"]
            MET["metrics.py"]
            INS["insights.py"]
            FOR["forecast.py"]
            ALA["alarm.py"]
        end
        REPO["repository.py — every query"]
        STATIC["StaticFiles — serves the frontend"]
    end

    MODEL[("model_store/<br/>stage_model.joblib")]
    DB[("MongoDB<br/>nights · daily_context")]

    UI -->|"fetch /api/..."| routers
    UI -->|"GET /"| STATIC
    RN --> PARSE --> PIPE
    RD --> SYN --> PIPE
    PIPE --> FEAT --> STAGE --> MET
    STAGE -. "loads once" .-> MODEL
    RN --> ALA
    RA --> INS
    RA --> FOR
    routers --> REPO --> DB
```

Rules the diagram encodes:

- Arrows never go upward. A service never calls a router; `repository.py` never calls a
  service.
- Services never import `fastapi` and never open a database connection. That is why nine of
  the ten can be tested as plain functions.
- Only `repository.py` touches collections. Swapping MongoDB for something else would be one
  file plus `db.py`.
- `config.py` is the only module that reads environment variables.

---

## What happens when a night is imported

```mermaid
sequenceDiagram
    actor User
    participant UI as Browser
    participant R as routers/nights.py
    participant P as parser.py
    participant S as staging.py
    participant M as metrics.py
    participant Repo as repository.py
    participant DB as MongoDB

    User->>UI: choose CSV
    UI->>R: POST /api/nights/import (multipart)
    R->>R: size check (10 MB) → 413 if too big
    R->>P: parse_csv(bytes)
    alt file is broken
        P-->>R: ParseError("gap of 12 min at line 340")
        R-->>UI: 422 with the message
    else file is valid
        P-->>R: DataFrame (1-min epochs) + warnings
        R->>S: stage_night(df)
        S->>S: all of HR + HRV + movement present?
        alt yes
            S-->>R: labels, "ml"
        else no
            S-->>R: labels, "heuristic"
        end
        R->>M: summarize_night(df, labels)
        M-->>R: metrics + score + breakdown
        R->>Repo: save_night(document)
        Repo->>DB: replace_one({night_date}, doc, upsert=true)
        R-->>UI: id, night_date, stage_method, warnings, summary
    end
```

The upsert by `night_date` is why importing the same night twice replaces it instead of
creating a duplicate, and why the response carries `replaced_existing`.

---

## Deployment today, and next

```mermaid
flowchart LR
    subgraph dev["Today — one machine"]
        direction TB
        B1["Browser<br/>localhost:8000"]
        A1["Container: app<br/>uvicorn + model"]
        M1[("Container: mongo:7<br/>volume mongo_data")]
        B1 --> A1 --> M1
    end

    subgraph alpha["Alpha — week 7+ (planned)"]
        direction TB
        B2["Browser (HTTPS)"]
        A2["Cloud host<br/>app + auth"]
        M2[("Managed MongoDB")]
        B2 --> A2 --> M2
    end

    dev -.->|"add auth, TLS,<br/>per-user data"| alpha
```

The gap between the two boxes is the Alpha release in [ROADMAP.md](../../ROADMAP.md): without
authentication the app must not be exposed, because everything it stores is health data.

---

## Key design decisions, and the reason for each

| Decision | Reason | Cost |
|---|---|---|
| One process serves API and static files | Nothing to deploy twice, no CORS, no second origin to secure. At this size a separate frontend server would be ceremony. | The frontend cannot be put on a CDN without changing this. |
| One epoch = one minute, everywhere | Every module can assume the same grid: metrics count minutes, the model's windows are minutes, the alarm steps in minutes. | Sub-minute events (a 20-second arousal) are invisible. |
| Naive local timestamps | A night is a local thing: "I went to bed at 23:40" does not mean a UTC instant to the user. Offsets are dropped at the parser. | Travel across time zones mid-night is not handled. |
| `night_date = (bedtime − 12 h).date()` | A night that starts at 01:30 belongs to the previous evening; grouping by calendar date would split it. | One rule to remember when reading the code. |
| Epochs embedded in the night document | A night is always read whole. One query, no joins. | Documents are large; `MAX_EPOCHS` keeps them bounded. |
| Model loaded once into a module-level cache | Loading a RandomForest per request would dominate the response time. | Global state; `reset_model_cache()` exists for tests. |
| Model only used when its three signals are present | It was trained on seven features derived from HR, HRV and movement; feeding it imputed columns would produce confident nonsense. | Two staging paths to maintain and test. |
| `USE_MOCK_DB=1` runs without MongoDB | Tests need no infrastructure, and the project can be demonstrated anywhere. | A second database code path, though `mongomock` matches the PyMongo API. |

A critique of these decisions — including the ones that are wrong — is in
[critique.md](critique.md). The two decisions with the longest reasoning have their own
records in [adr/](adr/).
