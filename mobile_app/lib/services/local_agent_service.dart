import 'package:google_generative_ai/google_generative_ai.dart';

import '../database_helper.dart';
import '../models/chat_message.dart';
import '../models/mobile_config.dart';
import '../models/summary_entry.dart';

class LocalAgentService {
  final DatabaseHelper _db;
  GenerativeModel? _model;
  // Memory for current session - limited to prevent token bloat
  final List<Content> _history = [];
  static const int _maxHistoryMessages =
      20; // Keep last 10 exchanges (20 messages)

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
    _truncateHistory();
  }

  void _truncateHistory() {
    if (_history.length > _maxHistoryMessages) {
      // Remove oldest messages (keep pairs together)
      final excess = _history.length - _maxHistoryMessages;
      _history.removeRange(0, excess);
    }
  }

  void init(String apiKey, MobileConfig config) {
    // Cap max tokens to save costs - most responses don't need more than 800
    final maxTokens = (config.maxTokens > 800) ? 800 : config.maxTokens;

    _model = GenerativeModel(
      model: config.model,
      apiKey: apiKey,
      generationConfig: GenerationConfig(
        maxOutputTokens: maxTokens,
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
        "تعليمات إضافية للجودة:\n"
        "1. لا تستخدم النجوم (*) في التنسيق\n"
        "2. قدم إجابات شاملة ومفصلة - ليس فقط ملخصات سريعة\n"
        "3. استند دائماً على السياق المقدم\n"
        "4. ذكر التواريخ والأسماء والأرقام المحددة\n"
        "5. نظم المعلومات بشكل واضح مع عناوين أو نقاط\n"
        "6. إذا كانت المعلومات غير كافية، وضح ذلك بوضوح\n"
        "7. أنت 'مساعد الصحفي' (أنشأه حسان قدور - أبو نوح).",
      ),
    );
  }

  Future<String> chat(String userMessage) async {
    if (_model == null) {
      return "يرجى إعداد مفتاح API في الإعدادات أولاً.";
    }

    try {
      // 1. Fetch relevant context (only if needed)
      String? contextStr;
      if (_needsContext(userMessage)) {
        final summaries = await _fetchContext(userMessage);
        if (summaries.isNotEmpty) {
          final buffer = StringBuffer("سياق:");
          for (var s in summaries.take(2)) {
            // Reduced from unlimited to 2
            final content = s.content.length > 200
                ? "${s.content.substring(0, 200)}..."
                : s.content;
            buffer.write(" $content");
          }
          contextStr = buffer.toString();
        }
      }

      // 2. Build the final prompt efficiently
      String fullPrompt;
      if (contextStr == null) {
        // Force conversational mode if no news context is found
        fullPrompt = "$userMessage";
      } else {
        fullPrompt = "$contextStr | سؤال: $userMessage";
      }

      // 3. Use Chat Session for Memory
      final chatSession = _model!.startChat(history: _history);
      final response = await chatSession.sendMessage(Content.text(fullPrompt));

      final responseText =
          response.text?.replaceAll('*', '').trim() ?? "رد فارغ.";

      // 4. Update memory (Limited history to save tokens)
      _history.add(Content('user', [TextPart(userMessage)]));
      _history.add(Content('model', [TextPart(responseText)]));
      _truncateHistory(); // Keep history size manageable

      print("DEBUG Agent: History size: ${_history.length} messages");
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

    // Use SMART context search first (extracts only relevant lines)
    final snippets = await _db.searchSmartContext(query, maxSnippets: 3);
    if (snippets.isNotEmpty) {
      // Convert snippets back to SummaryEntry format for compatibility
      return snippets
          .map((s) => SummaryEntry(
                id: 0,
                periodType: s.periodType,
                periodStart: s.periodStart,
                periodEnd: s.periodStart,
                content: s.snippet,
                createdAt: DateTime.now(),
              ))
          .toList();
    }

    final dateRange = _detectDateRange(query);
    final isGeneral = _isGeneralNewsQuery(query);

    if (isGeneral) {
      // Fallback: get recent summaries but extract only first 150 chars
      final summaries = await _db.getRecentSummaries(limit: 2);
      return summaries
          .map((s) => SummaryEntry(
                id: s.id,
                periodType: s.periodType,
                periodStart: s.periodStart,
                periodEnd: s.periodEnd,
                content: s.content.length > 150
                    ? '${s.content.substring(0, 150)}...'
                    : s.content,
                createdAt: s.createdAt,
              ))
          .toList();
    } else if (dateRange != null) {
      return await _db.getSummariesByDateRange(dateRange.$1, dateRange.$2);
    } else {
      // 2. Specific search
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

  bool _needsContext(String query) {
    final lower = query.toLowerCase();
    final contextKeywords = [
      'خبر',
      'أخبار',
      'news',
      'حدث',
      'حصل',
      'صار',
      'أمس',
      'اليوم',
      'وزير',
      'رئيس',
      'حكومة',
      'بلد',
      'قرار',
      'قانون',
      'حادث',
      'مباراة',
      'فريق',
      'منتخب',
      'سوريا',
      'لبنان',
      'أمريكا',
      'company',
      'report',
      'announced',
      'launched',
      'released',
    ];
    for (final keyword in contextKeywords) {
      if (lower.contains(keyword)) return true;
    }
    return false;
  }
}
