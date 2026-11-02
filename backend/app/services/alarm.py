"""Smart alarm: choose the best wake-up moment inside a time window.

Idea: waking from light sleep (or while already restless) usually feels
easier than being pulled out of deep sleep ("sleep inertia"). Given the
user's window (for example 06:30-07:00) the algorithm picks the first
minute in which the person is in light sleep or awake.

In this prototype the algorithm REPLAYS a recorded night, so it shows what
the alarm would have done. Running it live on streaming data is on the
roadmap. The function itself is pure (no database, no clock), so the same
code can be reused for live data later.
"""
from datetime import datetime

# Higher = easier to wake up. REM is in between; deep sleep is the worst moment.
READINESS = {"wake": 3, "light": 2, "rem": 1, "deep": 0}
GOOD_ENOUGH = 2


def _naive(value: datetime) -> datetime:
    return value.replace(tzinfo=None)  # the app works in local wall-clock time


def simulate_alarm(epochs: list[dict], window_start: datetime, window_end: datetime) -> dict:
    """`epochs` are stored night epochs ({'t': iso, 'stage': ..., ...}). Raises ValueError for bad windows."""
    start, end = _naive(window_start), _naive(window_end)
    if end < start:
        raise ValueError("The window must end after it starts.")

    candidates = [e for e in epochs if start <= datetime.fromisoformat(e["t"]) <= end]
    if not candidates:
        first, last = epochs[0]["t"], epochs[-1]["t"]
        raise ValueError(f"The window is outside the recorded night ({first} to {last}).")

    chosen = next((e for e in candidates if READINESS[e["stage"]] >= GOOD_ENOUGH), None)
    if chosen is not None:
        reason = "First minute in the window with light sleep or wakefulness."
    else:
        best = max(READINESS[e["stage"]] for e in candidates)
        # Nobody is in light sleep: pick the lightest stage available, as late as possible.
        chosen = [e for e in candidates if READINESS[e["stage"]] == best][-1]
        reason = f"No light sleep in the window; chose the lightest available stage ({chosen['stage']}) as late as possible."

    fixed = candidates[-1]  # a normal alarm would ring at the end of the window
    minutes_earlier = int((datetime.fromisoformat(fixed["t"]) - datetime.fromisoformat(chosen["t"])).total_seconds() // 60)
    return {
        "window_start": start.isoformat(timespec="minutes"),
        "window_end": end.isoformat(timespec="minutes"),
        "smart_alarm": {"time": chosen["t"], "stage": chosen["stage"]},
        "fixed_alarm": {"time": fixed["t"], "stage": fixed["stage"]},
        "minutes_earlier": minutes_earlier,
        "reason": reason,
        "better_than_fixed": READINESS[chosen["stage"]] > READINESS[fixed["stage"]],
        "window_stages": [{"t": e["t"], "stage": e["stage"]} for e in candidates],
        "note": "Replay of a recorded night. Evidence that smart alarms improve how people feel is limited.",
    }
