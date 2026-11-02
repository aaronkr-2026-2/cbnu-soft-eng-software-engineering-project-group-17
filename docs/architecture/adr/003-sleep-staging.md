# ADR 003 — Rule-based staging and a RandomForest, chosen by which signals a file has

- **Status:** accepted
- **Date:** 2026-10-15
- **Deciders:** Charlie (solo project)

## Context

Everything downstream — the metrics, the score, the insights, the alarm — depends on one
thing: labelling each minute of the night as wake, light, deep or REM. The input is wrist
data (heart rate, HRV, movement, SpO2, respiration), not EEG, so there is no ground truth in
the data itself.

Two more constraints: imported files vary in which optional columns they contain, and the
training data available is simulated (see ADR 002).

## Decision

Two methods, and an explicit rule for which one runs:

- **Rule-based** (`heuristic_stages`): per-night percentile thresholds on relative heart rate
  and movement, then a mode filter that removes one-minute flicker. Works with heart rate
  alone.
- **RandomForest** (100 trees, depth 12, balanced classes) over **seven named features**:
  relative heart rate, heart-rate variability over 5 and 15 minutes, relative HRV, movement
  over 5 and 15 minutes, and position within the night.
- **The model runs only when heart rate, HRV and movement are all present.** Otherwise the
  rules run.
- The night document records which method was used, the interface shows it, and
  `/api/model-info` reports the training details and metrics.

Measured on held-out *simulated* nights: model ≈ 0.90 accuracy (κ ≈ 0.84), rules ≈ 0.68.

## Alternatives considered

| Option | Why not |
|---|---|
| A neural network (LSTM or CNN over the raw signal) | 60 simulated nights cannot justify it; it would learn the generator even harder than the forest does; and I could not explain it line by line in the week-15 walkthrough, which the course requires. |
| Rules only | Roughly 0.68 on simulated nights, and no way to weigh several weak signals against each other. Keeping it as the fallback preserves its one real advantage: it works with one column. |
| Model only, imputing the missing columns | Feeding a model zeros or means for signals it was trained to rely on produces confident, wrong labels — worse than a simpler method that is honest about using less information. |
| A pre-trained open model | None exists for this exact feature set, and adopting one would move the "I cannot explain it" problem rather than solve it. |

## Consequences

**Good**

- A file with only heart rate still produces a full analysis.
- The forest is explainable: seven features with names, and per-stage recall published.
- The rule-based path doubles as the baseline the model is measured against — without it,
  0.90 would have no comparison.
- `stage_night` is the single dispatch point, so there is one place where this logic lives.

**Bad**

- Two code paths to maintain, test and keep consistent.
- Nights staged by different methods sit side by side in the same trend chart with a roughly
  0.22 accuracy difference between them and nothing marking the discontinuity (critique #5).
- The model's accuracy is an accuracy *against the simulator*. It is not evidence about real
  sleep, and every place that shows the number says so.

**Neutral**

- The model is cached at module level and loaded once at startup; `reset_model_cache()` exists
  so tests can train into a temporary directory.

## Revisit when

A real labelled night exists. At that point both methods should be re-measured against it,
and the headline number in the README replaced with the real one — whatever it is.
