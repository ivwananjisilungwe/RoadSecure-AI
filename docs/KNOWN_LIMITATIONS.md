# Known limitations

- Training and evaluation use generated road-transport telemetry. The metrics describe that distribution and do not establish real-world detection accuracy or readiness for agency deployment.
- SQLite and per-process rate limiting suit the single-workstation demo. Internet deployment would require a separate review of TLS, proxy trust, shared rate limiting, authentication and authorization, database durability, and incident data retention.
- The Windows scripts target a standard Windows developer workstation. Windows CI and a local in-person run are tracked separately in the acceptance report.
- The root Flask application is a historical prototype with different storage and security assumptions. The presentation uses the new frontend and API.
