from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Annotated
from sqlmodel import Field, Session, SQLModel, create_engine, select
from datetime import datetime

from dotenv import load_dotenv
from pathlib import Path
import os

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("NOTICE_DATABASE_URL")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite only
)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

def created_db_and_tables():
    SQLModel.metadata.create_all(engine)

router = APIRouter()

class NoticeBase(SQLModel):
    title: str = Field(index=True)
    author: str | None = Field(default=None, index=True)
    content: str | None = Field(default=None, index=True)
    create_at: datetime | None = Field(default=None, index=True)

class Notice(NoticeBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

class NoticePublic(NoticeBase):
    id: int

class NoticeCreate(NoticeBase):
    pass

class NoticeUpdate(NoticeBase):
    title: str | None = None
    author: str | None = None
    content: str | None = None

@router.post("/notices/", response_model = NoticePublic)
def create_notice(notice: NoticeCreate, session: SessionDep):
    db_notice = Notice.model_validate(notice)
    session.add(db_notice)
    session.commit()
    session.refresh(db_notice)
    return db_notice

@router.get("/notices/", response_model=list[NoticePublic])
def read_notices(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(le=100)] = 10
):
    offset = (page - 1) * size
    notices = session.exec(select(Notice).offset(offset).limit(size)).all()
    return notices

@router.get("/notices/{notice_id}", response_model=NoticePublic)
def read_notice(notice_id: int, session: SessionDep):
    notice = session.get(Notice, notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    return notice

@router.patch("/notices/{notice_id}", response_model=NoticePublic)
def update_notice(notice_id: int, notice: NoticeUpdate, session: SessionDep):
    notice_db = session.get(Notice, notice_id)
    if not notice_db:
        raise HTTPException(status_code=404, detal="Notice not found")
    notice_data = notice.model_dump(exclude_unset=True)
    notice_db.sqlmodel_update(notice_data)
    session.add(notice_db)
    session.commit()
    session.refresh(notice_db)
    return notice_db

@router.delete("/notices/{notice_id}")
def delete_notice(notice_id: int, session: SessionDep):
    notice = session.get(Notice, notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    session.delete(notice)
    session.commit()
    return {"ok": True}