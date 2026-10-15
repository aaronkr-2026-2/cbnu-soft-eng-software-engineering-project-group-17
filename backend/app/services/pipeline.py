"""Turn a clean DataFrame of one night into the document stored in MongoDB.

This is the single place where the steps are chained:
    signals -> stage labels (AI engine) -> summary metrics -> database document
Both CSV import and demo seeding use it, so they behave identically.
"""
from datetime import datetime, timedelta, timezone

import pandas as pd

from .metrics import summarize_night
from .staging import stage_night

_EPOCH_FIELDS = {  # DataFrame column -> short key in the stored epoch
    "heart_rate": "hr",
    "hrv_rmssd": "hrv",
    "spo2": "spo2",
    "movement": "mov",
    "resp_rate": "rr",
}


def night_date_for(start: datetime):
    """Date the night 'belongs to': the evening it started.

    Shifting by 12 hours puts a 00:30 bedtime on the previous calendar day,
    so a night that crosses midnight has one clear date.
    """
    return (start - timedelta(hours=12)).date()


def _to_epochs(df: pd.DataFrame, stages: list[str]) -> list[dict]:
    columns = [c for c in _EPOCH_FIELDS if c in df.columns]
    epochs = []
    for i, row in enumerate(df.itertuples(index=False)):
        epoch = {"t": row.timestamp.isoformat(timespec="minutes"), "stage": stages[i]}
        for col in columns:
            value = getattr(row, col)
            epoch[_EPOCH_FIELDS[col]] = None if pd.isna(value) else round(float(value), 1)
        epochs.append(epoch)
    return epochs


def build_night_document(df: pd.DataFrame, source: str) -> dict:
    """`source` is 'import' (user file) or 'synthetic' (generated demo data)."""
    signals = df.drop(columns=["stage_true"], errors="ignore")  # never let truth labels leak in
    stages, method = stage_night(signals)
    start = pd.Timestamp(signals["timestamp"].iloc[0]).to_pydatetime()
    end = pd.Timestamp(signals["timestamp"].iloc[-1]).to_pydatetime()
    return {
        "night_date": night_date_for(start).isoformat(),
        "source": source,
        "start": start.isoformat(timespec="minutes"),
        "end": end.isoformat(timespec="minutes"),
        "stage_method": method,
        "summary": summarize_night(signals, stages),
        "epochs": _to_epochs(signals, stages),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
