import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import func, select, exists, or_, delete
from sqlalchemy.orm import noload, selectinload
from app import crud

from app.api.deps import CurrentUser, SessionDep, CompanyRoleDep
from app.models import Company, CompanyStatus, CompanysPublic, CompanyPublic, CompanyCreate, CompanyUpdate, UserCompanyLink, CompanyRole, Message, User

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
def read_company(session: SessionDep, company_id: uuid.UUID, role: CompanyRoleDep) -> Any:
    """
    Get Company by ID.
    """
    company = session.get(Company, company_id)
    return company


@router.put("/{company_id}", response_model=CompanyPublic)
def update_company(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    company_id: uuid.UUID,
    company_in: CompanyUpdate,
    role: CompanyRoleDep
) -> Any:
    """
    Update an company.
    """

    if not role or role != CompanyRole.owner:
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
    session: SessionDep, current_user: CurrentUser, company_id: uuid.UUID, role: CompanyRoleDep
) -> Message:
    """
    Delete an Company.
    """
    if not role or role != CompanyRole.owner:
        raise HTTPException(
            status_code=400, detail="Not enough permissions")

    statement = delete(Company).where(Company.id == id)
    session.exec(statement)
    session.commit()
    return Message(message="Company deleted successfully")
