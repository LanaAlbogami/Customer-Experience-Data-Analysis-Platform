from sqlalchemy import delete, select, update

from database.connection import SessionLocal
from database.models import Department, Service

#Add a new department to the database and return the created Department object.
def  create_department(department_name: str) -> Department:
    department_name = department_name.strip()
    if not department_name:
        raise ValueError("Department name cannot be empty.")

    with SessionLocal() as session:
        department = Department(
            department_name=department_name
        )

        session.add(department)
        session.commit()
        session.refresh(department)

        return department


#Get a department by its ID. Returns None if not found.
def get_department(department_id : int) -> Department | None:
    with SessionLocal() as session:
        department = session.get(
            Department,
            department_id,
        )  

        return department

#Get all departments. Returns a list of Department objects.
def get_all_departments() -> list[Department]:
    with SessionLocal() as session:
        statement = select(Department).order_by(
            Department.department_name
        )

        departments = session.scalars(statement).all()

        return list(departments)
    
#Update a department's name by its ID. Returns the updated Department object or None if not found.
def update_department(
        department_id: int,
        new_name: str,
) -> Department | None:
    new_name = new_name.strip()

    if not new_name:
        raise ValueError("Department name cannot be empty.")

    with SessionLocal() as session:
        department = session.get(
            Department,
            department_id,
        )

        if department is None:
            return None

        department.department_name = new_name

        session.commit()
        session.refresh(department)

        return department


#Delete a department by its ID and reassign its services to a new department. Returns True if deleted, False if not found. Raises ValueError if the new department is the same as the one being deleted or if the new department does not exist.
def delete_department(
    department_id: int,
    new_department_id: int,
) -> bool:
    if department_id == new_department_id:
        raise ValueError(
            "The new department must be different."
        )

    with SessionLocal() as session:
        department_exists = session.scalar(
            select(Department.department_id).where(
                Department.department_id == department_id
            )
        )

        if department_exists is None:
            return False

        new_department_exists = session.scalar(
            select(Department.department_id).where(
                Department.department_id == new_department_id
            )
        )

        if new_department_exists is None:
            raise ValueError(
                "New department was not found."
            )

        session.execute(
            update(Service)
            .where(
                Service.department_id == department_id
            )
            .values(
                department_id=new_department_id
            )
        )

        session.execute(
            delete(Department).where(
                Department.department_id == department_id
            )
        )

        session.commit()

        return True