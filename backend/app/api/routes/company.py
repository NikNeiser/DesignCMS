import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select, exists, or_, delete
from sqlalchemy.orm import noload, selectinload
from app import crud

from app.api.deps import CurrentUser, SessionDep
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


@router.get("/{id}", response_model=CompanyPublic)
def read_company(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get Company by ID.
    """
    company = session.get(Company, id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if not current_user.is_superuser and company.is_deleted:
        raise HTTPException(status_code=400, detail="Company is deleted")
    if not current_user.is_superuser and (company.status != CompanyStatus.public and not any(c.id == current_user.id for c in company.employee)):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    return company


@router.put("/{id}", response_model=CompanyPublic)
def update_company(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    company_in: CompanyUpdate,
) -> Any:
    """
    Update an company.
    """
    company = session.exec(
        select(Company)
        .where(Company.id == id)
        .options(
            selectinload(
                Company.employee.and_(
                    User.id == current_user.id,
                    UserCompanyLink.role == CompanyRole.owner
                )
            ), noload(Company.design_items), noload(Company.tags)
        )
    ).first()

    if not company:
        raise HTTPException(status_code=404, detail="company not found")

    if not current_user.is_superuser and len(company.employee) == 0:
        raise HTTPException(
            status_code=400, detail="Not enough permissions")

    if company_in.title and company_in.title.lower() != company.title.lower() and crud.check_company_name_exist(session=session, name=company_in.title):
        raise HTTPException(
            status_code=400, detail=f"Company named \"{company_in.title}\" already exists")

    update_dict = company_in.model_dump(exclude_unset=True)
    company.sqlmodel_update(update_dict)
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


@router.delete("/{id}")
def delete_company(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete an Company.
    """
    # company = session.get(Company, id)

    if not crud.company_exist(session=session, id=id):
        raise HTTPException(status_code=404, detail="Company not found")

    if not current_user.is_superuser:
        user_company_role = crud.get_user_company_role(
            session=session, company_id=id, user_id=current_user.id)

        if user_company_role or user_company_role != CompanyRole.owner:
            raise HTTPException(
                status_code=400, detail="Not enough permissions")

    statement = delete(Company).where(Company.id == id)
    session.exec(statement)
    session.commit()
    return Message(message="Company deleted successfully")
