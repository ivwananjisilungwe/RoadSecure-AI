from dataclasses import dataclass

import numpy as np

from .features import feature_vector

SOURCE_SYSTEMS = (
    "vehicle_registration",
    "driver_licensing",
    "vehicle_inspection",
    "transport_payments",
    "administration",
    "network_infrastructure",
)

# These are fictional event records. Generating them does not perform any network operations.
SCENARIOS = {
    "normal": ("record_access", {"sensitive_record_access": True, "sensitive_records_accessed": 3}),
    "successful_authentication": ("authentication", {}),
    "legitimate_admin": ("privileged_action", {"privileged_action": True}),
    "normal_transfer": ("data_transfer", {"data_transfer_mb": 8.0}),
    "failed_login": ("authentication", {"failed_login_count": 7}),
    "unknown_device": ("device_activity", {"unknown_device": True}),
    "outside_hours": ("record_access", {"outside_working_hours": True}),
    "large_transfer": ("data_transfer", {"data_transfer_mb": 120.0}),
    "privileged_action": (
        "privileged_action",
        {"privileged_action": True, "suspicious_privileged_action": True},
    ),
    "sensitive_access": (
        "record_access",
        {"sensitive_record_access": True, "sensitive_records_accessed": 90},
    ),
    "combined": (
        "privileged_action",
        {
            "failed_login_count": 9,
            "requests_per_minute": 180.0,
            "data_transfer_mb": 120.0,
            "outside_working_hours": True,
            "unknown_device": True,
            "unusual_location": True,
            "privileged_action": True,
            "suspicious_privileged_action": True,
            "sensitive_record_access": True,
            "sensitive_records_accessed": 90,
        },
    ),
}

ANOMALY_CATEGORIES = (
    "failed_login", "unknown_device", "outside_hours", "large_transfer",
    "privileged_action", "sensitive_access", "combined", "traffic",
)


def simulate(scenario: str, source_system: str | None = None) -> dict:
    event_type, indicators = SCENARIOS[scenario]
    options = {
        "record_access": "vehicle_registration",
        "authentication": "driver_licensing",
        "privileged_action": "administration",
        "data_transfer": "transport_payments",
        "device_activity": "network_infrastructure",
    }
    source_system = source_system or options[event_type]
    index = SOURCE_SYSTEMS.index(source_system) + 1
    return {
        "event_type": event_type,
        "source_system": source_system,
        "username": f"demo-operator-{index:02d}",
        "device_id": f"DEMO-TERM-{index:02d}",
        "source_ip": f"192.0.2.{index}",
        "failed_login_count": 0,
        "requests_per_minute": 31.0,
        "data_transfer_mb": 3.0,
        "outside_working_hours": False,
        "unknown_device": False,
        "unusual_location": False,
        "privileged_action": False,
        "suspicious_privileged_action": False,
        "sensitive_record_access": False,
        "sensitive_records_accessed": 0,
        **indicators,
    }


@dataclass
class Dataset:
    events: list[dict]
    labels: np.ndarray
    seed: int

    @property
    def features(self) -> np.ndarray:
        return np.stack([feature_vector(event) for event in self.events])


def _normal(rng: np.random.Generator) -> dict:
    kind = str(rng.choice(
        ("normal", "successful_authentication", "legitimate_admin", "normal_transfer"),
        p=(0.47, 0.31, 0.06, 0.16),
    ))
    event = simulate(kind, str(rng.choice(SOURCE_SYSTEMS)))
    event.update(
        failed_login_count=int(rng.poisson(0.65)),
        requests_per_minute=float(np.clip(rng.normal(39, 17), 1, 170)),
        data_transfer_mb=float(rng.lognormal(1.35 if kind == "normal_transfer" else 0.9, 1.05)),
        outside_working_hours=bool(rng.random() < 0.06),
        unknown_device=bool(rng.random() < 0.025),
        unusual_location=bool(rng.random() < 0.045),
        sensitive_records_accessed=int(rng.poisson(8)) if kind == "normal" else 0,
    )
    return event


def _anomalous(event: dict, rng: np.random.Generator) -> None:
    category = str(rng.choice(ANOMALY_CATEGORIES))
    if category == "failed_login":
        event["failed_login_count"] = int(rng.integers(2, 13))
    elif category == "unknown_device":
        event["unknown_device"] = bool(rng.random() < 0.80)
        event["unusual_location"] = bool(rng.random() < 0.55)
    elif category == "outside_hours":
        event["outside_working_hours"] = bool(rng.random() < 0.85)
        event["unusual_location"] = bool(rng.random() < 0.22)
    elif category == "large_transfer":
        event["data_transfer_mb"] = float(rng.lognormal(3.4, 1.15))
    elif category == "privileged_action":
        event["privileged_action"] = True
        event["suspicious_privileged_action"] = bool(rng.random() < 0.65)
    elif category == "sensitive_access":
        event["sensitive_record_access"] = True
        event["sensitive_records_accessed"] = int(rng.integers(7, 85))
    elif category == "combined":
        event.update(failed_login_count=int(rng.integers(3, 13)), unknown_device=True)
        event["data_transfer_mb"] = float(rng.lognormal(3.2, 1.1))
    elif category == "traffic":
        event["requests_per_minute"] = float(np.clip(rng.normal(118, 45), 18, 300))


def generate_dataset(count: int, seed: int, anomaly_fraction: float = 0.0) -> Dataset:
    rng = np.random.default_rng(seed)
    labels = np.zeros(count, dtype=np.int8)
    labels[:round(count * anomaly_fraction)] = 1
    rng.shuffle(labels)
    events = []
    for label in labels:
        event = _normal(rng)
        if label:
            _anomalous(event, rng)
        events.append(event)
    return Dataset(events, labels, seed)
