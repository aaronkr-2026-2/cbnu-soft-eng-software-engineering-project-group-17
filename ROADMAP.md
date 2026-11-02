# Roadmap

Four releases, mapped onto the course schedule. Each one has a goal, the features that serve
it, and a success criterion that can be checked rather than argued about.

Everything that is **not** in the MVP column was cut on purpose — the scope-creep audit in
[docs/product/creep-audit.md](docs/product/creep-audit.md) records what was cut and why.

---

## MVP — "one night, explained" (week 3) — **done**

**Goal:** prove that raw wearable data can become something a person can act on, with the
reasoning visible.

- Import one night from CSV (validation, gap filling, 1-minute epochs)
- Synthetic night generator, so the app is usable without a wearable
- Sleep staging: wake / light / deep / REM (rule-based + RandomForest)
- Night metrics and a 0–100 sleep score with a visible breakdown
- Daily context: steps, caffeine, alcohol, stress, late workout
- Insights: correlations and rule-based recommendations that carry their evidence
- Next-day energy forecast (transparent formula)
- Smart alarm, replayed on a recorded night
- Web interface, Docker setup, 81 tests

**Success criterion (met):** a person with no wearable can open the app, load demo data and
read a full night analysis; a person with a CSV export can import it and get the same.

---

## Alpha — "trustworthy and deployed" (weeks 7–10)

**Goal:** the prototype becomes something that can be put on the internet without being
irresponsible.

| Feature | Why |
|---|---|
| Authentication and per-user data | Sleep data is health data. Today anyone who reaches the server reads everything. |
| Deployment to a cloud host with a managed MongoDB | Course milestone, week 7 |
| Security pass: rate limits on import, stricter upload handling, secrets out of the image | Course milestone, week 10 |
| Validation against **real** nights (at least one wearable export with the vendor's own stage labels) | The model has only ever seen simulated data |
| Structured logging and an error budget for failed imports | Right now a failed import is only a message to the user |

**Success criterion:** two different users can keep their nights separate on a public URL,
and the README reports staging agreement on at least one real night, whatever that number
turns out to be.

---

## Beta — "more signals, real feedback" (weeks 11–13)

**Goal:** replace guesses with measurements.

| Feature | Why |
|---|---|
| Daily energy / mood rating by the user | Without ground truth the forecast can never be calibrated or evaluated |
| Replace the forecast formula with a model fitted on that rating, reported honestly | Turns the weakest part of the MVP into something measurable |
| Live wearable sync: a companion app reading Health Connect (Android) or HealthKit (iOS) | Apple and Google have no server-side API for sleep data; the only supported route is an app on the phone |
| Import of more vendor formats (Fitbit, Garmin, Samsung Health exports) | One CSV format is a barrier for anyone who does not want to convert files |
| Report export (PDF) and a shareable link to a single night | Asked for so a night can be shown to a doctor; needs auth first |
| CI (tests on every push) + API documentation pass | Course milestone, week 13 |

**Success criterion:** at least 14 nights of real data with user-reported energy, and a
stated, measured error for the forecast — not an uncalibrated number.

---

## Final — "the full concept" (week 15 and beyond)

**Goal:** the parts of the original concept the MVP deliberately left out.

| Feature | Why it waited |
|---|---|
| Audio monitoring: snoring and apnoea-like events from the microphone | A whole second data pipeline (recording, privacy, on-device processing) — a project of its own |
| Blood pressure trends | No consumer wearable in reach measures it reliably |
| Smart alarm on live data instead of a replay | Needs the companion app from Beta; the algorithm itself is already a pure function and can be reused as is |
| Long-term trends (monthly, seasonal) and anomaly detection | Needs months of data per user |
| Multi-user comparison / anonymous benchmarks | Needs users, and a privacy review before anything is compared |

**Success criterion (week 15):** a before/after story — the week-3 MVP next to the current
system, with the engineering decisions that explain the difference.

---

## Explicitly out of scope, permanently

- Diagnosing sleep apnoea or any other condition. The app can say "this looks unusual, talk
  to a doctor"; it must never say what the cause is.
- Replacing medical measurement. A wrist sensor is not a polysomnogram and the documentation
  says so everywhere it could be misread.
