# SQLite persistence

| Table | Responsibility |
| --- | --- |
| `users` | Unique usernames, hashed passwords, roles |
| `login_sessions` | Revocable session IDs and expiry |
| `security_events` | Synthetic event envelope, input features, and detection result |
| `alerts` | Alert status and severity, linked to a unique event |
| `incidents` | Investigation assignment, status, resolution, and revision |
| `incident_history` | Recorded actions and notes for an incident |
| `audit_logs` | Security-relevant actions with actor, detail, and time |

The API enables foreign keys and SQLite write-ahead logging. A sequential incident lifecycle and revision checks guard conflicting incident edits. A stable local runtime directory preserves records and signing material over restarts. The service creates the schema on first launch. This demo uses a fresh schema alongside the original Flask prototype database.
