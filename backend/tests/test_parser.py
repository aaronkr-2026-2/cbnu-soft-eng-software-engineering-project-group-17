import pandas as pd
import pytest

from app import config
from app.services.parser import ParseError, parse_csv

from .conftest import csv_bytes


def frame(rows: int = 120, freq: str = "1min", suffix: str = "") -> pd.DataFrame:
    """A valid file as a DataFrame: constant heart rate, one reading per `freq`."""
    ts = pd.date_range("2026-03-01 23:00", periods=rows, freq=freq)
    return pd.DataFrame({"timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S") + suffix, "heart_rate": 60.0, "spo2": 96.0})


def as_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode()


def test_valid_generated_file_round_trips(sample_nights):
    original = sample_nights[0]["data"]
    df, warnings = parse_csv(csv_bytes(original))
    assert len(df) == len(original)
    assert warnings == []
    assert {"timestamp", "heart_rate", "hrv_rmssd", "spo2", "movement", "resp_rate"} <= set(df.columns)


def test_missing_required_column():
    with pytest.raises(ParseError, match="heart_rate"):
        parse_csv(as_bytes(frame().drop(columns="heart_rate")))


def test_unreadable_timestamp_reports_file_line():
    df = frame()
    df.loc[5, "timestamp"] = "not-a-time"  # data row 5 is file line 7 (header + 1-based)
    with pytest.raises(ParseError, match="line 7"):
        parse_csv(as_bytes(df))


def test_not_a_csv():
    with pytest.raises(ParseError):
        parse_csv(b"\xff\xfe\x00 binary junk")


def test_utc_offset_is_dropped_and_wall_clock_time_kept():
    df, _ = parse_csv(as_bytes(frame(suffix="+09:00")))
    assert df["timestamp"].dt.tz is None
    assert df["timestamp"].iloc[0].hour == 23


def test_out_of_range_value_is_flagged_and_interpolated():
    df = frame()
    df.loc[10, "heart_rate"] = 300
    clean, warnings = parse_csv(as_bytes(df))
    assert any("heart_rate" in w for w in warnings)
    assert clean["heart_rate"].iloc[10] == pytest.approx(60)


def test_long_gap_is_rejected():
    df = frame().drop(index=range(20, 30))  # 10 missing minutes
    with pytest.raises(ParseError, match="gap"):
        parse_csv(as_bytes(df))


def test_short_gap_is_filled():
    df = frame().drop(index=[20, 21])  # 2 missing minutes
    clean, _ = parse_csv(as_bytes(df))
    assert len(clean) == 120 and clean["heart_rate"].notna().all()


def test_too_short():
    with pytest.raises(ParseError, match="at least"):
        parse_csv(as_bytes(frame(rows=30)))


def test_too_long(monkeypatch):
    monkeypatch.setattr(config, "MAX_EPOCHS", 100)
    with pytest.raises(ParseError, match="too much"):
        parse_csv(as_bytes(frame(rows=120)))


def test_unknown_columns_are_ignored_with_warning():
    df = frame()
    df["mood"] = "happy"
    clean, warnings = parse_csv(as_bytes(df))
    assert "mood" not in clean.columns
    assert any("mood" in w for w in warnings)


def test_thirty_second_data_is_resampled_to_one_minute():
    clean, _ = parse_csv(as_bytes(frame(rows=240, freq="30s")))
    assert len(clean) == 120


def test_column_names_are_case_insensitive():
    df = frame().rename(columns={"heart_rate": " Heart_Rate "})
    clean, _ = parse_csv(as_bytes(df))
    assert "heart_rate" in clean.columns
