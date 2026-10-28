# User stories and acceptance criteria

Retrofitted onto the existing MVP (course week 4). Status is what the code actually does
today, verified against the test suite; the test that proves each one is named.

Format: *As a [persona], I want [something], so that [reason].*

---

## Epic 1 — Getting data in

### S-01 Import a night from a CSV export · **done**

*As Dmitri, I want to import a night exported from my watch, so that I can analyse data I
actually recorded.*

- [x] A CSV with `timestamp` and `heart_rate` is accepted; `hrv_rmssd`, `spo2`, `movement`
      and `resp_rate` are used when present.
- [x] Data between 10 s and 1 min apart is resampled to 1-minute epochs.
- [x] Gaps of up to 3 minutes are interpolated; a longer gap rejects the file and the message
      names the file line.
- [x] Implausible values are replaced and reported as warnings, not silently kept.
- [x] Importing the same night twice replaces the first import rather than duplicating it.
- [x] A file over 10 MB is rejected with 413 before it is parsed.

*Tests:* `test_parser.py` (12), `test_api.py::test_import_*`

### S-02 Try the product without a wearable · **done**

*As a visitor, I want realistic data with one click, so that I can see what the product does
before investing any effort.*

- [x] One button generates N synthetic nights with their daily context.
- [x] The same seed always produces the same nights.
- [x] Synthetic nights are labelled as synthetic in the interface.
- [x] Removing demo data deletes only synthetic records; imported nights and my own context
      survive.

*Tests:* `test_synthetic_and_staging.py`, `test_api.py::test_clearing_demo_data_keeps_imported_nights_and_user_context`

### S-03 Record what I did during the day · **done**

*As Dmitri, I want to log steps, caffeine, alcohol, stress and late workouts, so that the app
can relate them to my sleep.*

- [x] One record per day, saved and replaced by date.
- [x] Out-of-range values (stress 9, negative steps) are rejected with 422.
- [x] The form states that the day means the day **before** the night.

*Tests:* `test_api.py::test_context_*`

---

## Epic 2 — Understanding the night

### S-04 See my sleep stages · **done**

*As Dmitri, I want the night split into wake / light / deep / REM, so that the summary numbers
mean something.*

- [x] Every epoch gets a stage; the hypnogram shows the whole night.
- [x] The machine-learning model is used only when heart rate, HRV and movement are all
      present; otherwise the rule-based method runs and the night says which was used.
- [x] `/api/model-info` reports how the model was trained, on what, and how it scored.
- [x] The interface states that the model was trained on simulated data.

*Tests:* `test_synthetic_and_staging.py::test_stage_night_*`, `test_api.py::test_model_info_*`

### S-05 See the metrics behind the score · **done**

*As Dmitri, I want time asleep, latency, WASO, efficiency, stage shares, heart rate, HRV and
SpO2, so that I can check the score instead of trusting it.*

- [x] All of the above are computed per night and shown as tiles.
- [x] The 0–100 score shows its six components and what each scored.
- [x] A night with no sleep at all scores 0 and does not crash.
- [x] Oxygen metrics are absent (not zero) when the file had no `spo2` column.

*Tests:* `test_metrics.py` (13 hand-calculated cases)

---

## Epic 3 — Acting on it

### S-06 Find out what affects my sleep · **done**

*As Dmitri, I want to see which daily factors correlate with my sleep score, so that I can
change one of them on purpose.*

- [x] Correlations need at least 7 nights with that factor; a factor with no variation is
      skipped rather than producing a meaningless number.
- [x] Each correlation shows r, p and n.
- [x] A relationship is marked *notable* only at |r| ≥ 0.4, p < 0.05 and n ≥ 14.
- [x] The panel states that correlation is not causation.

*Tests:* `test_alarm_insights_forecast.py` (correlation section)

### S-07 Get advice I can check · **done**

*As Hyejin, I want plain-language suggestions with the numbers that produced them, so that I
can judge whether they apply to me.*

- [x] Every recommendation carries a title, text and an `evidence` string with real numbers.
- [x] Recommendations look at the last 7 nights.
- [x] Nothing in the output names a diagnosis.
- [x] Repeated oxygen dips (≥ 2 of the last 7 nights with ODI ≥ 5) produce an *attention*
      item that suggests talking to a doctor, and says a wearable is not a diagnostic tool.
- [x] When no rule fires, the panel says so rather than inventing advice.

*Tests:* `test_alarm_insights_forecast.py` (recommendation section)

### S-08 Know what tomorrow looks like · **done**

*As Dmitri, I want an energy estimate for the coming day, so that I can plan hard work around
it.*

- [x] A 0–100 score with a label, based on last night, 7-night sleep debt and bedtime
      regularity.
- [x] Each component is shown with its weight and value.
- [x] Fewer than 3 nights → the regularity component is dropped and confidence is "low".
- [x] The response says the formula is uncalibrated.

*Tests:* `test_alarm_insights_forecast.py` (forecast section)

### S-09 Wake up at a better moment · **done (as a replay)**

*As Dmitri, I want the alarm to pick a light-sleep minute inside my window, so that I wake up
less groggy.*

- [x] Given a window, the first light-sleep or awake minute is chosen.
- [x] With no light sleep in the window, the lightest available stage is chosen as late as
      possible, and the reason says so.
- [x] The result is compared with a fixed alarm at the end of the window.
- [x] A window outside the recorded night is rejected with 422.
- [x] The interface and the response state that this is a replay, and that evidence for smart
      alarms is limited.

*Tests:* `test_alarm_insights_forecast.py` (alarm section), `test_api.py::test_smart_alarm_*`

---

## Not built — tracked in the roadmap

| Story | Status | Where |
|---|---|---|
| S-10 Keep my data private from other users (accounts, auth) | not built | Alpha |
| S-11 Sync automatically from my phone instead of exporting files | not built | Beta |
| S-12 Rate my energy each day so the forecast can be calibrated | not built | Beta |
| S-13 Export a report to show a doctor | not built | Beta |
| S-14 Detect snoring / apnoea-like events from audio | not built | Final |
| S-15 See blood-pressure trends | not built | Final |

**TODO(Charlie):** after validating the personas, check whether S-11 should move ahead of
S-10 — if nobody will export a CSV, auth protects data that was never collected.
