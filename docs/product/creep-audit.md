# Scope-creep audit

The original product concept was large: multimodal biometrics, audio monitoring of snoring
and apnoea-like events, blood-pressure trends, an AI engine, a smart alarm, forecasts,
reports to share with a doctor, live synchronisation with wearables.

This file records what was cut from the MVP, why, and what the cut costs. The point of the
audit is that a cut with no recorded reason comes back as a surprise in week 10.

---

## Cut, with reasons

| # | Cut from MVP | Why | What it costs | Returns in |
|---|---|---|---|---|
| 1 | **Audio monitoring** (snoring, apnoea-like events) | A second data pipeline end to end: microphone capture, a privacy model for recording someone's bedroom, on-device processing, its own detection logic and its own validation problem. Larger than the rest of the MVP combined. | The apnoea-adjacent story is weaker: only SpO2 supports it. | Final |
| 2 | **Blood pressure** | No consumer wearable within reach measures it in a way worth analysing. Building a trend view over fabricated numbers would be a demo of nothing. | The "multimodal" claim is narrower than the concept promised. The README says so. | Final |
| 3 | **Live wearable sync** | Checked before deciding: Apple Health has no server API, and Google Fit's REST API is being retired in favour of Health Connect, which is on-device. Any live sync needs a companion phone app — a separate product. | Users must export a CSV, which Persona B will not do. This is the MVP's biggest adoption gap. | Beta |
| 4 | **Report export and sharing** | Sharing a health report without accounts is a data leak with extra steps. Auth has to come first. | Hyejin photographs the screen instead of exporting a PDF. | Beta |
| 5 | **Authentication / multiple users** | Deliberate for an MVP that runs on one machine — but it is the item I am least comfortable with, because the data is health data. It is first in the Alpha list and first in the security pass. | The app must not be put on a public URL as it is. Stated in the README and in the architecture critique. | Alpha |
| 6 | **Deep learning for sleep staging** | 60 simulated nights cannot justify a neural network, and the course requires me to explain every line in a live walkthrough. | Staging accuracy may be lower than the state of the art — but the state of the art is measured on real polysomnography, which this project does not have either. | — |
| 7 | **Several vendor import formats** | One well-specified format first. Each vendor export is its own parser and its own set of quirks. | Anyone whose export does not match must convert the file. | Beta |
| 8 | **Long-term trends, anomaly detection, benchmarks** | Need months of data, and benchmarks need other users and a privacy review. | The app analyses nights and weeks, not seasons. | Final |

---

## Kept, and why each earned its place

| Kept | Why it is not creep |
|---|---|
| Synthetic generator | Without it the product cannot be demonstrated, tested or developed — I do not have months of wearable data. It is also what the model trains on. It is infrastructure, not a feature. |
| Smart alarm (replay) | It is the concept's most distinctive feature. As a pure function over a recorded night it cost one small module and no new data pipeline, and the same code runs live later. |
| Daily context | The insights feature is empty without it: correlations need something to correlate the score with. |
| Energy forecast | Small (a formula), directly from the concept, and it exposes a real weakness honestly — which is more useful in week 15 than a feature that hides one. |

---

## Creep that happened anyway (honest)

Two things grew beyond the plan during the MVP build:

1. **Oxygen metrics.** The plan said "SpO2 mean/min". The result also has desaturation event
   detection with dip merging, ODI and T90. Justification: a mean SpO2 over a night is almost
   useless — the dips are the signal. Cost: the most intricate function in `metrics.py` and
   the one with the most tests.
2. **The model-transparency endpoint** (`/api/model-info`) was not in the plan. It exists
   because the model is trained on simulated data, and shipping that without a visible way to
   see the training details would have been dishonest.

Both are defensible, but both are still scope that arrived without a decision being written
down first — which is exactly the pattern this audit is meant to catch.

**TODO(Charlie):** at the week-10 security pass, re-read row 5 and decide whether the Alpha
plan is still good enough, or whether auth has to come earlier.
