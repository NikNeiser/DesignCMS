import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select, exists, delete
from sqlalchemy.orm import noload
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep, CurrentEmployee
from app.models import TagPublic, TagCreate, Tag, TagUpdate, Message, CompanyRole

router = APIRouter(prefix="/{company_id}/tag", tags=["tag"])


@router.post("/", response_model=TagPublic)
def create_tag(
    *, session: SessionDep, company_id: uuid.UUID, current_employee: CurrentEmployee, tag_in: TagCreate
) -> Any:
    """
    Create tag.
    """
    if not current_employee.role or current_employee.role == CompanyRole.reader:
        raise HTTPException(
            status_code=400, detail="Not enough permissions")

    tag = Tag.model_validate(
        tag_in, update={"company_id": company_id})

    try:
        session.add(tag)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            409, f"Tag with title\"{tag.title}\" already exists")
    return tag


@router.put("/{tag_id}", response_model=TagPublic)
def update_tag(
    *, session: SessionDep, company_id: uuid.UUID, tag_id: uuid.UUID, current_employee: CurrentEmployee, tag_in: TagUpdate
) -> Any:
    """
    Create/Update tag.
    """
    if not current_employee.role or current_employee.role == CompanyRole.reader:
        raise HTTPException(
            status_code=400, detail="Not enough permissions")

    tag = session.exec(
        select(Tag)
        .where(Tag.id == tag_id)
        .options(
            noload(Tag.company),
            noload(Tag.design_items)
        )
    ).first()

    if not tag:
        tag = Tag.model_validate(
            tag_in, update={"company_id": company_id})

    update_dict = tag_in.model_dump(exclude_unset=True)
    tag.sqlmodel_update(update_dict)

    try:
        session.add(tag)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            409, f"Tag with title \"{tag_in.title}\" already exists")

    session.refresh(tag)
    return tag


@router.delete("/{tag_id}")
def delete_tag(
    session: SessionDep, company_id: uuid.UUID, current_employee: CurrentEmployee, tag_id: uuid.UUID
) -> Message:
    """
    Delete a tag.
    """

    if not current_employee.role or current_employee.role == CompanyRole.reader:
        raise HTTPException(
            status_code=400, detail="Not enough permissions")

    tag_exist = session.exec(
        select(exists().where(Tag.id == tag_id, Tag.company_id == company_id))
    ).first()

    if not tag_exist:
        raise HTTPException(
            status_code=404, detail="Didn't find this tag")

    session.exec(delete(Tag).where(Tag.id == tag_id))
    session.commit()
    return Message(message="Tag deleted successfully")
