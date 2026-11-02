"""Turn raw 1-minute signals into features for sleep-stage classification.

Each feature describes one minute *in the context of its neighbours and of
the person's own night*, because absolute heart rate differs between people
but the pattern within a night is what separates the stages.
"""
import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "hr_rel",      # heart rate minus the night's median (bpm)
    "hr_std_5",    # heart-rate variability over a 5-minute window (REM and wake are 'noisy')
    "hr_std_15",   # same over 15 minutes (slower, steadier in deep sleep)
    "hrv_rel",     # HRV (RMSSD) relative to the night's median (high in deep sleep)
    "mov_5",       # mean movement over 5 minutes
    "mov_15",      # mean movement over 15 minutes
    "night_frac",  # position in the night, 0..1 (deep sleep early, REM late)
]

# The ML model needs all three signals; otherwise the app falls back to rules.
ML_REQUIRED_COLUMNS = ["heart_rate", "hrv_rmssd", "movement"]


def _rolling(series: pd.Series, window: int, how: str) -> pd.Series:
    roll = series.rolling(window, center=True, min_periods=1)
    return roll.std().fillna(0.0) if how == "std" else roll.mean()


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame with the columns in FEATURE_COLUMNS (same index as `df`)."""
    n = len(df)
    hr = df["heart_rate"].astype(float)

    if "hrv_rmssd" in df:
        hrv = df["hrv_rmssd"].astype(float)
        hrv_rel = hrv / (hrv.median() or 1.0)
    else:
        hrv_rel = pd.Series(1.0, index=df.index)  # neutral value when the sensor is missing

    if "movement" in df:
        mov = df["movement"].astype(float).fillna(0.0)
    else:
        mov = pd.Series(0.0, index=df.index)

    return pd.DataFrame(
        {
            "hr_rel": hr - hr.median(),
            "hr_std_5": _rolling(hr, 5, "std"),
            "hr_std_15": _rolling(hr, 15, "std"),
            "hrv_rel": hrv_rel.fillna(1.0),
            "mov_5": _rolling(mov, 5, "mean"),
            "mov_15": _rolling(mov, 15, "mean"),
            "night_frac": np.linspace(0.0, 1.0, n) if n > 1 else np.zeros(n),
        },
        index=df.index,
    )[FEATURE_COLUMNS]
