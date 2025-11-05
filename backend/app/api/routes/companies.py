import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select, exists, or_

from app.api.deps import CurrentUser, SessionDep
from app.models import Company, CompanyStatus, CompanysPublic, CompanyPublic, UserCompanyLink

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/", response_model=CompanysPublic)
def read_companies(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve Companies.
    """

    if current_user.is_superuser:
        count_statement = select(func.count()).select_from(Company)
        count = session.exec(count_statement).one()
        statement = select(Company.id, Company.title,
                           Company.description).offset(skip).limit(limit)
        items: list[CompanyPublic] = session.exec(statement).all()
    else:
        count_statement = (
            select(func.count())
            .select_from(Company)
            .where(or_(Company.status == CompanyStatus.public,
                       exists().where(UserCompanyLink.company_id == Company.id,
                                      UserCompanyLink.user_id == current_user.id)))
        )
        count = session.exec(count_statement).one()
        statement = (
            select(Company.id, Company.title, Company.description)
            .where(or_(Company.status == CompanyStatus.public,
                       exists().where(UserCompanyLink.company_id == Company.id,
                                      UserCompanyLink.user_id == current_user.id)))
            .offset(skip)
            .limit(limit)
        )
        items: list[CompanyPublic] = session.exec(statement).all()

    return CompanysPublic(data=items, count=count)


@router.get("/{name}", response_model=CompanysPublic)
def read_companies(
    session: SessionDep, current_user: CurrentUser, name: str, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve Companies.
    """

    if current_user.is_superuser:
        count_statement = select(func.count()).select_from(
            Company).where(Company.title.ilike(f"%{name}%"))
        count = session.exec(count_statement).one()
        if count > 0:
            statement = select(Company.id, Company.title, Company.description).where(
                Company.title.ilike(f"%{name}%")).offset(skip).limit(limit)
            items: list[CompanyPublic] = session.exec(statement).all()
    else:
        count_statement = (
            select(func.count())
            .select_from(Company)
            .where(or_(Company.status == CompanyStatus.public,
                       exists().where(UserCompanyLink.company_id == Company.id,
                                      UserCompanyLink.user_id == current_user.id)),
                   Company.title.ilike(f"%{name}%")))

        count = session.exec(count_statement).one()

        if count > 0:
            statement = (
                select(Company.id, Company.title, Company.description)
                .where(or_(Company.status == CompanyStatus.public,
                           exists().where(UserCompanyLink.company_id == Company.id,
                                          UserCompanyLink.user_id == current_user.id)),
                       Company.title.ilike(f"%{name}%"))
                .offset(skip)
                .limit(limit)
            )
            items: list[CompanyPublic] = session.exec(statement).all()

    return CompanysPublic(data=None if count == 0 else items, count=count)
