from typing import Union
from fastapi import FastAPI
from pydantic import BaseModel
from routers import notices, auth

from db.database import create_db_and_tables

#from notice import create_db_and_tables
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    #### STARTUP
    create_db_and_tables()
    yield
    #### SHUTDOWN

app = FastAPI(lifespan=lifespan)
app.include_router(notices.router)
app.include_router(auth.router)

@app.get("/")
def read_root():
    return {"Hello" : "World"}
