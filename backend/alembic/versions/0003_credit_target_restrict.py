"""credit target restrict

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-06
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("credit_release_id_fkey", "credit", type_="foreignkey")
    op.drop_constraint("credit_recording_id_fkey", "credit", type_="foreignkey")
    op.create_foreign_key(
        "credit_release_id_fkey",
        "credit",
        "release",
        ["release_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "credit_recording_id_fkey",
        "credit",
        "recording",
        ["recording_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("credit_release_id_fkey", "credit", type_="foreignkey")
    op.drop_constraint("credit_recording_id_fkey", "credit", type_="foreignkey")
    op.create_foreign_key(
        "credit_release_id_fkey",
        "credit",
        "release",
        ["release_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "credit_recording_id_fkey",
        "credit",
        "recording",
        ["recording_id"],
        ["id"],
        ondelete="SET NULL",
    )
