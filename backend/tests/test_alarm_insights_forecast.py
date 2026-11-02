from datetime import datetime, timedelta

import numpy as np
import pytest

from app.services.alarm import simulate_alarm
from app.services.forecast import energy_forecast
from app.services.insights import bedtime_hour, build_insights, build_table, correlations


# ----- smart alarm ----------------------------------------------------------------

def epochs(stages: list[str], start="2026-03-02T06:00") -> list[dict]:
    """One stored epoch per minute, like the night documents in the database."""
    base = datetime.fromisoformat(start)
    return [{"t": (base + timedelta(minutes=i)).isoformat(timespec="minutes"), "stage": s} for i, s in enumerate(stages)]


def window(a: str, b: str):
    return datetime.fromisoformat(f"2026-03-02T{a}"), datetime.fromisoformat(f"2026-03-02T{b}")


def test_alarm_picks_first_light_sleep_minute():
    eps = epochs(["deep", "deep", "light", "light", "deep"])
    result = simulate_alarm(eps, *window("06:00", "06:04"))
    assert result["smart_alarm"] == {"time": "2026-03-02T06:02", "stage": "light"}
    assert result["fixed_alarm"]["stage"] == "deep"
    assert result["minutes_earlier"] == 2
    assert result["better_than_fixed"] is True


def test_alarm_prefers_being_awake_counts_as_ready():
    result = simulate_alarm(epochs(["rem", "wake", "deep"]), *window("06:00", "06:02"))
    assert result["smart_alarm"]["stage"] == "wake"


def test_alarm_without_light_sleep_chooses_rem_over_deep_as_late_as_possible():
    result = simulate_alarm(epochs(["deep", "rem", "deep", "rem", "deep"]), *window("06:00", "06:04"))
    assert result["smart_alarm"] == {"time": "2026-03-02T06:03", "stage": "rem"}
    assert "No light sleep" in result["reason"]


def test_alarm_all_deep_falls_back_to_end_of_window():
    result = simulate_alarm(epochs(["deep"] * 5), *window("06:00", "06:04"))
    assert result["smart_alarm"]["time"] == "2026-03-02T06:04"
    assert result["better_than_fixed"] is False


def test_alarm_window_outside_recording_is_rejected():
    with pytest.raises(ValueError, match="outside"):
        simulate_alarm(epochs(["deep"] * 5), *window("09:00", "09:30"))


def test_alarm_window_must_end_after_start():
    with pytest.raises(ValueError, match="after"):
        simulate_alarm(epochs(["deep"] * 5), *window("06:04", "06:00"))


def test_alarm_ignores_timezone_info():
    a = datetime.fromisoformat("2026-03-02T06:00:00+09:00")
    b = datetime.fromisoformat("2026-03-02T06:04:00+09:00")
    assert simulate_alarm(epochs(["light"] * 5), a, b)["smart_alarm"]["time"] == "2026-03-02T06:00"


# ----- insights ---------------------------------------------------------------------

def fake_night(day: int, score=80, tst=450, start=None, odi=0.0, deep=15.0, latency=10, eff=0.92) -> dict:
    return {
        "night_date": f"2026-03-{day:02d}",
        "start": start or f"2026-03-{day:02d}T23:00",
        "summary": {"score": score, "total_sleep_min": tst, "deep_pct": deep, "sleep_latency_min": latency, "efficiency": eff, "odi": odi},
    }


def test_bedtime_hour_handles_midnight():
    assert bedtime_hour("2026-03-01T23:30") == 23.5
    assert bedtime_hour("2026-03-02T00:30") == 24.5


def test_correlations_need_at_least_seven_nights():
    nights = [fake_night(d) for d in range(1, 6)]
    ctx = {n["night_date"]: {"caffeine_cups": d} for d, n in enumerate(nights)}
    assert correlations(build_table(nights, ctx)) == []


def test_planted_relationship_is_found_and_marked_notable():
    rng = np.random.default_rng(0)
    nights, ctx = [], {}
    for day in range(1, 21):
        caffeine = day % 4
        nights.append(fake_night(day, score=int(90 - 12 * caffeine + rng.normal(0, 3))))
        ctx[f"2026-03-{day:02d}"] = {"caffeine_cups": caffeine}
    found = {c["factor"]: c for c in correlations(build_table(nights, ctx))}
    assert found["caffeine_cups"]["r"] < -0.8
    assert found["caffeine_cups"]["notable"] is True
    assert found["caffeine_cups"]["direction"] == "lower score"


def test_constant_factor_is_skipped_instead_of_crashing():
    nights = [fake_night(d, score=70 + d) for d in range(1, 11)]
    ctx = {n["night_date"]: {"steps": 5000} for n in nights}
    assert all(c["factor"] != "steps" for c in correlations(build_table(nights, ctx)))


def ids(recs):
    return {r["id"] for r in recs}


def test_no_nights_gives_no_recommendations():
    assert build_insights([], {})["recommendations"] == []


def test_healthy_nights_trigger_nothing_special():
    nights = [fake_night(d) for d in range(1, 8)]
    assert ids(build_insights(nights, {})["recommendations"]) == {"on-track"}


def test_short_sleep_rule():
    nights = [fake_night(d, tst=330) for d in range(1, 8)]
    assert "short-sleep" in ids(build_insights(nights, {})["recommendations"])


def test_irregular_bedtime_rule():
    starts = ["22:00", "01:30", "23:00", "02:00", "21:30", "00:30", "03:00"]
    nights = [fake_night(d, start=f"2026-03-{d:02d}T{t}") for d, t in zip(range(1, 8), starts)]
    assert "irregular-bedtime" in ids(build_insights(nights, {})["recommendations"])


def test_oxygen_rule_needs_repeated_nights():
    one = [fake_night(d, odi=8.0 if d == 7 else 0.0) for d in range(1, 8)]
    two = [fake_night(d, odi=8.0 if d >= 6 else 0.0) for d in range(1, 8)]
    assert "oxygen-dips" not in ids(build_insights(one, {})["recommendations"])
    rec = next(r for r in build_insights(two, {})["recommendations"] if r["id"] == "oxygen-dips")
    assert rec["level"] == "attention" and "doctor" in rec["text"] and "2 of the last 7" in rec["evidence"]


def test_every_recommendation_explains_itself():
    nights = [fake_night(d, tst=330, deep=5.0, latency=45, eff=0.8) for d in range(1, 8)]
    for rec in build_insights(nights, {})["recommendations"]:
        assert rec["evidence"] and rec["text"] and rec["title"]


# ----- forecast ------------------------------------------------------------------------

def test_forecast_without_data_is_none():
    assert energy_forecast([]) is None


def test_forecast_is_higher_after_good_sleep_than_after_bad_sleep():
    good = [fake_night(d, score=92, tst=470) for d in range(1, 8)]
    bad = [fake_night(d, score=35, tst=300) for d in range(1, 8)]
    assert energy_forecast(good)["energy_score"] > energy_forecast(bad)["energy_score"] + 30
    assert energy_forecast(bad)["label"] == "low"


def test_forecast_with_one_night_has_low_confidence_and_no_regularity_component():
    result = energy_forecast([fake_night(1, score=80, tst=450)])
    assert result["confidence"] == "low"
    assert [c["name"] for c in result["components"]] == ["Last night's sleep score", "Sleep debt (7 nights)"]
    assert 0 <= result["energy_score"] <= 100


def test_forecast_date_is_the_day_after_the_night():
    assert energy_forecast([fake_night(14)])["for_date"] == "2026-03-15"
