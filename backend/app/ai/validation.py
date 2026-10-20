"""Independent schedule validation, separate from every scheduling engine."""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.scheduling import Candidate, PlatformProblem, TrainProblem, conflicts


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    train_id: int | None = None
    platform_id: int | None = None


def validate_assignments(
    trains: list[TrainProblem], platforms: list[PlatformProblem], assignments: dict[int, Candidate], *, horizon_start: int, horizon_end: int, maximum_delay: int
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    train_map = {item.id: item for item in trains}
    platform_map = {item.id: item for item in platforms}
    if set(assignments) != set(train_map):
        missing = sorted(train_map.keys() - assignments.keys())
        for train_id in missing:
            issues.append(ValidationIssue("MISSING_ASSIGNMENT", f"Train {train_map[train_id].identifier} has no platform assignment.", train_id))
    for train_id, assignment in assignments.items():
        train = train_map.get(train_id)
        platform = platform_map.get(assignment.platform_id)
        if train is None or platform is None:
            issues.append(ValidationIssue("UNKNOWN_RESOURCE", "The assignment references a train or platform outside this workspace.", train_id, assignment.platform_id))
            continue
        if not platform.available:
            issues.append(ValidationIssue("PLATFORM_UNAVAILABLE", f"Platform {platform.code} is unavailable.", train_id, platform.id))
        if platform.id not in train.compatible_platform_ids or (train.required_type and train.required_type != platform.platform_type):
            issues.append(ValidationIssue("PLATFORM_INCOMPATIBLE", f"Platform {platform.code} is not compatible with {train.identifier}.", train.id, platform.id))
        if train.length > platform.length:
            issues.append(ValidationIssue("INSUFFICIENT_LENGTH", f"Platform {platform.code} is too short for {train.identifier}.", train.id, platform.id))
        if assignment.start < horizon_start or assignment.end > horizon_end:
            issues.append(ValidationIssue("OUTSIDE_HORIZON", f"{train.identifier} falls outside the plan horizon.", train.id, platform.id))
        if assignment.start < train.arrival + train.recorded_delay:
            issues.append(ValidationIssue("ARRIVAL_VIOLATION", f"{train.identifier} is assigned before its effective arrival.", train.id, platform.id))
        if assignment.end - assignment.start < train.minimum_dwell:
            issues.append(ValidationIssue("DWELL_VIOLATION", f"{train.identifier} does not meet its minimum dwell time.", train.id, platform.id))
        if assignment.end - assignment.start != train.duration:
            issues.append(ValidationIssue("TIMING_VIOLATION", f"{train.identifier} does not preserve its planned occupancy duration.", train.id, platform.id))
        if assignment.delay < 0 or assignment.delay > maximum_delay or assignment.delay != assignment.start - train.arrival:
            issues.append(ValidationIssue("DELAY_VIOLATION", f"{train.identifier} exceeds or misstates the maximum allowed delay.", train.id, platform.id))
    assignment_items = list(assignments.items())
    for index, (left_id, left) in enumerate(assignment_items):
        for right_id, right in assignment_items[index + 1:]:
            if left.platform_id in platform_map and conflicts(left, right, platform_map):
                platform = platform_map[left.platform_id]
                issues.append(ValidationIssue("PLATFORM_OVERLAP", f"{train_map[left_id].identifier} and {train_map[right_id].identifier} overlap on {platform.code}, including its clearance buffer.", left_id, platform.id))
    return issues
