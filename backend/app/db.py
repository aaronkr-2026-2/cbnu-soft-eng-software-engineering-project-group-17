"""MongoDB connection helpers."""
from functools import lru_cache

from pymongo import ASCENDING, MongoClient

from . import config


@lru_cache(maxsize=1)
def get_client():
    """Create the MongoDB client once and reuse it (the client pools connections)."""
    if config.USE_MOCK_DB:
        import mongomock  # imported lazily: only needed for demo/tests

        return mongomock.MongoClient()
    # Fail fast (3 s) instead of hanging when MongoDB is not running.
    return MongoClient(config.MONGO_URL, serverSelectionTimeoutMS=3000)


def get_db():
    """FastAPI dependency: returns the application database."""
    return get_client()[config.DB_NAME]


def ensure_indexes(db) -> None:
    """One sleep record per night and one context record per day."""
    db.nights.create_index([("night_date", ASCENDING)], unique=True)
    db.daily_context.create_index([("date", ASCENDING)], unique=True)
