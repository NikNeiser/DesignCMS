import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import SessionDep, CurrentEmployee
from app.models import User, EmployeePublic, EmployeesPublic, UserCompanyLink, UserCompanyLinkCreate, Message, CompanyRole

router = APIRouter(prefix="/{company_id}/employee", tags=["employee"])


@router.get("/", response_model=EmployeesPublic)
def read_employees(
    session: SessionDep, company_id: uuid.UUID, current_employee: CurrentEmployee, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve Company employees.
    """

    count_statement = (
        select(func.count())
        .select_from(UserCompanyLink)
        .where(UserCompanyLink.company_id == company_id)
    )
    count = session.exec(count_statement).one()

    results = session.exec(
        select(User.id,
               User.email,
               User.full_name,
               UserCompanyLink.role.label("role"))
        .join(UserCompanyLink)
        .where(UserCompanyLink.company_id == company_id).offset(skip)
        .limit(limit)
    ).all()

    employees = [EmployeePublic(**row._mapping) for row in results]

    return EmployeesPublic(data=employees, count=count)


@router.post("/", response_model=UserCompanyLink)
def add_employee(
    *, session: SessionDep, company_id: uuid.UUID, current_employee: CurrentEmployee, employee_in: UserCompanyLinkCreate
) -> Any:
    """
    Add employee.
    """
    if not current_employee.role or current_employee.role == CompanyRole.reader:
        raise HTTPException(
            status_code=400, detail="Not enough permissions")
    if current_employee.role.value < employee_in.role.value:
        raise HTTPException(
            status_code=400, detail="You can't add employee role higher than your own")

    employee = UserCompanyLink.model_validate(
        employee_in, update={"company_id": company_id})
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


@router.put("/", response_model=UserCompanyLink)
def update_employee(
    *, session: SessionDep, company_id: uuid.UUID, current_employee: CurrentEmployee, employee_in: UserCompanyLinkCreate
) -> Any:
    """
    Add/Update employee.
    """
    if not current_employee.role or current_employee.role == CompanyRole.reader:
        raise HTTPException(
            status_code=400, detail="Not enough permissions")
    if current_employee.role.value < employee_in.role.value:
        raise HTTPException(
            status_code=400, detail="You can't add employee role higher than your own")\

    employee = session.exec(
        select(UserCompanyLink)
        .where(UserCompanyLink.company_id == company_id,
               UserCompanyLink.user_id == employee_in.user_id)
    ).first()

    if not employee:
        employee = UserCompanyLink.model_validate(
            employee_in, update={"company_id": company_id})

    if employee.role.value >= role.value:
        raise HTTPException(
            status_code=400, detail="You can't update employee with the same or higher role than yours")

    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


@router.delete("/{id}")
def delete_employee(
    session: SessionDep, company_id: uuid.UUID, current_employee: CurrentEmployee, id: uuid.UUID
) -> Message:
    """
    Delete an employee.
    """

    if not current_employee.role or current_employee.role == CompanyRole.reader:
        raise HTTPException(
            status_code=400, detail="Not enough permissions")

    employee = session.exec(
        select(UserCompanyLink)
        .where(UserCompanyLink.company_id == company_id,
               UserCompanyLink.user_id == id)
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404, detail="Didn't find this user among the employees")

    if employee.role.value >= current_employee.role.value:
        raise HTTPException(
            status_code=400, detail="You can't delete employee with the same or higher role than yours")

    session.delete(employee)
    session.commit()
    return Message(message="Employee deleted successfully")
