"""End-to-end tests of the HTTP API (fake in-memory database, see conftest.py)."""
from app import config

from .conftest import csv_bytes


def upload(client, data: bytes, name: str = "night.csv"):
    return client.post("/api/nights/import", files={"file": (name, data, "text/csv")})


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_frontend_is_served_at_the_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "SleepInsight" in response.text


# ----- import ------------------------------------------------------------------------

def test_import_returns_a_summary_and_stores_the_night(client, sample_nights):
    response = upload(client, csv_bytes(sample_nights[0]["data"]))
    assert response.status_code == 200
    body = response.json()
    assert body["replaced_existing"] is False
    assert body["stage_method"] == "ml"
    assert body["summary"]["total_sleep_min"] > 0

    stored = client.get(f"/api/nights/{body['id']}").json()
    assert stored["source"] == "import"
    assert len(stored["epochs"]) > 60
    assert {"t", "stage", "hr"} <= set(stored["epochs"][0])


def test_importing_the_same_night_twice_replaces_it(client, sample_nights):
    data = csv_bytes(sample_nights[0]["data"])
    first = upload(client, data).json()
    second = upload(client, data).json()
    assert second["replaced_existing"] is True
    assert second["night_date"] == first["night_date"]
    assert len(client.get("/api/nights").json()) == 1


def test_import_rejects_a_broken_file(client):
    response = upload(client, b"timestamp,heart_rate\nnot-a-time,60\n")
    assert response.status_code == 422
    assert "line" in response.json()["detail"] or "at least" in response.json()["detail"]


def test_import_rejects_a_file_that_is_too_large(client, monkeypatch, sample_nights):
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 500)
    assert upload(client, csv_bytes(sample_nights[0]["data"])).status_code == 413


# ----- list, read, delete --------------------------------------------------------------

def test_list_is_oldest_first_and_has_no_per_minute_data(client):
    client.post("/api/demo/seed", json={"nights": 5, "seed": 7})
    nights = client.get("/api/nights").json()
    assert len(nights) == 5
    assert [n["night_date"] for n in nights] == sorted(n["night_date"] for n in nights)
    assert "epochs" not in nights[0]
    assert nights[0]["summary"]["score"] is not None


def test_list_limit_returns_the_newest_nights(client):
    client.post("/api/demo/seed", json={"nights": 5, "seed": 7})
    all_nights = client.get("/api/nights").json()
    limited = client.get("/api/nights?limit=2").json()
    assert [n["night_date"] for n in limited] == [n["night_date"] for n in all_nights[-2:]]


def test_delete_removes_one_night(client, sample_nights):
    night_id = upload(client, csv_bytes(sample_nights[0]["data"])).json()["id"]
    assert client.delete(f"/api/nights/{night_id}").status_code == 204
    assert client.get("/api/nights").json() == []
    assert client.delete(f"/api/nights/{night_id}").status_code == 404


def test_unknown_or_malformed_night_id_gives_404(client):
    assert client.get("/api/nights/507f1f77bcf86cd799439011").status_code == 404
    assert client.get("/api/nights/not-an-id").status_code == 404


# ----- daily context ---------------------------------------------------------------------

def test_context_can_be_saved_and_read_back(client):
    body = {"steps": 9000, "caffeine_cups": 2, "stress": 4, "late_workout": False}
    assert client.put("/api/context/2026-03-01", json=body).status_code == 200
    saved = client.get("/api/context").json()
    assert len(saved) == 1
    assert saved[0]["steps"] == 9000 and saved[0]["source"] == "user"


def test_saving_context_twice_overwrites_it(client):
    client.put("/api/context/2026-03-01", json={"steps": 1000})
    client.put("/api/context/2026-03-01", json={"steps": 2000})
    assert [c["steps"] for c in client.get("/api/context").json()] == [2000]


