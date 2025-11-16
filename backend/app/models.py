import uuid
import enum

from datetime import date
from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel


@enum.unique
class CompanyRole(enum.Enum):
    reader = 1
    creator = 5
    owner = 9


@enum.unique
class CompanyStatus(enum.Enum):
    public = 1
    private = 9


# Link Tables -------------------------------------------------

class TagItemLink(SQLModel, table=True):
    design_item_id: uuid.UUID = Field(
        foreign_key="designitem.id", primary_key=True)
    tag_id: uuid.UUID = Field(foreign_key="tag.id", primary_key=True)


class UserCompanyLink(SQLModel, table=True):
    company_id: uuid.UUID = Field(
        foreign_key="company.id", primary_key=True, ondelete='CASCADE')
    user_id: uuid.UUID = Field(foreign_key="user.id", primary_key=True)
    role: CompanyRole = CompanyRole.reader


# User Model -------------------------------------------------

# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    is_delited: bool = Field(default=False)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=40)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(
        default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=40)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    items: list["Item"] = Relationship(
        back_populates="owner", cascade_delete=True)
    design_items: list["DesignItem"] = Relationship(back_populates="creator")
    companies: list["Company"] = Relationship(
        back_populates="employee", link_model=UserCompanyLink)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


class EmployeePublic(UserPublic):
    role: CompanyRole


class EmployeesPublic(SQLModel):
    data: list[EmployeePublic]
    count: int


class EmployeeAccess:
    id: uuid.UUID | None
    is_superuser: bool = False
    role: CompanyRole | None


# Item Model -------------------------------------------------

# Shared properties


class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(
        default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)


# Company Model -------------------------------------------------


# Shared properties
class CompanyBase(SQLModel):
    title: str = Field(unique=True, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on Company creation
class CompanyCreate(CompanyBase):
    status: CompanyStatus = CompanyStatus.public


# Properties to receive on Company update
class CompanyUpdate(CompanyBase):
    title: str | None = Field(default=None, max_length=255)
    status: CompanyStatus | None = Field(default=None)  # type: ignore


# Database model, database table inferred from class name
class Company(CompanyBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    status: CompanyStatus = CompanyStatus.public
    is_deleted: bool = False

    employee: list["User"] = Relationship(
        back_populates="companies", link_model=UserCompanyLink, sa_relationship_kwargs={"lazy": "selectin"})
    design_items: list["DesignItem"] | None = Relationship(
        back_populates="company", cascade_delete=True, sa_relationship_kwargs={"lazy": "raise"})
    tags: list["Tag"] | None = Relationship(
        back_populates="company", cascade_delete=True, sa_relationship_kwargs={"lazy": "raise"})


# Properties to return via API, id is always required
class CompanyPublic(CompanyBase):
    id: uuid.UUID


class CompanysPublic(SQLModel):
    data: list[CompanyPublic] | None
    count: int


# DesignItem Model -------------------------------------------------


# Shared properties
class DesignItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on DesignItem creation
class DesignItemCreate(DesignItemBase):
    pass


# Properties to receive on DesignItem update
class DesignItemUpdate(DesignItemBase):
    title: str | None = Field(
        default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class DesignItem(DesignItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(
        foreign_key="company.id", nullable=False, ondelete="CASCADE")
    creator_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False)
    file_path: str = Field(min_length=1, max_length=511)
    preview_path: str = Field(min_length=1, max_length=255)
    created_date: date = Field(default_factory=date.today)

    creator: User = Relationship(back_populates="design_items")
    company: Company = Relationship(back_populates="design_items")
    tags: list["Tag"] = Relationship(
        back_populates="design_items", link_model=TagItemLink)


# Properties to return via API, id is always required
class DesignItemPublic(DesignItemBase):
    id: uuid.UUID
    creator_id: uuid.UUID


class DesignItemsPublic(SQLModel):
    data: list[DesignItemPublic]
    count: int


# Tag Model -------------------------------------------------


# Shared properties
class TagBase(SQLModel):
    title: str = Field(min_length=1, max_length=31)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on Tag creation
class TagCreate(TagBase):
    pass


# Properties to receive on Tag update
class TagUpdate(TagBase):
    title: str | None = Field(
        default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Tag(TagBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(
        foreign_key="company.id", nullable=False, ondelete="CASCADE")

    company: Company = Relationship(back_populates="tags")
    design_items: list["DesignItem"] = Relationship(
        back_populates="tags", link_model=TagItemLink)


# Properties to return via API, id is always required
class TagPublic(TagBase):
    id: uuid.UUID


class TagsPublic(SQLModel):
    data: list[TagPublic]
    count: int
