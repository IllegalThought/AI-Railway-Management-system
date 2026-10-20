from enum import StrEnum


class SessionStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class PlanStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    APPLIED = "applied"
    INVALID = "invalid"
    ARCHIVED = "archived"


class TrainStatus(StrEnum):
    SCHEDULED = "scheduled"
    DELAYED = "delayed"
    CANCELLED = "cancelled"


class SimulationRunStatus(StrEnum):
    PAUSED = "paused"
    RUNNING = "running"


class IncidentType(StrEnum):
    ARRIVAL_DELAY = "train_arrival_delay"
    DEPARTURE_DELAY = "train_departure_delay"
    PLATFORM_CLOSURE = "platform_closure"
    TRACK_BLOCKAGE = "track_blockage"
    JUNCTION_CLOSURE = "junction_closure"
    NEW_TRAIN_REQUEST = "new_train_request"


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
    SIMULATION_STARTED = "simulation_started"
    SIMULATION_PAUSED = "simulation_paused"
    SIMULATION_STEPPED = "simulation_stepped"
    SIMULATION_RESET = "simulation_reset"
    REPLAN_CREATED = "replan_created"

