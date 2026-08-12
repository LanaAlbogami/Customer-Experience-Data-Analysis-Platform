import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

required_variables = [
    "DB_HOST",
    "DB_PORT",
    "DB_USER",
    "DB_PASSWORD",
    "DB_NAME_INDIVIDUALS",
]

missing_variables = [
    variable
    for variable in required_variables
    if not os.getenv(variable)
]

if missing_variables:
    raise ValueError(
        "Missing environment variables: "
        + ", ".join(missing_variables)
    )

database_url = URL.create(
    drivername="mysql+pymysql",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", "3306")),
    database=os.getenv("DB_NAME_INDIVIDUALS"),
)

# Creates the database engine used to connect to the individuals database.
engine = create_engine(
    database_url,
    pool_pre_ping=True,
    echo=False,
)

# Creates reusable database sessions for reading and modifying individual records.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    # Base class inherited by all SQLAlchemy models in the individuals database.
    pass


def test_connection() -> None:
    """Tests whether the application can successfully connect to the individuals database."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        print("Individuals database connection successful.")

    except Exception as error:
        print("Individuals database connection failed:")
        print(error)


if __name__ == "__main__":
    test_connection()