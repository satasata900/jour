# خطة عمل قابلة للتنفيذ لمشروع "المراقبة الإخبارية الذكية"

## الأهداف والمخرجات
- منصة تجمع أخبار واتساب/تليغرام، تنظفها، وتصنف أهميتها بدرجة 1-10 باستخدام Gemini، وتعرضها على الويب والجوال.
- واجهة إدارة (React + Tailwind) للتحكم في مصادر الجمع، جداول التشغيل، والإرشادات العامة للوكلاء.
- تطبيق Flutter بمصادقة آمنة، تجربة دردشة Markdown، وتخزين مؤقت لمدة 30 ثانية.
- بنية تحتية قابلة للنشر عبر Docker Compose (FastAPI، PostgreSQL، Redis، خدمة Node للواتساب، Celery إن لزم).

## مراحل العمل (ترتيب تنفيذي)
1) **تهيئة البيئة والبنية التحتية**
   - إنشاء مستودع/تنظيم المجلدات، إضافة `docker-compose.yml` لخدمات: FastAPI، PostgreSQL، Redis، خدمة Node للواتساب. (تم)
   - Add SearXNG service and config to Docker Compose for search agent workflows. (تم)
   - ضبط ملفات البيئة `.env` لكل خدمة (مفاتيح Gemini/Tavily، بيانات DB، مفاتيح Firebase).
   - إعداد أدوات التطوير: `poetry`/`pip` لمكتبات بايثون، `npm` لخدمة الواتساب، `pnpm/yarn` للداشبورد، `flutter` للتطبيق.

2) **تصميم قاعدة البيانات**
   - اعتماد الجداول: Users، News_Archive، Chat_History (حذف تلقائي >30 يوم)، System_Config. (تم)
   - News_Archive: add `author_name` column for sender attribution. (تم)
   - إنشاء مخططات ومهاجرات (Alembic) مع فهارس على الحقول: `timestamp`, `importance_score`, `category`. (تم)
   - إضافة قيود جودة البيانات (NOT NULL، CHECK على مدى `importance_score` 1-10، وENUM لـ `role` و`platform`). (تم)
   - إضافة حقول مساعدة للتنظيف وإزالة التكرار مثل `content_hash` و`clean_content` و`source_message_id`. (تم)
   - تحديد سياسة الاحتفاظ لكل جدول (أرشفة/حذف News_Archive بعد مدة متفق عليها).
   - فهارس مركبة للعرض السريع مثل (`timestamp`, `importance_score`) و(`platform`, `category`). (تم)
   - جداول تشغيل أساسية فقط: `Sources`, `Scraper_Runs`, `User_Devices`, `Notification_Log`. (تم)
   - جداول اختيارية لاحقاً عند الحاجة: `Prompt_Versions`, `Agent_Logs`, `Feedback`, `Audit_Log`, `News_Tags` مع جدول ربط للوسوم.

   - Add summary_period=interval and Telegram subscription columns on users. (تم)
3) **بناء الـ Backend (FastAPI)**
   - حفظ محادثات المستخدم مع إعداد مدة الاحتفاظ (حتى 30 يوم). (تم)
   - Mobile auth endpoints + test user seed for app login. (تم)
   - نماذج/مخططات Pydantic، طبقة CRUD للوصول لـ PostgreSQL.
   - مصادقة أساسية (JWT أو جلسات) وأدوار admin/journalist، مفتاح `X-Gemini-Key` للتطبيق. (تم)
   - Endpoints أساسية: إدارة المستخدمين، مصادر الأخبار، News feed مع ترشيح/فرز، Chat history، System_Config، Webhooks للسكرابر، إشعارات.
   - تفعيل مصادر الأخبار: `GET /sources` و`POST /sources`. (تم)
   - تفعيل إدخال الأخبار والـ Feed: `POST /news` و`GET /news`. (تم)
   - التحقق من صحة الملخصات قبل حذف الرسائل اليومية. (تم)
   - جدولة حذف Chat_History >30 يوم (Celery periodic task أو cron داخل الحاوية).

   - Summary scheduler: 30-min interval + daily/weekly/monthly at 11:55 Homs, cleanup after daily, Telegram sends. (تم)
   - Summaries use OpenRouter with selectable models. (تم)
4) **محرك الجمع (Scraper Engine)**
   - تليغرام: Telethon Client (تسجيل الجلسة)، جلب الرسائل النصية، التطهير والتخزين.
   - Telegram linking deferred until TG_API_ID/TG_API_HASH are available.
   - WhatsApp payload: include group subject as `source_name` and sender as `author_name`. (تم)
   - واتساب: خدمة Node بـ `Baileys`، تخزين جلسة داخل Volume، وWebhook للـ FastAPI. (تم)
   - إظهار QR عبر سجلات الخدمة لربط حساب واتساب. (تم)
   - دعم ربط عبر Pairing Code باستخدام `WA_PHONE_NUMBER` عند الحاجة. (تم)
   - إزالة التكرار (تشابه ≥80%) قبل الإدخال، تسجيل المصدر/المنصة مع الطابع الزمني.

