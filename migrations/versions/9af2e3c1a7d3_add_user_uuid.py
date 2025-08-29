"""add user uuid

Revision ID: 9af2e3c1a7d3
Revises: ec4915352f9d
Create Date: 2025-08-28 23:59:00.000000

"""

from alembic import op
import sqlalchemy as sa
import uuid


# revision identifiers, used by Alembic.
revision = "9af2e3c1a7d3"
down_revision = "ec4915352f9d"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("uuid", sa.String(length=36), nullable=True))
        batch_op.create_index(batch_op.f("ix_users_uuid"), ["uuid"], unique=True)

    # Remplir les valeurs uuid pour les lignes existantes
    conn = op.get_bind()
    users = conn.execute(sa.text("SELECT id, uuid FROM users")).fetchall()
    for row in users:
        if not row.uuid:
            conn.execute(
                sa.text("UPDATE users SET uuid=:u WHERE id=:i"),
                {
                    "u": str(uuid.uuid4()),
                    "i": row.id,
                },
            )

    # Rendre la colonne non nulle
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "uuid", existing_type=sa.String(length=36), nullable=False
        )


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_uuid"))
        batch_op.drop_column("uuid")
