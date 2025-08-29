"""users uuid primary key

Revision ID: c3c1f2a8b7e1
Revises: 9af2e3c1a7d3
Create Date: 2025-08-29 00:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c3c1f2a8b7e1"
down_revision = "9af2e3c1a7d3"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # Si la table temp existe déjà, on la drop (sécurité)
    if insp.has_table("users_tmp"):
        op.drop_table("users_tmp")

    # Créer une table temporaire avec uuid PK
    op.create_table(
        "users_tmp",
        sa.Column("uuid", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("spotify_client_id", sa.String(length=255), nullable=True),
        sa.Column("spotify_client_secret", sa.String(length=255), nullable=True),
        sa.Column("spotify_refresh_token", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # Copier les données de users -> users_tmp (en s'appuyant sur la colonne uuid existante)
    conn.execute(
        sa.text(
            """
            INSERT INTO users_tmp (uuid, username, email, password_hash, spotify_client_id, spotify_client_secret, spotify_refresh_token, created_at, updated_at)
            SELECT uuid, username, email, password_hash, spotify_client_id, spotify_client_secret, spotify_refresh_token, created_at, updated_at
            FROM users
            """
        )
    )

    # Drop ancienne table
    op.drop_index("ix_users_uuid", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")

    # Renommer users_tmp -> users et recréer index/contraintes
    op.rename_table("users_tmp", "users")
    with op.batch_alter_table("users") as batch_op:
        batch_op.create_index(
            batch_op.f("ix_users_username"), ["username"], unique=True
        )
        batch_op.create_index(batch_op.f("ix_users_email"), ["email"], unique=True)
        # uuid est PK, l'index unique dédié n'est plus nécessaire


def downgrade():
    conn = op.get_bind()
    insp = sa.inspect(conn)
    # Recréer ancienne structure avec id PK (perte de données possible si erreur). On tente une migration inverse safe.

    if insp.has_table("users_old"):
        op.drop_table("users_old")

    # Créer users_old avec id auto-incrément
    op.create_table(
        "users_old",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("spotify_client_id", sa.String(length=255), nullable=True),
        sa.Column("spotify_client_secret", sa.String(length=255), nullable=True),
        sa.Column("spotify_refresh_token", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # Copier données
    conn.execute(
        sa.text(
            """
            INSERT INTO users_old (uuid, username, email, password_hash, spotify_client_id, spotify_client_secret, spotify_refresh_token, created_at, updated_at)
            SELECT uuid, username, email, password_hash, spotify_client_id, spotify_client_secret, spotify_refresh_token, created_at, updated_at
            FROM users
            """
        )
    )

    # Drop et rename inverse
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
    op.rename_table("users_old", "users")
    with op.batch_alter_table("users") as batch_op:
        batch_op.create_index(batch_op.f("ix_users_email"), ["email"], unique=True)
        batch_op.create_index(
            batch_op.f("ix_users_username"), ["username"], unique=True
        )
        batch_op.create_index(batch_op.f("ix_users_uuid"), ["uuid"], unique=True)