5) **تقييم وترتيب الأخبار**
   - تكامل Gemini (`google-generativeai`) لتوليد `importance_score` وتحديد الفئة.
   - منطق: إذا كان `importance_score >= 8` إرسال Firebase Push Notification للمستخدمين المهتمين.

6) **نظام الوكلاء (LangChain Multi-Agent)**
   - خدمة agents مستقلة (FastAPI) على منفذ 8001 مع المسارات `/agents/run` و`/health`. (تم)
   - Router Agent: توجيه طلب المستخدم (سؤال/تلخيص/بحث) إلى الوكيل المناسب. (تم)
   - Monitor Agent: استعلام SQL على News_Archive لاستخراج أحدث/أهم الأخبار. (تم)
   - Editor Agent: تنسيق الردود إلى تنسيقات مختصرة أو موسعة حسب الحاجة. (تم)
   - استخدام الملخصات تلقائياً عندما لا توجد رسائل حديثة للوكلاء. (تم)
   - Web Search Agent: دمج SearXNG بدل Tavily للمصادر الخارجية. (تم)
   - تشغيل خدمة agents عبر Docker (بناء الصورة وتشغيل الحاوية). (تم)
   - واجهة تحكم الوكلاء داخل الداشبورد (تشغيل/اختبار المسارات). (تم)
   - إدارة تعريفات الوكلاء والبرومبتات (CRUD عبر API + لوحة التحكم). (تم)
   - Post writer agents (official + casual) with strict no-intro/no-markdown output. (تم)
   - OpenRouter agent provider with live model list in dashboard settings. (تم)

7) **واجهة الإدارة (React + Tailwind)**
   - تنظيم قسم المصادر بتبويبات وإضافة إدارة RSS (إضافة/حذف). (تم)
   - صفحات: Live Feed (استعراض الأخبار والبحث/الفرز)، Scraper Control (تشغيل/إيقاف، جداول cron: 5/10/15 د)، Global Prompting (System instructions).
   - Live Feed dashboard section implemented. (تم)
   - Overview stats (total messages + counts by platform/source). (تم)
   - إزالة أقسام Scraper Control و Global Prompting من الداشبورد حسب الطلب. (تم)
   - Live Feed: source filter + author attribution + group naming. (تم)
   - Agents sidebar submenu + Search agent page with SearXNG settings. (تم)
   - إعداد مدة الاحتفاظ بالرسائل الخام من الداشبورد. (تم)
   - صفحة إعدادات مركزية لإدارة المفاتيح وإعدادات الذكاء والاتصال بالمصادر. (تم)
   - ربط إعدادات Telegram/WhatsApp من لوحة الإعدادات عبر System_Config. (تم)
   - دمج API للمصادقة، تحديث System_Config، ومراقبة حالة الخدمات.

   - Settings: Telegram bot delivery panel (token, username, enable). (تم)
   - Settings: OpenRouter model list + free-only filter for summary/agent models. (تم)
8) **تطبيق Flutter**
   - New `mobile_app` Flutter client: RTL dark chat, login, drawer (settings + agents). (تم)
   - مصادقة وتخزين آمن للمفاتيح بـ `flutter_secure_storage`. (تم)
   - شاشة دردشة تعرض Markdown، كاش TTL=30 ثانية للردود.
   - استدعاء API مع Header `X-Gemini-Key`. (تم)
   - التعامل مع الحالات غير المتصلة.

   - Telegram linking + summary preferences in mobile settings (deep link + toggles). (تم)
   - Post writer chat screen + summary import + copy button for outputs. (تم)
9) **المراقبة والجودة**
   - سجلات وهيكلة أخطاء في كل خدمة، تنبيهات عند فشل السكرابر أو الوكلاء.
   - اختبارات: وحدات لـ CRUD والمنطق، تكامل لـ مسارات API الرئيسية، وتشغيلها في CI.

10) **الإطلاق والتوثيق**
    - توحيد قوالب `.env.example`، وثيقة تشغيل محلية/إنتاجية. (تم)
    - تحديث ملف `requirements.md` لتوثيق متطلبات الإنتاج. (تم)
    - تجربة تشغيل كاملة عبر `docker-compose up`، والتحقق من تدفق: جمع → تخزين → تصنيف → إشعار → عرض.

    - Update .env.example with TG_BOT_* and summary timezone defaults. (تم)
## أولويات البدء (أسبوع 1)
1. إعداد المستودع، `docker-compose.yml`، وملفات البيئة. (تم)
2. بناء مخطط قاعدة البيانات والمهاجرات. (تم)
3. إنشاء FastAPI بهيكل الحزم، مصادقة بسيطة، ونقاط نهاية placeholder. (تم)
4. تفعيل Telethon لجلب رسائل أولية وتخزينها في News_Archive. (deferred - waiting for TG_API_ID/TG_API_HASH)
