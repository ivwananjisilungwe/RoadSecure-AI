# Presentation guide

## Five minutes

| Time | Show and explain |
| --- | --- |
| 0:00–0:40 | Sign in and introduce the dashboard. RoadSecure monitors synthetic road transport telemetry in an isolated environment. |
| 0:40–1:30 | Open Simulator. Submit Normal activity, then Combined suspicious activity. Explain that both inputs are records processed by FastAPI. |
| 1:30–2:20 | Inspect the resulting alert. Show the signal values, triggered rules, Isolation Forest output, risk score, and severity. |
| 2:20–3:40 | Create an incident from the alert, start investigation, add a note, record a resolution, then close it. Open the history. |
| 3:40–4:40 | Open Model evaluation. Explain the independent synthetic test split, confusion matrix, accuracy, precision, recall, false-positive rate, and measured detection latency. |
| 4:40–5:00 | Return to the dashboard and summarize the three capstone objectives. Emphasize that the experiment measures performance on synthetic data. |

## One minute

Sign in, submit Combined suspicious activity, open the alert and point to the rules and model output, create the incident, then show the evidence on Model evaluation.

## Example investigation

Use the note “Reviewed repeated authentication failures and device changes in the synthetic event.” Use the resolution “Confirmed the simulator scenario and documented its detection signals.”

Before presenting, run the setup and check that the login, Simulator, Alerts, Incidents and Model evaluation pages open. A fresh database starts with an empty dashboard. Use Simulator to generate the activity you want to present.
