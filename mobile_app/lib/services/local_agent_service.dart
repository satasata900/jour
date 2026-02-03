import 'package:google_generative_ai/google_generative_ai.dart';

import '../database_helper.dart';
import '../models/chat_message.dart';
import '../models/mobile_config.dart';
import '../models/summary_entry.dart';

class LocalAgentService {
  final DatabaseHelper _db;
  GenerativeModel? _model;
  // Memory for current session
  final List<Content> _history = [];

  LocalAgentService() : _db = DatabaseHelper();

  void clearHistory() {
    _history.clear();
  }

  void seedHistory(List<ChatMessage> messages) {
    _history.clear();
    for (final message in messages) {
      if (message.role == ChatRole.user) {
        _history.add(Content('user', [TextPart(message.content)]));
      } else if (message.role == ChatRole.assistant) {
        _history.add(Content('model', [TextPart(message.content)]));
      }
    }
  }

  void init(String apiKey, MobileConfig config) {
    _model = GenerativeModel(
      model: config.model,
      apiKey: apiKey,
      generationConfig: GenerationConfig(
        maxOutputTokens: config.maxTokens,
        temperature: config.temperature,
      ),
      safetySettings: [
        SafetySetting(HarmCategory.harassment, HarmBlockThreshold.none),
        SafetySetting(HarmCategory.hateSpeech, HarmBlockThreshold.none),
        SafetySetting(HarmCategory.sexuallyExplicit, HarmBlockThreshold.none),
        SafetySetting(HarmCategory.dangerousContent, HarmBlockThreshold.none),
      ],
      systemInstruction: Content.system(
        "${config.systemPrompt}\n\n"
        "قواعد صارمة:\n"
        "1. لا تستخدم النجوم (*) في التنسيق.\n"
        "2. كن مباشراً: لا مقدمات ولا خواتم.\n"
        "3. قدم المعلومات بشكل ملخص وسهل القراءة.\n"
        "4. أنت 'مساعد الصحفي' (أنشأه حسان قدور - أبو نوح).",
      ),
    );
  }

  Future<String> chat(String userMessage) async {
    if (_model == null) {
      return "يرجى إعداد مفتاح API في الإعدادات أولاً.";
    }

    try {
      // 1. Fetch relevant context
      final summaries = await _fetchContext(userMessage);

      final contextBuffer = StringBuffer();
      if (summaries.isNotEmpty) {
        contextBuffer.writeln("السياق الإخباري المتوفر من قاعدة البيانات:");
        for (var s in summaries) {
          contextBuffer.writeln("- [${s.periodType}] ${s.content}");
        }
      }

      // 2. Build the final prompt with context separation
      String fullPrompt;
      if (summaries.isEmpty) {
        // Force conversational mode if no news context is found
        fullPrompt = "User says: '$userMessage'\n"
            "This is a casual chat message. Reply naturally and briefly in Arabic. "
            "Do NOT offer news unless explicitly asked. Do NOT say 'How can I help you' if it's just a greeting.";
      } else {
        fullPrompt = "${contextBuffer.toString()}\n\n"
            "بناءً على السياق أعلاه، أجب على حوار المستخدم التالي بوضوح واختصار: $userMessage";
      }

      // 3. Use Chat Session for Memory
      final chatSession = _model!.startChat(history: _history);
      final response = await chatSession.sendMessage(Content.text(fullPrompt));

      final responseText =
          response.text?.replaceAll('*', '').trim() ?? "رد فارغ.";

      // 4. Update memory (Full history enabled)
      _history.add(Content('user', [TextPart(userMessage)]));
      _history.add(Content('model', [TextPart(responseText)]));

      print("DEBUG Agent: Found ${summaries.length} summaries in DB context.");
      return responseText;
    } catch (e) {
      if (e.toString().contains("API_KEY_INVALID")) {
        return "مفتاح API غير صالح. يرجى التحقق من الإعدادات.";
      }
      return "حدث خطأ: $e";
    }
  }

  Future<List<SummaryEntry>> _fetchContext(String query) async {
    // 1. Ignore very short context lookups (e.g. conversational greetings)
    if (query.trim().length < 3) {
      print("DEBUG: Query too short ('$query'), skipping context search.");
      return [];
    }

    final dateRange = _detectDateRange(query);
    final isGeneral = _isGeneralNewsQuery(query);

    if (isGeneral) {
      return await _db.getRecentSummaries(limit: 50);
    } else if (dateRange != null) {
      return await _db.getSummariesByDateRange(dateRange.$1, dateRange.$2);
    } else {
      // 2. Specific search
      // Only return search results if they actually exist.
      // Do NOT fallback to recent news, as it confuses general chat.
      return await _db.searchSummaries(query);
    }
  }

  // Helper to detect simple date references
  (DateTime, DateTime)? _detectDateRange(String query) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final text = query.toLowerCase();

    if (text.contains("اليوم") || text.contains("today")) {
      // Use last 24 hours for "today" to ensure we catch recent news across timezones
      return (now.subtract(const Duration(hours: 24)), now);
    }

    if (text.contains("أمس") ||
        text.contains("yesterday") ||
        text.contains("البارحة") ||
        text.contains("امبارح")) {
      final startOfToday = DateTime(now.year, now.month, now.day);
      final yesterday = startOfToday.subtract(const Duration(days: 1));
      return (yesterday, startOfToday.subtract(const Duration(seconds: 1)));
    }

    if (text.contains("أسبوع") || text.contains("week")) {
      final lastWeek = today.subtract(const Duration(days: 7));
      return (lastWeek, now);
    }

    return null;
  }

  bool _isGeneralNewsQuery(String text) {
    final t = text.toLowerCase();
    final keywords = [
      'أخبار',
      'اخبار',
      'الأخبار',
      'الاخبار',
      'وضع',
      'جديد',
      'ملخص',
      'صار',
      'حدث',
      'أحداث',
      'احداث',
      'تطورات',
      'مستجدات',
      'news',
      'latest',
      'update',
      'happening',
      'summary',
      'brief',
      'report',
    ];
    for (final k in keywords) {
      if (t.contains(k)) return true;
    }
    return false;
  }
}
