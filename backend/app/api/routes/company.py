import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select, delete
from sqlalchemy.orm import noload
from app import crud

from app.api.deps import CurrentUser, SessionDep, CurrentEmployee
from app.models import (Company,
                        EmployeesPublic,
                        EmployeePublic,
                        CompanyPublic,
                        CompanyCreate,
                        CompanyUpdate,
                        UserCompanyLink,
                        CompanyRole,
                        Message,
                        User,
                        Tag,
                        TagsPublic)

router = APIRouter(prefix="/company", tags=["company"])


@router.post("/", response_model=CompanyPublic)
def create_company(
    *, session: SessionDep, current_user: CurrentUser, company_in: CompanyCreate
) -> Any:
    """
    Create new Company.
    """
    company = Company.model_validate(company_in)
    if crud.check_company_name_exist(session=session, name=company.title):
        raise HTTPException(
            status_code=400, detail=f"Company named {company_in.title} already exists")

    link = UserCompanyLink(
        company_id=company.id,
        user_id=current_user.id,
        role=CompanyRole.owner
    )
    session.add(company)
    session.add(link)
    session.commit()
    session.refresh(company)
    return company


@router.get("/{company_id}", response_model=CompanyPublic)
def read_company(session: SessionDep, company_id: uuid.UUID, current_employee: CurrentEmployee) -> Any:
    """
    Get Company by ID.
    """
    company = session.get(Company, company_id)
    return company


@router.get("/{company_id}/employees", response_model=EmployeesPublic)
def read_company_employees(session: SessionDep, company_id: uuid.UUID, current_employee: CurrentEmployee, skip: int = 0, limit: int = 100) -> Any:
    """
    Get Company Employees.
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


@router.get("/{company_id}/tags", response_model=TagsPublic)
def read_company_tags(session: SessionDep, company_id: uuid.UUID, current_employee: CurrentEmployee) -> Any:
    """
    Get Company Tags.
    """

    results = session.exec(
        select(Tag)
        .where(Tag.company_id == company_id)
        .options(
            noload(Tag.company),
            noload(Tag.design_items)
        )
    ).all()

    return TagsPublic(data=results)


@router.put("/{company_id}", response_model=CompanyPublic)
def update_company(
    *,
    session: SessionDep,
    company_id: uuid.UUID,
    company_in: CompanyUpdate,
    current_employee: CurrentEmployee
) -> Any:
    """
    Update an company.
    """

    if not current_employee.role or current_employee.role != CompanyRole.owner:
        raise HTTPException(
            status_code=400, detail="Not enough permissions")

    company = session.exec(
        select(Company)
        .where(Company.id == company_id)
        .options(
            noload(Company.employee),
            noload(Company.design_items),
            noload(Company.tags)
        )
    ).first()

    if company_in.title and company_in.title.lower() != company.title.lower() and crud.check_company_name_exist(session=session, name=company_in.title):
        raise HTTPException(
            status_code=400, detail=f"Company named \"{company_in.title}\" already exists")

    update_dict = company_in.model_dump(exclude_unset=True)
    company.sqlmodel_update(update_dict)
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


@router.delete("/{company_id}")
def delete_company(
    session: SessionDep, company_id: uuid.UUID, current_employee: CurrentEmployee
) -> Message:
    """
    Delete an Company.
    """
    if not current_employee.role or current_employee.role != CompanyRole.owner:
        raise HTTPException(
            status_code=400, detail="Not enough permissions")

    statement = delete(Company).where(Company.id == id)
    session.exec(statement)
    session.commit()
    return Message(message="Company deleted successfully")
