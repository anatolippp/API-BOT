"""Initial migration222

Revision ID: fb3bf5b4762d
Revises: 480d3b927fba
Create Date: 2025-03-13 15:56:28.139765

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'fb3bf5b4762d'
down_revision: Union[str, None] = '480d3b927fba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("creator_id", sa.Integer(), sa.ForeignKey("telegram_users.id"), nullable=False),
    )

    op.create_table(
        "project_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("telegram_users.id"), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="admin"),
    )

    op.create_table(
        "search_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("telegram_users.id"), nullable=False),
        sa.Column("query_text", sa.String(500), nullable=False),
        sa.Column("results_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )




def downgrade() -> None:
    op.drop_table("search_history")
    op.drop_table("project_members")
    op.drop_table("projects")
