from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress, StringConstraints, field_validator

Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
IncidentStatus = Literal["OPEN", "INVESTIGATING", "RESOLVED", "CLOSED"]
AlertStatus = Literal["NEW", "ACKNOWLEDGED", "DISMISSED"]
EventType = Literal["record_access", "authentication", "privileged_action", "data_transfer", "device_activity"]
Source = Literal[
    "vehicle_registration", "driver_licensing", "vehicle_inspection",
    "transport_payments", "administration", "network_infrastructure",
]
Scenario = Literal[
    "normal", "successful_authentication", "legitimate_admin", "normal_transfer",
    "failed_login", "unknown_device", "outside_hours", "large_transfer",
    "privileged_action", "sensitive_access", "combined",
]
Identifier = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64, pattern=r"^[\w.@-]+$")
]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(Input):
    username: Identifier
    password: str = Field(min_length=1, max_length=256)


class EventInput(Input):
    event_id: Identifier | None = None
    event_type: EventType
    source_system: Source
    username: Identifier
    device_id: Identifier
    source_ip: IPvAnyAddress
    event_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    failed_login_count: int = Field(default=0, ge=0, le=10_000)
    requests_per_minute: float = Field(default=0, ge=0, le=100_000, allow_inf_nan=False)
    data_transfer_mb: float = Field(default=0, ge=0, le=1_000_000, allow_inf_nan=False)
    outside_working_hours: bool = False
    unknown_device: bool = False
    unusual_location: bool = False
    privileged_action: bool = False
    suspicious_privileged_action: bool = False
    sensitive_record_access: bool = False
    sensitive_records_accessed: int = Field(default=0, ge=0, le=1_000_000)

    @field_validator("event_timestamp")
    @classmethod
    def normalise_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Include the timestamp time zone")
        return value.astimezone(timezone.utc)


class AlertUpdate(Input):
    status: AlertStatus


class IncidentInput(Input):
    alert_id: int = Field(gt=0)
    title: Title
    priority: Severity | None = None
    assigned_to: int | None = Field(default=None, gt=0)


class IncidentUpdate(Input):
    status: IncidentStatus | None = None
    priority: Severity | None = None
    assigned_to: int | None = Field(default=None, gt=0)
    resolution: Note | None = None


class IncidentNote(Input):
    note: Note


class SimulationInput(Input):
    scenario: Scenario
    source_system: Source | None = None
    count: int = Field(default=1, ge=1, le=25)


class LiveSimulationInput(Input):
    scenario: Scenario = "normal"
    source_system: Source | None = None
    interval_seconds: int = Field(default=5, ge=2, le=60)


class SimulationReset(Input):
    confirmation: Literal["RESET SYNTHETIC DATA"]
