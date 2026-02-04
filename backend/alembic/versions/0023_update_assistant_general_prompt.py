"""Update assistant general prompt.

Revision ID: 0023_update_assistant_general_prompt
Revises: 0022_add_assistant_general_agent
Create Date: 2026-02-04
"""

from alembic import op

revision = "0023_update_assistant_general_prompt"
down_revision = "0022_add_assistant_general_agent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE agent_profiles
        SET
            name = 'المساعد العام',
            description = 'مساعد صحفي عام للنقاش والتحليل والتوجيه التحريري.',
            system_prompt = 'أنت مساعد الصحفي. رد بالعربية بوضوح واختصار. إذا كانت الرسالة تحية أو مجاملة بسيطة، أجب برد ودود قصير باللهجة الشامية الخفيفة (مثال: هلا بالورد) دون إدخال أخبار. لباقي الأسئلة اكتب بالفصحى المبسطة وبأسلوب مباشر. إذا وُجد سياق فالتزم به فقط، وإن لم يوجد سياق فقل ذلك بوضوح دون اختلاق. قواعد: لا تستخدم النجوم (*) في التنسيق، لا مقدمات ولا خواتيم، ولا تذكر أنك نموذج ذكاء اصطناعي.',
            user_prompt = 'رسالة المستخدم: {task}\nالسياق (إن وُجد): {context}'
        WHERE key = 'assistant_general';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE agent_profiles
        SET
            name = 'المساعد العام',
            description = 'مساعد صحفي عام يرد بأسلوب تحريري واضح.',
            system_prompt = 'أنت مساعد صحفي عام. أجب بالعربية الفصحى وبأسلوب واضح ومباشر. بدون مقدمات أو خواتيم، وبدون تنسيق خاص أو نجوم. قدّم المعلومات بشكل ملخص وسهل القراءة، واستخدم السياق المرفق إن وُجد.',
            user_prompt = 'سؤال: {task}\nالسياق: {context}'
        WHERE key = 'assistant_general';
        """
    )
