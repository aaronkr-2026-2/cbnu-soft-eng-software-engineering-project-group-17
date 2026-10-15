# Code walkthrough

Written for the week-15 requirement: *pick a file, explain what it does and why it is built
that way.* This is the preparation material — module by module, the non-obvious decision in
each one, and the question I should expect to be asked about it.

Read it with the file open next to it. It is not a substitute for reading the code.

---

## The one path that explains most of the system

Everything important happens on the import path. If I can explain this, I can explain the
project:

```
CSV bytes
  → parser.parse_csv          validate, clean, resample to 1-minute epochs
  → pipeline.build_night_document
        → staging.stage_night        label every minute (model or rules)
              → features.build_features   7 features per minute
        → metrics.summarize_night    TST, latency, WASO, SpO2, score
  → repository.save_night       upsert by night_date
  → MongoDB
```

Demo seeding takes the same path with `synthetic.generate_nights` in place of the parser,
which is why generated and imported nights behave identically everywhere downstream.

---

## `services/parser.py` — the strict front door

Reads the uploaded bytes into pandas, lower-cases and strips the column names, requires
`timestamp` and `heart_rate`, and keeps the four optional columns if present.

Four things worth being able to explain:

1. **Timestamps.** Parsed with `format="ISO8601"` and `errors="coerce"`, so a bad value
   becomes `NaT` instead of raising. If any are bad, the error names the *file line*
   (`idxmax() + 2` — the header is line 1 and rows are 1-based), because "row 338 is broken"
   is useful and "parsing failed" is not. A UTC offset is dropped with `tz_localize(None)`:
   the app works in local wall-clock time, since "I went to bed at 23:40" is a local fact.
2. **Ranges before interpolation.** Each column has a plausible range; values outside it
   become `NaN` and are reported as a warning. They are then interpolated like any other gap.
   Replacing a heart rate of 300 with an interpolated value is a correction; keeping it would
   poison the night's median, which every feature is relative to.
3. **The 1-minute grid.** `resample("1min").mean()` then `interpolate(limit=3,
   limit_area="inside")`. One epoch = one minute everywhere in the system, so every later
   module can count minutes instead of integrating over irregular samples. `limit_area="inside"`
   stops it from extrapolating past the ends of the recording.
4. **Long gaps are rejected, not filled.** If any heart-rate minute is still missing after
   interpolation, the file is rejected with the timestamp of the first gap. The reason is the
   one to give out loud: an interpolated hour would produce sleep stages that look exactly
   like measured ones in every chart afterwards, and nothing downstream could tell them apart.

**Expect to be asked:** *why reject instead of doing your best?* — see point 4.

---

## `services/synthetic.py` — the simulator

Builds a night from the top down: sample the day's factors (steps, caffeine, alcohol, stress,
late workout, bedtime shift) → convert them into a single sleep-quality number → build a
hypnogram from that quality → generate the signals that such a hypnogram would produce.

- `quality_from_factors` is a linear formula with hand-chosen coefficients: caffeine −0.09 per
  cup, alcohol −0.07 per unit, stress −0.07 per point, a late workout −0.12, plus Gaussian
  noise. **These coefficients are the planted relationships** the insights feature later
  finds. That is why a correlation found in demo data is a demonstration and never a finding.
- `_hypnogram` builds 90-minute cycles with deep sleep weighted towards the start of the
  night and REM towards the end, which is the real pattern and also what the `night_frac`
  feature keys on.
- `_ar1` gives the signals autocorrelated noise instead of white noise: real heart rate
  wanders, it does not jump independently each minute. Without this the rolling-standard-
  deviation features would be meaningless.
- Each person is `apnea_prone` with 25% probability, which produces SpO2 dips — that is what
  makes the desaturation metrics testable.
- A seed produces exactly the same nights, which is what the test suite relies on.

**Expect to be asked:** *isn't it circular to train a model on your own simulator?* — yes, and
that is written down as the project's biggest limitation in ADR 002 and the critique.

---

## `services/features.py` — seven features, all relative

Every feature is relative to the person's own night rather than absolute, because resting
heart rate differs between people while the *pattern* within one night is what separates the
stages.

| Feature | What it captures |
|---|---|
| `hr_rel` | heart rate minus this night's median |
| `hr_std_5`, `hr_std_15` | short- and long-window variability — REM and wake are noisy, deep sleep is steady |
| `hrv_rel` | HRV over this night's median — high in deep sleep |
| `mov_5`, `mov_15` | movement averaged over 5 and 15 minutes |
| `night_frac` | position in the night, 0→1 — deep sleep early, REM late |

