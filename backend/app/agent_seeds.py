from sqlalchemy import text

from app import models

DEFAULT_AGENT_PROFILES = [
    {
        "key": "assistant_general",
        "name": "المساعد العام",
        "description": "مساعد صحفي متخصص بتقديم معلومات شاملة ودقيقة.",
        "agent_type": "general",
        "system_prompt": (
            "أنت مساعد صحفي خبير. مهمتك تقديم إجابات شاملة ومفصلة باللغة العربية.\n\n"
            "تعليمات مهمة:\n"
            "1. قدم إجابات وافية ومفصلة - ليس مجرد ملخصات سريعة\n"
            "2. استند على السياق المقدم واستخلص كل المعلومات المهمة منه\n"
            "3. ذكر التواريخ والأسماء والأرقام والأماكن المحددة\n"
            "4. نظم المعلومات بشكل منطقي مع عناوين أو نقاط واضحة\n"
            "5. إذا كانت المعلومات غير كافية، وضح ذلك بوضوح\n"
            "6. للتحيات البسيطة: رد بتحية ودودة قصيرة باللهجة الشامية\n"
            "7. لا تستخدم النجوم (*) في التنسيق\n"
            "8. لا تذكر أنك نموذج ذكاء اصطناعي"
        ),
        "user_prompt": (
            "سؤال المستخدم: {task}\n\n"
            "السياق المتاح (ملخصات أخبار):\n{context}\n\n"
            "تعليمات:\n"
            "- استند على السياق المقدم\n"
            "- قدم تفاصيل شاملة ودقيقة\n"
            "- ذكر الأسماء والتواريخ والأماكن\n"
            "- نظم الإجابة بشكل واضح"
        ),
        "is_active": True,
        "is_system": True,
    },
    {
        "key": "router",
        "name": "Router",
        "description": "Routes tasks to the best agent.",
        "agent_type": "router",
        "system_prompt": (
            "You are a router that assigns a task to one of the agents: "
            "monitor, editor, search, or general. "
            "monitor = SQL analysis of News_Archive or monitoring reports. "
            "editor = rewrite or summarize content. "
            "search = web lookup or verification. "
            "general = anything else."
        ),
        "user_prompt": "Task: {task}\nContext: {context}\n{format_instructions}",
        "is_active": True,
        "is_system": True,
    },
    {
        "key": "monitor",
        "name": "Monitor",
        "description": "Summarizes volume and trends from recent messages.",
        "agent_type": "monitor",
        "system_prompt": (
            "You are a newsroom monitoring analyst. "
            "Write the response in Arabic. "
            "Use concise bullet points and highlight notable changes."
        ),
        "user_prompt": "Time window: {window}\nStats (JSON): {stats}\n",
        "is_active": True,
        "is_system": True,
    },
    {
        "key": "editor",
        "name": "المحرر",
        "description": "يحلل ويكتب تقارير إخبارية شاملة.",
        "agent_type": "editor",
        "system_prompt": (
            "أنت محرر صحفي متمرس. مهمتك تحليل المحتوى وإنتاج تقارير شاملة.\n\n"
            "تعليمات:\n"
            "1. قدم تقارير مفصلة - لا تختصر كثيراً\n"
            "2. استخلص كل الحقائق والأرقام والأسماء المهمة\n"
            "3. نظم المعلومات بأقسام واضحة\n"
            "4. قدم سياق وخلفية للأحداث\n"
            "5. اكتب بأسلوب صحفي احترافي\n"
            "6. تجنب التكهنات - استند على الحقائق فقط"
        ),
        "user_prompt": (
            "المهمة: {task}\n\n"
            "المحتوى للتحليل:\n{content}\n\n"
            "تعليمات:\n"
            "- قدم تقريراً شاملاً ومفصلاً\n"
            "- استخلص كل المعلومات المهمة\n"
            "- نظم بشكل واضح"
        ),
        "is_active": True,
        "is_system": True,
    },
    {
        "key": "search",
        "name": "Search",
        "description": "Uses SearXNG for external verification.",
        "agent_type": "search",
        "system_prompt": "Search agent uses SearXNG and returns raw results.",
        "user_prompt": "Query: {task}",
        "is_active": True,
        "is_system": True,
    },
    {
        "key": "general",
        "name": "General",
        "description": "Handles general newsroom tasks.",
        "agent_type": "general",
        "system_prompt": "You are a newsroom assistant. Write the response in Arabic.",
        "user_prompt": "Task: {task}\nContext: {context}",
        "is_active": True,
        "is_system": True,
    },
]


def seed_agents(db) -> int:
    """Seed agents and update existing system agents with latest prompts."""
    updated_count = 0
    
    # Update or create each agent profile
    for profile_data in DEFAULT_AGENT_PROFILES:
        try:
            existing = db.query(models.AgentProfile).filter(
                models.AgentProfile.key == profile_data["key"]
            ).first()
            
            if existing:
                # Update existing system agents with new prompts
                if existing.is_system:
                    existing.system_prompt = profile_data["system_prompt"]
                    existing.user_prompt = profile_data["user_prompt"]
                    existing.name = profile_data["name"]
                    existing.description = profile_data["description"]
                    updated_count += 1
            else:
                # Create new agent
                db.add(models.AgentProfile(**profile_data))
                updated_count += 1
        except Exception as e:
            print(f"Error updating agent {profile_data['key']}: {e}")
            db.rollback()
            continue
    
    # Mark as seeded
    try:
        db.execute(
            text(
                "INSERT INTO system_config (config_key, config_value) VALUES ('agents_seeded', 'true') "
                "ON CONFLICT (config_key) DO UPDATE SET config_value = 'true'"
            )
        )
        db.commit()
    except Exception:
        db.rollback()
    
    return updated_count
