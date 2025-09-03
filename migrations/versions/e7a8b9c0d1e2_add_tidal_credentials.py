"""add tidal_credentials table

Revision ID: e7a8b9c0d1e2
Revises: f1a2b3c4d5e6
Create Date: 2025-09-03 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e7a8b9c0d1e2"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tidal_credentials",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_type", sa.String(length=50), nullable=True),
        sa.Column("access_token", sa.String(length=2048), nullable=True),
        sa.Column("refresh_token", sa.String(length=2048), nullable=True),
        sa.Column("expiry_time", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.internal_id"], ondelete="CASCADE"),
    )
    # Un enregistrement max par utilisateur
    op.create_unique_constraint(
        "uq_tidal_credentials_user_id", "tidal_credentials", ["user_id"]
    )
    op.create_index(
        op.f("ix_tidal_credentials_user_id"),
        "tidal_credentials",
        ["user_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_tidal_credentials_user_id"), table_name="tidal_credentials")
    op.drop_constraint(
        "uq_tidal_credentials_user_id", "tidal_credentials", type_="unique"
    )
    op.drop_table("tidal_credentials")

