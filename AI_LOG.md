# AI_LOG.md

AI collaboration log for the SleepInsight semester project (Advanced Software Engineering,
8866357-02). Template from the course project guide; one entry per milestone.

> **Honesty note.** This project is built with heavy AI assistance, and the entries below say
> so plainly. What the course grades is not how little AI I used, but whether I understood,
> decided and can defend what is in the repository. Lines marked **TODO(Charlie)** are my own
> reflection, which I fill in after reviewing the code — they are not for an AI to write.

---

## Milestone 1: idea, stack, MVP skeleton — 2026-10-15

**Tool(s) used:** Claude (claude.ai, Sonnet/Opus), used as a pair programmer in one long
session with file and shell access.

**What I asked for:** I brought my own product concept (multimodal sleep analysis: biometrics
→ AI engine → insights, smart alarm, forecasts) and asked for a working prototype of the
whole application rather than a snippet. I answered its clarifying questions myself and those
answers set the project:

- stack: FastAPI + MongoDB + plain HTML/JS (what I already know and read fluently — Python,
  FastAPI, MongoDB and ML are my working stack, see `docs/architecture/adr/001-stack.md`);
- data: CSV import **and** a synthetic generator, because neither Apple nor Google exposes a
  server API for sleep data (see `docs/architecture/adr/002-data-source.md`);
- AI engine: rule-based heuristics **plus** scikit-learn, not deep learning;
- MVP scope: import, night analysis, insights, recommendations and the smart alarm; audio
  monitoring, blood pressure, report export and live wearable sync pushed to the roadmap.

**What I kept as-is:** the layered structure (`routers` → `services` → `repository`), the CSV
parser's validation rules, the night metrics, the score weights after retuning, the test
suite (81 tests) and the web interface.

**What I changed or rejected, and why:**
- Rejected the original concept's full feature list for the MVP. Audio monitoring and blood
  pressure are each a second data pipeline; shipping them badly would have cost the parts
  that make the product defensible. Recorded in `docs/product/creep-audit.md`.
- Rejected deep learning for sleep staging. 60 simulated nights cannot justify it, and I
  cannot defend a model I cannot explain in a live walkthrough. A RandomForest on seven named
  features I can.
- Rejected a live wearable integration after checking: Apple Health has no server API and
  Google Fit's API is being retired in favour of Health Connect, which is on-device. Any live
  sync needs a companion phone app — that is a Beta item, not an MVP item.
- Changed the staging rule: the machine-learning model is only used when heart rate, HRV and
  movement are all present; otherwise the app falls back to the rule-based method instead of
  feeding the model columns it was not trained on.

**Something the AI got wrong that I had to catch:** several things, found while reviewing and
while running the thing. Honest attribution: the defects in the first group were caught by
the AI itself during its own review and test runs, the ones in the second group are mine.

Caught during the AI's own review/testing (all fixed, all in the code now):
1. The synthetic generator produced bedtimes with fractional seconds, so epochs did not land
   on whole minutes and the parser's resampling behaved inconsistently.
2. An all-wake night (someone who never fell asleep) scored 20 out of 100 instead of 0,
   because the score components were computed before checking that any sleep existed.
3. The first version of the score bands and the generator's coefficients squeezed every night
   into the 60–75 range, so the demo data showed no visible effect of caffeine or alcohol —
   the feature "worked" and demonstrated nothing. Both were retuned.
4. `/api/insights` crashed with a `KeyError` on an empty database (sorting an empty table by
   a column that does not exist yet). Found by a test written for exactly that case.
5. The web interface built the default alarm window with buggy date arithmetic, and the
   hypnogram lost its "Awake"/"Deep" axis labels because Chart.js placed ticks at non-integer
   values.

**TODO(Charlie):** add here what *I* caught when I read the code myself — at minimum one
place where I disagreed with how something is written, and one number (a threshold or a
weight) I checked against a source rather than trusting. This line stays until I write it.

**TODO(Charlie):** record the build log the course asks for — what I ran, what broke on my
machine, and how long the first `docker compose up --build` took.

---

## Template for the next entries

```
## [Milestone name] — [Date]
**Tool(s) used:**
**What I asked for:**
**What I kept as-is:**
**What I changed or rejected, and why:**
**Something the AI got wrong that I had to catch:**
```
