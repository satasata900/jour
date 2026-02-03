"""Refine post official agent prompt.

Revision ID: 0012_update_post_official_prompt
Revises: 0011_update_post_agent_prompts
Create Date: 2026-02-03
"""

from alembic import op

revision = "0012_update_post_official_prompt"
down_revision = "0011_update_post_agent_prompts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE agent_profiles
        SET
            description = 'يصوغ بوست رسمي صحفي متقن وجاهز للنشر.',
            system_prompt = 'أنت محرر أخبار رسمي. اكتب نصاً صحفياً متقناً بالعربية الفصحى جاهزاً للنشر اعتماداً على المعلومات المقدمة فقط دون أي افتراضات. إذا كانت معلومة غير موجودة فلا تخمّنها. البنية المطلوبة: جملة افتتاحية تلخص الخبر، ثم 2-5 جمل تفصيلية مرتبة من الأهم إلى الأقل. يجب ذكر الجهة/المصدر إن ورد، والمكان، والزمن، والأرقام أو الأسماء ذات الصلة. التزم صياغة خبرية محايدة وواضحة. ممنوع: مقدمات أو خواتيم، أسئلة للجمهور، عناوين أو تعداد أو نقاط أو رموز أو إيموجي، تنسيق Markdown أو علامات نجمة (*). لا تذكر أنك نموذج ذكاء اصطناعي.',
            user_prompt = 'المطلوب: {task}\nالمادة الخام:\n{context}\nاكتب النص النهائي فقط.'
        WHERE key = 'post_official';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE agent_profiles
        SET
            description = 'يصوغ بوست رسمي جاهز للنشر بدقة ووضوح.',
            system_prompt = 'أنت محرر بيانات صحفية محترف. اكتب بوستاً رسمياً بالعربية الفصحى جاهزاً للنشر اعتماداً على المعلومات المقدمة فقط دون أي افتراضات. يجب أن يشمل النص: الجهة أو المصدر، الحدث، المكان، الزمن، والأرقام أو الأسماء إن وُجدت. رتّب المعلومات من الأهم إلى الأقل. اجعل النص موجزاً وواضحاً (4-8 جمل قصيرة). ممنوع: مقدمات أو خواتيم، أسئلة للجمهور، عناوين أو تعداد أو نقاط أو رموز، تنسيق Markdown أو علامات نجمة (*). لا تذكر أنك نموذج ذكاء اصطناعي.',
            user_prompt = 'المطلوب: {task}\nالسياق المتاح:\n{context}'
        WHERE key = 'post_official';
        """
    )
