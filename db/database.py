from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database
import logging


SQLALCHEMY_DATABASE_URL = "sqlite:///db/sql_app.db"
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
if not database_exists(engine.url):
    logging.info(f"DB does not exist, creating on {SQLALCHEMY_DATABASE_URL}")
    create_database(engine.url)
    logging.info(f"Created successfully")

SessionLocal = sessionmaker(
    engine,
    expire_on_commit=False,
    autocommit=False,
    autoflush=True,
    # future=True
)
logging.info(f"DB {SQLALCHEMY_DATABASE_URL} connected")

Base = declarative_base()
