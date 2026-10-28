"""Night summary metrics and the 0-100 sleep score.

All numbers are derived from the per-minute stage labels and signals.
The score is a transparent heuristic (weighted bands around commonly cited
healthy ranges), NOT a clinical measure.
"""
import numpy as np
import pandas as pd

MIN_SLEEP_RUN = 5          # a sleep run shorter than this does not count as falling asleep
DESAT_DROP = 3.0           # SpO2 this many points below the night's median = desaturation
ODI_ATTENTION = 5.0        # events per hour above which the app flags the night

# Score components: (weight, trapezoid band). See `_band`.
SCORE_WEIGHTS = {
    "duration": 0.30,
    "efficiency": 0.20,
    "deep": 0.15,
    "rem": 0.15,
    "latency": 0.10,
    "waso": 0.10,
}


def _band(value: float, zero_low: float, full_low: float, full_high: float, zero_high: float) -> float:
    """100 inside [full_low, full_high], falling linearly to 0 at zero_low / zero_high."""
    if value < zero_low or value > zero_high:
        return 0.0
    if value < full_low:
        return 100.0 * (value - zero_low) / (full_low - zero_low)
    if value > full_high:
        return 100.0 * (zero_high - value) / (zero_high - full_high)
    return 100.0


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """(start, end_exclusive) of each run of True values."""
    padded = np.concatenate([[False], mask, [False]]).astype(int)
    edges = np.flatnonzero(np.diff(padded))
    return list(zip(edges[::2], edges[1::2]))


def _mean(values) -> float | None:
    arr = np.asarray(values, dtype=float)
    return None if arr.size == 0 or np.isnan(arr).all() else round(float(np.nanmean(arr)), 1)


def sleep_score(summary: dict) -> tuple[int, dict]:
    """Combine the summary metrics into a 0-100 score and a per-component breakdown."""
    if summary["total_sleep_min"] == 0:
        # No sleep detected: latency and wake-time components must not earn points.
        return 0, {name: 0 for name in SCORE_WEIGHTS}
    parts = {
        "duration": _band(summary["total_sleep_min"], 270, 420, 540, 660),
        "efficiency": _band(summary["efficiency"], 0.75, 0.92, 1.01, 1.02),
        "deep": _band(summary["deep_pct"], 4, 13, 23, 35),
        "rem": _band(summary["rem_pct"], 8, 18, 28, 38),
        "latency": _band(summary["sleep_latency_min"], -1, 0, 10, 40),
        "waso": _band(summary["waso_min"], -1, 0, 10, 50),
    }
    score = sum(SCORE_WEIGHTS[k] * v for k, v in parts.items())
    return int(round(score)), {k: round(v) for k, v in parts.items()}


def summarize_night(df: pd.DataFrame, stages: list[str]) -> dict:
    """Compute the night summary from signals `df` and stage labels `stages`."""
    st = np.asarray(stages, dtype=object)
    n = len(st)
    times = pd.to_datetime(df["timestamp"]).reset_index(drop=True)
    asleep = st != "wake"

    sleep_runs = [r for r in _runs(asleep) if r[1] - r[0] >= MIN_SLEEP_RUN]
    if not sleep_runs:
        onset = final = 0
    else:
        onset, final = sleep_runs[0][0], sleep_runs[-1][1]  # [onset, final) is the sleep period

    period = st[onset:final]
    total_sleep = int((period != "wake").sum())
    waso = int((period == "wake").sum())
    stage_min = {s: int((period == s).sum()) for s in ("light", "deep", "rem")}

    def pct(minutes: int) -> float:
        return round(100.0 * minutes / total_sleep, 1) if total_sleep else 0.0

    summary = {
        "time_in_bed_min": n,
        "total_sleep_min": total_sleep,
        "sleep_latency_min": int(onset),
        "waso_min": waso,
        "efficiency": round(total_sleep / n, 3) if n else 0.0,
        "awakenings": sum(1 for a, b in _runs(period == "wake") if b - a >= 2),
        "light_min": stage_min["light"],
        "deep_min": stage_min["deep"],
        "rem_min": stage_min["rem"],
        "light_pct": pct(stage_min["light"]),
        "deep_pct": pct(stage_min["deep"]),
        "rem_pct": pct(stage_min["rem"]),
        "onset_time": times[onset].isoformat(timespec="minutes") if total_sleep else None,
        "final_wake_time": times[min(final, n - 1)].isoformat(timespec="minutes") if total_sleep else None,
    }

    sleep_df = df.iloc[onset:final][asleep[onset:final]] if total_sleep else df.iloc[0:0]
    hr = sleep_df["heart_rate"].astype(float)
    summary["avg_hr"] = _mean(hr)
    summary["min_hr_5min"] = round(float(hr.rolling(5).mean().min()), 1) if len(hr) >= 5 else None
    summary["avg_hrv"] = _mean(sleep_df["hrv_rmssd"]) if "hrv_rmssd" in sleep_df else None
    summary["avg_resp"] = _mean(sleep_df["resp_rate"]) if "resp_rate" in sleep_df else None

    summary.update({"spo2_mean": None, "spo2_min": None, "desat_events": None, "odi": None, "t90_min": None})
    if "spo2" in sleep_df and sleep_df["spo2"].notna().any():
        spo2 = sleep_df["spo2"].astype(float)
        baseline = float(spo2.median())
        low = (spo2 <= baseline - DESAT_DROP).to_numpy()
        # Merge dips separated by at most 2 minutes into one event.
        merged = pd.Series(low).rolling(3, min_periods=1).max().astype(bool).to_numpy()
        events = len(_runs(merged))
        summary.update(
            {
                "spo2_mean": round(float(spo2.mean()), 1),
                "spo2_min": round(float(spo2.min()), 1),
                "desat_events": events,
                "odi": round(events / (total_sleep / 60), 1) if total_sleep else None,
                "t90_min": int((spo2 < 90).sum()),
            }
        )

    summary["score"], summary["score_breakdown"] = sleep_score(summary)
    summary["spo2_attention"] = bool(summary["odi"] is not None and summary["odi"] >= ODI_ATTENTION)
    return summary
