from typing import Union
from fastapi import FastAPI
from pydantic import BaseModel
from routers import notices

#from notice import create_db_and_tables
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    #### STARTUP
    notices.created_db_and_tables()
    yield
    #### SHUTDOWN

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"Hello" : "World"}
