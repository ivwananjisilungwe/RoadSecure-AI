# API

Visit [OpenAPI](http://127.0.0.1:8000/docs) when the backend is running. Application paths are relative to `/api/v1`. The Next.js console proxies those paths to FastAPI.

| Operation | Path | Purpose |
| --- | --- | --- |
| POST | `/auth/login` | Validate credentials and open a session |
| GET / POST | `/auth/me` / `/auth/logout` | Read the current user or revoke the session |
| GET | `/dashboard`, `/reports/summary` | Current counts and aggregated analytics |
| GET / POST | `/events` | Filter and paginate events or submit synthetic telemetry |
| GET | `/events/{id}` | Retrieve persisted detection evidence |
| GET / PATCH | `/alerts/{id}` | Inspect or set the alert review status |
| GET | `/alerts` | Search and filter the alert queue |
| GET / POST | `/incidents` | List or create incidents |
| GET / PATCH | `/incidents/{id}` | Read or update an investigation |
| POST | `/incidents/{id}/notes` | Append an investigation note |
| POST | `/simulator/generate` | Generate a bounded batch of fictional telemetry |
| GET | `/evaluation`, `/model/status` | Inspect the saved experiment and detector metadata |
| GET | `/users`, `/audit-logs`, `/settings` | Inspect accounts, recent audit actions, and settings |

Login and public service health are available before authentication. The application uses an HttpOnly cookie for authenticated requests. Validation errors return HTTP 422, authentication failures return 401, forbidden actions return 403, and conflicts return 409.
