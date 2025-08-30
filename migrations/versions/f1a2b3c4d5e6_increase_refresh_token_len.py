"""increase spotify_refresh_token length to 1024

Revision ID: f1a2b3c4d5e6
Revises: d4f1a2b3c6e7
Create Date: 2025-08-30 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f1a2b3c4d5e6"
down_revision = "d4f1a2b3c6e7"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "spotify_refresh_token",
            type_=sa.String(length=1024),
            existing_type=sa.String(length=512),
            existing_nullable=True,
        )


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "spotify_refresh_token",
            type_=sa.String(length=512),
            existing_type=sa.String(length=1024),
            existing_nullable=True,
        )
