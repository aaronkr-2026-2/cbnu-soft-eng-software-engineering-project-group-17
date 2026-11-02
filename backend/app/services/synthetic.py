"""Synthetic sleep data generator.

WHY THIS EXISTS
    Apple Health has no server API and Google Fit's API is being retired in
    favour of Health Connect, so a web prototype cannot pull live wearable
    data. Instead the app (1) imports CSV files and (2) uses this generator
    to create realistic demo nights and labelled training data.

IMPORTANT LIMITATION
    The data is simulated by rules written by the developer. Anything the
    app "discovers" in it (for example that caffeine lowers the sleep score)
    was put there on purpose by `quality_from_factors`. It proves the
    pipeline works end to end; it does NOT prove anything about real sleep.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

STAGES = ["wake", "light", "deep", "rem"]

# Typical heart-rate offsets (bpm), HRV multipliers and noise by stage.
_HR_OFFSET = {"wake": 9.0, "light": 2.0, "deep": -5.0, "rem": 3.0}
_HR_NOISE = {"wake": 3.5, "light": 1.8, "deep": 1.0, "rem": 3.0}
_HRV_MULT = {"wake": 0.6, "light": 0.9, "deep": 1.35, "rem": 0.8}
_MOVE_SCALE = {"wake": 30.0, "light": 5.0, "deep": 0.8, "rem": 2.0}
_RESP_OFFSET = {"wake": 1.5, "light": 0.0, "deep": -1.8, "rem": 1.2}
_RESP_NOISE = {"wake": 2.5, "light": 0.8, "deep": 0.5, "rem": 1.5}


@dataclass
class DayFactors:
    """What happened during the day before the night (the 'daily context')."""

    steps: int
    caffeine_cups: float      # caffeinated drinks after 14:00
    alcohol_units: float
    stress: int               # 1 (calm) .. 5 (very stressed)
    late_workout: bool        # hard workout within 3 h of bedtime
    bedtime_shift_min: float  # minutes after 23:00 (negative = earlier)

    def as_context(self) -> dict:
        return {
            "steps": self.steps,
            "caffeine_cups": self.caffeine_cups,
            "alcohol_units": self.alcohol_units,
            "stress": self.stress,
            "late_workout": self.late_workout,
        }


def sample_factors(rng: np.random.Generator) -> DayFactors:
    return DayFactors(
        steps=int(np.clip(rng.normal(8000, 3000), 500, 22000)),
        caffeine_cups=float(rng.choice([0, 0, 1, 1, 2, 3])),
        alcohol_units=float(rng.choice([0, 0, 0, 0, 1, 2, 4])),
        stress=int(np.clip(round(rng.normal(3, 1)), 1, 5)),
        late_workout=bool(rng.random() < 0.2),
        bedtime_shift_min=float(np.clip(rng.normal(0, 50), -90, 150)),
    )


def quality_from_factors(f: DayFactors, rng: np.random.Generator) -> float:
    """Hidden 'sleep quality' q in [0.05, 0.98] built from the day's factors.

    This formula is the planted ground truth behind the demo insights.
    """
    q = (
        0.60
        + 0.02 * (f.steps / 1000 - 8)
        - 0.09 * f.caffeine_cups
        - 0.07 * f.alcohol_units
        - 0.07 * (f.stress - 3)
        - 0.12 * float(f.late_workout)
        - 0.10 * max(0.0, f.bedtime_shift_min - 60) / 60
        + rng.normal(0, 0.05)
    )
    return float(np.clip(q, 0.05, 0.98))


def _hypnogram(rng: np.random.Generator, n: int, q: float) -> np.ndarray:
    """Per-minute stage labels for a night of `n` minutes in bed."""
    stages = np.array(["wake"] * n, dtype=object)

    mean_latency = 50 - 45 * q
    latency = int(np.clip(rng.gamma(3, mean_latency / 3), 2, 90))
    final_wake = int(rng.integers(3, 12))
    pos, end = latency, max(latency + 30, n - final_wake)

    k = 0
    while pos < end:
        cycle_len = int(np.clip(rng.normal(90, 8), 70, 110))
        deep_frac = max(0.0, 0.30 - 0.07 * k) * (0.3 + 1.2 * q)
        rem_frac = min(0.40, 0.12 + 0.07 * k)
        light_total = cycle_len * (1 - deep_frac - rem_frac)
        l1 = round(light_total * 0.4)
        deep = round(cycle_len * deep_frac)
        l2 = round(light_total - l1)
        rem = cycle_len - l1 - deep - l2
        for label, length in (("light", l1), ("deep", deep), ("light", l2), ("rem", rem)):
            stop = min(pos + max(0, length), end)
            stages[pos:stop] = label
            pos = stop
        k += 1

    # Brief awakenings: fewer when quality is high.
    for _ in range(int(rng.poisson(1 + 8 * (1 - q)))):
        start = int(rng.integers(latency, max(latency + 1, end)))
        stages[start : start + int(rng.integers(1, 4 + int(8 * (1 - q))))] = "wake"
    return stages


def _ar1(rng: np.random.Generator, n: int, phi: float = 0.8) -> np.ndarray:
    """Smooth unit-variance noise (each value depends on the previous one)."""
    out = np.zeros(n)
    e = rng.normal(size=n)
    for i in range(1, n):
        out[i] = phi * out[i - 1] + np.sqrt(1 - phi**2) * e[i]
    return out


def generate_night(
    rng: np.random.Generator,
    bedtime: datetime,
    factors: DayFactors,
    time_in_bed_min: int,
    apnea_prone: bool = False,
) -> pd.DataFrame:
    """One night as a 1-minute DataFrame, including the true stage in `stage_true`."""
    n = time_in_bed_min
    q = quality_from_factors(factors, rng)
    stage = _hypnogram(rng, n, q)

    def by_stage(table: dict) -> np.ndarray:
        return np.array([table[s] for s in stage])

    # Heart rate: personal baseline + stage effect + smooth noise + slow overnight fall.
    base_hr = rng.normal(58, 4) + 1.2 * (factors.stress - 3) + 1.5 * factors.alcohol_units
    hr = base_hr + by_stage(_HR_OFFSET) + by_stage(_HR_NOISE) * _ar1(rng, n) - np.linspace(0, 3, n)

    base_hrv = max(15.0, rng.normal(50, 8) * (1 - 0.06 * (factors.stress - 3)) * (1 - 0.04 * factors.alcohol_units))
    hrv = base_hrv * by_stage(_HRV_MULT) * np.exp(rng.normal(0, 0.15, n))

    movement = rng.exponential(by_stage(_MOVE_SCALE))
    changes = np.flatnonzero(stage[1:] != stage[:-1]) + 1  # minutes where the stage changes
    movement[changes] += rng.uniform(15, 40, len(changes))

    resp = 14.5 + by_stage(_RESP_OFFSET) + by_stage(_RESP_NOISE) * _ar1(rng, n)

    spo2 = np.clip(rng.normal(96.5, 0.8), 94, 99) + rng.normal(0, 0.4, n)
    n_events = int(rng.poisson((12 if apnea_prone else 1) + 0.7 * factors.alcohol_units))
    asleep_idx = np.flatnonzero(stage != "wake")
    if len(asleep_idx) > 10:
        for _ in range(n_events):
            at = int(rng.choice(asleep_idx[:-3]))
            depth = rng.uniform(3, 8)
            length = int(rng.integers(1, 4))
            dip = depth * np.array([0.5, 1.0, 0.6][:length])  # shape of the drop, 1-3 minutes
            spo2[at : at + len(dip)] -= dip
            movement[min(n - 1, at + len(dip))] += rng.uniform(10, 25)

    times = pd.date_range(bedtime, periods=n, freq="1min")
    return pd.DataFrame(
        {
            "timestamp": times,
            "heart_rate": np.clip(hr, 35, 130).round(1),
            "hrv_rmssd": np.clip(hrv, 5, 200).round(1),
            "spo2": np.clip(spo2, 80, 100).round(1),
            "movement": np.clip(movement, 0, 100).round(1),
            "resp_rate": np.clip(resp, 6, 30).round(1),
            "stage_true": stage,
        }
    )


def generate_nights(n_nights: int, seed: int, last_night: date) -> list[dict]:
    """Create `n_nights` consecutive nights ending with the night of `last_night`.

    Returns dicts with: night_date (date), factors (DayFactors), data (DataFrame
    with `stage_true`).
    """
    rng = np.random.default_rng(seed)
    apnea_prone = bool(rng.random() < 0.25)  # same 'person' for the whole series
    nights = []
    for i in range(n_nights):
        night_date = last_night - timedelta(days=n_nights - 1 - i)
        factors = sample_factors(rng)
        # Whole minutes only, so timestamps look like real exports (no fractions of a second).
        bedtime = datetime.combine(night_date, datetime.min.time()) + timedelta(hours=23, minutes=round(factors.bedtime_shift_min))
        wake = datetime.combine(night_date + timedelta(days=1), datetime.min.time()) + timedelta(hours=7, minutes=round(float(rng.normal(0, 25))))
        minutes = int(np.clip((wake - bedtime).total_seconds() / 60, 300, 600))
        nights.append(
            {
                "night_date": night_date,
                "factors": factors,
                "data": generate_night(rng, bedtime, factors, minutes, apnea_prone),
            }
        )
    return nights
