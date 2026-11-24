"""Exercise the production UI against FastAPI, including a backend restart."""

import argparse
import contextlib
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
BACKEND_PORT = 8000
FRONTEND_PORT = 3000
BACKEND_URL = f"http://127.0.0.1:{BACKEND_PORT}"
FRONTEND_URL = f"http://127.0.0.1:{FRONTEND_PORT}"
BACKEND_COMMAND = [
    sys.executable,
    "-m",
    "uvicorn",
    "backend.app.main:app",
    "--host",
    "127.0.0.1",
    "--port",
    str(BACKEND_PORT),
]
FRONTEND_COMMAND = [
    "node",
    str(ROOT / "frontend/node_modules/next/dist/bin/next"),
    "start",
    "--hostname",
    "127.0.0.1",
    "--port",
    str(FRONTEND_PORT),
]


@contextlib.contextmanager
def server(command, *, cwd, env, log_path, health_url):
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f"{command[0]} exited with {process.returncode}")
                try:
                    with urlopen(health_url, timeout=2) as response:
                        if response.status == 200:
                            break
                except (URLError, TimeoutError):
                    time.sleep(0.25)
            else:
                raise RuntimeError(f"Timed out waiting for {health_url}")
            yield
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def api_records(page, path):
    response = page.request.get(f"{FRONTEND_URL}/api/v1/{path}")
    assert response.ok, f"GET {path} returned {response.status}"
    return response.json()


def snapshot(page, directory, label):
    assert page.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth + 1"
    ), f"Horizontal overflow on {label}"
    if directory is not None:
        directory.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(directory / f"{label}.png"), full_page=True, animations="disabled")


def details_link(page, section):
    matches = page.locator(f'a[href^="/{section}/"]')
    expect(matches).not_to_have_count(0)
    return matches.first


