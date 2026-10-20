from app.models import SchedulingPlan, TrainAssignment
from app.models.enums import PlanStatus
from app.schemas.railway import PlatformUpdate, TrainUpdate
from app.services.records import (
    create_simulation_session,
    list_platforms,
    list_trains,
    update_platform,
    update_train,
)
from app.services.scenarios import restore_scenario


def test_train_and_platform_changes_invalidate_ready_plans(database) -> None:
    simulation_session = create_simulation_session(database, name="Plan validation")
    restore_scenario(database, simulation_session, "normal-traffic")
    train = list_trains(database, session_id=simulation_session.id)[0]
    platform = list_platforms(database, session_id=simulation_session.id)[0]
    plan = SchedulingPlan(
        session_id=simulation_session.id,
        name="Ready plan",
        status=PlanStatus.READY,
        horizon_start_minute=0,
        horizon_end_minute=1_440,
    )
    assignment = TrainAssignment(
        plan=plan,
        train_id=train.id,
        platform_id=platform.id,
        occupancy_start_minute=train.arrival_minute,
        occupancy_end_minute=train.departure_minute,
    )
    database.add_all([plan, assignment])
    database.commit()

    _, train_validation_required = update_train(
        database,
        simulation_session=simulation_session,
        train_id=train.id,
        data=TrainUpdate(priority=2),
    )
    database.refresh(plan)
    assert train_validation_required is True
    assert plan.status == PlanStatus.DRAFT

    plan.status = PlanStatus.READY
    database.commit()
    _, platform_validation_required = update_platform(
        database,
        simulation_session=simulation_session,
        platform_id=platform.id,
        data=PlatformUpdate(
            is_available=False,
            unavailable_reason="Validation test closure",
        ),
    )
    database.refresh(plan)
    assert platform_validation_required is True
    assert plan.status == PlanStatus.DRAFT
