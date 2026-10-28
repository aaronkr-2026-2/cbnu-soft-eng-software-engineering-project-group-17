"""Personal insights: correlations between daily factors and sleep, plus recommendations.

Everything here is explainable on purpose: each recommendation carries the
numbers ("evidence") that triggered it. The advice is general sleep-hygiene
guidance, not medical advice.
"""
from datetime import datetime

import numpy as np
import pandas as pd
from scipy.stats import pearsonr

# --- thresholds (kept together so they are easy to find and discuss) ----------
MIN_NIGHTS_FOR_CORRELATION = 7
MIN_NIGHTS_FOR_PERSONAL_RULE = 14
PERSONAL_R_THRESHOLD = 0.4       # |r| at or above this counts as a 'notable' relationship
PERSONAL_P_THRESHOLD = 0.05
WINDOW = 7                       # recent nights used by the rules
SHORT_SLEEP_MIN = 6.5 * 60
IRREGULAR_BEDTIME_STD_H = 1.0
LOW_DEEP_PCT = 10.0
LONG_LATENCY_MIN = 30.0
LOW_EFFICIENCY = 0.85
ODI_ATTENTION_NIGHTS = 2         # nights with an elevated desaturation index in the window

FACTOR_LABELS = {
    "steps": "Steps during the day",
    "caffeine_cups": "Caffeinated drinks after 14:00",
    "alcohol_units": "Alcohol (units)",
    "stress": "Stress level (1-5)",
    "late_workout": "Hard workout within 3 h of bedtime",
    "bedtime_hour": "Bedtime (hour of day)",
}

DISCLAIMER = (
    "General wellness information, not medical advice. A correlation shows that two things "
    "moved together in your data; it does not prove that one caused the other."
)


def bedtime_hour(start_iso: str) -> float:
    """Bedtime as hours after noon-of-the-evening, e.g. 23:30 -> 23.5, 00:30 -> 24.5."""
    t = datetime.fromisoformat(start_iso)
    hour = t.hour + t.minute / 60
    return hour + 24 if hour < 12 else hour


def build_table(nights: list[dict], context: dict[str, dict]) -> pd.DataFrame:
    """One row per night: summary metrics + bedtime + that day's context (if any)."""
    rows = []
    for night in nights:
        s = night["summary"]
        row = {
            "night_date": night["night_date"],
            "score": s["score"],
            "tst": s["total_sleep_min"],
            "deep_pct": s["deep_pct"],
            "latency": s["sleep_latency_min"],
            "efficiency": s["efficiency"],
            "odi": s.get("odi"),
            "bedtime_hour": bedtime_hour(night["start"]),
        }
        ctx = context.get(night["night_date"], {})
        for key in ("steps", "caffeine_cups", "alcohol_units", "stress", "late_workout"):
            value = ctx.get(key)
            row[key] = float(value) if value is not None else np.nan
        rows.append(row)
    if not rows:
        return pd.DataFrame()  # no nights yet: callers check `.empty`
    return pd.DataFrame(rows).sort_values("night_date").reset_index(drop=True)


def correlations(table: pd.DataFrame) -> list[dict]:
    """Pearson correlation of each factor with the sleep score (needs enough nights)."""
    results = []
    for factor, label in FACTOR_LABELS.items():
        if factor not in table:
            continue
        pair = table[["score", factor]].dropna()
        if len(pair) < MIN_NIGHTS_FOR_CORRELATION or pair[factor].nunique() < 2 or pair["score"].nunique() < 2:
            continue
        r, p = pearsonr(pair[factor], pair["score"])
        strength = "strong" if abs(r) >= 0.5 else "moderate" if abs(r) >= 0.3 else "weak"
        results.append(
            {
                "factor": factor,
                "label": label,
                "r": round(float(r), 2),
                "p": round(float(p), 3),
                "n": int(len(pair)),
                "strength": strength,
                "direction": "higher score" if r > 0 else "lower score",
                "notable": bool(abs(r) >= PERSONAL_R_THRESHOLD and p < PERSONAL_P_THRESHOLD and len(pair) >= MIN_NIGHTS_FOR_PERSONAL_RULE),
            }
        )
    return sorted(results, key=lambda c: -abs(c["r"]))


