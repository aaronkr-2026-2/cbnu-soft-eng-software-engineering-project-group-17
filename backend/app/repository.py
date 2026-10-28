"""All MongoDB access lives here, so routers never talk to the database directly."""
from bson import ObjectId
from bson.errors import InvalidId


def _clean(doc: dict | None) -> dict | None:
    """Replace Mongo's `_id` (ObjectId) with a plain string `id` for JSON."""
    if doc is None:
        return None
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


# --- nights ---------------------------------------------------------------------

def save_night(db, night: dict) -> dict:
    """Insert the night, or replace the existing one with the same night_date."""
    db.nights.replace_one({"night_date": night["night_date"]}, night, upsert=True)
    return _clean(db.nights.find_one({"night_date": night["night_date"]}))


def get_night(db, night_id: str) -> dict | None:
    try:
        oid = ObjectId(night_id)
    except (InvalidId, TypeError):
        return None
    return _clean(db.nights.find_one({"_id": oid}))


def get_night_by_date(db, night_date: str) -> dict | None:
    return _clean(db.nights.find_one({"night_date": night_date}, {"epochs": 0}))


def list_nights(db, limit: int = 90, with_epochs: bool = False) -> list[dict]:
    """Newest `limit` nights returned oldest-first (the order charts need)."""
    projection = None if with_epochs else {"epochs": 0}
    docs = db.nights.find({}, projection).sort("night_date", -1).limit(limit)
    return [_clean(d) for d in reversed(list(docs))]


def delete_night(db, night_id: str) -> bool:
    try:
        oid = ObjectId(night_id)
    except (InvalidId, TypeError):
        return False
    return db.nights.delete_one({"_id": oid}).deleted_count == 1


def delete_synthetic(db) -> dict:
    nights = db.nights.delete_many({"source": "synthetic"}).deleted_count
    contexts = db.daily_context.delete_many({"source": "synthetic"}).deleted_count
    return {"nights_deleted": nights, "context_deleted": contexts}


# --- daily context -----------------------------------------------------------------

def upsert_context(db, day: str, values: dict, source: str = "user") -> dict:
    doc = {"date": day, "source": source, **values}
    db.daily_context.replace_one({"date": day}, doc, upsert=True)
    return _clean(db.daily_context.find_one({"date": day}))


def context_by_date(db) -> dict[str, dict]:
    return {c["date"]: c for c in (_clean(d) for d in db.daily_context.find({}))}
