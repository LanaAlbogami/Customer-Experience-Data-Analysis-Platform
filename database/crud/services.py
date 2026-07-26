from sqlalchemy import select

from database.connection import SessionLocal
from database.models import Department, Service

#اضافه خدمه
def create_service(
        service_name: str,
        department_id: int,
) -> Service:

    service_name = service_name.strip()

    if not service_name:
        raise ValueError("Service name cannot be empty.")

    with SessionLocal() as session:

     department = session.get(
        Department,
        department_id,
     )

     if department is None:
        raise ValueError("Department was not found.")

     service = Service(
        service_name=service_name,
        department=department,
     )

     session.add(service)
     session.commit()
     session.refresh(service)

     return service

#ارجع خدمه بناء على الايدي
def get_service(
      service_id: int,
) -> Service | None:

   with SessionLocal() as session:
      service = session.get(
         Service,
         service_id,
      )

      return service

#ارجع كل الخدمات
def get_all_services() -> list[Service]:
   with SessionLocal() as session:

      statement = select(Service).order_by(
         Service.service_name
      )

      services = session.scalars(statement).all()

      return list(services)
   
#اطلع الخدمه بناء على القسم
def get_services_by_department(
    department_id: int,
) -> list[Service]:
    with SessionLocal() as session:
        statement = (
            select(Service)
            .where(Service.department_id == department_id)
            .order_by(Service.service_name)
        )

        services = session.scalars(statement).all()

        return list(services)


#تحديث الخدمه, تغيير اسمها, نقلها لقسم ثاني
def update_service(
      service_id: int,
      new_name: str,
      new_department_id: int,
) -> Service | None:

   new_name = new_name.strip()

   if not new_name:
      raise ValueError("Service name cannot be empty.")

   with SessionLocal() as session:
      service = session.get(
         Service,
         service_id,
      )

      if service is None:
         return None

      department = session.get(
         Department,
         new_department_id,
      )

      if department is None:
         raise ValueError("Department was not found.")

      service.service_name = new_name
      service.department = department

      session.commit()
      session.refresh(service)

      return service    


def delete_service(service_id: int) -> bool:
    with SessionLocal() as session:
        service = session.get(
            Service,
            service_id,
        )

        if service is None:
            return False

        if service.measurement_records:
            raise ValueError(
                "Cannot delete a service that has measurement records."
            )

        session.delete(service)
        session.commit()

        return True