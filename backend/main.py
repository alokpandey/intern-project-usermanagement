from fastapi import FastAPI
from src.api.router import router
from src.models.DB_models import Base
from src.session import engine

app = FastAPI()

@app.get("/")
async def root():
    return "WELCOME TO USER REGISTRATION APP"

app.include_router(router,prefix="/api/v1")

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
