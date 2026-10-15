# Personas

Two personas, retrofitted onto a product that already existed (week 4 of the course asks for
exactly that: personas for work already started, not personas invented first).

> **Validation status: not validated.** Both personas were written from my own reasoning
> about who the product is for, not from interviews. Persona A is close to me, which is the
> classic trap — a persona that is really the author agrees with every decision I already
> made.
>
> **TODO(Charlie):** talk to at least two real people who own a sleep-tracking wearable, ask
> the questions at the bottom of this file, and rewrite whatever turns out to be wrong.
> Record who I spoke to and the date here.

---

## Persona A — Dmitri, 24, graduate student

**Lives with:** a smartwatch he bought himself, mostly to see his heart rate.

**Context.** Classes two days a week, lab work the rest, occasionally a night shift. Bedtime
moves between 22:30 and 02:00 depending on what is due. Drinks coffee late when a deadline is
close. Comfortable with a terminal; will happily run `docker compose up`.

**What he does today.** Opens the watch's app in the morning, sees "Sleep score 72", shrugs,
closes it. The number changes and he never learns why.

**Goal.** Find out which of the things he actually controls — bedtime, caffeine, alcohol,
training time — moves his sleep, so he can stop guessing.

**Frustrations.**
- The vendor app shows conclusions with no reasoning and no numbers.
- Every app wants an account and uploads his health data to someone's server.
- "Sleep score" is defined differently by every vendor and explained by none.

**What makes him trust a tool.** Seeing the rule that fired and the data behind it. He would
rather read "deep sleep averaged 8.4% over 7 nights" than "your deep sleep is poor".

**How he reaches SleepInsight.** Exports a CSV, runs the app locally, imports the night.

---

## Persona B — Hyejin, 47, office worker

**Not me, and deliberately not technical.**

**Context.** Works in an office, wears a fitness band her daughter set up for her. Sleeps
about six hours, wakes up two or three times, snores (her husband says so). She is tired in
the afternoons and has started to wonder whether it is "just age".

**What she does today.** Looks at the band's weekly summary. Does not export anything. Does
not know what REM is, and does not want a lecture about it.

**Goal.** Know whether what she experiences is worth taking to a doctor, and what to say when
she gets there.

**Frustrations.**
- Health apps either say nothing or sound alarming.
- She has read online that a watch can "detect sleep apnoea" and does not know whether to
  believe it.
- Setup steps with exports and files are a wall; her daughter would have to do it.

**What makes her trust a tool.** Plain language, honesty about limits, and a clear line
between "here is what was measured" and "here is what it might mean". A tool that told her
she had a condition would make her trust it *less*, not more.

**How she reaches SleepInsight today.** She does not, and that is a real finding: the MVP
needs a CSV export and a local server. For her the product is the Beta companion app
([ROADMAP.md](../../ROADMAP.md)), and the MVP serves her only through her daughter.

---

## What each persona demands of the product

| | Dmitri | Hyejin |
|---|---|---|
| Must have | raw numbers, the rule that fired, local data | plain language, no diagnosis, no setup |
| Breaks the deal | hidden reasoning, forced cloud account | technical jargon, alarming wording |
| MVP serves them? | yes | no — Beta |

Hyejin is why `/api/insights` returns `evidence` as a sentence and not just a number, why the
oxygen recommendation says "consider discussing it with a doctor" instead of naming a
condition, and why "not a medical device" is in the interface and not only in the README.

---

## Questions to ask the real people (TODO(Charlie))

1. What do you look at in your sleep app in the morning, and what do you do after looking?
2. Has a sleep app ever told you something you acted on? What was it?
3. When it says your sleep was "poor", do you believe it? Why?
4. Would you export a file to get a better analysis? (Watch for the polite "yes".)
5. What would make you distrust a sleep app?