Rolling windows are `center=True, min_periods=1`, so the windows are symmetric around each
minute and the first and last minutes still get a value instead of `NaN`.

When HRV or movement is missing, neutral values (1.0 and 0.0) are substituted — but note that
this is *not* how the model gets used: `stage_night` refuses to run the model at all in that
case. The neutral values exist so the rule-based path can share the same feature code.

---

## `services/staging.py` — two methods and one dispatch point

**`heuristic_stages`** — the transparent path:

1. Movement over 5 minutes above `ACTIVE_MOVEMENT = 15` counts as active.
2. `_quiet_run_bounds` finds the first and last run of `ONSET_MINUTES = 10` consecutive quiet
   minutes — that window is the sleep period. If no such run exists, the whole night is wake
   (which is a real case, and `test_never_asleep_night_is_all_wake` covers it).
3. Inside the sleep period, thresholds are **percentiles of this night** (25th for relative
   heart rate, 50th and 65th for the variability windows), so they adapt per person instead of
   being universal constants.
4. Deep = low heart rate + low long-window variability + almost no movement. REM = high
   short-window variability, after the first 20% of the night, low movement. Everything else
   is light.
5. `smooth` applies a mode filter over a 5-minute window to remove one-minute flickers
   (deep-light-deep is not physiological). Note the detail: it keeps the original label if it
   is *among* the most common, so it only changes a label that is genuinely isolated.

**`ml_stages`** — RandomForest prediction over the same features, then the same smoothing.

**`stage_night`** is the dispatcher and the rule is one line: use the model only if
`heart_rate`, `hrv_rmssd` and `movement` are all present. Feeding a model neutral substitutes
for signals it was trained to rely on gives confident wrong answers, which is worse than a
simpler method that is honest about having less information.

The model is cached in a module-level variable behind a `threading.Lock`, loaded once at
startup by the FastAPI lifespan. `reset_model_cache()` exists so tests can train into a
temporary directory.

**Expect to be asked:** *why not just impute the missing columns?* — see the dispatch rule.

---

## `services/training.py` — how the model is made

Generates `TRAIN_NIGHTS` (default 60) synthetic nights, builds features for each, and splits
**by whole nights, not by minutes**. That detail matters: minutes within one night are
heavily autocorrelated, so a random minute-level split would put nearly identical neighbouring
minutes in train and test and report an accuracy that means nothing.

RandomForest, 100 trees, depth 12, `class_weight="balanced"` (light sleep is roughly half of
every night, so without balancing the model is rewarded for predicting it everywhere). Saves
`stage_model.joblib` plus a metrics JSON that includes `trained_on: "synthetic"` and the
warning string — the transparency endpoint serves that file's contents directly.

---

## `services/metrics.py` — every number on the dashboard

- `_runs` turns a boolean mask into `(start, end)` pairs by padding with `False` and taking
  `np.diff` — one small helper used for sleep runs, wake runs and desaturation runs alike.
- The **sleep period** is from the start of the first sleep run of at least `MIN_SLEEP_RUN = 5`
  minutes to the end of the last one. A 3-minute doze while reading is not falling asleep, so
  latency is measured to the first *real* onset (`test_short_sleep_blips_before_real_onset_are_ignored`).
- **WASO** is wake time *inside* the sleep period only; wake before onset is latency and wake
  after final awakening is neither. **Awakenings** count wake runs of at least 2 minutes.
- **Desaturations:** points at least `DESAT_DROP = 3.0` below the night's median SpO2; runs
  within 2 minutes of each other are merged into one event, because one dip that briefly
  recovers is one event, not three. ODI is events per hour of sleep; `ODI_ATTENTION = 5` is
  the flag threshold.
- **The score** is six `_band` components. `_band(value, zero_low, full_low, full_high,
  zero_high)` is a trapezoid: 100 inside the healthy range, falling linearly to 0 at the
  outer edges. Weights: duration 0.30, efficiency 0.20, deep 0.15, REM 0.15, latency 0.10,
  WASO 0.10.
- The guard at the top of `sleep_score`: a night with no sleep returns 0 with every component
  0. Without it, zero latency and zero WASO would score full marks for someone who never
  slept — which is exactly what the first version did.

