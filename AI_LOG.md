# AI_LOG.md

AI collaboration log for the Sheepcounter semester project (Advanced Software Engineering,
8866357-02). Template from the course project guide; one entry per milestone.


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

---

## Milestone 2: deployment on Render — 2026-11-02

**Tool(s) used:** Claude (claude.ai), reading the Render deploy log, the Dockerfile and the
app's configuration (`backend/app/config.py`, `backend/app/main.py`).

**What I asked for:** help putting the site online: the app on Render, built from the existing
Dockerfile, and the database on a free MongoDB Atlas cluster. The first deploy failed and I did
not know why, so I gave Claude the Render log and asked it to find the cause.

**What I kept as-is:** Claude's diagnosis. The build itself was fine (dependencies installed,
the model trained, the image was built). The app crashed on startup with
`pymongo.errors.OperationFailure: bad auth : Authentication failed` while creating indexes
(`ensure_indexes`), because Atlas rejected the username and password in `MONGO_URL`. Render's
"No open ports detected" was a consequence of that crash, not a separate problem, so I left
`PORT=8000` and the Dockerfile alone. I also kept the deploy settings: Docker, Singapore region,
Free instance, health check on `/api/health`.

**What I changed or rejected, and why:**
- The fix was configuration only, no file in this repository changed. I set a new password for
  the Atlas database user `Sheepcounter_app` and put the corrected connection string into
  `MONGO_URL` in Render's Environment Variables. The password lives only in Render, not in git.
- Moved the Render service from my personal `sheepcounter` repository to this course
  repository (group-17), so the live site is built from the same code the teacher reviews.
- Result: the site is live at https://cbnu-soft-eng-software-engineering-puhw.onrender.com/.

**Something the AI got wrong that I had to catch:** Claude's example connection string used
`sheepcounter_app` in lowercase, but my Atlas user is `Sheepcounter_app`. MongoDB usernames are
case-sensitive, so copying the example as written produces exactly this `bad auth` error. Claude
pointed out the mismatch itself when I asked which user's password to reset.

---

## Milestone 3: README and AI log update — 2026-11-02

**Tool(s) used:** Claude (claude.ai, Opus 5.5), reading this repository's git history.

**What I asked for:** a "Live Demo" link at the top of the README and the Milestone 2 entry in
this log. I asked Claude to take the cause of the failed deploy from the git history only, and
to stop and ask me if the history did not show it unambiguously.

**What I kept as-is:** the placement of the Live Demo link right after the project description,
and the content of the Milestone 2 entry.

**What I changed or rejected, and why:** I did not let Claude edit the repository. It gave me
the text and I made the changes in both files myself, so every change in my working copy is one
I made and can explain.

**Something the AI got wrong that I had to catch:** nothing in this step. Worth recording:
Claude checked `git log` and found no commit that fixed the deploy (the deploy files were last
changed on 2026-10-15, before the deploy), so it stopped and asked instead of inventing a code
fix. That is why Milestone 2 is based on the deployment conversation, not on a commit.
