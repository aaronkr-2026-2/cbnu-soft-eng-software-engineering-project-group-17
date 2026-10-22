# ADR 002 — CSV import plus a synthetic generator, instead of live wearable sync

- **Status:** accepted
- **Date:** 2026-10-15
- **Deciders:** Charlie (solo project)

## Context

The product analyses biometric data recorded during sleep: heart rate, HRV, SpO2, movement,
respiration. The original concept assumed the app would read that data from a wearable.

Three facts turned out to decide this:

1. **Apple Health has no server-side API.** HealthKit data is only reachable from an app
   running on the user's own iPhone or Watch.
2. **Google is retiring the Fit REST API** in favour of Health Connect, which is likewise an
   on-device API — reachable from an Android app, not from a server.
3. I have one smartwatch and no months of recorded nights. A product that needs 14 nights
   before its main feature appears cannot be developed, demonstrated or tested on data I do
   not have.

So "the app syncs with your wearable" is not an integration: it is a second product (a
companion mobile app) that must exist before the first line of sync code can be written.

## Decision

Two data sources in the MVP, and no live integration:

1. **CSV import** of one night, with a documented format and strict validation
   (`services/parser.py`).
2. **A synthetic night generator** (`services/synthetic.py`) as a first-class part of the
   system — it produces demo data, it is the training set for the staging model, and it is
   the fixture for the test suite.

Live sync through a companion app reading Health Connect / HealthKit is a Beta item in the
roadmap.

## Alternatives considered

| Option | Why not |
|---|---|
| Vendor cloud APIs (Fitbit Web API, Garmin, Withings) | Each is its own OAuth integration, developer registration and review process, and each covers only the users of that one brand. Too much surface for an MVP, and it does not help the user who owns a different watch. |
| Public polysomnography datasets (Sleep-EDF and similar) | They are EEG-based clinical recordings. This product consumes wrist signals; a model trained on EEG would not transfer, and the files do not contain the columns the app reads. Useful later as a sanity check for the *metrics*, not as training data. |
| Wait and record my own nights first | Three weeks of nights is still not enough to train or validate anything, and nothing would exist to show in week 3. |
| A single fixed sample file instead of a generator | Cannot train a model, cannot produce a trend chart, cannot test the correlation logic, and every demo looks identical. |

## Consequences

**Good**

- The product works for anyone whose device can export a CSV, not only one brand's users.
- `USE_MOCK_DB=1` plus the generator means the whole system can be demonstrated on any
  machine with no hardware, no account and no database.
- Deterministic seeds make the test suite reproducible: the same seed is the same ten nights.
- The generator plants known relationships (caffeine, alcohol, stress, late workouts worsen
  sleep), which makes the insights feature verifiable — a correlation the code *should* find.

**Bad — and these are the serious ones**

- **The staging model is trained on simulation and evaluated on simulation.** Its reported
  0.90 accuracy measures how well it learned my generator. The generator and the model share
  my assumptions, so the evaluation cannot catch a wrong one. This is the project's largest
  limitation and is stated in the README, in `/api/model-info` and in the interface.
- **Correlations in demo data are guaranteed**, because they were planted. Demo insights
  demonstrate the feature; they are never a finding.
- **Persona B cannot use the product at all** — she will not export a file. The MVP serves
  only users who are comfortable with exports and a local server.

**Neutral**

- The parser is stricter than a vendor export usually is (gaps over 3 minutes are rejected).
  That is deliberate: interpolating across a long gap would invent sleep stages that look
  identical to measured ones in every chart afterwards.

## Revisit when

A companion mobile app exists (Beta), or a real labelled night becomes available — the second
one should happen first, because it is what turns the model from a demonstration into a
measurement.