**Expect to be asked:** *where do the bands come from?* — honest answer: commonly cited adult
sleep ranges for duration, efficiency and stage shares, tuned so the demo data spreads across
the scale. This is listed as a weakness in `architecture/critique.md` (#6) and the fix is to
annotate each constant with its source or mark it as my own judgement.

---

## `services/insights.py` — correlations and rules

`build_table` makes one row per night (metrics + bedtime + that day's context);
`correlations` runs `scipy.stats.pearsonr` for each of six factors against the sleep score.

Guards worth explaining: at least 7 nights of paired data, and the factor and the score must
each have more than one distinct value — a constant factor would otherwise raise or produce a
nonsense correlation. A relationship is only marked `notable` at |r| ≥ 0.4, **p < 0.05 and
n ≥ 14**.

`recommendations` runs six rules over the last 7 nights (short sleep, irregular bedtime, low
deep sleep, long latency, low efficiency, repeated oxygen dips) and every one returns an
`evidence` string containing the numbers that triggered it. If nothing fires, it says so
rather than inventing advice.

`bedtime_hour` maps 23:30 → 23.5 and 00:30 → **24.5**, so that the standard deviation of
bedtimes across midnight is meaningful instead of enormous.

**Expect to be asked:** *six tests at p < 0.05 — what about multiple comparisons?* — this is a
real hole, and it is written down as critique #7 with the fix (Holm or Benjamini–Hochberg).
Knowing the weakness is better than being caught by it.

---

## `services/forecast.py` and `services/alarm.py`

`energy_forecast` is a weighted formula — last night's score 0.55, 7-night sleep debt against
a 7.5-hour target 0.25, bedtime regularity 0.20 — and the weights are re-normalised when a
component is missing (fewer than 3 nights drops regularity). It returns its components so the
interface can show the arithmetic, and a `note` saying it is uncalibrated. It is not a model
and the code says so in the docstring.

`simulate_alarm` is a pure function over the stored epochs. `READINESS` ranks the stages
(wake 3, light 2, REM 1, deep 0); the first minute in the window at or above `GOOD_ENOUGH = 2`
wins. If nothing qualifies, it takes the lightest stage available **as late as possible** —
later is better when the choice is bad anyway. It compares against a fixed alarm at the end of
the window and reports `minutes_earlier`. Being pure is deliberate: the same function runs on
live data once a companion app exists.

---

## `repository.py`, `db.py`, `routers/`

`repository.py` holds every query, so there is one place to change if the storage changes.
`_clean` swaps Mongo's `ObjectId` `_id` for a string `id`, because an `ObjectId` is not JSON.
`list_nights` sorts newest-first with a limit and then **reverses**, so the caller gets the
newest N in oldest-first order, which is what charts need. `save_night` is `replace_one(...,
upsert=True)` keyed on `night_date` — that single call is why re-importing a night replaces
it.

The routers do nothing but HTTP: read the request, call a service, map a domain error to a
status code (`ParseError` → 422, missing night → 404, oversized upload → 413). The smart-alarm
endpoint's only logic is its default window: 30 minutes before the night's final awakening.

`db.py` returns either a real `MongoClient` (3-second server-selection timeout, so a missing
database fails fast instead of hanging) or a `mongomock` client when `USE_MOCK_DB=1`.
`get_client` is wrapped in `lru_cache` so one client is reused for the process.

---

## `frontend/app.js`

One module, no framework. `loadNights()` fetches the summaries and fills the night selector;
selecting a night fetches the full document with its epochs and re-renders. Charts are
destroyed and rebuilt on each change, which is wasteful and fine at this size.

Two details worth pointing at:

- Every piece of data goes into the DOM through `textContent`, never `innerHTML` — the values
  come from a file the user supplied, and a warning string containing markup should never
  become markup.
- The hypnogram's y-axis overrides `afterBuildTicks` to force ticks at exactly 0–3. Chart.js
  otherwise placed them at −0.2, 0.8, … and the stage labels silently disappeared. That bug
  was found by looking at the rendered page, which is also the reason critique #10 (no
  frontend tests) is in the list.

---

## Questions I should be able to answer without looking

1. Why is one epoch one minute, and what does that make impossible? (Sub-minute arousals.)
2. Why `night_date = (bedtime − 12 h).date()`? (A 01:30 bedtime belongs to the previous
   evening.)
3. Why does the model only run when three columns are present?
4. Why is a 2-hour gap rejected instead of interpolated?
5. What exactly does 0.90 accuracy measure? (How well the forest learned my simulator.)
6. Why does a night with no sleep score 0 — and what did it score before?
7. Why is `alarm.py` a pure function?
8. What breaks if the app is put on a public URL today? (Everything: no auth, health data.)
