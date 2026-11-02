"""Endpoints for the daily context (steps, caffeine, ...)."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from .. import repository
from ..db import get_db
from ..models import DailyContext

router = APIRouter(prefix="/api/context", tags=["context"])


@router.get("")
def list_context(db=Depends(get_db)):
    return list(repository.context_by_date(db).values())


@router.put("/{day}")
def save_context(day: str, body: DailyContext, db=Depends(get_db)):
    """Create or replace the context for `day` (YYYY-MM-DD) - the day BEFORE the night."""
    try:
        date.fromisoformat(day)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Date must look like 2026-10-14.") from exc
    return repository.upsert_context(db, day, body.model_dump(exclude_none=True))
