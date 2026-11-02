"""Endpoints for the AI engine's outputs: insights, forecast, model information."""
from fastapi import APIRouter, Depends

from .. import repository
from ..db import get_db
from ..services import staging
from ..services.forecast import energy_forecast
from ..services.insights import build_insights

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/insights")
def insights(db=Depends(get_db)):
    nights = repository.list_nights(db)
    return build_insights(nights, repository.context_by_date(db))


@router.get("/forecast")
def forecast(db=Depends(get_db)):
    result = energy_forecast(repository.list_nights(db))
    return result or {"energy_score": None, "note": "No nights recorded yet."}


@router.get("/model-info")
def model_info():
    """Transparency: how the sleep-stage model was trained and how it scored."""
    bundle = staging.get_model_bundle()
    return bundle["metrics"] if bundle else {"error": "Model not available; rule-based staging is used."}
