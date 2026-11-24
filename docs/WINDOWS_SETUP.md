# Windows setup

Use Python 3.12 and Node.js 22 LTS. Open the repository root in VS Code and use a PowerShell terminal.

```powershell
git clone --branch feature/mvp-demo-v1 https://github.com/ivwananjisilungwe/RoadSecure-AI.git
cd RoadSecure-AI
.\setup.bat
.\start.bat
```

Enter a password between 12 and 256 characters when initializing the local administrator. Open http://localhost:3000 and sign in as `admin`. The API and its OpenAPI documentation are on http://127.0.0.1:8000/docs. Use `.\stop.bat` or Ctrl+C in the start terminal. The launcher starts both services on loopback.

## Manual fallback

From the repository root, initialize dependencies and train the model:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
npm --prefix frontend ci
.\train_model.bat
```

Run the backend from one terminal. The bootstrap password below is entered in a masked prompt and removed when the process exits.

```powershell
$env:ROADSECURE_DATA_DIR = Join-Path $PWD "database\runtime"
$secure = Read-Host "Initial administrator password" -AsSecureString
$env:ROADSECURE_ADMIN_PASSWORD = [System.Net.NetworkCredential]::new("", $secure).Password
try {
  .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
} finally {
  Remove-Item Env:ROADSECURE_ADMIN_PASSWORD -ErrorAction SilentlyContinue
}
```

Run the frontend in a second terminal from the repository root:

```powershell
npm --prefix frontend run dev -- --hostname 127.0.0.1 --port 3000
```

Keep the same data directory when restarting. If FastAPI reports a missing detector, run `.\train_model.bat` and verify that both commands use the same data directory. If a port is in use, close the service already occupying it or use the manual commands with matching proxy configuration. To inspect the saved evaluation, use `.\evaluate_model.bat`. To verify the checkout, use `.\run_tests.bat` or the CI workflow.
