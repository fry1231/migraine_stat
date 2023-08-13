from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
import logging
from src.settings import IS_TESTING, POSTGRES_USER, POSTGRES_PASS


SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASS}@migraine_db:5432/db_prod"
TEST_DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASS}@migraine_db:5432/db_test"


engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # connect_args={"check_same_thread": False}
)
test_engine = create_engine(
    TEST_DATABASE_URL,
    # connect_args={"check_same_thread": False}
)

logging.info(f"DB {SQLALCHEMY_DATABASE_URL} connected")
