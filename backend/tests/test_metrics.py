import numpy as np
import pandas as pd
import pytest

from app.services.metrics import sleep_score, summarize_night


def night(stages: list[str], spo2: list[float] | None = None) -> tuple[pd.DataFrame, list[str]]:
    n = len(stages)
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-03-01 23:00", periods=n, freq="1min"),
            "heart_rate": 60.0,
            "spo2": spo2 if spo2 is not None else 96.0,
        }
    )
    return df, stages


# 10 min awake, 30 light, 30 deep, 30 rem, 20 awake = 120 minutes in bed
BASIC = ["wake"] * 10 + ["light"] * 30 + ["deep"] * 30 + ["rem"] * 30 + ["wake"] * 20


def test_basic_numbers_match_hand_calculation():
    s = summarize_night(*night(BASIC))
    assert s["time_in_bed_min"] == 120
    assert s["total_sleep_min"] == 90
    assert s["sleep_latency_min"] == 10
    assert s["waso_min"] == 0
    assert s["efficiency"] == pytest.approx(0.75)
    assert s["deep_min"] == 30 and s["deep_pct"] == pytest.approx(33.3)
    assert s["onset_time"] == "2026-03-01T23:10"
    assert s["final_wake_time"] == "2026-03-02T00:40"


def test_wake_inside_the_night_counts_as_waso_and_awakening():
    stages = ["wake"] * 5 + ["light"] * 40 + ["wake"] * 6 + ["deep"] * 40 + ["wake"] * 5
    s = summarize_night(*night(stages))
    assert s["waso_min"] == 6
    assert s["awakenings"] == 1
    assert s["total_sleep_min"] == 80


def test_one_minute_wake_is_not_an_awakening():
    stages = ["wake"] * 5 + ["light"] * 30 + ["wake"] + ["deep"] * 30 + ["wake"] * 5
    assert summarize_night(*night(stages))["awakenings"] == 0


def test_short_sleep_blips_before_real_onset_are_ignored():
    stages = ["wake"] * 5 + ["light"] * 3 + ["wake"] * 20 + ["light"] * 60
    assert summarize_night(*night(stages))["sleep_latency_min"] == 28


def test_all_wake_night_scores_zero_without_crashing():
    s = summarize_night(*night(["wake"] * 90))
    assert s["total_sleep_min"] == 0 and s["score"] == 0 and s["deep_pct"] == 0.0


def test_single_desaturation_event():
    spo2 = [96.0] * 120
    spo2[50:53] = [91.0, 90.0, 92.0]
    s = summarize_night(*night(BASIC, spo2))
    assert s["desat_events"] == 1
    assert s["spo2_min"] == 90.0
    assert s["odi"] == pytest.approx(0.7, abs=0.05)  # 1 event in 1.5 h of sleep


def test_dips_two_minutes_apart_merge_but_five_minutes_apart_do_not():
    close = [96.0] * 120
    close[50], close[53] = 90.0, 90.0  # two normal minutes between
    far = [96.0] * 120
    far[50], far[56] = 90.0, 90.0
    assert summarize_night(*night(BASIC, close))["desat_events"] == 1
    assert summarize_night(*night(BASIC, far))["desat_events"] == 2


def test_frequent_dips_set_the_attention_flag():
    spo2 = [96.0] * 120
    for start in range(15, 100, 10):  # 9 separate events in 1.5 h of sleep
        spo2[start] = 90.0
    s = summarize_night(*night(BASIC, spo2))
    assert s["odi"] >= 5 and s["spo2_attention"] is True


def test_missing_spo2_column_gives_none_values():
    df, stages = night(BASIC)
    s = summarize_night(df.drop(columns="spo2"), stages)
    assert s["spo2_min"] is None and s["odi"] is None and s["spo2_attention"] is False


def test_score_is_between_0_and_100_and_weights_add_up():
    s = summarize_night(*night(BASIC))
    assert 0 <= s["score"] <= 100
    from app.services.metrics import SCORE_WEIGHTS

    assert sum(SCORE_WEIGHTS.values()) == pytest.approx(1.0)


def test_healthy_night_scores_higher_than_poor_night():
    healthy = dict(total_sleep_min=450, efficiency=0.95, deep_pct=18, rem_pct=23, sleep_latency_min=8, waso_min=5)
    poor = dict(total_sleep_min=260, efficiency=0.76, deep_pct=4, rem_pct=9, sleep_latency_min=50, waso_min=70)
    assert sleep_score(healthy)[0] >= 95
    assert sleep_score(poor)[0] <= 15
