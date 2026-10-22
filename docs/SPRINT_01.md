# Sprint 01 — MVP

Week 5 of the course asks for a lightweight Agile process retrofitted onto work that is
already running. This is that retrofit: the sprint that produced the MVP, written down after
the fact, plus the process I will actually use from Sprint 02 on.

**Dates:** 2026-10-15 (one working session) · **Team:** solo · **Goal below.**

---

## Sprint goal

> A person with no wearable can open the app, load demo data and read a full night analysis
> with the reasoning visible; a person with a CSV export can import their own night and get
> the same.

One sentence, and it is testable — which is the only thing that makes a sprint goal useful
when there is nobody else to disagree with me.

---

## What was committed and what happened

| Story | Points | Status | Note |
|---|---:|---|---|
| S-01 Import a night from CSV | 5 | done | stricter than planned (gaps rejected, not filled) |
| S-02 Demo data without a wearable | 5 | done | became the training set as well |
| S-03 Daily context | 2 | done | |
| S-04 Sleep stages | 8 | done | two methods instead of one — see ADR 003 |
| S-05 Metrics and score | 5 | done | oxygen metrics grew beyond plan (creep audit #1) |
| S-06 Correlations | 3 | done | |
| S-07 Recommendations with evidence | 3 | done | |
| S-08 Energy forecast | 2 | done | |
| S-09 Smart alarm | 3 | done | replay only, as planned |
| — Web interface | 8 | done | |
| — Tests | 5 | done | 81 tests |
| — Docker, docs | 5 | done | |
| **Total** | **54** | **12 / 12 done** | |

Velocity from one sprint is not a velocity. It is a starting number for Sprint 02 and nothing
more.

## Not committed, on purpose

Authentication, live wearable sync, audio monitoring, blood pressure, report export. Each
one has a reason and a release in [product/creep-audit.md](product/creep-audit.md) and
[ROADMAP.md](../ROADMAP.md).

---

## Definition of done (Sprint 01)

A story is done when:

1. the code is in the repository and I have read every line of it;
2. there is a test that would fail if the behaviour broke, and `pytest` is green;
3. failure paths are handled explicitly, not by a stack trace;
4. anything derived from a model or a formula states what it was built on;
5. the feature is reachable from the interface, not only from the API.

All twelve items meet this. Where they do not meet something *stricter* — a validated model,
real-user validation of the personas — that is recorded as a gap rather than quietly counted
as done.

---

## Retrospective

**What worked**

- Writing the parser's failure cases first. The gap rule, the range rule and the file-line
  error message were decided before any analysis code existed, and nothing downstream had to
  defend itself against malformed input afterwards.
- Keeping services free of FastAPI and of the database. It cost nothing and it is why 81
  tests run with no infrastructure.
- Building the synthetic generator early. It unblocked the model, the tests and the demo at
  once — three problems solved by one module.
- Hand-calculating expected metric values in the tests instead of asserting what the code
  already returned. That is what caught the all-wake night scoring 20.

**What did not**

- The first version of the score bands and the generator coefficients squeezed every night
  into 60–75. The feature "worked" and demonstrated nothing. I only noticed by looking at the
  seeded data, not from a test — **a test asserting that demo nights span a wide range would
  have caught it**, and there still is not one.
- Scope grew inside two stories (oxygen metrics, the model-info endpoint) without a decision
  being written down first. Both are defensible; neither was decided.
- The frontend was verified by looking at it. That found two real bugs, which is an argument
  for looking — and no argument at all for not having tests.

**Actions for Sprint 02**

1. Add a test that demo data spans a wide score range (closes the gap that let #1 happen).
2. Annotate every threshold constant with a source or an explicit "my judgement" (critique #6).
3. Decide the multiple-comparison correction for the insights panel (critique #7).
4. Validate the personas with two real people before building anything else for them.
5. Write the decision *before* the code when scope grows, even by one function.

---

## The process from Sprint 02 on

Solo Scrum, stripped to what a single person actually benefits from:

- **Sprint length:** one week, aligned with the course milestone for that week.
- **Planning:** pick a goal in one sentence; pull only stories that serve it; anything else
  goes to the backlog, not into the sprint.
- **Backlog:** GitHub issues, labelled and prioritised — see
  [backlog-issues.md](backlog-issues.md).
- **Board:** the repository's GitHub Projects board, three columns (To do / Doing / Done),
  one item in Doing at a time.
- **Daily:** a two-line note in the issue I am working on — what moved, what is blocked.
  Nobody needs a stand-up with themselves; the written trail is for the teacher and for me in
  week 15.
- **Review:** at the end of the week, the milestone deliverable is demonstrable in the running
  app, not only in a document.
- **Retro:** three headings, as above, and **the actions become issues** — a retro action that
  is not an issue did not happen.
- **AI log:** one `AI_LOG.md` entry per sprint, filled in at the retro while it is still
  accurate.

**TODO(Charlie):** create the GitHub Projects board and move the issues from
`backlog-issues.md` into it, so the process has somewhere to live.
