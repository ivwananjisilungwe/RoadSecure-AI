from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, ForeignKey, JSON, String, Text, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role in ('ADMIN', 'ANALYST')"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(10), default="ADMIN")


class LoginSession(Base):
    __tablename__ = "login_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[int] = mapped_column(index=True)


class SecurityEvent(Base):
    __tablename__ = "security_events"
    __table_args__ = (CheckConstraint("severity in ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True)
    event_type: Mapped[str] = mapped_column(String(32))
    source_system: Mapped[str] = mapped_column(String(32), index=True)
    username: Mapped[str] = mapped_column(String(64))
    device_id: Mapped[str] = mapped_column(String(64))
    source_ip: Mapped[str] = mapped_column(String(45))
    event_timestamp: Mapped[str] = mapped_column(String(40))
    raw_features: Mapped[dict] = mapped_column(JSON)
    detection_result: Mapped[dict] = mapped_column(JSON)
    severity: Mapped[str] = mapped_column(String(8), index=True)
    created_at: Mapped[str] = mapped_column(String(40), default=utc_now, index=True)


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint("status in ('NEW', 'ACKNOWLEDGED', 'DISMISSED')"),
        CheckConstraint("severity in ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("security_events.id"), unique=True)
    severity: Mapped[str] = mapped_column(String(8), index=True)
    status: Mapped[str] = mapped_column(String(14), default="NEW", index=True)
    created_at: Mapped[str] = mapped_column(String(40), default=utc_now)


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint("status in ('OPEN', 'INVESTIGATING', 'RESOLVED', 'CLOSED')"),
        CheckConstraint("priority in ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"), unique=True)
    title: Mapped[str] = mapped_column(String(120))
    priority: Mapped[str] = mapped_column(String(8))
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(14), default="OPEN", index=True)
    resolution: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40), default=utc_now)
    updated_at: Mapped[str] = mapped_column(String(40), default=utc_now)
    revision: Mapped[int] = mapped_column(default=1)

    __mapper_args__ = {"version_id_col": revision}


class IncidentHistory(Base):
    __tablename__ = "incident_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(24))
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40), default=utc_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(32))
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40), default=utc_now)


def initialise_database(directory):
    engine = create_engine(f"sqlite:///{directory / 'roadsecure.sqlite3'}")

    @event.listens_for(engine, "connect")
    def sqlite_pragmas(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine, sessionmaker(engine, expire_on_commit=False)