def exercise(page, password, screenshot_dir):
    page.goto("/login")
    expect(page.get_by_role("button", name="Sign in", exact=True)).to_be_visible()
    assert page.request.get(f"{FRONTEND_URL}/api/v1/events").status == 401
    snapshot(page, screenshot_dir, "login-desktop")

    page.get_by_label("Username", exact=True).fill("admin")
    password_input = page.get_by_label(re.compile(r"^Password\b"))
    password_input.fill(secrets.token_urlsafe(24))
    with page.expect_response(
        lambda response: response.url.endswith("/api/v1/auth/login")
    ) as rejected_login:
        page.get_by_role("button", name="Sign in", exact=True).click()
    assert rejected_login.value.status == 401
    expect(page).to_have_url(f"{FRONTEND_URL}/login")
    password_input.fill(password)
    page.get_by_role("button", name="Sign in", exact=True).click()
    expect(page).to_have_url(f"{FRONTEND_URL}/")
    expect(page.get_by_role("link", name="Simulate Activity", exact=True)).to_be_visible()
    snapshot(page, screenshot_dir, "dashboard-empty-desktop")

    page.get_by_role("link", name="Simulate Activity", exact=True).click()
    with page.expect_response(
        lambda response: "/api/v1/simulator/generate" in response.url
        and response.request.method == "POST"
    ) as normal_response:
        page.get_by_role("button", name=re.compile(r"\bnormal activity\b", re.I)).click()
    assert normal_response.value.ok
    normal_events = api_records(page, "events")
    assert len(normal_events) == 1
    assert normal_events[0]["detection_result"]["ml_prediction"] == "normal"
    assert api_records(page, "alerts") == []
    with page.expect_response(
        lambda response: "/api/v1/simulator/generate" in response.url
        and response.request.method == "POST"
    ) as suspicious_response:
        page.get_by_role("button", name=re.compile("combined suspicious activity", re.I)).click()
    assert suspicious_response.value.ok
    events = api_records(page, "events")
    assert len(events) == 2
    alerts = api_records(page, "alerts")
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["event_id"] != normal_events[0]["id"]
    assert alert["event_id"] in {event["id"] for event in events}
    detection = alert["event"]["detection_result"]
    assert detection["rule_results"]
    assert detection["ml_prediction"] == "anomaly"
    assert detection["risk_score"] > 0
    snapshot(page, screenshot_dir, "simulator-desktop")

    page.goto("/events")
    expect(page).to_have_url(f"{FRONTEND_URL}/events")
    expect(page.get_by_role("heading", name="Security events", exact=True)).to_be_visible()
    page.get_by_label("Severity", exact=True).select_option(alert["severity"])
    snapshot(page, screenshot_dir, "events-desktop")
    page.goto(f"/events/{alert['event_id']}")
    expect(page.get_by_role("heading", name="Detection analysis")).to_be_visible()
    snapshot(page, screenshot_dir, "event-desktop")
    page.goto("/alerts")
    expect(page).to_have_url(f"{FRONTEND_URL}/alerts")
    expect(page.get_by_role("heading", name="Security alerts", exact=True)).to_be_visible()
    snapshot(page, screenshot_dir, "alerts-desktop")
    page.goto(f"/alerts/{alert['id']}")
    expect(page).to_have_url(re.compile(r"/alerts/[^/]+$"))
    expect(page.get_by_role("heading", name="Triggered rules", exact=True)).to_be_visible()
    expect(page.get_by_text("Isolation Forest", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="Create incident", exact=True)).to_be_visible()
    snapshot(page, screenshot_dir, "alert-desktop")
    page.get_by_role("button", name="Create incident", exact=True).click()
    expect(page).to_have_url(re.compile(r"/incidents/[^/]+$"))

    page.get_by_role("button", name="Start investigation", exact=True).click()
    note = "Reviewed synthetic event and confirmed related alert."
    page.get_by_role("textbox", name="Investigation note", exact=True).fill(note)
    page.get_by_role("button", name="Add note", exact=True).click()
    expect(page.get_by_text(note, exact=True)).to_be_visible()
    resolution = "Closed the synthetic investigation after reviewing the detection evidence."
    page.get_by_role("textbox", name="Resolution", exact=True).fill(resolution)
    page.get_by_role("button", name="Resolve incident", exact=True).click()
    with page.expect_response(
        lambda response: "/api/v1/incidents/" in response.url
        and response.request.method == "PATCH"
    ) as close_response:
        page.get_by_role("button", name="Close incident", exact=True).click()
    assert close_response.value.ok
    incident_url = page.url
    incident_path = incident_url.split("/")[-1]
    incident = api_records(page, f"incidents/{incident_path}")
    assert incident["alert_id"] == alert["id"]
    assert incident["status"].upper() == "CLOSED"
    assert incident["resolution"] == resolution
    assert any(entry["detail"] == note for entry in incident["history"])
    snapshot(page, screenshot_dir, "incident-desktop")

    page.get_by_role("link", name="Model Evaluation", exact=True).click()
    expect(page.get_by_role("heading", name="Model evaluation", exact=False)).to_be_visible()
    dashboard = api_records(page, "dashboard")
    assert dashboard["total_events"] == 2
    assert dashboard["total_alerts"] == 1
    evaluation = api_records(page, "evaluation")
    test_count = evaluation["datasets"]["test"]["count"]
    experiments = evaluation["experiments"]
    assert set(experiments) == {"rules", "isolation_forest", "hybrid"}
    for experiment in experiments.values():
        assert sum(
            experiment[key]
            for key in ("true_positives", "true_negatives", "false_positives", "false_negatives")
        ) == test_count
    snapshot(page, screenshot_dir, "evaluation-desktop")

    page.goto("/")
    expect(page.get_by_role("link", name="Simulate Activity", exact=True)).to_be_visible()
    snapshot(page, screenshot_dir, "dashboard-desktop")
    for width, height, label in ((1280, 800, "laptop"), (390, 844, "mobile")):
        page.set_viewport_size({"width": width, "height": height})
        snapshot(page, screenshot_dir, f"dashboard-{label}")
    return incident_url, incident


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chromium", help="Path to an installed Chromium binary")
    parser.add_argument("--screenshots", type=Path, help="Directory for acceptance screenshots")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="roadsecure-acceptance-") as directory:
        temp = Path(directory)
        password = secrets.token_urlsafe(24)
        env = {
            **os.environ,
            "ROADSECURE_DATA_DIR": str(temp / "data"),
            "ROADSECURE_ADMIN_USERNAME": "admin",
            "ROADSECURE_ADMIN_PASSWORD": password,
            "ROADSECURE_BACKEND_URL": BACKEND_URL,
            "NEXT_TELEMETRY_DISABLED": "1",
        }
        backend_log = temp / "backend.log"
        frontend_log = temp / "frontend.log"
        try:
            subprocess.run(
                [sys.executable, "-m", "app.detection", "train"],
                cwd=ROOT / "backend",
                env=env,
                check=True,
            )
            with (
                server(
                    FRONTEND_COMMAND,
                    cwd=ROOT / "frontend",
                    env=env,
                    log_path=frontend_log,
                    health_url=f"{FRONTEND_URL}/login",
                ),
                sync_playwright() as playwright,
            ):
                browser = playwright.chromium.launch(executable_path=args.chromium)
                page = browser.new_page(
                    base_url=FRONTEND_URL, viewport={"width": 1440, "height": 900}
                )
                backend_options = {
                    "cwd": ROOT,
                    "env": env,
                    "log_path": backend_log,
                    "health_url": f"{BACKEND_URL}/health",
                }
                with server(BACKEND_COMMAND, **backend_options):
                    incident_url, incident = exercise(page, password, args.screenshots)
                backend_options["log_path"] = temp / "backend-restarted.log"
                with server(BACKEND_COMMAND, **backend_options):
                    page.goto(incident_url)
                    restored = api_records(page, f"incidents/{incident['id']}")
                    assert restored == incident, "Incident changed after a clean backend restart"
                    assert len(api_records(page, "events")) == 2
                    assert len(api_records(page, "alerts")) == 1
                browser.close()
        except Exception:
            for log in sorted(temp.glob("*.log")):
                print(f"\n{log.name}\n{log.read_text(encoding='utf-8', errors='replace')}", file=sys.stderr)
            raise
    print("PASS: browser login, event detection, alert, incident lifecycle, evaluation and SQLite restart")


if __name__ == "__main__":
    main()
