# Backlog — issues to create

The product backlog as GitHub issues, so the board has something in it. Each row is a real
issue: title, labels, priority, and enough acceptance criteria that it can be closed without
an argument.

Priority: **P1** = must happen this semester · **P2** = should · **P3** = if there is time.

Labels used: `security`, `ml`, `data`, `frontend`, `testing`, `docs`, `infra`, `product`,
`tech-debt`, plus the release label `alpha` / `beta` / `final`.

---

## P1 — the ones that matter

### #1 Add authentication and per-user data
`security` `alpha` · from critique #1, gap G-09

Sheepcounter stores health data and has no access control. Adding this later is not a
wrapper: both collections need an owner, and the unique indexes must become compound
(`owner + night_date`) **before** there is data to migrate.

- [ ] Sign-up and sign-in, password hashing, session or token auth
- [ ] `owner` on `nights` and `daily_context`; compound unique indexes
- [ ] Every repository function filtered by owner; a test proves user A cannot read user B
- [ ] `DELETE /api/demo` deletes only the caller's synthetic data
- [ ] README's "no authentication" warning replaced with how auth works

### #2 Validate sleep staging against at least one real night
`ml` `alpha` · from critique #2, gap G-02

The model is trained and evaluated on this project's own simulator. The reported 0.90
accuracy measures how well it learned the generator.

- [ ] Export one real night with the wearable's own stage labels
- [ ] Convert it to the project's CSV format, documented in `sample_data/`
- [ ] Agreement (accuracy + Cohen's κ) computed for **both** the model and the rules
- [ ] The number published in the README and in `/api/model-info`, whatever it is
- [ ] If it is poor, say so rather than retuning until it looks better

### #3 Collect a daily energy rating and calibrate (or demote) the forecast
`product` `ml` `beta` · from critique #3, gap G-04

The forecast is three hand-picked weights presented as a measurement.

- [ ] A one-tap daily rating (1–5) stored with the daily context
- [ ] After 14 ratings, correlation between forecast and rating reported in the UI
- [ ] Either a fitted model with a stated error, or the forecast visually demoted
- [ ] The "uncalibrated" note removed only when it stops being true

### #4 Correct for multiple comparisons in the insights panel
`ml` `alpha` · from critique #7

Six factors tested at p < 0.05 means roughly a 26% chance of at least one false positive.

- [ ] Holm or Benjamini–Hochberg correction across the six tests
- [ ] Or: `notable` requires the relationship to hold in two separate weeks
- [ ] A test with pure noise asserts that nothing is marked notable
- [ ] The panel's wording updated to match whichever rule is chosen

### #5 Set up CI
`infra` `testing` `alpha` · gap G-11

- [ ] GitHub Actions: `pytest` on every push and pull request
- [ ] The Docker image builds in CI
- [ ] A status badge in the README

---

## P2 — should happen

### #6 Add `schema_version` to stored documents
`tech-debt` `data` · from critique #8, gap G-15

- [ ] `schema_version` written by `build_night_document`
- [ ] Startup logs a warning for documents with an older version
- [ ] A short note in `docs/architecture/inventory.md` on how a migration would run

### #7 Annotate every threshold constant with a source
`docs` `ml` · from critique #6

Score bands, recommendation triggers and correlation cut-offs are named constants, but the
reader cannot tell which came from published guidance and which are my judgement.

- [ ] Each constant in `metrics.py` and `insights.py` carries a citation or "chosen by me"
- [ ] The sources collected in one place in `docs/`

### #8 Measure and handle the gap between the two staging methods
`ml` · from critique #5

- [ ] Both methods measured on the same held-out simulated nights
- [ ] The difference recorded in `/api/model-info`
- [ ] Nights staged by the fallback marked in the trend chart

### #9 Remove the `joblib` trust boundary
`security` · from critique #4, gap G-10

- [ ] The trust boundary documented where the model is loaded
- [ ] A checksum written at training time and verified at load
- [ ] Or: the forest exported as parameters instead of a pickle

### #10 Deploy to a cloud host with managed MongoDB
`infra` `alpha` · course milestone, week 7

- [ ] Deployed behind HTTPS, with #1 done first
- [ ] Secrets from the environment, never in the image
- [ ] The URL in the README

### #11 Frontend tests
`testing` `frontend` · from critique #10, gap G-14

- [ ] A headless-browser smoke test: load, seed, select a night, simulate an alarm
- [ ] Asserts no console errors and that each chart canvas rendered
- [ ] Runs in CI

### #12 Rate limiting and upload hardening
`security` · gap G-12

- [ ] Rate limit on `/api/nights/import` and `/api/demo/seed`
- [ ] Request size limited at the server, not only in the handler
- [ ] Security headers on the static responses

### #13 Test that demo data spans a wide score range
`testing` · Sprint 01 retro action

The first version of the generator and score bands squeezed every night into 60–75 and no
test noticed.

- [ ] A test asserting seeded nights span at least 40 score points
- [ ] A test asserting the planted caffeine/alcohol relationships are recoverable

### #14 Validate the personas with real people
`product` · gap from `docs/product/personas.md`

- [ ] Two interviews with people who own a sleep-tracking wearable
- [ ] `personas.md` rewritten where the interviews contradict it
- [ ] Decide whether S-11 (sync) should overtake S-10 (auth)

---

## P3 — if there is time

| # | Title | Labels |
|---|---|---|
| #15 | Companion mobile app reading Health Connect / HealthKit | `beta` `data` |
| #16 | Import adapters for Fitbit / Garmin / Samsung Health exports | `beta` `data` |
| #17 | PDF report export and a shareable single-night link (needs #1) | `beta` `product` |
| #18 | Split `app.js` by panel | `tech-debt` `frontend` |
| #19 | Audio monitoring: snoring and apnoea-like events | `final` `product` |
| #20 | Long-term trends and anomaly detection | `final` `ml` |

---

## Creating these as issues

`gh` reads the label and body from the command line; run from the repository root after
`gh auth login`. Create the labels once:

```bash
for L in security ml data frontend testing docs infra product tech-debt alpha beta final; do
  gh label create "$L" --force
done
```

Then create an issue, e.g.:

```bash
gh issue create \
  --title "Add authentication and per-user data" \
  --label security,alpha \
  --body "Health data with no access control (see docs/architecture/critique.md #1).

- [ ] Sign-up and sign-in, password hashing, session or token auth
- [ ] owner field on nights and daily_context; compound unique indexes
- [ ] Repository functions filtered by owner; test that user A cannot read user B
- [ ] DELETE /api/demo scoped to the caller
- [ ] README warning replaced"
```

**TODO(Charlie):** create #1–#14 by hand rather than scripting all twenty. Writing each body
is the point — a backlog pasted in bulk is a list, not a plan.
