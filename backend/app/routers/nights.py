"""Endpoints for sleep records: import, list, read, delete, smart alarm."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from .. import config, repository
from ..db import get_db
from ..models import AlarmRequest
from ..services.alarm import simulate_alarm
from ..services.parser import ParseError, parse_csv
from ..services.pipeline import build_night_document

router = APIRouter(prefix="/api/nights", tags=["nights"])


def _require_night(db, night_id: str) -> dict:
    night = repository.get_night(db, night_id)
    if night is None:
        raise HTTPException(status_code=404, detail="Night not found.")
    return night


@router.post("/import")
def import_night(file: UploadFile, db=Depends(get_db)):
    """Upload one CSV file (one night). Same night date = the old record is replaced."""
    content = file.file.read(config.MAX_UPLOAD_BYTES + 1)
    if len(content) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File is larger than {config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
    try:
        df, warnings = parse_csv(content)
    except ParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    night = build_night_document(df, source="import")
    replaced = repository.get_night_by_date(db, night["night_date"]) is not None
    saved = repository.save_night(db, night)
    return {
        "id": saved["id"],
        "night_date": saved["night_date"],
        "stage_method": saved["stage_method"],
        "replaced_existing": replaced,
        "warnings": warnings,
        "summary": saved["summary"],
    }


@router.get("")
def list_nights(limit: int = 90, db=Depends(get_db)):
    """Summaries of the newest nights, oldest first (no per-minute data)."""
    return repository.list_nights(db, limit=max(1, min(limit, 365)))


@router.get("/{night_id}")
def get_night(night_id: str, db=Depends(get_db)):
    """One full night including per-minute epochs."""
    return _require_night(db, night_id)


@router.delete("/{night_id}", status_code=204)
def delete_night(night_id: str, db=Depends(get_db)):
    if not repository.delete_night(db, night_id):
        raise HTTPException(status_code=404, detail="Night not found.")


@router.post("/{night_id}/smart-alarm")
def smart_alarm(night_id: str, body: AlarmRequest | None = None, db=Depends(get_db)):
    """Replay the smart alarm on a recorded night."""
    night = _require_night(db, night_id)
    body = body or AlarmRequest()
    end = body.window_end
    start = body.window_start
    if end is None:
        end = datetime.fromisoformat(night["summary"]["final_wake_time"]) if night["summary"].get("final_wake_time") else datetime.fromisoformat(night["end"])
    if start is None:
        start = end - timedelta(minutes=30)
    try:
        return simulate_alarm(night["epochs"], start, end)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
