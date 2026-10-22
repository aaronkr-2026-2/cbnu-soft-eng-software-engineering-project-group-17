from datetime import date, datetime

import numpy as np
import pytest
from sklearn.metrics import accuracy_score

from app.services import staging, training
from app.services.synthetic import DayFactors, generate_nights, quality_from_factors
from app.services.staging import heuristic_stages, smooth, stage_night

VALID = {"wake", "light", "deep", "rem"}


# ----- generator --------------------------------------------------------------

def test_generator_is_deterministic_for_a_seed():
    a = generate_nights(2, seed=5, last_night=date(2026, 3, 1))
    b = generate_nights(2, seed=5, last_night=date(2026, 3, 1))
    assert a[0]["data"].equals(b[0]["data"])


def test_generator_stage_shares_are_plausible(sample_nights):
    shares = {s: 0.0 for s in VALID}
    total = 0
    for night in sample_nights:
        counts = night["data"]["stage_true"].value_counts()
        for stage, count in counts.items():
            shares[stage] += count
        total += len(night["data"])
    shares = {s: v / total for s, v in shares.items()}
    assert 0.35 < shares["light"] < 0.70
    assert 0.08 < shares["deep"] < 0.30
    assert 0.10 < shares["rem"] < 0.30
    assert shares["wake"] < 0.20


def test_deep_sleep_has_lower_heart_rate_than_wake(sample_nights):
    data = sample_nights[0]["data"]
    assert data.loc[data.stage_true == "deep", "heart_rate"].mean() < data.loc[data.stage_true == "wake", "heart_rate"].mean()


def test_good_day_gives_higher_quality_than_bad_day():
    good = DayFactors(steps=11000, caffeine_cups=0, alcohol_units=0, stress=1, late_workout=False, bedtime_shift_min=0)
    bad = DayFactors(steps=2000, caffeine_cups=3, alcohol_units=4, stress=5, late_workout=True, bedtime_shift_min=120)
    rng = np.random.default_rng(0)
    assert np.mean([quality_from_factors(good, rng) for _ in range(30)]) > np.mean([quality_from_factors(bad, rng) for _ in range(30)]) + 0.3


def test_timestamps_are_whole_minutes(sample_nights):
    ts = sample_nights[0]["data"]["timestamp"]
    assert (ts.dt.second == 0).all() and (ts.dt.microsecond == 0).all()


# ----- staging --------------------------------------------------------------------

def test_smooth_removes_one_minute_flicker():
    labels = np.array(["light"] * 5 + ["deep"] + ["light"] * 5, dtype=object)
    assert list(smooth(labels)) == ["light"] * 11


def test_smooth_keeps_real_changes():
    labels = np.array(["light"] * 6 + ["deep"] * 6, dtype=object)
    assert list(smooth(labels)) == list(labels)


def test_heuristic_returns_valid_labels_and_beats_chance(sample_nights):
    accuracies = []
    for night in sample_nights[:5]:
        data = night["data"].drop(columns="stage_true")
        labels = heuristic_stages(data)
        assert len(labels) == len(data) and set(labels) <= VALID
        accuracies.append(accuracy_score(night["data"]["stage_true"], labels))
    assert np.mean(accuracies) > 0.55  # always predicting 'light' scores about 0.55


def test_heuristic_works_with_heart_rate_only(sample_nights):
    data = sample_nights[0]["data"][["timestamp", "heart_rate"]]
    labels = heuristic_stages(data)
    assert len(labels) == len(data)


def test_never_asleep_night_is_all_wake():
    import pandas as pd

    n = 90
    data = pd.DataFrame({"timestamp": pd.date_range("2026-03-01 23:00", periods=n, freq="1min"), "heart_rate": 75.0, "movement": 50.0})
    assert set(heuristic_stages(data)) == {"wake"}


def test_trained_model_is_accurate_on_held_out_synthetic_nights(tmp_path):
    bundle = training.train_and_save(n_nights=25, seed=3, model_dir=tmp_path)
    assert bundle["metrics"]["accuracy"] > 0.80
    assert bundle["metrics"]["trained_on"] == "synthetic"
    assert (tmp_path / training.MODEL_FILE).exists()


def test_stage_night_uses_model_when_all_signals_present(sample_nights):
    data = sample_nights[0]["data"].drop(columns="stage_true")
    labels, method = stage_night(data)
    assert method == "ml" and len(labels) == len(data) and set(labels) <= VALID


def test_stage_night_falls_back_to_rules_without_hrv(sample_nights):
    data = sample_nights[0]["data"].drop(columns=["stage_true", "hrv_rmssd"])
    _, method = stage_night(data)
    assert method == "heuristic"


def test_model_cache_can_be_reset():
    staging.reset_model_cache()
    assert staging.get_model_bundle() is not None
