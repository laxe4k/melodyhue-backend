"""add music_platform to users

Revision ID: a1b2c3d4e5f6
Revises: e7a8b9c0d1e2
Create Date: 2025-09-03 00:05:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "e7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("music_platform", sa.String(length=20), nullable=True))
    # Optionnel: définir 'spotify' comme valeur par défaut logique côté DB si souhaité


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("music_platform")

