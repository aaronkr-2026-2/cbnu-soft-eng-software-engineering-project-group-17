"""Request bodies. FastAPI validates incoming JSON against these classes."""
from datetime import datetime

from pydantic import BaseModel, Field


class DailyContext(BaseModel):
    """What the user did during the day before the night. All fields optional."""

    steps: int | None = Field(None, ge=0, le=100_000)
    caffeine_cups: float | None = Field(None, ge=0, le=20, description="Caffeinated drinks after 14:00")
    alcohol_units: float | None = Field(None, ge=0, le=30)
    stress: int | None = Field(None, ge=1, le=5, description="1 = calm, 5 = very stressed")
    late_workout: bool | None = Field(None, description="Hard workout within 3 hours of bedtime")


class AlarmRequest(BaseModel):
    """Wake-up window. If omitted, the last 30 minutes before the final awakening are used."""

    window_start: datetime | None = None
    window_end: datetime | None = None


class DemoRequest(BaseModel):
    nights: int = Field(28, ge=3, le=60)
    seed: int = 42
