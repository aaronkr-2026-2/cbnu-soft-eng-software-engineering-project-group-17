"""Shared test setup.

The environment variables below MUST be set before the app is imported, so
that tests use an in-memory fake MongoDB (mongomock) and a small, quickly
trained model stored in a temporary folder.
"""
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

os.environ["USE_MOCK_DB"] = "1"
os.environ["MODEL_DIR"] = tempfile.mkdtemp(prefix="sheepcounter_model_")
os.environ["TRAIN_NIGHTS"] = "25"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mongomock  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import ensure_indexes, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.synthetic import generate_nights  # noqa: E402


@pytest.fixture
def db():
    """A fresh empty fake database for every test."""
    database = mongomock.MongoClient()["sheepcounter_test"]
    ensure_indexes(database)
    return database


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:  # `with` runs the startup code (model training)
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def sample_nights():
    """Ten deterministic synthetic nights (data includes the true stage labels)."""
    return generate_nights(10, seed=1, last_night=date(2026, 3, 31))


def csv_bytes(night_df, drop=()) -> bytes:
    """Serialize a generated night like a user's export (without the true stage)."""
    return night_df.drop(columns=["stage_true", *drop], errors="ignore").to_csv(index=False).encode()
