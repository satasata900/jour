"""Add interval summaries and Telegram subscription fields.

Revision ID: 0007_add_summary_interval
Revises: 0006_add_rss_platform
Create Date: 2026-01-22 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0007_add_summary_interval"
down_revision = "0006_add_rss_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE summary_period ADD VALUE IF NOT EXISTS 'interval';")
    op.add_column("users", sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True))
    op.add_column("users", sa.Column("telegram_username", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("telegram_link_token", sa.String(length=64), nullable=True))
    op.add_column(
        "users", sa.Column("telegram_linked_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column(
            "telegram_daily_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "telegram_weekly_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "telegram_monthly_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_unique_constraint(
        "uq_users_telegram_chat_id", "users", ["telegram_chat_id"]
    )
    op.create_unique_constraint(
        "uq_users_telegram_link_token", "users", ["telegram_link_token"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_users_telegram_link_token", "users", type_="unique")
    op.drop_constraint("uq_users_telegram_chat_id", "users", type_="unique")
    op.drop_column("users", "telegram_monthly_enabled")
    op.drop_column("users", "telegram_weekly_enabled")
    op.drop_column("users", "telegram_daily_enabled")
    op.drop_column("users", "telegram_linked_at")
    op.drop_column("users", "telegram_link_token")
    op.drop_column("users", "telegram_username")
    op.drop_column("users", "telegram_chat_id")
