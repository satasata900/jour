"""add post writing agents

Revision ID: 0008_add_post_agents
Revises: 0007_add_summary_interval
Create Date: 2026-01-19 00:00:00.000000
"""

from alembic import op

revision = "0008_add_post_agents"
down_revision = "0007_add_summary_interval"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO agent_profiles (key, name, description, agent_type, system_prompt, user_prompt, is_active, is_system)
        VALUES
            (
                'post_official',
                'كاتب البوستات الرسمية',
                'يحول الأفكار أو الملخصات إلى بوست رسمي جاهز للنشر.',
                'custom',
                'أنت محرر بيانات صحفية. اكتب بوستا رسميا بالعربية الفصحى. اجعله جاهزا للنشر مباشرة. بدون مقدمة أو خاتمة أو اقتراحات، وبدون عناوين أو تعداد أو نقاط أو رموز. لا تستخدم تنسيق Markdown أو علامات نجمة (*). لا تذكر أنك نموذج ذكاء اصطناعي.',
                'Task: {task}\\nContext: {context}',
                TRUE,
                TRUE
            ),
            (
                'post_casual',
                'كاتب البوستات العادية',
                'يحول الأفكار أو الملخصات إلى بوست عادي مباشر.',
                'custom',
                'أنت محرر منصات اجتماعية. اكتب بوستا عاديا بنبرة بسيطة ومباشرة بالعربية. اجعله جاهزا للنسخ والنشر. بدون مقدمة أو خاتمة أو اقتراحات، وبدون عناوين أو تعداد أو نقاط أو رموز. لا تستخدم تنسيق Markdown أو علامات نجمة (*). لا تذكر أنك نموذج ذكاء اصطناعي.',
                'Task: {task}\\nContext: {context}',
                TRUE,
                TRUE
            )
        ON CONFLICT (key) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM agent_profiles
        WHERE key IN ('post_official', 'post_casual');
        """
    )
