"""API integration coverage for the RoadSecure local presentation workflow."""

import asyncio
from contextvars import ContextVar
from pathlib import Path
import os
import shutil
import subprocess
import sys

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.auth import password_hash
from app.main import create_app
from app.models import Incident, IncidentHistory, LoginSession, User
from app.ml.synthetic import simulate


BACKEND = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME = BACKEND.parent / "database" / "runtime"
PASSWORD = "RoadSecure-Test-Password-2026!"
MODEL_FILES = ("roadsecure-iforest.joblib", "evaluation.json")


@pytest.fixture(scope="session")
def model_source(tmp_path_factory):
    if (DEFAULT_RUNTIME / MODEL_FILES[0]).is_file():
        return DEFAULT_RUNTIME
    target = tmp_path_factory.mktemp("roadsecure-model")
    env = {**os.environ, "ROADSECURE_DATA_DIR": str(target)}
    subprocess.run(
        [sys.executable, "-m", "app.detection", "train"],
        cwd=BACKEND,
        env=env,
        check=True,
    )
    return target


@pytest.fixture()
def data_dir(tmp_path, model_source):
    target = tmp_path / "data"
    target.mkdir()
    for name in MODEL_FILES:
        source = model_source / name
        if source.is_file():
            shutil.copy2(source, target / name)
    return target


@pytest.fixture()
def client_factory(data_dir, monkeypatch):
    monkeypatch.setenv("ROADSECURE_DATA_DIR", str(data_dir))
    monkeypatch.setenv("ROADSECURE_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ROADSECURE_ADMIN_PASSWORD", PASSWORD)
    monkeypatch.setenv("ROADSECURE_SECURE_COOKIES", "0")

    def factory():
        return TestClient(create_app())

    return factory


def login(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response


def create_event(client, scenario="combined"):
    response = client.post("/api/v1/events", json=simulate(scenario))
    assert response.status_code == 201, response.text
    return response.json()


def create_incident(client, alert_id):
    response = client.post(
        "/api/v1/incidents",
        json={"alert_id": alert_id, "title": "Synthetic investigation"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_authentication_validation_and_unauthorized_access(client_factory):
    with client_factory() as client:
        assert client.get("/api/v1/events").status_code == 401
        assert client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "incorrect-password"},
        ).status_code == 401
        response = login(client)
        cookie = response.headers["set-cookie"]
        assert "HttpOnly" in cookie
        assert "SameSite=strict" in cookie
        assert client.get("/api/v1/auth/me").json()["role"] == "ADMIN"
        assert client.get("/api/v1/audit-logs").status_code == 200
        assert client.post("/api/v1/auth/logout").status_code == 200
        assert client.get("/api/v1/auth/me").status_code == 401


def test_expired_session_is_rejected(client_factory):
    with client_factory() as client:
        login(client)
        app = client.app
        with app.state.session_factory.begin() as db:
            for session in db.scalars(select(LoginSession)).all():
                session.expires_at = 0
        assert client.get("/api/v1/auth/me").status_code == 401


def test_analyst_cannot_access_administrator_endpoints(client_factory):
    with client_factory() as client:
        login(client)
        app = client.app
        with app.state.session_factory.begin() as db:
            db.add(User(
                username="analyst",
                password_hash=password_hash.hash(PASSWORD),
                role="ANALYST",
            ))
        client.post("/api/v1/auth/logout")
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "analyst", "password": PASSWORD},
        )
        assert response.status_code == 200, response.text
        assert client.get("/api/v1/audit-logs").status_code == 403
        assert client.get("/api/v1/settings").status_code == 403


