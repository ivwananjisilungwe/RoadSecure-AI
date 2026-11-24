from collections.abc import Callable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    condition: str
    contribution: int
    evidence: tuple[str, ...]
    matches: Callable[[Mapping], bool]


RULES = (
    Rule("RS-01", "Repeated failed logins", "At least five failed logins in the event aggregate",
         25, ("failed_login_count",), lambda e: e.get("failed_login_count", 0) >= 5),
    Rule("RS-02", "Unusual access time", "Event marked as outside authorized working hours",
         15, ("outside_working_hours",), lambda e: bool(e.get("outside_working_hours"))),
    Rule("RS-03", "Unknown device", "Event marked as using an unrecognized device",
         20, ("unknown_device",), lambda e: bool(e.get("unknown_device"))),
    Rule("RS-04", "Large data transfer", "Event transfer exceeds 40 MB",
         25, ("data_transfer_mb",), lambda e: e.get("data_transfer_mb", 0) > 40),
    Rule("RS-05", "Suspicious privileged action", "Privileged event with a suspicious-context indicator",
         35, ("privileged_action", "suspicious_privileged_action"),
         lambda e: bool(e.get("privileged_action") and e.get("suspicious_privileged_action"))),
    Rule("RS-06", "Unusual sensitive-record access", "Event marks sensitive access involving at least 30 records",
         30, ("sensitive_record_access", "sensitive_records_accessed"),
         lambda e: bool(e.get("sensitive_record_access")) and e.get("sensitive_records_accessed", 0) >= 30),
)


def evaluate_rules(event: Mapping) -> list[dict]:
    return [
        {
            "rule_id": rule.id,
            "name": rule.name,
            "condition": rule.condition,
            "explanation": rule.condition,
            "risk_contribution": rule.contribution,
            "evidence": {key: event.get(key) for key in rule.evidence},
        }
        for rule in RULES
        if rule.matches(event)
    ]
