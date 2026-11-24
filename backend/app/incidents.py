from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from .auth import CurrentUser, Database, log_action
from .models import Alert, Incident, IncidentHistory, User, utc_now
from .monitoring import get_record
from .schemas import IncidentInput, IncidentNote, IncidentStatus, IncidentUpdate

router = APIRouter(prefix="/incidents", tags=["Incidents"])
TRANSITIONS = {"OPEN": "INVESTIGATING", "INVESTIGATING": "RESOLVED", "RESOLVED": "CLOSED"}


def history_data(db, incident_id):
    rows = db.execute(
        select(IncidentHistory, User.username).join(User)
        .where(IncidentHistory.incident_id == incident_id).order_by(IncidentHistory.id)
    )
    return [
        {
            "id": record.id, "action": record.action, "detail": record.detail,
            "username": username, "created_at": record.created_at,
        }
        for record, username in rows
    ]


def incident_data(db, record):
    return {
        "id": record.id, "alert_id": record.alert_id, "title": record.title,
        "priority": record.priority, "assigned_to": record.assigned_to, "status": record.status,
        "resolution": record.resolution, "created_at": record.created_at, "updated_at": record.updated_at,
        "history": history_data(db, record.id),
    }


def record_change(db, incident, user, action, detail):
    incident.updated_at = utc_now()
    db.add(IncidentHistory(incident_id=incident.id, user_id=user.id, action=action, detail=detail))
    log_action(db, user.id, f"INCIDENT_{action}", f"Incident {incident.id}")


def verify_assignee(db, user_id):
    if user_id is not None:
        get_record(db, User, user_id, "Assigned user")


@router.get("")
def list_incidents(
    db: Database,
    user: CurrentUser,
    status: IncidentStatus | None = None,
    alert_id: Annotated[int | None, Query(gt=0)] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    query = select(Incident)
    if status:
        query = query.where(Incident.status == status)
    if alert_id is not None:
        query = query.where(Incident.alert_id == alert_id)
    if q:
        query = query.where(Incident.title.icontains(q, autoescape=True))
    return [
        incident_data(db, record)
        for record in db.scalars(query.order_by(Incident.id.desc()).offset(offset).limit(limit))
    ]


@router.post("", status_code=201)
def create_incident(payload: IncidentInput, db: Database, user: CurrentUser):
    alert = get_record(db, Alert, payload.alert_id, "Alert")
    if db.scalar(select(Incident.id).where(Incident.alert_id == alert.id)) is not None:
        raise HTTPException(409, "An incident already exists for this alert")
    verify_assignee(db, payload.assigned_to)
    record = Incident(
        alert_id=alert.id, title=payload.title,
        priority=payload.priority or alert.severity, assigned_to=payload.assigned_to,
    )
    db.add(record)
    db.flush()
    record_change(db, record, user, "CREATED", f"Opened from alert {alert.id}")
    db.commit()
    return incident_data(db, record)


@router.get("/{incident_id}")
def get_incident(incident_id: int, db: Database, user: CurrentUser):
    return incident_data(db, get_record(db, Incident, incident_id, "Incident"))


@router.patch("/{incident_id}")
def update_incident(incident_id: int, payload: IncidentUpdate, db: Database, user: CurrentUser):
    record = get_record(db, Incident, incident_id, "Incident")
    changes = payload.model_dump(exclude_unset=True)
    if record.status == "CLOSED":
        raise HTTPException(409, "Closed incidents are read-only")

    if payload.status and payload.status != record.status:
        if TRANSITIONS.get(record.status) != payload.status:
            raise HTTPException(409, f"Cannot change {record.status} to {payload.status}")
        if payload.status == "RESOLVED" and not payload.resolution:
            raise HTTPException(422, "Resolution text is required when resolving")
        record_change(db, record, user, "STATUS_CHANGED", f"{record.status} → {payload.status}")
        record.status = payload.status

    if "resolution" in changes and record.status not in {"RESOLVED", "CLOSED"}:
        raise HTTPException(422, "Record the resolution when resolving the incident")
    if payload.resolution is not None and payload.resolution != record.resolution:
        record.resolution = payload.resolution
        record_change(db, record, user, "RESOLUTION_RECORDED", payload.resolution)

    if payload.priority and payload.priority != record.priority:
        record_change(db, record, user, "PRIORITY_CHANGED", f"{record.priority} → {payload.priority}")
        record.priority = payload.priority

    if "assigned_to" in changes and payload.assigned_to != record.assigned_to:
        verify_assignee(db, payload.assigned_to)
        record.assigned_to = payload.assigned_to
        assignee = db.get(User, payload.assigned_to) if payload.assigned_to is not None else None
        record_change(db, record, user, "ASSIGNMENT_CHANGED", assignee.username if assignee else "Unassigned")

    db.commit()
    return incident_data(db, record)


@router.post("/{incident_id}/notes", status_code=201)
def add_note(incident_id: int, payload: IncidentNote, db: Database, user: CurrentUser):
    record = get_record(db, Incident, incident_id, "Incident")
    if record.status == "CLOSED":
        raise HTTPException(409, "Closed incidents are read-only")
    record_change(db, record, user, "NOTE_ADDED", payload.note)
    db.commit()
    return incident_data(db, record)
