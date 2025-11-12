import uuid
from typing import Any

from sqlmodel import Session, select, func, exists, outerjoin, and_

from app.core.security import get_password_hash, verify_password
from app.models import (
    Item,
    ItemCreate,
    User,
    UserCreate,
    UserUpdate,
    Company,
    CompanyRole,
    UserCompanyLink,
    CompanyStatus,
    AccessStatus
)


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={
            "hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


def check_company_name_exist(*, session: Session, name: str) -> bool:
    statement = select(exists().where(Company.title.ilike(name)))
    return session.exec(statement).one()


def company_exist(*, session: Session, id: uuid.UUID) -> bool:
    statement = select(exists().where(Company.id == id))
    return session.exec(statement).one()


def get_user_company_role(*, session: Session, company_id: uuid.UUID, user_id: uuid.UUID) -> CompanyRole | None:
    user_company_role = session.exec(
        select(UserCompanyLink.role).where(
            UserCompanyLink.company_id == company_id,
            UserCompanyLink.user_id == user_id
        )
    ).first()
    return user_company_role
