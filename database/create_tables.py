from database.connection import Base, engine
import database.models

# Create all tables in the database based on the models defined in database.models
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

# Run the create_tables function only when this file is executed directly
if __name__ == "__main__":
    create_tables()