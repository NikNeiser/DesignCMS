import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select, exists, or_

from app.api.deps import CurrentUser, SessionDep
from app.models import Company, CompanyStatus, CompanysPublic, CompanyPublic, CompanyCreate, CompanyUpdate, UserCompanyLink, CompanyRole, Message

router = APIRouter(prefix="/company", tags=["company"])


@router.post("/", response_model=CompanyPublic)
def create_company(
    *, session: SessionDep, current_user: CurrentUser, company_in: CompanyCreate
) -> Any:
    """
    Create new Company.
    """
    company = Company.model_validate(company_in)
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
    company = session.get(Company, id)
    if not company:
        raise HTTPException(status_code=404, detail="company not found")
    if not current_user.is_superuser and (company.owner_id != current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
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
    company = session.get(Company, id)

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    user_company_link = session.exec(
        select(UserCompanyLink).where(
            UserCompanyLink.company_id == id,
            UserCompanyLink.user_id == current_user.id
        )
    ).first()

    if not current_user.is_superuser or user_company_link.role != CompanyRole.owner:
        raise HTTPException(status_code=400, detail="Not enough permissions")

    session.delete(company)
    session.commit()
    return Message(message="Company deleted successfully")
