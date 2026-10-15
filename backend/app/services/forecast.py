"""Next-day energy forecast.

A transparent weighted formula, NOT a trained or validated model. It combines
three things that sleep research links to next-day alertness:

    last night's sleep score   (weight 0.55)
    sleep debt over 7 nights   (weight 0.25)   target: 7.5 h per night
    bedtime regularity         (weight 0.20)

There is no ground truth (self-reported energy) in the data yet, so the
output is an uncalibrated estimate. The roadmap adds a daily energy rating
so a real model can be fitted and checked later.
"""
from datetime import date, timedelta

import numpy as np

from .insights import bedtime_hour

TARGET_SLEEP_MIN = 7.5 * 60
WEIGHTS = {"last_night": 0.55, "sleep_debt": 0.25, "regularity": 0.20}


def _label(score: float) -> str:
    return "low" if score < 40 else "moderate" if score < 70 else "high"


def energy_forecast(nights: list[dict]) -> dict | None:
    """`nights` must be sorted oldest -> newest. Returns None when there is no data."""
    if not nights:
        return None
    recent = nights[-7:]
    last = recent[-1]

    last_score = float(last["summary"]["score"])
    debt_min = max(0.0, TARGET_SLEEP_MIN * len(recent) - sum(n["summary"]["total_sleep_min"] for n in recent))
    debt_score = 100.0 - min(100.0, debt_min / 60 * 12)  # every hour of debt costs 12 points

    components = [
        {"name": "Last night's sleep score", "value": round(last_score), "weight": WEIGHTS["last_night"]},
        {"name": "Sleep debt (7 nights)", "value": round(debt_score), "weight": WEIGHTS["sleep_debt"], "detail": f"{debt_min / 60:.1f} h below target"},
    ]
    if len(recent) >= 3:
        std_h = float(np.std([bedtime_hour(n["start"]) for n in recent]))
        components.append(
            {"name": "Bedtime regularity", "value": round(100.0 - min(100.0, std_h * 50)), "weight": WEIGHTS["regularity"], "detail": f"bedtime varies by {std_h * 60:.0f} min"}
        )

    total_weight = sum(c["weight"] for c in components)  # re-normalise if a component is missing
    energy = sum(c["value"] * c["weight"] for c in components) / total_weight

    wake_day = date.fromisoformat(last["night_date"]) + timedelta(days=1)
    return {
        "for_date": wake_day.isoformat(),
        "based_on_night": last["night_date"],
        "nights_used": len(recent),
        "energy_score": round(energy),
        "label": _label(energy),
        "components": components,
        "confidence": "low" if len(recent) < 3 else "moderate",
        "note": "Uncalibrated estimate from a fixed formula; it has not been validated against how people actually feel.",
    }
