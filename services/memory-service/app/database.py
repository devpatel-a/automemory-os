from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "postgresql://devpatel@localhost/automemory_os"


class Base(DeclarativeBase):
    pass

# creates a new database engine instance that will be used to connect to the PostgreSQL database specified by the DATABASE_URL. The create_engine function is part of SQLAlchemy and is used to establish a connection to the database.
engine = create_engine(DATABASE_URL)

# Instead of opening one permanent connection FastAPI creates a session for each request.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)