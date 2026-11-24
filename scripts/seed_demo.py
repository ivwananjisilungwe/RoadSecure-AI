"""Populate the running local RoadSecure API with reproducible synthetic scenarios."""
import getpass
import os

import httpx

from backend.app.ml.synthetic import simulate

SAMPLES = (
    ("normal", "vehicle_registration", None),
    ("successful_authentication", "driver_licensing", None),
    ("normal_transfer", "vehicle_inspection", None),
    ("legitimate_admin", "administration", None),
    ("failed_login", "driver_licensing", "OPEN"),
    ("privileged_action", "administration", "INVESTIGATING"),
    ("combined", "network_infrastructure", "RESOLVED"),
    ("large_transfer", "transport_payments", None),
)


def main():
    username = os.getenv("ROADSECURE_ADMIN_USERNAME", "admin")
    password = getpass.getpass("RoadSecure administrator password: ")
    with httpx.Client(base_url="http://127.0.0.1:8000/api/v1", timeout=15, trust_env=False) as client:
        def request(method, path, body=None, allow_conflict=False):
            response = client.request(method, path, json=body)
            if allow_conflict and response.status_code == 409:
                return None
            response.raise_for_status()
            return response.json()

        admin = request("POST", "/auth/login", {"username": username, "password": password})
        try:
            for scenario, source, initial_status in SAMPLES:
                event = request("POST", "/events", {
                    **simulate(scenario, source), "event_id": f"demo-seed-{scenario}",
                }, allow_conflict=True)
                if event is None:
                    continue
                print(f"{source}: {scenario} → {event['severity']}")
                if not initial_status:
                    continue
                alerts = request("GET", f"/alerts?q={event['event_id']}")
                alert = next(record for record in alerts if record["event_id"] == event["id"])
                incident = request("POST", "/incidents", {
                    "alert_id": alert["id"], "title": f"Demo investigation · {scenario.replace('_', ' ')}",
                    "assigned_to": admin["id"],
                })
                path = f"/incidents/{incident['id']}"
                if initial_status in {"INVESTIGATING", "RESOLVED"}:
                    request("PATCH", path, {"status": "INVESTIGATING"})
                    request("POST", f"{path}/notes", {"note": "Reviewed the generated detection evidence."})
                if initial_status == "RESOLVED":
                    request("PATCH", path, {
                        "status": "RESOLVED", "resolution": "Documented the cause of the synthetic event.",
                    })
        finally:
            request("POST", "/auth/logout")


if __name__ == "__main__":
    try:
        main()
    except httpx.HTTPError as exc:
        raise SystemExit(f"Demo data preparation failed: {exc}") from exc
