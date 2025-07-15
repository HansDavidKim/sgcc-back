from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Annotated
from sqlmodel import Field, Session, SQLModel, create_engine, select
from datetime import datetime

from dotenv import load_dotenv
from pathlib import Path
import os

class Notice(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

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

@router.post("/notices", response_model=Notice)
def create_notice(notice: Notice, session: SessionDep) -> Notice:
    session.add(notice)
    session.commit()
    session.refresh(notice)
    return notice

@router.get("/notices", response_model=Notice)
def read_notices(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[Notice]:
    notices = session.exec(select(Notice).offset(offset).limit(limit)).all()
    return notices

@router.get("/notices/{notice_id}", response_model=Notice)
def read_notice(notice_id: int, session: SessionDep) -> Notice:
    notice = session.get(Notice, notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    return notice

@router.delete("/notices/{notice_id}")
def delete_notice(notice_id: int, session: SessionDep):
    notice = session.get(Notice, notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    session.delete(notice)
    session.commit()
    return {"ok": True}