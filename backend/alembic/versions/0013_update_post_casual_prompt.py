"""Refine post casual agent prompt.

Revision ID: 0013_update_post_casual_prompt
Revises: 0012_update_post_official_prompt
Create Date: 2026-02-03
"""

from alembic import op

revision = "0013_update_post_casual_prompt"
down_revision = "0012_update_post_official_prompt"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE agent_profiles
        SET
            description = 'يصوغ بوست عادي واضح وسلس بلهجة عربية سهلة.',
            system_prompt = 'أنت محرر منصات اجتماعية. اكتب بوستاً عادياً بأسلوب عربي مبسّط ودود وأقل رسمية، اعتماداً على المعلومات المقدمة فقط دون أي افتراضات. ابدأ بالخبر مباشرة وبأسلوب واضح وقريب من الناس. استخدم 3-6 جمل قصيرة، وفضّل الجمل الفعلية. اذكر المكان والزمن والأرقام أو الأسماء إن وُجدت. ممنوع: مقدمات أو خواتيم، أسئلة للجمهور، عناوين أو تعداد أو نقاط أو رموز أو إيموجي، تنسيق Markdown أو علامات نجمة (*). لا تذكر أنك نموذج ذكاء اصطناعي.',
            user_prompt = 'المطلوب: {task}\nالمادة الخام:\n{context}\nاكتب النص النهائي فقط.'
        WHERE key = 'post_casual';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE agent_profiles
        SET
            description = 'يصوغ بوست عادي مباشر وسهل القراءة.',
            system_prompt = 'أنت محرر منصات اجتماعية. اكتب بوستاً عادياً مباشراً بالعربية السهلة اعتماداً على المعلومات المقدمة فقط دون أي افتراضات. ابدأ بالخبر مباشرة وبأسلوب واضح وقريب. اجعل النص قصيراً وسلساً (3-6 جمل قصيرة). ممنوع: مقدمات أو خواتيم، عناوين أو تعداد أو نقاط أو رموز، تنسيق Markdown أو علامات نجمة (*). لا تذكر أنك نموذج ذكاء اصطناعي.',
            user_prompt = 'المطلوب: {task}\nالسياق المتاح:\n{context}'
        WHERE key = 'post_casual';
        """
    )
