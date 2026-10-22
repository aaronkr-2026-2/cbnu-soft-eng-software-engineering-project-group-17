# Critique of the current design

Week 6 asks for a critique, not a defence. This is a list of what is wrong with the system as
built, worst first, written while the decisions are still fresh enough to be honest about.

Severity is about what happens if the problem is not fixed before the thing is used for real.

---

## 1. Health data with no access control — **critical**

There is no authentication, no user identity and no per-user partitioning. Every night, every
daily-context record and every insight is readable by anyone who can reach the port.

Today that is defensible only because the app is a local prototype, and the README says it
must stay local. But the whole design assumes a single implicit user: `repository.py` has no
owner field, `night_date` is globally unique, and the demo-clear endpoint deletes synthetic
data across the entire database. Adding auth later is not a wrapper — it touches the data
model, every query and every endpoint.

**Fix:** Alpha. Add an owner to both collections and make the unique indexes compound
(`owner + night_date`) *before* there is data to migrate.

## 2. A model that has never seen reality — **critical**

The RandomForest is trained on nights produced by `synthetic.py` and evaluated on more nights
from the same generator. The reported 0.90 accuracy measures how well it learned my simulator.
The simulator and the model share every assumption I made about what deep sleep looks like, so
the evaluation cannot catch a wrong assumption — it is circular by construction.

The product is honest about this (`/api/model-info`, the README, the interface), which makes
it acceptable for a prototype and completely unacceptable for anything else.

**Fix:** Alpha. One real night with the wearable's own stage labels, agreement reported
whatever it turns out to be. A low number published honestly is worth more than this one.

## 3. The forecast is the most confident number and the least supported — **high**

`energy_forecast` outputs "74 — high energy" with component bars. It looks like a model
output. It is three hand-picked weights (0.55 / 0.25 / 0.20) with no ground truth anywhere in
the system, because nothing records how the user actually felt.

The response and the interface both say it is uncalibrated, but presentation outweighs
disclaimers: a big number with a progress bar reads as a measurement.

**Fix:** Beta — collect a daily energy rating, then either fit and report an error, or demote
the display until it earns the prominence it already has.

## 4. `joblib.load` executes whatever is in the file — **medium**

The model is loaded with `joblib`, which unpickles. A `stage_model.joblib` from an untrusted
source would run arbitrary code at startup. Today the file is always produced by this project
on the same machine, and the Docker build regenerates it, so the risk is theoretical — but it
is an unstated trust boundary, which is exactly the kind of thing a security audit finds.

**Fix:** document the boundary now; consider storing the forest as parameters (JSON) rather
than a pickle, or verifying a checksum written at training time.

## 5. The two staging paths can disagree, and nothing notices — **medium**

`stage_night` chooses the model or the rules depending on which columns exist. A user who
imports one night with HRV and one without gets two different algorithms over two nights that
sit side by side in the same trend chart. The night document records which was used and the
interface shows it, but no metric compares them, so a systematic difference (the rule-based
method is roughly 0.68 accurate on simulated nights against the model's 0.90) silently
becomes a step in the trend.

**Fix:** measure the disagreement on simulated nights, and either calibrate the heuristic or
mark affected nights in the trend chart.

## 6. Thresholds are stated with more precision than they deserve — **medium**

The score bands (420 minutes, 0.92 efficiency, 13% deep), the recommendation triggers
(6.5 hours, 10% deep, 30 minutes to fall asleep) and the "notable correlation" cut-offs
(|r| ≥ 0.4, p < 0.05, n ≥ 14) are all named constants at the top of their modules, which is
good. What is missing is a source for each. Some come from widely published sleep guidance,
some are my judgement about what makes the demo legible. Right now the reader cannot tell
which is which.

**Fix:** a citation or an explicit "chosen by me, no source" next to each constant. This is
the honest version of a style pass.

## 7. Multiple comparisons in the insights panel — **medium**

Six factors are correlated against the sleep score and anything with p < 0.05 is marked
*notable*. With six tests, the chance of at least one false positive is roughly 26%, not 5%.
The panel can therefore confidently show a "pattern in your data" that is noise.

The `n ≥ 14` and `|r| ≥ 0.4` conditions reduce it but do not address it. The disclaimer says
correlation is not causation — a different problem from the one this actually is.

**Fix:** a correction (Holm or Benjamini–Hochberg) over the six tests, or phrase a notable
correlation as "worth watching" and require it to persist across two separate weeks.

## 8. No schema version on stored documents — **medium**

The night document's shape is implicit in `pipeline.py`. If a future version adds a metric or
renames a field, old documents will silently miss it and the interface will show blanks.
There is no migration mechanism and no version marker to branch on.

**Fix:** add `schema_version` before the first deployment that holds data worth keeping.

## 9. `app.js` is one 345-line module — **low**

Fetching, state and five chart renderers live in one file. It is still readable, but the
night-selection state is implicit and each chart rebuilds from scratch on every change. At
roughly twice this size it becomes the kind of file where a change in one renderer breaks
another.

**Fix:** split by panel when it next grows; not worth doing today.

## 10. The frontend has no automated tests — **low (now) / medium (later)**

81 backend tests, zero frontend tests. The interface was verified by rendering the page,
reading the console and looking at it. That caught two real defects, so it was not nothing,
but it does not survive a refactor.

**Fix:** week 12, with the real test-suite milestone.

---

## What the design gets right (so the critique stays balanced)

- **The layer rule holds.** No service imports FastAPI; no router touches a collection. That
  is why nine of ten services are testable as plain functions and why the test suite needs no
  database.
- **The logic is deterministic and mostly pure.** `alarm.py`, `metrics.py`, `insights.py` and
  `forecast.py` take data and return data — which is why every metric could be checked against
  a hand calculation in `test_metrics.py` rather than an approximation.
- **Failure paths are explicit.** The parser rejects with a file line number instead of
  guessing; a window outside the night is a 422; a night with no sleep scores 0 instead of
  crashing. These are the cases that were tested first, not last.
- **Honesty is implemented, not just documented.** `evidence` strings, `/api/model-info`, the
  "synthetic" label on demo nights and the uncalibrated note in the forecast response are all
  in the code, so they survive a README going stale.

**TODO(Charlie):** before the week-10 security audit, re-rank items 1, 2 and 4 and decide
which is actually first. My ranking here is a judgement, not a measurement.