def test_context_rejects_a_bad_date_and_out_of_range_values(client):
    assert client.put("/api/context/01-03-2026", json={"steps": 10}).status_code == 422
    assert client.put("/api/context/2026-03-01", json={"stress": 9}).status_code == 422
    assert client.put("/api/context/2026-03-01", json={"steps": -5}).status_code == 422


# ----- smart alarm -------------------------------------------------------------------------

def test_smart_alarm_uses_the_last_30_minutes_before_waking_by_default(client, sample_nights):
    night_id = upload(client, csv_bytes(sample_nights[0]["data"])).json()["id"]
    result = client.post(f"/api/nights/{night_id}/smart-alarm").json()
    assert result["window_stages"]
    assert result["smart_alarm"]["stage"] in {"wake", "light", "rem", "deep"}
    assert result["minutes_earlier"] >= 0


def test_smart_alarm_accepts_an_explicit_window(client, sample_nights):
    night = upload(client, csv_bytes(sample_nights[0]["data"])).json()
    stored = client.get(f"/api/nights/{night['id']}").json()
    start, end = stored["epochs"][10]["t"], stored["epochs"][40]["t"]
    result = client.post(f"/api/nights/{night['id']}/smart-alarm", json={"window_start": start, "window_end": end}).json()
    assert result["window_start"] == start and result["window_end"] == end
    assert len(result["window_stages"]) == 31


def test_smart_alarm_rejects_a_window_outside_the_night(client, sample_nights):
    night_id = upload(client, csv_bytes(sample_nights[0]["data"])).json()["id"]
    response = client.post(
        f"/api/nights/{night_id}/smart-alarm",
        json={"window_start": "2000-01-01T06:00", "window_end": "2000-01-01T06:30"},
    )
    assert response.status_code == 422
    assert "outside" in response.json()["detail"]


# ----- demo data and analytics -----------------------------------------------------------------

def test_seed_creates_nights_and_their_context(client):
    body = client.post("/api/demo/seed", json={"nights": 10, "seed": 3}).json()
    assert body["nights_created"] == 10 and body["synthetic"] is True
    assert len(client.get("/api/context").json()) == 10


def test_clearing_demo_data_keeps_imported_nights_and_user_context(client, sample_nights):
    client.post("/api/demo/seed", json={"nights": 5, "seed": 3})
    imported = upload(client, csv_bytes(sample_nights[0]["data"])).json()["night_date"]
    client.put("/api/context/2026-03-01", json={"steps": 1234})

    removed = client.delete("/api/demo").json()
    assert removed["nights_deleted"] == 5 and removed["context_deleted"] == 5
    assert [n["night_date"] for n in client.get("/api/nights").json()] == [imported]
    assert [c["steps"] for c in client.get("/api/context").json()] == [1234]


def test_insights_on_an_empty_database(client):
    body = client.get("/api/insights").json()
    assert body == {"nights_analyzed": 0, "correlations": [], "recommendations": [], "disclaimer": body["disclaimer"]}


def test_insights_after_seeding_has_correlations_and_recommendations(client):
    client.post("/api/demo/seed", json={"nights": 28, "seed": 42})
    body = client.get("/api/insights").json()
    assert body["nights_analyzed"] == 28
    assert body["recommendations"]
    factors = {c["factor"] for c in body["correlations"]}
    assert {"caffeine_cups", "alcohol_units", "stress"} <= factors
    assert all(-1 <= c["r"] <= 1 for c in body["correlations"])


def test_forecast_is_empty_without_data_and_filled_after_seeding(client):
    assert client.get("/api/forecast").json()["energy_score"] is None
    client.post("/api/demo/seed", json={"nights": 7, "seed": 5})
    body = client.get("/api/forecast").json()
    assert 0 <= body["energy_score"] <= 100
    assert body["components"] and body["note"]


def test_model_info_reports_how_the_model_was_trained(client):
    body = client.get("/api/model-info").json()
    assert body["trained_on"] == "synthetic"
    assert 0 < body["accuracy"] <= 1
    assert body["features"]
