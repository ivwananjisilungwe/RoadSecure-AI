"""Start the two local demo services and stop only their owned processes."""
import getpass
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
RUNTIME = ROOT / "database" / "runtime"
STOP_REQUEST = RUNTIME / "launcher.stop"
LOCK_ADDRESS = ("127.0.0.1", 18399)
BACKEND_PORT = int(os.environ.get("ROADSECURE_BACKEND_PORT", "8000"))
FRONTEND_PORT = int(os.environ.get("ROADSECURE_FRONTEND_PORT", "3000"))


def stop():
    try:
        with socket.create_connection(LOCK_ADDRESS, timeout=1):
            STOP_REQUEST.touch()
    except ConnectionRefusedError:
        print("The RoadSecure launcher is not running.")
        return 0
    print("RoadSecure stop requested.")
    return 0


def terminate(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def port_available(port):
    with socket.socket() as probe:
        probe.settimeout(0.25)
        return probe.connect_ex(("127.0.0.1", port)) != 0


def run():
    next_cli = FRONTEND / "node_modules" / "next" / "dist" / "bin" / "next"
    if not next_cli.is_file():
        print("Frontend dependencies are missing. Run setup.bat or setup.sh first.", file=sys.stderr)
        return 1
    for name, port in (("backend", BACKEND_PORT), ("frontend", FRONTEND_PORT)):
        if not port_available(port):
            print(f"The RoadSecure {name} port {port} is already occupied. Stop that service or set ROADSECURE_{name.upper()}_PORT.", file=sys.stderr)
            return 1

    RUNTIME.mkdir(parents=True, exist_ok=True)
    with socket.socket() as lock:
        try:
            lock.bind(LOCK_ADDRESS)
            lock.listen()
            lock.setblocking(False)
        except OSError:
            print("The RoadSecure launcher is already running or its control port is occupied.", file=sys.stderr)
            return 1

        STOP_REQUEST.unlink(missing_ok=True)
        backend_env = os.environ.copy()
        backend_env.setdefault("ROADSECURE_DATA_DIR", str(RUNTIME))
        backend_env.setdefault(
            "ROADSECURE_ALLOWED_ORIGINS",
            f"http://localhost:{FRONTEND_PORT},http://127.0.0.1:{FRONTEND_PORT}",
        )
        if not backend_env.get("ROADSECURE_ADMIN_PASSWORD"):
            print("First launch requires an administrator password. On subsequent starts press Enter.")
            password = getpass.getpass("Administrator password: ")
            if password:
                backend_env["ROADSECURE_ADMIN_PASSWORD"] = password

        frontend_env = os.environ.copy()
        frontend_env.pop("ROADSECURE_ADMIN_PASSWORD", None)
        frontend_env["ROADSECURE_BACKEND_URL"] = f"http://127.0.0.1:{BACKEND_PORT}"
        frontend_command = "start" if (FRONTEND / ".next" / "BUILD_ID").is_file() else "dev"
        options = dict(start_new_session=True) if os.name != "nt" else dict(
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
        processes = []
        try:
            processes.append(subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)],
                cwd=ROOT, env=backend_env, **options,
            ))
            processes.append(subprocess.Popen(
                ["node", str(next_cli), frontend_command, "--hostname", "127.0.0.1", "--port", str(FRONTEND_PORT)],
                cwd=FRONTEND, env=frontend_env, **options,
            ))
            print(f"Dashboard: http://localhost:{FRONTEND_PORT}")
            print(f"API documentation: http://127.0.0.1:{BACKEND_PORT}/docs")
            print(f"Frontend mode: {frontend_command}")
            print("Press Ctrl+C or run stop.sh/stop.bat to stop RoadSecure.")
            while not STOP_REQUEST.exists():
                try:
                    connection, _ = lock.accept()
                    connection.close()
                except BlockingIOError:
                    pass
                if any(process.poll() is not None for process in processes):
                    print("A RoadSecure service exited. See its startup or runtime output above.", file=sys.stderr)
                    return 1
                time.sleep(0.25)
        except KeyboardInterrupt:
            pass
        finally:
            for process in reversed(processes):
                terminate(process)
            STOP_REQUEST.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(stop() if sys.argv[1:] == ["stop"] else run())
