from collections.abc import Generator
from typing import Annotated

import uuid
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session, select, and_
from sqlalchemy.orm import noload

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.models import TokenPayload, User, CompanyRole, Company, UserCompanyLink, CompanyStatus, EmployeeAccess
from app.crud import company_exist

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = session.exec(
        select(User)
        .where(User.id == token_data.sub, User.is_delited == False)
        .options(
            noload(User.items),
            noload(User.companies),
            noload(User.design_items)
        )
    ).first()
    # user = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_employee(session: SessionDep, token: TokenDep, company_id: uuid.UUID) -> EmployeeAccess:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    statement = select(User.is_superuser, Company.status, UserCompanyLink.role)\
        .select_from(User).outerjoin(Company, Company.id == company_id)\
        .outerjoin(UserCompanyLink,
                   and_(
                       UserCompanyLink.company_id == Company.id,
                       UserCompanyLink.user_id == User.id))\
        .where(User.id == token_data.sub, User.is_delited == False)

    result = session.exec(statement).first()

    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    if not result.status:
        raise HTTPException(status_code=404, detail="Company not found")
    if result.status != CompanyStatus.public and not result.role:
        raise HTTPException(status_code=400, detail="Not enough permissions")

    return EmployeeAccess(id=token_data.sub, is_superuser=result.is_superuser, role=None if not result.role else result.role)


CurrentEmployee = Annotated[EmployeeAccess, Depends(get_current_employee)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user
