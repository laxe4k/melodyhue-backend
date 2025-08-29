"""add default color hex to users

Revision ID: d4f1a2b3c6e7
Revises: c3c1f2a8b7e1
Create Date: 2025-08-29 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d4f1a2b3c6e7"
down_revision = "c3c1f2a8b7e1"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("default_color_hex", sa.String(length=7), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("default_color_hex")
