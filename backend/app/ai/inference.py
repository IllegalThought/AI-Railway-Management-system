"""Small explainable forward-chaining engine for movement decisions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Fact:
    predicate: str
    arguments: tuple[str, ...]

    def render(self) -> str:
        return f"{self.predicate}({', '.join(self.arguments)})"


@dataclass(frozen=True)
class Rule:
    name: str
    requires: frozenset[str]
    forbids: frozenset[str]
    conclusion: str


@dataclass(frozen=True)
class InferenceResult:
    indicator: str
    decision: str
    facts: tuple[Fact, ...]
    evaluated_rules: tuple[str, ...]
    explanation: str


RULES = (
    Rule("blocked-resource", frozenset({"ResourceBlocked"}), frozenset(), "MovementBlocked"),
    Rule("occupied-track", frozenset({"TrackOccupied"}), frozenset(), "MovementBlocked"),
    Rule("all-modeled-checks", frozenset({"PlatformOccupied", "PlatformCompatible", "RouteReserved"}), frozenset({"ResourceBlocked", "TrackOccupied", "MovementBlocked"}), "MovementAllowed"),
)


def forward_chain(initial_facts: set[Fact]) -> tuple[set[Fact], list[str]]:
    facts = set(initial_facts)
    evaluated: list[str] = []
    changed = True
    while changed:
        changed = False
        predicates = {fact.predicate for fact in facts}
        for rule in RULES:
            evaluated.append(f"{rule.name}: requires {', '.join(sorted(rule.requires)) or 'none'}; forbids {', '.join(sorted(rule.forbids)) or 'none'}")
            if rule.requires <= predicates and not (rule.forbids & predicates) and rule.conclusion not in predicates:
                subject = next(iter(facts)).arguments[0] if facts else "unknown"
                facts.add(Fact(rule.conclusion, (subject,)))
                changed = True
    return facts, evaluated


def infer_movement(
    train_identifier: str,
    platform_code: str | None,
    *,
    platform_occupied: bool | None,
    platform_compatible: bool | None,
    route_reserved: bool | None,
    track_occupied: bool = False,
    blocked_resource: str | None = None,
) -> InferenceResult:
    facts: set[Fact] = set()
    if platform_occupied:
        facts.add(Fact("PlatformOccupied", (train_identifier, platform_code or "unknown")))
    if platform_compatible:
        facts.add(Fact("PlatformCompatible", (train_identifier, platform_code or "unknown")))
    if route_reserved:
        facts.add(Fact("RouteReserved", (train_identifier,)))
    if track_occupied:
        facts.add(Fact("TrackOccupied", (train_identifier,)))
    if blocked_resource:
        facts.add(Fact("ResourceBlocked", (blocked_resource,)))
    derived, evaluated = forward_chain(facts)
    evaluated = list(dict.fromkeys(evaluated))
    predicates = {fact.predicate for fact in derived}
    mandatory_known = platform_occupied is not None and platform_compatible is not None and route_reserved is not None
    if "MovementBlocked" in predicates:
        indicator, decision = "RED", "MovementBlocked"
    elif mandatory_known and "MovementAllowed" in predicates:
        indicator, decision = "GREEN", "MovementAllowed"
    else:
        indicator, decision = "YELLOW", "MovementBlocked"
    fact_text = "; ".join(fact.render() for fact in sorted(derived)) or "No movement facts were available."
    if indicator == "GREEN":
        summary = "All mandatory platform, compatibility, and route-reservation facts were established."
    elif indicator == "RED":
        summary = "A blocked or occupied modeled resource prevents movement."
    else:
        summary = "Movement remains pending because mandatory modeled information is missing."
    rule_text = "; ".join(evaluated)
    return InferenceResult(indicator, decision, tuple(sorted(derived)), tuple(evaluated), f"{summary} Evaluated facts: {fact_text}. Evaluated rules: {rule_text}.")
