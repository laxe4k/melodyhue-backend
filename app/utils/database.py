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
    # Migrations légères: ajouter des colonnes si manquantes
    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    """
                ALTER TABLE api_user_settings
                ADD COLUMN IF NOT EXISTS default_overlay_color VARCHAR(7) DEFAULT '#25d865'
                """
                )
            )
            conn.execute(
                text(
                    """
                ALTER TABLE api_overlays
                ADD COLUMN IF NOT EXISTS template VARCHAR(32) DEFAULT 'classic'
                """
                )
            )
            conn.execute(
                text(
                    """
                ALTER TABLE api_overlays
                ADD COLUMN IF NOT EXISTS style VARCHAR(32) DEFAULT 'light'
                """
                )
            )
            conn.commit()
            # Supprimer une éventuelle contrainte unique sur api_users.username
            try:
                # MySQL/MariaDB: trouver l'index unique et le supprimer
                res = conn.execute(
                    text(
                        """
                    SELECT INDEX_NAME FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'api_users'
                      AND COLUMN_NAME = 'username'
                      AND NON_UNIQUE = 0
                    """
                    )
                )
                unique_indexes = [row[0] for row in res]
                for idx in unique_indexes:
                    conn.execute(text(f"ALTER TABLE api_users DROP INDEX {idx}"))
                conn.commit()
            except Exception:
                pass
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
                      AND COLUMN_NAME = 'default_overlay_color'
                    """
                    )
                )
                count = res.scalar() if hasattr(res, "scalar") else list(res)[0][0]
                if count == 0:
                    conn.execute(
                        text(
                            "ALTER TABLE api_user_settings ADD COLUMN default_overlay_color VARCHAR(7) DEFAULT '#25d865'"
                        )
                    )
                    conn.commit()

                # Vérifier et ajouter les colonnes template/style si absentes
                def ensure_col(table: str, column: str, ddl: str):
                    res = conn.execute(
                        text(
                            f"""
                        SELECT COUNT(*) FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA = DATABASE()
                          AND TABLE_NAME = '{table}'
                          AND COLUMN_NAME = '{column}'
                        """
                        )
                    )
                    cnt = res.scalar() if hasattr(res, "scalar") else list(res)[0][0]
                    if cnt == 0:
                        conn.execute(text(ddl))
                        conn.commit()

                ensure_col(
                    "api_overlays",
                    "template",
                    "ALTER TABLE api_overlays ADD COLUMN template VARCHAR(32) DEFAULT 'classic'",
                )
                ensure_col(
                    "api_overlays",
                    "style",
                    "ALTER TABLE api_overlays ADD COLUMN style VARCHAR(32) DEFAULT 'light'",
                )
                # Supprimer unique sur username si présent (fallback)
                try:
                    res = conn.execute(
                        text(
                            """
                        SELECT INDEX_NAME FROM information_schema.STATISTICS
                        WHERE TABLE_SCHEMA = DATABASE()
                          AND TABLE_NAME = 'api_users'
                          AND COLUMN_NAME = 'username'
                          AND NON_UNIQUE = 0
                        """
                        )
                    )
                    unique_indexes = [row[0] for row in res]
                    for idx in unique_indexes:
                        conn.execute(text(f"ALTER TABLE api_users DROP INDEX {idx}"))
                    conn.commit()
                except Exception:
                    pass
        except Exception:
            # Laisser passer: l'app fonctionnera mais la colonne devra être ajoutée manuellement
            pass
