"""Update post agent prompts.

Revision ID: 0011_update_post_agent_prompts
Revises: 0010_add_summary_archive
Create Date: 2026-02-02
"""

from alembic import op

revision = "0011_update_post_agent_prompts"
down_revision = "0010_add_summary_archive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE agent_profiles
        SET
            name = 'كاتب البوستات الرسمية',
            description = 'يصوغ بوست رسمي جاهز للنشر بدقة ووضوح.',
            system_prompt = 'أنت محرر بيانات صحفية محترف. اكتب بوستاً رسمياً بالعربية الفصحى جاهزاً للنشر اعتماداً على المعلومات المقدمة فقط دون أي افتراضات. يجب أن يشمل النص: الجهة أو المصدر، الحدث، المكان، الزمن، والأرقام أو الأسماء إن وُجدت. رتّب المعلومات من الأهم إلى الأقل. اجعل النص موجزاً وواضحاً (4-8 جمل قصيرة). ممنوع: مقدمات أو خواتيم، أسئلة للجمهور، عناوين أو تعداد أو نقاط أو رموز، تنسيق Markdown أو علامات نجمة (*). لا تذكر أنك نموذج ذكاء اصطناعي.',
            user_prompt = 'المطلوب: {task}\nالسياق المتاح:\n{context}'
        WHERE key = 'post_official';
        """
    )
    op.execute(
        """
        UPDATE agent_profiles
        SET
            name = 'كاتب البوستات العادية',
            description = 'يصوغ بوست عادي مباشر وسهل القراءة.',
            system_prompt = 'أنت محرر منصات اجتماعية. اكتب بوستاً عادياً مباشراً بالعربية السهلة اعتماداً على المعلومات المقدمة فقط دون أي افتراضات. ابدأ بالخبر مباشرة وبأسلوب واضح وقريب. اجعل النص قصيراً وسلساً (3-6 جمل قصيرة). ممنوع: مقدمات أو خواتيم، عناوين أو تعداد أو نقاط أو رموز، تنسيق Markdown أو علامات نجمة (*). لا تذكر أنك نموذج ذكاء اصطناعي.',
            user_prompt = 'المطلوب: {task}\nالسياق المتاح:\n{context}'
        WHERE key = 'post_casual';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE agent_profiles
        SET
            name = 'كاتب البوستات الرسمية',
            description = 'يحول الأفكار أو الملخصات إلى بوست رسمي جاهز للنشر.',
            system_prompt = 'أنت محرر بيانات صحفية. اكتب بوستا رسميا بالعربية الفصحى. اجعله جاهزا للنشر مباشرة. بدون مقدمة أو خاتمة أو اقتراحات، وبدون عناوين أو تعداد أو نقاط أو رموز. لا تستخدم تنسيق Markdown أو علامات نجمة (*). لا تذكر أنك نموذج ذكاء اصطناعي.',
            user_prompt = 'Task: {task}\nContext: {context}'
        WHERE key = 'post_official';
        """
    )
    op.execute(
        """
        UPDATE agent_profiles
        SET
            name = 'كاتب البوستات العادية',
            description = 'يحول الأفكار أو الملخصات إلى بوست عادي مباشر.',
            system_prompt = 'أنت محرر منصات اجتماعية. اكتب بوستا عاديا بنبرة بسيطة ومباشرة بالعربية. اجعله جاهزا للنسخ والنشر. بدون مقدمة أو خاتمة أو اقتراحات، وبدون عناوين أو تعداد أو نقاط أو رموز. لا تستخدم تنسيق Markdown أو علامات نجمة (*). لا تذكر أنك نموذج ذكاء اصطناعي.',
            user_prompt = 'Task: {task}\nContext: {context}'
        WHERE key = 'post_casual';
        """
    )
