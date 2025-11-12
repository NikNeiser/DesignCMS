from collections.abc import Generator
from typing import Annotated

import uuid
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session, select, and_

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.models import TokenPayload, User, CompanyRole, Company, UserCompanyLink, CompanyStatus
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
    user = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user


def verify_company_access(
    company_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep
) -> CompanyRole | None:

    if current_user.is_superuser:
        if company_exist(session=session, id=company_id):
            return CompanyRole.owner
        else:
            raise HTTPException(status_code=404, detail="Company not found")
    else:
        statement = select(Company.status, UserCompanyLink.role).\
            outerjoin(UserCompanyLink, and_(
                UserCompanyLink.company_id == Company.id,
                UserCompanyLink.user_id == current_user.id
            )).\
            where(Company.id == company_id)
        result = session.exec(statement).first()

        if not result:
            raise HTTPException(status_code=404, detail="Company not found")

        if result.status != CompanyStatus.public and not result.role:
            raise HTTPException(
                status_code=400, detail="Not enough permissions")

        return result.role


CompanyRoleDep = Annotated[CompanyRole | None, Depends(verify_company_access)]
