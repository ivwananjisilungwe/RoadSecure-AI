from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request
from sqlalchemy import select

from .auth import Administrator, CurrentUser, Database, log_action, router as auth_router, user_data
from .incidents import router as incidents_router
from .models import Alert, AuditLog, Incident, SecurityEvent, User
from .monitoring import aggregate_dashboard, alert_data, event_data, get_record, save_event, search_events
from .schemas import AlertStatus, AlertUpdate, EventInput, EventType, Severity, Source

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(incidents_router)
SearchTerm = Annotated[str | None, Query(max_length=100)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.get("/dashboard", tags=["Analytics"])
@router.get("/reports/summary", tags=["Analytics"])
def dashboard(db: Database, user: CurrentUser):
    return aggregate_dashboard(db)


@router.get("/events", tags=["Events"])
def list_events(
    db: Database, user: CurrentUser, severity: Severity | None = None,
    source_system: Source | None = None, event_type: EventType | None = None,
    detection_result: Literal["normal", "suspicious"] | None = None,
    q: SearchTerm = None, limit: Limit = 50, offset: Offset = 0,
):
    query = select(SecurityEvent)
    if severity:
        query = query.where(SecurityEvent.severity == severity)
    if source_system:
        query = query.where(SecurityEvent.source_system == source_system)
    if event_type:
        query = query.where(SecurityEvent.event_type == event_type)
    if detection_result:
        query = query.where(SecurityEvent.detection_result["detection_result"].as_string() == detection_result)
    if q:
        query = search_events(query, q)
    rows = db.scalars(query.order_by(SecurityEvent.id.desc()).offset(offset).limit(limit))
    return [event_data(event) for event in rows]


@router.post("/events", status_code=201, tags=["Events"])
def create_event(payload: EventInput, request: Request, db: Database, user: CurrentUser):
    event = save_event(db, request.app.state.detector, payload)
    log_action(db, user.id, "EVENT_CREATED", f"Event {event.id}")
    db.commit()
    return event_data(event)


@router.get("/events/{event_id}", tags=["Events"])
def get_event(event_id: int, db: Database, user: CurrentUser):
    event = get_record(db, SecurityEvent, event_id, "Event")
    alert_id = db.scalar(select(Alert.id).where(Alert.event_id == event.id))
    return {**event_data(event), "alert_id": alert_id}


@router.get("/alerts", tags=["Alerts"])
def list_alerts(
    db: Database, user: CurrentUser, status: AlertStatus | None = None,
    severity: Severity | None = None, q: SearchTerm = None, limit: Limit = 50, offset: Offset = 0,
):
    query = select(Alert, SecurityEvent).join(SecurityEvent)
    if status:
        query = query.where(Alert.status == status)
    if severity:
        query = query.where(Alert.severity == severity)
    if q:
        query = search_events(query, q)
    rows = db.execute(query.order_by(Alert.id.desc()).offset(offset).limit(limit))
    return [alert_data(alert, event) for alert, event in rows]


@router.get("/alerts/{alert_id}", tags=["Alerts"])
def get_alert(alert_id: int, db: Database, user: CurrentUser):
    alert = get_record(db, Alert, alert_id, "Alert")
    incident_id = db.scalar(select(Incident.id).where(Incident.alert_id == alert.id))
    return {**alert_data(alert, db.get(SecurityEvent, alert.event_id)), "incident_id": incident_id}


@router.patch("/alerts/{alert_id}", tags=["Alerts"])
def update_alert(alert_id: int, payload: AlertUpdate, db: Database, user: CurrentUser):
    alert = get_record(db, Alert, alert_id, "Alert")
    if alert.status != payload.status:
        log_action(db, user.id, "ALERT_UPDATED", f"Alert {alert.id}: {alert.status} → {payload.status}")
        alert.status = payload.status
        db.commit()
    incident_id = db.scalar(select(Incident.id).where(Incident.alert_id == alert.id))
    return {**alert_data(alert, db.get(SecurityEvent, alert.event_id)), "incident_id": incident_id}


@router.get("/evaluation", tags=["Model"])
def evaluation(request: Request, user: CurrentUser):
    return request.app.state.detector.evaluation


@router.get("/model/status", tags=["Model"])
def model_status(request: Request, user: CurrentUser):
    return {
        "loaded": True, "model": "Isolation Forest",
        **request.app.state.detector.evaluation["model"],
    }


@router.get("/users", tags=["Administration"])
def list_users(db: Database, user: CurrentUser):
    return [user_data(record) for record in db.scalars(select(User).order_by(User.username))]


@router.get("/audit-logs", tags=["Administration"])
def audit_logs(db: Database, admin: Administrator, limit: Limit = 50, offset: Offset = 0):
    query = (
        select(AuditLog, User.username).outerjoin(User).order_by(AuditLog.id.desc()).offset(offset).limit(limit)
    )
    return [
        {
            "id": row.id, "username": username, "action": row.action, "detail": row.detail,
            "created_at": row.created_at,
        }
        for row, username in db.execute(query)
    ]


@router.get("/settings", tags=["Administration"])
def settings(request: Request, admin: Administrator):
    return {
        "mode": "synthetic_only", "session_hours": 8,
        "secure_cookies": request.app.state.secure_cookies, "database": "SQLite",
    }
