from app.models import Platform, Train
from app.schemas.railway import PlatformResponse, TrainResponse


def train_response(train: Train) -> TrainResponse:
    return TrainResponse(
        id=train.id,
        identifier=train.identifier,
        priority=train.priority,
        arrival_minute=train.arrival_minute,
        departure_minute=train.departure_minute,
        minimum_dwell_minutes=train.minimum_dwell_minutes,
        length_meters=train.length_meters,
        required_platform_type=train.required_platform_type,
        compatible_platform_codes=sorted(
            item.platform.code for item in train.compatible_platforms
        ),
        service_status=train.service_status,
        delay_minutes=train.delay_minutes,
        origin_node_code=train.origin_node_code,
        destination_node_code=train.destination_node_code,
        created_at=train.created_at,
        updated_at=train.updated_at,
    )


def platform_response(platform: Platform) -> PlatformResponse:
    return PlatformResponse(
        id=platform.id,
        code=platform.code,
        platform_type=platform.platform_type,
        length_meters=platform.length_meters,
        clearance_minutes=platform.clearance_minutes,
        is_available=platform.is_available,
        unavailable_reason=platform.unavailable_reason,
        compatible_train_count=len(platform.compatible_trains),
        created_at=platform.created_at,
        updated_at=platform.updated_at,
    )
