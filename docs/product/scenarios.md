# Scenarios

Narrative walkthroughs of the product in use. They come before the user stories, because a
scenario shows the seams between features that a story list hides.

---

## Scenario 1 — "Why was last night bad?" (Dmitri, works today)

It is 08:10. Dmitri slept badly and wants to know whether it was the two coffees after the
seminar or just the deadline.

He opens Sheepcounter, which is already running locally. He exported last night from his
watch to `night-2026-03-02.csv` and presses **Import CSV**. The file is accepted; a line
appears saying the night was imported, with a warning that 4 heart-rate values were outside
the plausible range and have been interpolated.

The night appears in **Night detail**: score 61, asleep 5 h 48 min, fell asleep after 39
minutes, awake 51 minutes during the night, deep sleep 9.4%. The hypnogram shows a long wake
block around 03:00. Below it, the score breakdown shows which component cost him the points —
latency scored 0, duration 48.

He scrolls to **Daily context**, picks yesterday's date, enters 2 caffeinated drinks after
14:00, stress 4, and saves.

**Insights** now covers 18 nights. Caffeine shows r = −0.52 over 18 nights, p = 0.027, marked
*notable*. The recommendation below it says exactly that, with the numbers, and adds that a
correlation in his own records is not proof of cause.

He has what he came for: not a verdict, but the two numbers he can check again next week.

**Seams this scenario exposed**
- The context has to be entered *after* the night, for the day *before* it. That is confusing
  and the form has to say which day it means. (It does; the label is "the day before the
  night".)
- Warnings from the parser must survive to the interface, not be swallowed — otherwise
  interpolated data looks like measured data.

---

## Scenario 2 — "Is this worth a doctor?" (Hyejin, with her daughter, works today)

Hyejin's daughter sets the app up at home and imports a week of her mother's nights.

Four of the seven nights have 5 or more oxygen desaturations per hour. The
**Recommendations** panel shows an item marked *attention*: repeated blood-oxygen dips, with
the sentence that a wearable's SpO2 is not a diagnostic tool, that this is 4 of the last 7
nights, and that it is worth discussing with a doctor — especially alongside snoring or
daytime sleepiness.

Hyejin takes a photo of the panel to her clinic appointment.

**What the product must never do here:** name a condition. The value of this scenario is
entirely in the restraint. It also has a cost: it is the scenario most likely to be
misunderstood, so the disclaimer is attached to the panel itself and not only to the footer.

---

## Scenario 3 — "Wake me at a good moment" (Dmitri, works today, as a replay)

Dmitri has to be up by 07:00 and would rather not be dragged out of deep sleep.

He opens last night, sets the window 06:30–07:00 and presses **Simulate**. The app replays
the recorded night: at 06:30 he was in deep sleep; the first light-sleep minute inside the
window was 06:41. A fixed alarm at 07:00 would have rung while he was in deep sleep again.

The panel says the smart alarm would have rung 19 minutes earlier, in light sleep, and adds
that the evidence that smart alarms improve how people feel is limited.

**The seam this exposes, honestly:** this is a replay, not an alarm. The algorithm is a pure
function (`services/alarm.py`) precisely so that the same code can run on live data once a
companion app exists, but today it answers "what would have happened", not "wake me".

---

## Scenario 4 — "I have no wearable" (a classmate, works today)

Someone opens the project to see what it does and has no data at all.

They press **Load demo data**. 28 synthetic nights appear with their daily context, generated
by the project's own simulator. Everything in the product works immediately: charts,
correlations, forecast, alarm.

**The honesty requirement this creates:** the demo data has relationships planted in it, so a
correlation found in demo data is a demonstration, not a discovery. The night detail panel
labels synthetic nights as synthetic, and the README says it again.

---

## Scenario 5 — "A broken export" (failure path, works today)

A user exports from an app that writes a row every 5 minutes, with a two-hour gap where the
watch was charging.

The import is rejected with a message naming the problem and the file line where the gap
starts. Nothing is saved. The user can fix the file or import a different night.

**Why rejection, not a best effort:** interpolating across two hours would invent a sleep
stage for a period where nothing was measured, and the invented part would be indistinguishable
from the measured part in every chart afterwards.
