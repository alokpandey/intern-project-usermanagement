from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config.settings import DATABASE_URL

#engine = create_engine(DATABASE_URL)
#SessionLocal = sessionmaker(bind=engine)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

def init_db():
    from app.db import models
    Base.metadata.create_all(bind=engine)

# def init_db():
#     for _ in range(10):
#         try:
#             Base.metadata.create_all(bind=engine)
#             print("Database ready")
#             return
#         except OperationalError:
#             print("Database not ready, retrying...")
#             time.sleep(2)
#     raise RuntimeError("Database never became available")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()