from collections.abc import Iterable


MAX_SCHEDULE_MINUTE = 525_600


def validate_non_blank(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank.")
    return normalized


def validate_minute(value: int, field_name: str) -> int:
    if value < 0:
        raise ValueError(f"{field_name} must be zero or greater.")
    if value > MAX_SCHEDULE_MINUTE:
        raise ValueError(
            f"{field_name} must not exceed {MAX_SCHEDULE_MINUTE} minutes."
        )
    return value


def validate_half_open_interval(start: int, end: int, label: str) -> None:
    validate_minute(start, f"{label} start")
    validate_minute(end, f"{label} end")
    if end <= start:
        raise ValueError(
            f"{label} must be a non-empty half-open interval where end is greater than start."
        )


def validate_unique_values(values: Iterable[str], field_name: str) -> None:
    normalized = [value.casefold() for value in values]
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must not contain duplicate values.")

