import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import text

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


# Fabrique de sessions non scoppées (une session par requête FastAPI)
SessionLocal = sessionmaker(
    bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        # Assurer un rollback si une exception est remontée
        db.rollback()
        raise
    finally:
        db.close()


def create_all(BaseCls: type[DeclarativeBase] | None = None):
    """Créer les tables si elles n'existent pas (bootstrap sans Alembic)."""
    base = BaseCls or Base
    base.metadata.create_all(bind=engine)
    # Migrations légères: ajouter la colonne default_color_overlays si manquante
    try:
        with engine.connect() as conn:
            # MySQL/MariaDB information_schema check
            conn.execute(
                text(
                    """
                ALTER TABLE api_user_settings
                ADD COLUMN IF NOT EXISTS default_color_overlays VARCHAR(7) DEFAULT '#25d865'
                """
                )
            )
            conn.commit()
    except Exception:
        # Compat MySQL versions without IF NOT EXISTS on ADD COLUMN
        try:
            with engine.connect() as conn:
                res = conn.execute(
                    text(
                        """
                    SELECT COUNT(*) FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'api_user_settings'
                      AND COLUMN_NAME = 'default_color_overlays'
                    """
                    )
                )
                count = res.scalar() if hasattr(res, "scalar") else list(res)[0][0]
                if count == 0:
                    conn.execute(
                        text(
                            "ALTER TABLE api_user_settings ADD COLUMN default_color_overlays VARCHAR(7) DEFAULT '#25d865'"
                        )
                    )
                    conn.commit()
        except Exception:
            # Laisser passer: l'app fonctionnera mais la colonne devra être ajoutée manuellement
            pass
