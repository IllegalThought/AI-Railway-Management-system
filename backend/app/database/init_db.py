import argparse

from app.database.base import Base
from app.database.seed import seed_demo_data
from app.database.session import SessionLocal, engine
from app import models  # noqa: F401 - imports models into SQLAlchemy metadata


def initialize_database(*, seed: bool = False) -> str:
    Base.metadata.create_all(bind=engine)
    if not seed:
        return "Database schema initialized successfully."

    with SessionLocal() as database:
        result = seed_demo_data(database)
    if result.created:
        return "Database schema initialized and demonstration data created successfully."
    return "Database schema initialized; demonstration data already exists."


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Initialize the RailOps AI database schema."
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Create the idempotent synthetic demonstration dataset.",
    )
    arguments = parser.parse_args()
    print(initialize_database(seed=arguments.seed))


if __name__ == "__main__":
    main()

