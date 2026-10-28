"""Sleep-stage detection: rule-based heuristic and a scikit-learn model.

Stages: wake, light, deep, rem.

Two methods exist on purpose:
* `heuristic_stages` - transparent rules; works with only heart rate (and
  movement if available). Used when the file lacks HRV or movement.
* `ml_stages` - a RandomForest trained on synthetic nights (see training.py).
  Used when heart rate, HRV and movement are all present.

NEITHER METHOD IS CLINICALLY VALIDATED. Real sleep staging uses EEG
(polysomnography); wearable-based staging from heart rate and movement is an
estimate even in commercial products.
"""
import threading

import numpy as np
import pandas as pd

from .features import FEATURE_COLUMNS, ML_REQUIRED_COLUMNS, build_features

ACTIVE_MOVEMENT = 15.0   # 5-minute mean movement above this = awake (0-100 scale)
ONSET_MINUTES = 10       # this many quiet minutes in a row = fell asleep

_model_lock = threading.Lock()
_model_bundle: dict | None = None


# --- helpers ------------------------------------------------------------------

def smooth(labels: np.ndarray, window: int = 5) -> np.ndarray:
    """Replace each label by the most common label among its neighbours.

    Removes one-minute flickers (e.g. deep-light-deep) that are not physiological.
    """
    n = len(labels)
    half = window // 2
    out = labels.copy()
    for i in range(n):
        chunk = labels[max(0, i - half) : min(n, i + half + 1)]
        values, counts = np.unique(chunk, return_counts=True)
        best = values[counts == counts.max()]
        out[i] = labels[i] if labels[i] in best else best[0]
    return out


def _quiet_run_bounds(active: np.ndarray, length: int) -> tuple[int, int] | None:
    """Index of the first and last minute that belong to a run of `length` quiet minutes."""
    quiet = ~active
    n = len(quiet)
    if n < length:
        return None
    run = np.convolve(quiet.astype(int), np.ones(length, dtype=int), mode="valid") == length
    starts = np.flatnonzero(run)
    if len(starts) == 0:
        return None
    return int(starts[0]), int(starts[-1] + length - 1)


# --- method 1: rules ------------------------------------------------------------

def heuristic_stages(df: pd.DataFrame) -> np.ndarray:
    feats = build_features(df)
    n = len(df)
    mov = feats["mov_5"].to_numpy()
    active = mov > ACTIVE_MOVEMENT if "movement" in df else np.zeros(n, dtype=bool)

    stages = np.array(["wake"] * n, dtype=object)
    bounds = _quiet_run_bounds(active, ONSET_MINUTES)
    if bounds is None:
        return stages  # never fell asleep according to the rules
    onset, offset = bounds

    asleep = np.zeros(n, dtype=bool)
    asleep[onset : offset + 1] = ~active[onset : offset + 1]
    if asleep.sum() < 5:
        return stages

    hr_rel = feats["hr_rel"].to_numpy()
    std5 = feats["hr_std_5"].to_numpy()
    std15 = feats["hr_std_15"].to_numpy()
    frac = feats["night_frac"].to_numpy()

    # Thresholds are percentiles of THIS night, so they adapt to the person.
    hr_low = np.percentile(hr_rel[asleep], 25)
    std15_mid = np.percentile(std15[asleep], 50)
    std5_high = np.percentile(std5[asleep], 65)

    stages[asleep] = "light"
    deep = asleep & (hr_rel <= hr_low) & (std15 <= std15_mid) & (mov < 5)
    rem = asleep & ~deep & (std5 >= std5_high) & (frac >= 0.2) & (mov < 10)
    stages[deep] = "deep"
    stages[rem] = "rem"
    return smooth(stages)


# --- method 2: machine learning ----------------------------------------------------

def get_model_bundle() -> dict | None:
    """Load the trained model, training it first if it does not exist yet."""
    global _model_bundle
    with _model_lock:
        if _model_bundle is None:
            from . import training  # imported here to avoid a circular import

            _model_bundle = training.load_or_train()
        return _model_bundle


def reset_model_cache() -> None:
    """Forget the in-memory model (used by tests)."""
    global _model_bundle
    with _model_lock:
        _model_bundle = None


def ml_stages(df: pd.DataFrame, bundle: dict) -> np.ndarray:
    feats = build_features(df)[FEATURE_COLUMNS]
    predicted = bundle["model"].predict(feats)
    return smooth(np.array(predicted, dtype=object))


def stage_night(df: pd.DataFrame, use_model: bool = True) -> tuple[list[str], str]:
    """Return (list of stage labels, method name: 'ml' or 'heuristic')."""
    has_signals = all(col in df for col in ML_REQUIRED_COLUMNS)
    if use_model and has_signals:
        bundle = get_model_bundle()
        if bundle is not None:
            return list(ml_stages(df, bundle)), "ml"
    return list(heuristic_stages(df)), "heuristic"
