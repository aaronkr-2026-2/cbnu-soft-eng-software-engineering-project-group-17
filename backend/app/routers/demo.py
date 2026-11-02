"""Endpoints that create or remove synthetic demo data."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends

from .. import repository
from ..db import get_db
from ..models import DemoRequest
from ..services.pipeline import build_night_document
from ..services.synthetic import generate_nights

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/seed")
def seed_demo(body: DemoRequest | None = None, db=Depends(get_db)):
    """Generate synthetic nights (and their daily context) ending last night."""
    body = body or DemoRequest()
    last_night = date.today() - timedelta(days=1)
    created = []
    for night in generate_nights(body.nights, body.seed, last_night):
        document = build_night_document(night["data"], source="synthetic")
        saved = repository.save_night(db, document)
        repository.upsert_context(db, saved["night_date"], night["factors"].as_context(), source="synthetic")
        created.append(saved["night_date"])
    return {"nights_created": len(created), "first": created[0], "last": created[-1], "synthetic": True}


@router.delete("")
def clear_demo(db=Depends(get_db)):
    """Remove only synthetic data; imported nights and your own context stay."""
    return repository.delete_synthetic(db)
