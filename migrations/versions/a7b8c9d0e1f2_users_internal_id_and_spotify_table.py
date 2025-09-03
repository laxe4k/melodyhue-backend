"""users internal_id PK and spotify_credentials table

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2025-09-03 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a7b8c9d0e1f2"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # Par sécurité, supprimer une éventuelle table temporaire résiduelle
    if insp.has_table("users_tmp2"):
        op.drop_table("users_tmp2")

    # 1) Créer une table temporaire users_tmp2 avec internal_id PK (auto-incrément)
    op.create_table(
        "users_tmp2",
        sa.Column("internal_id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("default_color_hex", sa.String(length=7), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # Créer index/contraintes uniques (seront conservés après rename)
    with op.batch_alter_table("users_tmp2") as batch:
        batch.create_index(batch.f("ix_users_tmp2_username"), ["username"], unique=True)
        batch.create_index(batch.f("ix_users_tmp2_email"), ["email"], unique=True)
        batch.create_index(batch.f("ix_users_tmp2_uuid"), ["uuid"], unique=True)

    # 2) Copier les données depuis la table users existante (uuid PK) vers users_tmp2
    conn.execute(
        sa.text(
            """
            INSERT INTO users_tmp2 (uuid, username, email, password_hash, default_color_hex, created_at, updated_at)
            SELECT uuid, username, email, password_hash, default_color_hex, created_at, updated_at
            FROM users
            """
        )
    )

    # 3) Créer la table spotify_credentials SANS FK pour d'abord migrer les données
    op.create_table(
        "spotify_credentials",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.String(length=255), nullable=True),
        sa.Column("client_secret", sa.String(length=255), nullable=True),
        sa.Column("refresh_token", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    with op.batch_alter_table("spotify_credentials") as batch:
        batch.create_index(batch.f("ix_spotify_credentials_user_id"), ["user_id"], unique=True)

    # 4) Peupler spotify_credentials à partir des colonnes de users (jonction via uuid)
    # On insère uniquement s'il y a au moins un champ non NULL
    # NOW() est MySQL/MariaDB ; pour portabilité, on utilise CURRENT_TIMESTAMP
    conn.execute(
        sa.text(
            """
            INSERT INTO spotify_credentials (user_id, client_id, client_secret, refresh_token, created_at, updated_at)
            SELECT u2.internal_id, u.spotify_client_id, u.spotify_client_secret, u.spotify_refresh_token,
                   CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM users u
            JOIN users_tmp2 u2 ON u.uuid = u2.uuid
            WHERE u.spotify_client_id IS NOT NULL
               OR u.spotify_client_secret IS NOT NULL
               OR u.spotify_refresh_token IS NOT NULL
            """
        )
    )

    # 5) Remplacer la table users et ajouter la contrainte FK sur spotify_credentials
    #    - Drop indexes/table users (ancienne structure)
    try:
        op.drop_index("ix_users_email", table_name="users")
    except Exception:
        pass
    try:
        op.drop_index("ix_users_username", table_name="users")
    except Exception:
        pass
    try:
        op.drop_index("ix_users_uuid", table_name="users")
    except Exception:
        pass

    op.drop_table("users")

    #    - Renommer users_tmp2 -> users
    op.rename_table("users_tmp2", "users")

    #    - Recréer les index sous le nom final si nécessaire
    with op.batch_alter_table("users") as batch:
        batch.create_index(batch.f("ix_users_username"), ["username"], unique=True)
        batch.create_index(batch.f("ix_users_email"), ["email"], unique=True)
        batch.create_index(batch.f("ix_users_uuid"), ["uuid"], unique=True)

    #    - Ajouter la FK maintenant que users.internal_id existe
    op.create_foreign_key(
        "fk_spotify_credentials_user_id_users",
        "spotify_credentials",
        "users",
        ["user_id"],
        ["internal_id"],
        ondelete="CASCADE",
    )


def downgrade():
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # 1) Recréer une table users_old avec uuid PK et colonnes Spotify
    if insp.has_table("users_old"):
        op.drop_table("users_old")

    op.create_table(
        "users_old",
        sa.Column("uuid", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("spotify_client_id", sa.String(length=255), nullable=True),
        sa.Column("spotify_client_secret", sa.String(length=255), nullable=True),
        sa.Column("spotify_refresh_token", sa.String(length=1024), nullable=True),
        sa.Column("default_color_hex", sa.String(length=7), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    with op.batch_alter_table("users_old") as batch:
        batch.create_index(batch.f("ix_users_old_username"), ["username"], unique=True)
        batch.create_index(batch.f("ix_users_old_email"), ["email"], unique=True)

    # 2) Copier les données de users (internal_id PK) -> users_old, en rejoignant spotify_credentials
    conn.execute(
        sa.text(
            """
            INSERT INTO users_old (uuid, username, email, password_hash, spotify_client_id, spotify_client_secret, spotify_refresh_token, default_color_hex, created_at, updated_at)
            SELECT u.uuid, u.username, u.email, u.password_hash, sc.client_id, sc.client_secret, sc.refresh_token, u.default_color_hex, u.created_at, u.updated_at
            FROM users u
            LEFT JOIN spotify_credentials sc ON sc.user_id = u.internal_id
            """
        )
    )

    # 3) Supprimer la FK et la table spotify_credentials
    try:
        op.drop_constraint(
            "fk_spotify_credentials_user_id_users", "spotify_credentials", type_="foreignkey"
        )
    except Exception:
        pass
    op.drop_index("ix_spotify_credentials_user_id", table_name="spotify_credentials")
    op.drop_table("spotify_credentials")

    # 4) Remplacer la table users
    try:
        op.drop_index("ix_users_email", table_name="users")
    except Exception:
        pass
    try:
        op.drop_index("ix_users_username", table_name="users")
    except Exception:
        pass
    try:
        op.drop_index("ix_users_uuid", table_name="users")
    except Exception:
        pass

    op.drop_table("users")

    op.rename_table("users_old", "users")
    with op.batch_alter_table("users") as batch:
        batch.create_index(batch.f("ix_users_username"), ["username"], unique=True)
        batch.create_index(batch.f("ix_users_email"), ["email"], unique=True)
        batch.create_index(batch.f("ix_users_uuid"), ["uuid"], unique=True)

