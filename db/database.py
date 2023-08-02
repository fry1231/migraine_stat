from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils import database_exists, create_database
import logging
from src.settings import IS_TESTING


SQLALCHEMY_DATABASE_URL = "sqlite:///db/db_file/sql_app.db"
TEST_DATABASE_URL = 'sqlite:///db/db_file/test.db'
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

logging.info(f"DB {SQLALCHEMY_DATABASE_URL} connected")

Base = declarative_base()

if not IS_TESTING:
    Base.metadata.create_all(bind=engine)