def _rec(rec_id: str, level: str, title: str, text: str, evidence: str) -> dict:
    return {"id": rec_id, "level": level, "title": title, "text": text, "evidence": evidence}


def recommendations(table: pd.DataFrame, corr: list[dict]) -> list[dict]:
    """Rule-based advice from the most recent nights."""
    if table.empty:
        return []
    recent = table.tail(WINDOW)
    n = len(recent)
    out: list[dict] = []

    avg_tst = recent["tst"].mean()
    if avg_tst < SHORT_SLEEP_MIN:
        out.append(_rec(
            "short-sleep", "advice", "Aim for more sleep",
            "Your recent sleep is short. Try moving bedtime 15-30 minutes earlier for a week and keep the wake time fixed.",
            f"Average sleep over the last {n} nights: {avg_tst / 60:.1f} h (guideline for adults: 7-9 h).",
        ))

    bed_std = recent["bedtime_hour"].std(ddof=0) if n >= 3 else 0.0
    if bed_std > IRREGULAR_BEDTIME_STD_H:
        out.append(_rec(
            "irregular-bedtime", "advice", "Keep a steadier schedule",
            "Your bedtime varies a lot from night to night. A regular schedule helps the body clock; try to stay within about 30 minutes.",
            f"Bedtime variation (std. deviation) over the last {n} nights: {bed_std * 60:.0f} min.",
        ))

    if recent["deep_pct"].mean() < LOW_DEEP_PCT:
        out.append(_rec(
            "low-deep", "advice", "Support deep sleep",
            "Deep sleep has been low. Keeping the bedroom cool (often suggested: about 16-19 °C), finishing exercise earlier in the evening "
            "and limiting alcohol can help.",
            f"Average deep sleep over the last {n} nights: {recent['deep_pct'].mean():.1f}% of sleep time.",
        ))

    if recent["latency"].mean() > LONG_LATENCY_MIN:
        out.append(_rec(
            "long-latency", "advice", "Wind down before bed",
            "It takes you a while to fall asleep. Try a 30-60 minute wind-down without screens, dim lights, and avoid caffeine for at least 6 hours before bed.",
            f"Average time to fall asleep over the last {n} nights: {recent['latency'].mean():.0f} min.",
        ))

    if recent["efficiency"].mean() < LOW_EFFICIENCY:
        out.append(_rec(
            "low-efficiency", "advice", "Spend less time awake in bed",
            "You spend a lot of time in bed awake. Go to bed when sleepy and get up if you cannot sleep for a long time.",
            f"Average sleep efficiency over the last {n} nights: {recent['efficiency'].mean() * 100:.0f}%.",
        ))

    odi_nights = int((recent["odi"].fillna(0) >= 5.0).sum())
    if odi_nights >= ODI_ATTENTION_NIGHTS:
        out.append(_rec(
            "oxygen-dips", "attention", "Repeated blood-oxygen dips",
            "Your oxygen level dipped repeatedly on several nights. Wearable SpO2 is not a diagnostic tool, but if this continues "
            "(especially with loud snoring or daytime sleepiness) consider discussing it with a doctor.",
            f"{odi_nights} of the last {n} nights had 5 or more desaturation events per hour.",
        ))

    for c in corr:
        if c["notable"]:
            out.append(_rec(
                f"personal-{c['factor']}", "insight", f"Pattern in your data: {c['label']}",
                f"On days with higher '{c['label']}', your sleep score tends to be {c['direction'].split()[0]}. "
                "This is a pattern in your own records, not proof of cause.",
                f"Correlation r = {c['r']:+.2f}, p = {c['p']:.3f}, over {c['n']} nights.",
            ))

    if not out:
        out.append(_rec("on-track", "info", "Nothing stands out", "No rule was triggered by your recent nights. Keep your routine.", f"Checked the last {n} nights."))
    return out


def build_insights(nights: list[dict], context: dict[str, dict]) -> dict:
    table = build_table(nights, context)
    corr = correlations(table)
    return {
        "nights_analyzed": int(len(table)),
        "correlations": corr,
        "recommendations": recommendations(table, corr),
        "disclaimer": DISCLAIMER,
    }
