# AGENTS.md

Conventions for AI assistants (and for me) working in this repository. Keep this file short
enough that it is actually read.

## The rule that overrides everything

**I have to be able to explain every line in this repository**, unscripted, in the week-15
walkthrough. So:

- No code I have not read goes into a commit.
- No dependency gets added to make one line shorter. A new package needs a reason in
  `README.md` (third-party table) and, if it changes the architecture, an ADR.
- Clever beats nothing; clear beats clever. If a function needs a paragraph to explain, it
  should be rewritten rather than annotated.

## Project shape

```
backend/app/routers/     HTTP only: parse the request, call a service, shape the response
backend/app/services/    all the logic; pure functions where possible, no database access
backend/app/repository.py every MongoDB query, and nothing else
frontend/                plain HTML/CSS/JS, no build step, no framework
```

- Routers never touch `db.*` collections directly — they call `repository`.
- Services never import `fastapi` and never read `request`.
- `config.py` holds every setting; nothing else calls `os.environ`.

## Style

- Python: standard library style, type hints on function signatures, f-strings. Line length
  up to ~140 characters — this project favours one readable line over a wrapped one.
- Docstrings explain **why**, not what. The code already says what.
- Numbers that come from sleep research or from a decision (thresholds, weights, ranges) are
  named constants at the top of their module, not literals buried in an `if`.
- Frontend: no `innerHTML` with data; build nodes and set `textContent`.
- English in code, comments, commits and documentation. (Working notes may be in Russian.)

## Health-data rules

- Never write a sentence that diagnoses. "Your oxygen dipped on 3 of 7 nights, consider
  discussing it with a doctor" is allowed; "you have sleep apnoea" is not.
- Every recommendation carries the numbers that triggered it (`evidence`).
- Anything produced by a model or a formula says what it was trained or built on, and how
  reliable it is. If it is uncalibrated, it says so in the response itself.

## Tests

- A new rule, metric or threshold arrives with a test that checks a hand-calculated case.
- Tests must not need MongoDB (`USE_MOCK_DB=1`, `mongomock`) and must not reach the network.
- `pytest` from `backend/` must stay green before a commit.

## Asking an AI assistant for work

1. Give it the context files first (this one, the relevant service, the test file).
2. Ask for one thing at a time, and ask for the reasoning, not only the code.
3. Read the result line by line. Where it guessed a number, check the number.
4. Log the session in `AI_LOG.md`: what I asked, what I kept, what I changed, what it got
   wrong. The log is graded on honesty.

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
