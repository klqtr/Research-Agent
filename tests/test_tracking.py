"""Clock/search doubles verify scheduling contracts; separate live probe records reality."""
from datetime import datetime, timedelta, timezone
import httpx
import pytest
from fastapi.testclient import TestClient
from src.app import create_app
from src.config import Settings
from src.store import Store
from src.tracking import WatchService


def paper(identifier):
    return {"title": "Research " + identifier, "abstract": "attention research", "url": "https://arxiv.org/abs/" + identifier, "code_available": False}


def test_empty_and_disabled_watches_never_contact_network(tmp_path):
    def forbidden(*args):
        raise AssertionError("No disabled watcher may call network")
    service = WatchService(Store(tmp_path), search=forbidden)
    assert service.tick() == []
    service.repo.create("attention", enabled=False)
    assert service.tick() == []


def test_due_detection_dedup_and_refresh_budget(tmp_path):
    now = [datetime(2026, 10, 16, tzinfo=timezone.utc)]
    calls = []
    def search(query, limit):
        calls.append(query)
        return [paper("1706.03762v1")] + ([paper("1706.03762v7")] if len(calls) > 1 else [])
    service = WatchService(Store(tmp_path), search=search, clock=lambda: now[0])
    watch = service.repo.create("attention", interval_minutes=30, enabled=True, refresh_limit=3, now=now[0])
    assert service.tick()[0]["new_count"] == 1
    assert service.tick() == []
    now[0] += timedelta(minutes=30)
    assert service.tick()[0]["new_count"] == 1  # New revision, not duplicate v1.
    now[0] += timedelta(minutes=30)
    assert service.tick()[0]["new_count"] == 0
    latest = service.repo.get(watch["id"])
    assert latest["runs_count"] == 3 and not latest["enabled"]
    assert latest["disabled_reason"] == "refresh_limit_reached"
    assert len(service.repo.runs(watch["id"])) == 3
    assert all(run["trigger_kind"] == "scheduled" for run in service.repo.runs(watch["id"]))
    with pytest.raises(ValueError):
        service.refresh(watch["id"], force=True)


def test_lease_blocks_duplicate_and_is_recoverable(tmp_path):
    now = datetime(2026, 10, 16, tzinfo=timezone.utc)
    service = WatchService(Store(tmp_path), clock=lambda: now)
    watch = service.repo.create("attention", enabled=True, now=now)
    service.repo.claim(watch["id"], now)
    with pytest.raises(ValueError):
        service.repo.claim(watch["id"], now)
    recovered = service.repo.claim(watch["id"], now + timedelta(minutes=3))
    assert recovered["id"] == watch["id"]


def test_failure_preserves_previous_success(tmp_path):
    now = [datetime(2026, 10, 16, tzinfo=timezone.utc)]
    service = WatchService(Store(tmp_path), search=lambda *_: [paper("1706.03762v1")], clock=lambda: now[0])
    watch = service.repo.create("attention", enabled=True, now=now[0])
    service.tick()
    succeeded = service.repo.get(watch["id"])["last_success_at"]
    now[0] += timedelta(hours=1)
    def timeout(*args):
        raise httpx.ReadTimeout("test transport timeout")
    service.search = timeout
    failed = service.tick()[0]
    assert failed["status"] == "failed" and failed["results"] == []
    assert service.repo.get(watch["id"])["last_success_at"] == succeeded
    runs = service.repo.runs(watch["id"])
    assert runs[0]["error"] and runs[1]["status"] == "completed"


def test_api_explicit_opt_in_and_parameter_limits(tmp_path):
    app = create_app(Settings(data_dir=tmp_path))
    app.state.watch_service.search = lambda *_: [paper("1706.03762v1")]
    with TestClient(app) as client:
        watch = client.post("/api/watchlist", json={"query": "attention", "refresh_limit": 1}).json()
        assert not watch["enabled"]
        assert client.post("/api/watchlist", json={"query": "bad", "interval_minutes": 1}).status_code == 422
        response = client.post(f"/api/watchlist/{watch['id']}/refresh")
        assert response.json()["status"] == "completed"
        runs = client.get(f"/api/watchlist/{watch['id']}/runs").json()["runs"]
        assert len(runs) == 1 and runs[0]["trigger_kind"] == "manual"
        assert client.post(f"/api/watchlist/{watch['id']}/refresh").status_code == 400


def test_tick_maximum_two_watches(tmp_path):
    now = datetime(2026, 10, 16, tzinfo=timezone.utc)
    calls = []
    def search(query, limit):
        calls.append(query)
        return []
    service = WatchService(Store(tmp_path), search=search, clock=lambda: now)
    for query in ("topic1", "topic2", "topic3"):
        service.repo.create(query, enabled=True, now=now)
    assert len(service.tick()) == 2 and len(calls) == 2
