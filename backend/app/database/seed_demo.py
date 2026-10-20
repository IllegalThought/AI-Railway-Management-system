"""Create the optional shared demonstration workspace without changing schema."""

from app.database.seed import seed_demo_data
from app.database.session import SessionLocal


def seed_production_demo() -> str:
    """Idempotently create the named demo workspace after migrations have run."""

    with SessionLocal() as database:
        result = seed_demo_data(database)
    if result.created:
        return "Demonstration data created successfully."
    return "Demonstration data already exists; no records were changed."


def main() -> None:
    print(seed_production_demo())


if __name__ == "__main__":
    main()
