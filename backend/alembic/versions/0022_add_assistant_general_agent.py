"""Add assistant general agent profile.

Revision ID: 0022_add_assistant_general_agent
Revises: 0021_chat_tables
Create Date: 2026-02-04
"""

from alembic import op

revision = "0022_add_assistant_general_agent"
down_revision = "0021_chat_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO agent_profiles (key, name, description, agent_type, system_prompt, user_prompt, is_active, is_system)
        SELECT
            'assistant_general',
            'المساعد العام',
            'مساعد صحفي عام يرد بأسلوب تحريري واضح.',
            'general',
            'أنت مساعد صحفي عام. أجب بالعربية الفصحى وبأسلوب واضح ومباشر. بدون مقدمات أو خواتيم، وبدون تنسيق خاص أو نجوم. قدّم المعلومات بشكل ملخص وسهل القراءة، واستخدم السياق المرفق إن وُجد.',
            'سؤال: {task}\nالسياق: {context}',
            TRUE,
            TRUE
        WHERE NOT EXISTS (
            SELECT 1 FROM agent_profiles WHERE key = 'assistant_general'
        );
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM agent_profiles WHERE key = 'assistant_general';")
