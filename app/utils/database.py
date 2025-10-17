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
            # Migration: copier l'ancienne colonne chiffrée vers refresh_token si présente
            try:
                res = conn.execute(
                    text(
                        """
                    SELECT COUNT(*) FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'api_user_sessions'
                      AND COLUMN_NAME = 'refresh_token_enc'
                    """
                    )
                )
                cnt = res.scalar() if hasattr(res, "scalar") else list(res)[0][0]
                if cnt and cnt > 0:
                    # Remplir refresh_token si NULL avec refresh_token_enc (déjà chiffré)
                    conn.execute(
                        text(
                            """
                        UPDATE api_user_sessions
                        SET refresh_token = refresh_token_enc
                        WHERE refresh_token IS NULL AND refresh_token_enc IS NOT NULL
                        """
                        )
                    )
                    conn.commit()
            except Exception:
                # Migration best-effort; on continue même si indisponible
                pass
            # Harmoniser la colonne refresh_token pour stockage chiffré (2048) et NOT NULL
            try:
                conn.execute(
                    text(
                        """
                ALTER TABLE api_user_sessions
                MODIFY COLUMN refresh_token VARCHAR(2048) NOT NULL
                """
                    )
                )
                conn.commit()
            except Exception:
                pass
            # Supprimer colonnes obsolètes si présentes
            for col in ("refresh_token_enc", "refresh_token_hash"):
                try:
                    conn.execute(
                        text(f"ALTER TABLE api_user_sessions DROP COLUMN {col}")
                    )
                    conn.commit()
                except Exception:
                    pass
            # Créer la table api_spotify_tokens si absente
            try:
                conn.execute(
                    text(
                        """
                CREATE TABLE IF NOT EXISTS api_spotify_tokens (
                  user_id VARCHAR(32) PRIMARY KEY,
                  refresh_token VARCHAR(1024) NULL,
                  updated_at DATETIME NOT NULL
                )
                """
                    )
                )
                conn.commit()
            except Exception:
                pass
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
            # Ajouter la colonne verified_at sur api_twofa si manquante
            try:
                conn.execute(
                    text(
                        """
                    ALTER TABLE api_twofa
                    ADD COLUMN IF NOT EXISTS verified_at DATETIME NULL
                    """
                    )
                )
                conn.commit()
            except Exception:
                pass
            # Agrandir la colonne secret (si trop courte) pour supporter les valeurs chiffrées
            try:
                conn.execute(
                    text(
                        """
                    ALTER TABLE api_twofa
                    MODIFY COLUMN secret VARCHAR(255)
                    """
                    )
                )
                conn.commit()
            except Exception:
                pass
            # Créer tables de modération si manquantes (warnings, bans)
            try:
                conn.execute(
                    text(
                        """
                    CREATE TABLE IF NOT EXISTS api_user_warnings (
                        id VARCHAR(36) PRIMARY KEY,
                        user_id VARCHAR(32) NOT NULL,
                        moderator_id VARCHAR(32) NOT NULL,
                        reason TEXT NOT NULL,
                        created_at DATETIME NOT NULL,
                        INDEX (user_id),
                        INDEX (moderator_id)
                    )
                    """
                    )
                )
                conn.execute(
                    text(
                        """
                    CREATE TABLE IF NOT EXISTS api_user_bans (
                        id VARCHAR(36) PRIMARY KEY,
                        user_id VARCHAR(32) NOT NULL,
                        moderator_id VARCHAR(32) NOT NULL,
                        reason TEXT NOT NULL,
                        created_at DATETIME NOT NULL,
                        until DATETIME NULL,
                        revoked_at DATETIME NULL,
                        INDEX (user_id),
                        INDEX (moderator_id)
                    )
                    """
                    )
                )
                # Assurer la présence des colonnes sur des tables existantes (MySQL 8+)
                try:
                    conn.execute(
                        text(
                            "ALTER TABLE api_user_warnings ADD COLUMN IF NOT EXISTS moderator_id VARCHAR(32) NULL"
                        )
                    )
                    conn.execute(
                        text(
                            "ALTER TABLE api_user_warnings ADD COLUMN IF NOT EXISTS reason TEXT NULL"
                        )
                    )
                    conn.execute(
                        text(
                            "ALTER TABLE api_user_warnings ADD COLUMN IF NOT EXISTS created_at DATETIME NULL"
                        )
                    )
                    conn.execute(
                        text(
                            "ALTER TABLE api_user_bans ADD COLUMN IF NOT EXISTS moderator_id VARCHAR(32) NULL"
                        )
                    )
                    conn.execute(
                        text(
                            "ALTER TABLE api_user_bans ADD COLUMN IF NOT EXISTS until DATETIME NULL"
                        )
                    )
                    conn.execute(
                        text(
                            "ALTER TABLE api_user_bans ADD COLUMN IF NOT EXISTS revoked_at DATETIME NULL"
                        )
                    )
                except Exception:
                    # Ignorer si le moteur ne supporte pas IF NOT EXISTS, géré plus bas
                    pass
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
                # Assurer colonnes de modération (fallback sans IF NOT EXISTS)
                ensure_col(
                    "api_user_warnings",
                    "moderator_id",
                    "ALTER TABLE api_user_warnings ADD COLUMN moderator_id VARCHAR(32) NULL",
                )
                ensure_col(
                    "api_user_warnings",
                    "reason",
                    "ALTER TABLE api_user_warnings ADD COLUMN reason TEXT NULL",
                )
                ensure_col(
                    "api_user_warnings",
                    "created_at",
                    "ALTER TABLE api_user_warnings ADD COLUMN created_at DATETIME NULL",
                )
                ensure_col(
                    "api_user_bans",
                    "moderator_id",
                    "ALTER TABLE api_user_bans ADD COLUMN moderator_id VARCHAR(32) NULL",
                )
                ensure_col(
                    "api_user_bans",
                    "until",
                    "ALTER TABLE api_user_bans ADD COLUMN until DATETIME NULL",
                )
                ensure_col(
                    "api_user_bans",
                    "revoked_at",
                    "ALTER TABLE api_user_bans ADD COLUMN revoked_at DATETIME NULL",
                )

                # Assurer refresh_token_hash (fallback sans IF NOT EXISTS)
                def ensure_col_generic(table: str, column: str, ddl: str):
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

                # Migration fallback: si refresh_token_enc existe, copier vers refresh_token
                try:
                    res = conn.execute(
                        text(
                            """
                        SELECT COUNT(*) FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA = DATABASE()
                          AND TABLE_NAME = 'api_user_sessions'
                          AND COLUMN_NAME = 'refresh_token_enc'
                        """
                        )
                    )
                    cnt = res.scalar() if hasattr(res, "scalar") else list(res)[0][0]
                    if cnt and cnt > 0:
                        conn.execute(
                            text(
                                """
                            UPDATE api_user_sessions
                            SET refresh_token = refresh_token_enc
                            WHERE refresh_token IS NULL AND refresh_token_enc IS NOT NULL
                            """
                            )
                        )
                        conn.commit()
                except Exception:
                    pass
                # Assurer refresh_token NOT NULL (fallback)
                try:
                    conn.execute(
                        text(
                            "ALTER TABLE api_user_sessions MODIFY COLUMN refresh_token VARCHAR(2048) NOT NULL"
                        )
                    )
                    conn.commit()
                except Exception:
                    pass
                # Créer api_spotify_tokens si absente (fallback)
                try:
                    conn.execute(
                        text(
                            """
                        CREATE TABLE IF NOT EXISTS api_spotify_tokens (
                          user_id VARCHAR(32) PRIMARY KEY,
                          refresh_token VARCHAR(1024) NULL,
                          updated_at DATETIME NOT NULL
                        )
                        """
                        )
                    )
                    conn.commit()
                except Exception:
                    pass
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
                # Ajouter verified_at (fallback sans IF NOT EXISTS)
                try:
                    res = conn.execute(
                        text(
                            """
                        SELECT COUNT(*) FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA = DATABASE()
                          AND TABLE_NAME = 'api_twofa'
                          AND COLUMN_NAME = 'verified_at'
                        """
                        )
                    )
                    cnt = res.scalar() if hasattr(res, "scalar") else list(res)[0][0]
                    if cnt == 0:
                        conn.execute(
                            text(
                                "ALTER TABLE api_twofa ADD COLUMN verified_at DATETIME NULL"
                            )
                        )
                        conn.commit()
                except Exception:
                    pass
                # Agrandir la colonne secret à VARCHAR(255) (fallback)
                try:
                    conn.execute(
                        text("ALTER TABLE api_twofa MODIFY COLUMN secret VARCHAR(255)")
                    )
                    conn.commit()
                except Exception:
                    pass
                # Créer tables warnings/bans (fallback)
                try:
                    conn.execute(
                        text(
                            """
                        CREATE TABLE IF NOT EXISTS api_user_warnings (
                            id VARCHAR(36) PRIMARY KEY,
                            user_id VARCHAR(32) NOT NULL,
                            moderator_id VARCHAR(32) NOT NULL,
                            reason TEXT NOT NULL,
                            created_at DATETIME NOT NULL,
                            INDEX (user_id),
                            INDEX (moderator_id)
                        )
                        """
                        )
                    )
                    conn.execute(
                        text(
                            """
                        CREATE TABLE IF NOT EXISTS api_user_bans (
                            id VARCHAR(36) PRIMARY KEY,
                            user_id VARCHAR(32) NOT NULL,
                            moderator_id VARCHAR(32) NOT NULL,
                            reason TEXT NOT NULL,
                            created_at DATETIME NOT NULL,
                            until DATETIME NULL,
                            revoked_at DATETIME NULL,
                            INDEX (user_id),
                            INDEX (moderator_id)
                        )
                        """
                        )
                    )
                    conn.commit()
                except Exception:
                    pass
        except Exception:
            # Laisser passer: l'app fonctionnera mais la colonne devra être ajoutée manuellement
            pass
