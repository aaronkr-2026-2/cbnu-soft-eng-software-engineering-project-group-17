"""Parse and validate an uploaded sleep CSV file.

Input format ("SleepInsight CSV", one row per measurement):

    timestamp,heart_rate,hrv_rmssd,spo2,movement,resp_rate
    2026-10-14T23:05:00,62.0,48.1,96.5,3.2,14.8

* `timestamp` and `heart_rate` are required.
* `hrv_rmssd` (ms), `spo2` (%), `movement` (0-100 activity index) and
  `resp_rate` (breaths/min) are optional.
* Timestamps are ISO 8601. If a UTC offset is present it is dropped and the
  wall-clock time is kept (the app works in the user's local time).

The parser is deliberately strict: health data that looks wrong is rejected
with a clear message instead of being silently "fixed".
"""
import io

import pandas as pd

from .. import config

NUMERIC_OPTIONAL = ["hrv_rmssd", "spo2", "movement", "resp_rate"]
VALID_RANGES = {
    "heart_rate": (25, 220),
    "hrv_rmssd": (0, 500),
    "spo2": (50, 100),
    "movement": (0, 100),
    "resp_rate": (2, 60),
}
MAX_GAP_FILL = 3  # fill at most 3 missing minutes in a row by interpolation


class ParseError(ValueError):
    """The uploaded file cannot be used; the message explains why."""


def parse_csv(content: bytes) -> tuple[pd.DataFrame, list[str]]:
    """Return (clean 1-minute DataFrame, list of warnings)."""
    warnings: list[str] = []

    try:
        text = content.decode("utf-8-sig")
        raw = pd.read_csv(io.StringIO(text))
    except Exception as exc:  # noqa: BLE001 - any read failure means "not a usable CSV"
        raise ParseError("The file could not be read as a UTF-8 CSV.") from exc

    raw.columns = [str(c).strip().lower() for c in raw.columns]
    for required in ("timestamp", "heart_rate"):
        if required not in raw.columns:
            raise ParseError(f"Missing required column: '{required}'.")

    known = {"timestamp", "heart_rate", *NUMERIC_OPTIONAL}
    ignored = [c for c in raw.columns if c not in known]
    if ignored:
        warnings.append(f"Ignored unknown columns: {', '.join(ignored)}.")

    # --- timestamps ---------------------------------------------------------
    try:
        ts = pd.to_datetime(raw["timestamp"], errors="coerce", format="ISO8601")
    except (ValueError, TypeError) as exc:
        raise ParseError("Timestamps must be ISO 8601 with a consistent UTC offset.") from exc
    if getattr(ts.dt, "tz", None) is not None:
        ts = ts.dt.tz_localize(None)  # keep wall-clock time, drop the offset
    bad = ts.isna()
    if bad.any():
        first = int(bad.idxmax()) + 2  # +2: header row and 1-based numbering
        raise ParseError(f"{int(bad.sum())} timestamps are unreadable (first problem on file line {first}).")

    df = raw[["timestamp", "heart_rate", *[c for c in NUMERIC_OPTIONAL if c in raw.columns]]].copy()
    df["timestamp"] = ts

    # --- numbers and plausible ranges ----------------------------------------
    for col in df.columns.drop("timestamp"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
        low, high = VALID_RANGES[col]
        out_of_range = ((df[col] < low) | (df[col] > high)) & df[col].notna()
        if out_of_range.any():
            warnings.append(f"{int(out_of_range.sum())} '{col}' values outside {low}-{high} were treated as missing.")
            df.loc[out_of_range, col] = float("nan")

    df = df.sort_values("timestamp")
    duplicates = df["timestamp"].duplicated()
    if duplicates.any():
        warnings.append(f"Dropped {int(duplicates.sum())} rows with duplicate timestamps.")
        df = df[~duplicates]

    # --- regular 1-minute grid ------------------------------------------------
    df = df.set_index("timestamp").resample("1min").mean()
    df = df.interpolate(limit=MAX_GAP_FILL, limit_area="inside")
    if df["heart_rate"].isna().any():
        first_gap = df.index[df["heart_rate"].isna()][0]
        raise ParseError(
            f"Heart rate has a gap longer than {MAX_GAP_FILL} minutes (first at {first_gap:%Y-%m-%d %H:%M}). "
            "Please split the file into separate sleep sessions or fix the gap."
        )

    for col in NUMERIC_OPTIONAL:
        if col in df.columns and df[col].isna().all():
            warnings.append(f"Column '{col}' has no valid values and was ignored.")
            df = df.drop(columns=col)

    if len(df) < config.MIN_EPOCHS:
        raise ParseError(f"Only {len(df)} minutes of data; at least {config.MIN_EPOCHS} are needed.")
    if len(df) > config.MAX_EPOCHS:
        raise ParseError(f"{len(df)} minutes of data is too much (limit {config.MAX_EPOCHS}). One file = one night.")

    return df.reset_index(), warnings
