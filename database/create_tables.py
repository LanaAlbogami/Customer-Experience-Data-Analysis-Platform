from database.connection import Base, engine
import database.models

def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

if __name__ == "__main__":
    create_tables()

    