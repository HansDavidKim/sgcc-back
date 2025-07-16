from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import Depends, APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel

from dotenv import load_dotenv
import os
from pathlib import Path

from db.database import get_session
from sqlmodel import Session, select, SQLModel, Field

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

SessionDep = Annotated[Session, Depends(get_session)]


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool = False

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

class UserOut(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None

class UserCreate(BaseModel):
    username: str
    password: str
    email: str | None = None
    full_name: str | None = None

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def get_user(session: Session, username: str) -> User | None:
    statement = select(User).where(User.username == username)
    result = session.exec(statement)
    return result.first()

def authenticate_user(session: Session, username: str, password: str) -> User | bool:
    user = get_user(session, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: SessionDep
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception

    user = get_user(session, username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep
):
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return Token(access_token=token, token_type="bearer")

@router.get("/users/me", response_model=UserOut)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    return current_user

### We will add email verification later.
@router.post("/register", response_model=UserOut, status_code=201)
def register_user(
    user_create: UserCreate,
    session: SessionDep,
):
    existing_user = session.exec(
        select(User).where(User.username == user_create.username)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )
    
    hashed_password = get_password_hash(user_create.password)
    user = User(
        username=user_create.username,
        hashed_password=hashed_password,
        email=user_create.email,
        full_name=user_create.full_name,
        disabled=False
    )

    session.add(user)
    session.commit()
    session.refresh(user)
    return user