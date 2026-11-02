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
