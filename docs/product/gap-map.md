# Gap map

Where the product promises more than it delivers, and where it quietly delivers something it
never promised. Kept as a single page so that nothing gets fixed by being forgotten.

---

## 1. Gaps between the concept and the build

| Gap | Promise | Reality today | Severity | Plan |
|---|---|---|---|---|
| G-01 | "Multimodal biometrics" | Heart rate, HRV, SpO2, movement, respiration. No audio, no blood pressure. | medium | Final release; README states the actual list |
| G-02 | "AI engine" | A RandomForest trained on **simulated** nights + rules. Never validated on real sleep. | **high** | Alpha: validate on at least one real labelled night |
| G-03 | "Smart alarm" | A replay of a recorded night, not an alarm that rings. | medium | Beta, with the companion app; the algorithm is already reusable |
| G-04 | "Energy forecast" | A fixed formula with no ground truth behind it. | **high** | Beta: collect a daily rating, then fit and report the error |
| G-05 | "Cross-platform platform" | One web app, single user, local. | medium | Alpha: deploy with auth |

## 2. Gaps between the personas and the build

| Gap | Who | Problem | Plan |
|---|---|---|---|
| G-06 | Hyejin | Cannot use the product at all: it needs a CSV export and a local server. | Beta companion app |
| G-07 | Both | Correlations need 7 nights and *notable* needs 14 — the first two weeks show nothing. | Accepted. Showing a correlation over 3 nights would be worse than showing none. The interface says how many nights are needed. |
| G-08 | Dmitri | Daily context is typed by hand. Steps could come from the same export the night came from. | Beta |

## 3. Gaps in engineering

| Gap | Problem | Severity | Plan |
|---|---|---|---|
| G-09 | No authentication; anyone reaching the server reads all health data. | **high** | Alpha (week 10 security pass) |
| G-10 | The trained model is loaded with `joblib`, which unpickles — a model file from an untrusted source would execute code. Only self-generated files are used today. | medium | Document the trust boundary; consider shipping the model as parameters rather than a pickle |
| G-11 | No CI: the tests only run when I run them. | medium | Week 13 (course milestone) |
| G-12 | No rate limiting or request size control beyond the 10 MB upload cap. | low (local) → high (deployed) | With Alpha deployment |
| G-13 | Whole-night epochs are embedded in one document; a very long recording approaches MongoDB's 16 MB document limit. | low | Bounded today by `MAX_EPOCHS = 2000`; revisit if multi-night recordings arrive |
| G-14 | The frontend has no tests; it was verified by rendering the page and reading the console. | medium | Week 12, with the real test-suite milestone |
| G-15 | No migrations: the night document shape is implicit in `pipeline.py`. Changing it orphans old records. | medium | Add a `schema_version` field before the Alpha deployment |

## 4. The reverse gap — delivered but never promised

| What | Why it is here |
|---|---|
| `/api/model-info` | Needed to be honest about a model trained on simulation |
| Desaturation event detection, ODI, T90 | A nightly mean SpO2 says nothing; the dips are the signal |
| `USE_MOCK_DB=1` | Makes the product demonstrable and testable with no infrastructure |
| Score breakdown in the interface | A score with no breakdown is exactly the thing this product exists to replace |

---

## The three that matter most

If only three things get fixed this semester, these:

1. **G-02 / G-09** — a model validated on nothing, serving health data with no auth. These
   are the two that would make a reviewer stop reading.
2. **G-04** — the forecast is the most confident-sounding number in the product and the least
   supported. Either it gets ground truth or it gets marked clearly as a toy.
3. **G-06** — if the product only works for people like me, the personas are decoration.

**TODO(Charlie):** after the week-7 and week-10 milestones, update the severity column here
rather than writing a new document.
