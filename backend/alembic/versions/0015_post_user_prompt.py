"""Update post agent user prompts.

Revision ID: 0015_post_user_prompt
Revises: 0014_post_official_prompt
Create Date: 2026-02-03
"""

from alembic import op

revision = "0015_post_user_prompt"
down_revision = "0014_post_official_prompt"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE agent_profiles
        SET user_prompt = 'المطلوب: {task}\nالسياق (إن وُجد):\n{context}\nاكتب النص النهائي فقط بدون أي تسميات أو عناوين.'
        WHERE key IN ('post_official', 'post_casual');
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE agent_profiles
        SET user_prompt = 'المطلوب: {task}\nالمادة الخام:\n{context}\nاكتب النص النهائي فقط.'
        WHERE key IN ('post_official', 'post_casual');
        """
    )
