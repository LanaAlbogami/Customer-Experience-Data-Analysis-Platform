import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text 
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Load environment variables from .env file
load_dotenv()

# List of environment variables that must be set for the app to work
required_variables = [
    "DB_HOST",
    "DB_PORT",
    "DB_USER",
    "DB_PASSWORD",
    "DB_NAME",
]

# Check which required variables are missing or empty
missing_variables = [
    variable
    for variable in required_variables
    if not os.getenv(variable)
]

# Stop the program early if any required variable is missing
if missing_variables:
    raise ValueError(
        "Missing environment variables: "
        + ", ".join(missing_variables)
    )

# Build the database connection URL from the environment variables
database_url = URL.create(
    drivername="mysql+pymysql",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", "3306")),
    database=os.getenv("DB_NAME"),
)

# Create the engine, which manages the connection to the database
engine = create_engine(
    database_url,
    pool_pre_ping=True,
    echo=False,
)

# Factory for creating new database sessions
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


# Base class that all database models (tables) will inherit from
class Base(DeclarativeBase):
    pass

# Try connecting to the database and run a simple query to confirm it works
def test_connection() -> None:
    try:
        # Open a connection and run a basic query
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        print("Database connection successful.")

    # If anything goes wrong, print the error instead of crashing
    except Exception as error:
        print("Database connection failed:")
        print(error)

# Run the connection test only when this file is executed directly
if __name__ == "__main__":
    test_connection()