from enum import StrEnum


class SessionStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class PlanStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    ARCHIVED = "archived"


class TrainStatus(StrEnum):
    SCHEDULED = "scheduled"
    DELAYED = "delayed"
    CANCELLED = "cancelled"


class IncidentSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(StrEnum):
    OPEN = "open"
    MONITORING = "monitoring"
    RESOLVED = "resolved"


class EventType(StrEnum):
    SESSION_CREATED = "session_created"
    TRAIN_REGISTERED = "train_registered"
    PLAN_CREATED = "plan_created"
    ASSIGNMENT_CREATED = "assignment_created"
    INCIDENT_REPORTED = "incident_reported"
    SCENARIO_RESTORED = "scenario_restored"
    TRAIN_UPDATED = "train_updated"
    TRAIN_DELETED = "train_deleted"
    PLATFORM_UPDATED = "platform_updated"

