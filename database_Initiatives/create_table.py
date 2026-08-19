from database_Initiatives.connection import engine, Base
from database_Initiatives.models import Section, Product, Status, Action

def init_db():
    """Create all tables defined under Base metadata in the connected MySQL database."""
    # Ensure database exists first in MySQL Workbench, then run this to create tables
    Base.metadata.create_all(bind=engine)
    print("Tables (Sections, Products, Status, Actions) created successfully!")

if __name__ == "__main__":
    init_db()