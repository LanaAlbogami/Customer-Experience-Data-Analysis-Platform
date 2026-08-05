from database_individuals.connection import Base, engine
import database_individuals.models


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    print("Individuals database tables created successfully.")


if __name__ == "__main__":
    create_tables()