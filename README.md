# RoadSecure — Cybersecurity Monitoring System for Road Transport Information Systems

A local, defensive academic prototype implementing machine-learning anomaly detection, prioritised alerts, an activity register, incident records and an evaluation page.

## Run on Windows
1. Install Python 3.10+.
2. Extract this ZIP and open Command Prompt in the `RoadSecurePrototype` folder.
3. Run:
   ```bat
   py -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
   ```
4. Open http://127.0.0.1:5000

## Run on Linux/macOS
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Demonstration
- Dashboard: review seeded synthetic activity and alert totals.
- Simulate Activity: submit normal or suspicious behaviour. Try 8 failed logins, 220 requests/minute, 75 MB sent, 6 port scans and all four risk checkboxes.
- Activity & Alerts: inspect anomaly score/severity and change event status.
- Incident Management: create incident records linked to detected anomalies.
- Evaluation: review counts and metric formulas.
- `GET /api/summary`: JSON summary endpoint.

## Important limitations
This is an isolated prototype using generated synthetic records. It does not connect to live transport systems, real devices, payment platforms or government databases. The Isolation Forest detector is trained on synthetic normal baseline data. The evaluation page intentionally does not claim accuracy, false-positive rate or response-time results without independent labelled test data and measured timings. There is no production authentication, role-based access control, TLS, hardened deployment or tamper-resistant audit trail. Keep it local; do not expose it to the public internet. Change `SECRET_KEY` and deployment settings before any non-demo use.
