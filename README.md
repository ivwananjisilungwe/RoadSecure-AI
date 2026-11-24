# RoadSecure AI

RoadSecure AI is a Mulungushi University ICT431 project that explores cybersecurity monitoring for road transport information systems. An operator generates synthetic telemetry, inspects rules and Isolation Forest results, and investigates alerts in a local security dashboard.

## Start on Windows

Install **Python 3.12** with the Python launcher, **Node.js 22 LTS**, and Git. In a VS Code terminal at the repository root, run:

```powershell
.\setup.bat
.\start.bat
```

Enter an administrator password of at least 12 characters on the first launch. Open [the dashboard](http://localhost:3000) and sign in as `admin`. On later launches, press Enter at the bootstrap prompt and sign in with the original password. Stop both application processes using Ctrl+C in their terminal or `.\stop.bat` from another terminal.

[Windows setup and manual fallback](docs/WINDOWS_SETUP.md) · [Presentation guide](docs/DEMONSTRATION.md)

## Architecture

The Next.js App Router console uses same-origin requests to reach FastAPI. The Python service runs weighted detection rules and a trained scikit-learn Isolation Forest, then stores security events, alerts, and incident history in SQLite. [Architecture](docs/ARCHITECTURE.md) · [ML evaluation](docs/ML_EVALUATION.md)

## Verification

Run `python -m pytest backend/tests` with the backend dependencies installed, and `npm run lint`, `npm run typecheck`, and `npm run build` from `frontend/`. The GitHub Actions workflow also runs a production browser acceptance test. See [acceptance and evidence](docs/MVP_ACCEPTANCE.md).

The original Flask prototype and design references remain in the root and `design/`. Use the Next.js and FastAPI application for the presentation.