def test_event_detection_alert_and_dashboard_integration(client_factory):
    with client_factory() as client:
        login(client)
        assert client.post("/api/v1/events", json={"event_type": "invalid"}).status_code == 422
        spoofed = simulate("combined")
        spoofed["detection_result"] = {"should_alert": False}
        assert client.post("/api/v1/events", json=spoofed).status_code == 422

        normal = create_event(client, "normal")
        suspicious = create_event(client, "combined")
        assert normal["detection_result"]["should_alert"] is False
        assert suspicious["detection_result"]["should_alert"] is True
        assert suspicious["detection_result"]["rule_results"]
        assert suspicious["detection_result"]["ml_prediction"] == "anomaly"
        assert suspicious["risk_score"] >= 75

        events = client.get("/api/v1/events").json()
        alerts = client.get("/api/v1/alerts").json()
        assert len(events) == 2
        assert len(alerts) == 1
        assert alerts[0]["event_id"] == suspicious["id"]
        assert alerts[0]["event"]["detection_result"] == suspicious["detection_result"]

        dashboard = client.get("/api/v1/dashboard").json()
        assert dashboard["total_events"] == 2
        assert dashboard["total_alerts"] == 1
        assert dashboard["critical_alerts"] == 1
        assert dashboard["anomalous_events"] == 1

        status = client.get("/api/v1/model/status").json()
        assert status["loaded"] is True
        evaluation = client.get("/api/v1/evaluation").json()
        assert evaluation["datasets"]["train"]["count"] == 5_000
        assert evaluation["datasets"]["validation"]["count"] == 1_000
        assert evaluation["datasets"]["test"]["count"] == 2_000
        assert set(evaluation["experiments"]) == {"rules", "isolation_forest", "hybrid"}


def test_simulator_generates_real_persisted_events(client_factory):
    with client_factory() as client:
        login(client)
        response = client.post(
            "/api/v1/simulator/generate",
            json={"scenario": "failed_login", "count": 2, "source_system": "administration"},
        )
        assert response.status_code == 201, response.text
        generated = response.json()["events"]
        assert len(generated) == 2
        assert all(event["source_system"] == "administration" for event in generated)
        assert all(event["detection_result"]["rule_results"] for event in generated)
        assert len(client.get("/api/v1/events").json()) == 2


def test_incident_lifecycle_notes_and_audit_history(client_factory):
    with client_factory() as client:
        login(client)
        account = client.get("/api/v1/auth/me").json()
        create_event(client)
        alert = client.get("/api/v1/alerts").json()[0]
        incident = create_incident(client, alert["id"])

        duplicate = client.post(
            "/api/v1/incidents",
            json={"alert_id": alert["id"], "title": "Duplicate"},
        )
        assert duplicate.status_code == 409
        assert client.patch(
            f"/api/v1/incidents/{incident['id']}",
            json={"assigned_to": 999_999},
        ).status_code == 404
        assert client.patch(
            f"/api/v1/incidents/{incident['id']}",
            json={"priority": "HIGH", "assigned_to": account["id"]},
        ).status_code == 200
        assert client.patch(
            f"/api/v1/incidents/{incident['id']}",
            json={"status": "RESOLVED", "resolution": "Invalid skip"},
        ).status_code == 409

        endpoint = f"/api/v1/incidents/{incident['id']}"
        response = client.patch(endpoint, json={"status": "INVESTIGATING"})
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "INVESTIGATING"

        note = "Reviewed synthetic event and confirmed related alert."
        response = client.post(f"{endpoint}/notes", json={"note": note})
        assert response.status_code == 201, response.text
        assert any(entry["detail"] == note for entry in response.json()["history"])
        second_note = "Checked the related alert and device evidence."
        assert client.post(f"{endpoint}/notes", json={"note": second_note}).status_code == 201

        assert client.patch(endpoint, json={"status": "RESOLVED"}).status_code == 422
        resolution = "Synthetic activity reviewed; no real infrastructure was affected."
        response = client.patch(endpoint, json={"status": "RESOLVED", "resolution": resolution})
        assert response.status_code == 200, response.text
        assert response.json()["resolution"] == resolution
        assert client.patch(endpoint, json={"status": "CLOSED"}).status_code == 200
        assert client.post(f"{endpoint}/notes", json={"note": "Too late"}).status_code == 409
        assert client.patch(endpoint, json={"priority": "LOW"}).status_code == 409

        restored = client.get(endpoint).json()
        assert restored["status"] == "CLOSED"
        assert restored["priority"] == "HIGH"
        assert restored["assigned_to"] == account["id"]
        details = [entry["detail"] for entry in restored["history"]]
        assert note in details
        assert second_note in details
        assert resolution in details
        assert "OPEN → INVESTIGATING" in details
        assert "INVESTIGATING → RESOLVED" in details
        assert "RESOLVED → CLOSED" in details

        audit = client.get("/api/v1/audit-logs?limit=100").json()
        actions = {entry["action"] for entry in audit}
        assert "INCIDENT_NOTE_ADDED" in actions
        assert "INCIDENT_STATUS_CHANGED" in actions
        assert "INCIDENT_RESOLUTION_RECORDED" in actions


