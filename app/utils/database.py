import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Fallback sur variables DB_* comme dans l'appli Flask
    db_host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_DATABASE")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_port = os.getenv("DB_PORT", "3306")
    db_driver = os.getenv("DB_DRIVER", "mysql+pymysql")
    if all([db_host, db_name, db_user, db_password]):
        from urllib.parse import quote_plus
        enc_pwd = quote_plus(str(db_password))
        DATABASE_URL = f"{db_driver}://{db_user}:{enc_pwd}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"
    else:
        raise RuntimeError("DATABASE_URL ou DB_* requis pour FastAPI")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

class Base(DeclarativeBase):
    pass

SessionLocal = scoped_session(sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, autocommit=False))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all(BaseCls: type[DeclarativeBase] | None = None):
    """Créer les tables si elles n'existent pas (bootstrap sans Alembic)."""
    base = BaseCls or Base
    base.metadata.create_all(bind=engine)