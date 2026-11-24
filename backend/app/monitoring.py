from collections import Counter
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .models import Alert, Incident, SecurityEvent
from .schemas import EventInput


def get_record(db, model, record_id, name):
    record = db.get(model, record_id)
    if record is None:
        raise HTTPException(404, f"{name} not found")
    return record


def save_event(db: Session, detector, payload: EventInput):
    raw = payload.model_dump(mode="json", exclude={"event_id"})
    prediction = detector.detect(raw)
    fields = {
        field: raw.pop(field)
        for field in ("event_type", "source_system", "username", "device_id", "source_ip", "event_timestamp")
    }
    record = SecurityEvent(
        **fields,
        event_id=payload.event_id or str(uuid4()),
        raw_features=raw,
        severity=prediction["severity"],
        detection_result=prediction,
    )
    db.add(record)
    db.flush()
    if prediction["should_alert"]:
        db.add(Alert(event_id=record.id, severity=record.severity))
    return record


def event_data(record):
    return {
        "id": record.id,
        "event_id": record.event_id,
        "event_type": record.event_type,
        "source_system": record.source_system,
        "username": record.username,
        "device_id": record.device_id,
        "source_ip": record.source_ip,
        "event_timestamp": record.event_timestamp,
        **record.raw_features,
        "detection_result": record.detection_result,
        "anomaly_score": record.detection_result["anomaly_score"],
        "risk_score": record.detection_result["risk_score"],
        "severity": record.severity,
        "status": record.detection_result["detection_result"],
        "created_at": record.created_at,
    }


def alert_data(alert, event):
    return {
        "id": alert.id,
        "event_id": alert.event_id,
        "severity": alert.severity,
        "status": alert.status,
        "created_at": alert.created_at,
        "event": event_data(event),
    }


def search_events(query, text):
    columns = (SecurityEvent.event_id, SecurityEvent.username, SecurityEvent.device_id, SecurityEvent.source_ip)
    return query.where(or_(*(column.icontains(text, autoescape=True) for column in columns)))


def aggregate_dashboard(db: Session):
    rule_frequencies = Counter()
    severity_distribution = Counter({key: 0 for key in ("LOW", "MEDIUM", "HIGH", "CRITICAL")})
    source_counts = Counter()
    detection_methods = Counter({key: 0 for key in ("rules", "ml", "hybrid", "normal")})
    today = datetime.now(timezone.utc).date()
    trend = {(today - timedelta(days=days)).isoformat(): 0 for days in range(6, -1, -1)}
    anomalous = 0
    for severity, source, created_at, detection in db.execute(select(
        SecurityEvent.severity, SecurityEvent.source_system,
        SecurityEvent.created_at, SecurityEvent.detection_result,
    )):
        severity_distribution[severity] += 1
        source_counts[source] += 1
        if created_at[:10] in trend:
            trend[created_at[:10]] += 1

        rules = detection["rule_results"]
        rule_frequencies.update(rule["rule_id"] for rule in rules)
        has_rules = bool(rules)
        has_ml = detection["ml_prediction"] == "anomaly"
        if has_rules and has_ml:
            detection_methods["hybrid"] += 1
        elif has_rules:
            detection_methods["rules"] += 1
        elif has_ml:
            detection_methods["ml"] += 1
        else:
            detection_methods["normal"] += 1
        anomalous += detection["detection_result"] == "suspicious"

    alert_counts = dict(db.execute(select(Alert.severity, func.count()).group_by(Alert.severity)).all())
    alerts_by_source = dict(db.execute(
        select(SecurityEvent.source_system, func.count(Alert.id)).join(Alert).group_by(SecurityEvent.source_system)
    ).all())
    incident_counts = dict(db.execute(select(Incident.status, func.count()).group_by(Incident.status)).all())
    recent_events = db.scalars(select(SecurityEvent).order_by(SecurityEvent.id.desc()).limit(8))
    recent_alerts = db.execute(
        select(Alert, SecurityEvent).join(SecurityEvent).order_by(Alert.id.desc()).limit(8)
    )
    return {
        "total_events": sum(severity_distribution.values()),
        "total_alerts": sum(alert_counts.values()),
        "critical_alerts": alert_counts.get("CRITICAL", 0),
        "open_incidents": incident_counts.get("OPEN", 0) + incident_counts.get("INVESTIGATING", 0),
        "resolved_incidents": incident_counts.get("RESOLVED", 0) + incident_counts.get("CLOSED", 0),
        "anomalous_events": anomalous,
        "events_over_time": [{"date": date, "count": count} for date, count in trend.items()],
        "severity_distribution": dict(severity_distribution),
        "events_by_source": dict(source_counts),
        "alerts_by_source": alerts_by_source,
        "alert_severity_distribution": {key: alert_counts.get(key, 0) for key in severity_distribution},
        "incidents_by_status": {key: incident_counts.get(key, 0) for key in ("OPEN", "INVESTIGATING", "RESOLVED", "CLOSED")},
        "rule_frequencies": dict(rule_frequencies),
        "detection_methods": dict(detection_methods),
        "recent_events": [event_data(record) for record in recent_events],
        "recent_alerts": [alert_data(alert, event) for alert, event in recent_alerts],
    }
