"""Remove Tidal support: drop tidal_credentials and music_platform

Revision ID: remove_tidal_and_music_platform
Revises: a7b8c9d0e1f2, a1b2c3d4e5f6
Create Date: 2025-09-04 01:38:19

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "remove_tidal_and_music_platform"
down_revision = ("a7b8c9d0e1f2", "a1b2c3d4e5f6")
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Drop tidal_credentials table if it exists
    if insp.has_table("tidal_credentials"):
        try:
            op.drop_index("ix_tidal_credentials_user_id", table_name="tidal_credentials")
        except Exception:
            pass
        try:
            op.drop_constraint("uq_tidal_credentials_user_id", "tidal_credentials", type_="unique")
        except Exception:
            pass
        try:
            op.drop_table("tidal_credentials")
        except Exception:
            # tolerate if already gone
            pass

    # Drop users.music_platform if present
    cols = []
    try:
        cols = [c["name"] for c in insp.get_columns("users")]
    except Exception:
        cols = []
    if "music_platform" in cols:
        with op.batch_alter_table("users") as batch_op:
            try:
                batch_op.drop_column("music_platform")
            except Exception:
                # already dropped or not supported
                pass


def downgrade():
    # Recreate users.music_platform (nullable)
    with op.batch_alter_table("users") as batch_op:
        try:
            batch_op.add_column(sa.Column("music_platform", sa.String(length=20), nullable=True))
        except Exception:
            pass

    # Recreate tidal_credentials table (structure as before, but empty)
    try:
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
        op.create_unique_constraint("uq_tidal_credentials_user_id", "tidal_credentials", ["user_id"])
        op.create_index(op.f("ix_tidal_credentials_user_id"), "tidal_credentials", ["user_id"], unique=False)
    except Exception:
        pass