def test_incident_and_events_persist_across_backend_restart(client_factory):
    with client_factory() as client:
        login(client)
        create_event(client)
        alert = client.get("/api/v1/alerts").json()[0]
        incident = create_incident(client, alert["id"])
        endpoint = f"/api/v1/incidents/{incident['id']}"
        client.patch(endpoint, json={"status": "INVESTIGATING"})
        client.post(f"{endpoint}/notes", json={"note": "Persistent investigation note"})
        expected = client.get(endpoint).json()

    with client_factory() as restarted:
        login(restarted)
        assert restarted.get(endpoint).json() == expected
        assert len(restarted.get("/api/v1/events").json()) == 1
        assert len(restarted.get("/api/v1/alerts").json()) == 1


def test_foreign_keys_and_optimistic_locking_remain_enforced(client_factory):
    with client_factory() as client:
        login(client)
        create_event(client)
        alert = client.get("/api/v1/alerts").json()[0]
        incident = create_incident(client, alert["id"])
        app = client.app
        with app.state.session_factory() as db:
            assert db.execute(text("PRAGMA foreign_keys")).scalar() == 1
            with pytest.raises(IntegrityError):
                with db.begin_nested():
                    db.add(IncidentHistory(
                        incident_id=999_999,
                        user_id=1,
                        action="NOTE_ADDED",
                        detail="Orphan",
                    ))

        with app.state.session_factory() as first, app.state.session_factory() as second:
            current = first.get(Incident, incident["id"])
            stale = second.get(Incident, incident["id"])
            current.status = "INVESTIGATING"
            first.commit()
            stale.status = "RESOLVED"
            stale.resolution = "Stale write"
            with pytest.raises(StaleDataError):
                second.commit()


def test_stale_incident_write_returns_exact_conflict_response(client_factory, monkeypatch):
    with client_factory() as client:
        login(client)
        create_event(client)
        alert = client.get("/api/v1/alerts").json()[0]
        incident = create_incident(client, alert["id"])
        incident_id = incident["id"]
        token = client.cookies.get("roadsecure_session")
        assert token
        app = client.app
        request_role = ContextVar("request_role", default="")
        original_commit = Session.commit

        def stale_note_commit(session):
            if request_role.get() == "stale-note":
                raise StaleDataError()
            return original_commit(session)

        async def role_app(scope, receive, send):
            if scope["type"] != "http":
                await app(scope, receive, send)
                return
            headers = dict(scope["headers"])
            value = request_role.set(headers.get(b"x-test-role", b"").decode())
            try:
                await app(scope, receive, send)
            finally:
                request_role.reset(value)

        monkeypatch.setattr(Session, "commit", stale_note_commit)
        headers = {"cookie": f"roadsecure_session={token}"}

        async def submit_note(role):
            transport = httpx.ASGITransport(app=role_app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
                headers={**headers, "x-test-role": role},
            ) as request:
                return await request.post(
                    f"/api/v1/incidents/{incident_id}/notes",
                    json={"note": "Reviewed synthetic event and confirmed related alert."},
                )

        conflict = asyncio.run(submit_note("stale-note"))
        assert conflict.status_code == 409
        assert conflict.json() == {
            "detail": "The record conflicts with current data. Refresh and try again."
        }

        restored = client.get(f"/api/v1/incidents/{incident_id}").json()
        assert not any(
            entry["detail"] == "Reviewed synthetic event and confirmed related alert."
            for entry in restored["history"]
        )
        accepted = asyncio.run(submit_note("sequential-note"))
        assert accepted.status_code == 201, accepted.text
        assert any(
            entry["detail"] == "Reviewed synthetic event and confirmed related alert."
            for entry in accepted.json()["history"]
        )
