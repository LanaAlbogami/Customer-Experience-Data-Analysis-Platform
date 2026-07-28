from connection import Base, engine
import models

def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

if __name__ == "__main__":
    create_tables()

    