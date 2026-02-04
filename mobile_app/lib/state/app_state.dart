import "dart:async";

import "package:flutter/material.dart";

import "../models/chat_message.dart";
import "../models/telegram_preferences.dart";
import "../models/user.dart";
import "../services/api_service.dart";
import "../services/secure_storage_service.dart";
import "../services/sync_service.dart";
import "../services/local_agent_service.dart";

class AppState extends ChangeNotifier {
  final ApiService apiService;
  final SecureStorageService storage;

  User? currentUser;
  String? authToken;
  bool initializing = true;
  bool isBusy = false;
  bool isSending = false;
  String? geminiKey;
  final List<ChatMessage> messages = [];
  int chatRetentionDays = 7;
  int chatRetentionMin = 1;
  int chatRetentionMax = 30;
  TelegramPreferences? telegramPreferences;
  late final SyncService syncService;
  late final LocalAgentService localAgentService;
  Timer? _syncTimer;
  static const String defaultAgentKey = "assistant_general";

  AppState({required this.apiService, required this.storage}) {
    syncService = SyncService(apiService);
    localAgentService = LocalAgentService();
  }

  bool get isAuthenticated => currentUser != null;

  Future<void> _updateCurrentSessionId(int? sessionId) async {
    currentSessionId = sessionId;
    if (currentUser == null) {
      return;
    }
    if (sessionId == null) {
      await storage.clearChatSessionId(currentUser!.id);
    } else {
      await storage.saveChatSessionId(currentUser!.id, sessionId);
    }
  }

  int? _parseSessionId(dynamic value) {
    if (value is int) {
      return value;
    }
    if (value is num) {
      return value.toInt();
    }
    if (value is String) {
      return int.tryParse(value.trim());
    }
    return null;
  }

  Future<void> loadSession() async {
    initializing = true;
    notifyListeners();
    final token = await storage.readToken();
    if (token != null && token.isNotEmpty) {
      try {
        final user = await apiService.getProfile(token);
        authToken = token;
        currentUser = user;
        geminiKey = await storage.readGeminiKeyForUser(user.username);
        if (geminiKey == null) {
          final legacy = await storage.readGeminiKey();
          final storedEmail = await storage.readEmail();
          if (legacy != null && storedEmail != null) {
            if (storedEmail.trim().toLowerCase() ==
                user.username.toLowerCase()) {
              await storage.saveGeminiKeyForUser(user.username, legacy);
              await storage.clearLegacyGeminiKey();
              geminiKey = legacy;
            }
          }
        }

        try {
          syncService.syncSummaries(token: token);
        } catch (e) {
          print("Failed to sync summaries: $e");
        }

        // Start periodic sync every 30 minutes
        _syncTimer?.cancel();
        _syncTimer = Timer.periodic(const Duration(minutes: 30), (timer) {
          if (isAuthenticated) {
            print("Running periodic sync...");
            syncService.syncSummaries(token: authToken);
          }
        });

        // Initialize Local Agent only when key exists
        if (geminiKey != null) {
          try {
            final config = await apiService.fetchMobileConfig(token: token);
            localAgentService.init(geminiKey!, config);
          } catch (e) {
            print("Failed to init local agent: $e");
          }
        }
      } catch (_) {
        await storage.clearAuth();
        authToken = null;
        currentUser = null;
      }
    }
    initializing = false;
    notifyListeners();
  }

  Future<String?> login(String email, String password) async {
    isBusy = true;
    notifyListeners();
    try {
      final result = await apiService.login(email, password);
      authToken = result.token;
      currentUser = result.user;
      await storage.saveToken(result.token);
      await storage.saveEmail(email);
      geminiKey = await storage.readGeminiKeyForUser(result.user.username);

      try {
        syncService.syncSummaries(token: result.token);
      } catch (e) {
        print("Failed to sync summaries on login: $e");
      }

      // Init Local Agent logic on login if key exists
      if (geminiKey != null) {
        try {
          final config = await apiService.fetchMobileConfig(
            token: result.token,
          );
          localAgentService.init(geminiKey!, config);
        } catch (e) {
          print("Failed to init local agent on login: $e");
        }
      }

      return null;
    } catch (e) {
      return e.toString();
    } finally {
      isBusy = false;
      notifyListeners();
    }
  }

  Future<String?> register(
    String email,
    String password,
    String displayName,
  ) async {
    isBusy = true;
    notifyListeners();
    try {
      final result = await apiService.register(email, password, displayName);
      authToken = result.token;
      currentUser = result.user;
      await storage.saveToken(result.token);
      await storage.saveEmail(email);
      geminiKey = await storage.readGeminiKeyForUser(result.user.username);

      try {
        syncService.syncSummaries(token: result.token);
      } catch (e) {
        print("Failed to sync summaries on register: $e");
      }

      if (geminiKey != null) {
        try {
          final config =
              await apiService.fetchMobileConfig(token: result.token);
          localAgentService.init(geminiKey!, config);
        } catch (e) {
          print("Failed to init local agent on register: $e");
        }
      }

      return null;
    } catch (e) {
      return e.toString();
    } finally {
      isBusy = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    _syncTimer?.cancel();
    final userId = currentUser?.id;
    await storage.clearAuth();
    if (userId != null) {
      await storage.clearChatSessionId(userId);
    }
    authToken = null;
    currentUser = null;
    geminiKey = null;
    messages.clear();
    localAgentService.clearHistory();
    telegramPreferences = null;
    notifyListeners();
  }

  int? currentSessionId;

  Future<void> startNewChat() async {
    messages.clear();
    await _updateCurrentSessionId(null);
    localAgentService.clearHistory();
    notifyListeners();
  }

  Future<bool> loadChatSession(int sessionId, {bool silent = false}) async {
    isBusy = true;
    notifyListeners();
    try {
      final session = await apiService.getChatSessionDetails(
        authToken!,
        sessionId,
      );
      await _updateCurrentSessionId(sessionId);
      messages.clear();
      localAgentService.clearHistory();

      if (session['messages'] != null) {
        final msgs = (session['messages'] as List);
        for (var m in msgs) {
          final content = m['content'] as String;
          final role = m['role'] as String;
          if (role == 'user') {
            messages.add(ChatMessage.user(content));
          } else {
            messages.add(ChatMessage.assistant(content));
          }
        }
      }
      localAgentService.seedHistory(List<ChatMessage>.from(messages));
      return true;
    } catch (e) {
      print("Error loading session: $e");
      if (!silent) {
        messages.add(ChatMessage.system("فشل تحميل المحادثة: $e"));
      }
      return false;
    } finally {
      isBusy = false;
      notifyListeners();
    }
  }

  Future<void> sendMessage(String text, {String? route}) async {
    final prompt = text.trim();
    if (prompt.isEmpty || isSending) {
      return;
    }
    messages.add(ChatMessage.user(prompt));
    isSending = true;
    notifyListeners();

    try {
      // 1. Create session if needed
      if (currentSessionId == null && authToken != null) {
        try {
          final session = await apiService.createChatSession(
            authToken!,
            title:
                prompt.length > 30 ? "${prompt.substring(0, 30)}..." : prompt,
          );
          final sessionId = _parseSessionId(session['id']);
          if (sessionId != null) {
            await _updateCurrentSessionId(sessionId);
          }
        } catch (e) {
          print("Failed to create session: $e");
        }
      }

      // 2. Log User Msg
      if (currentSessionId != null && authToken != null) {
        apiService
            .addChatMessage(authToken!, currentSessionId!, 'user', prompt)
            .catchError((e) => print("Log error: $e"));
      }

      String output = "";

      // 3. Generate Response via backend agent profile
      if (authToken == null) {
        messages.add(
          ChatMessage.system(
            "يرجى تسجيل الدخول أولاً لاستخدام المساعد.",
          ),
        );
        isSending = false;
        notifyListeners();
        return;
      }
      final result = await apiService.runAgent(
        task: prompt,
        route: route ?? defaultAgentKey,
        token: authToken,
        geminiKey: geminiKey,
      );
      output = result.output;

      messages.add(ChatMessage.assistant(output));

      // 4. Log Assistant Msg
      if (currentSessionId != null && authToken != null) {
        apiService
            .addChatMessage(authToken!, currentSessionId!, 'model', output)
            .catchError((e) => print("Log error: $e"));
      }
    } catch (e) {
      print("Chat error: $e");
      messages.add(
        ChatMessage.system("حدث خطأ أثناء الاتصال بالخادم. حاول مرة أخرى."),
      );
    } finally {
      isSending = false;
      notifyListeners();
    }
  }

  Future<void> updateGeminiKey(String key) async {
    if (currentUser?.role == "admin") {
      await apiService.updateGeminiKey(key, token: authToken);
    }
    if (currentUser != null) {
      await storage.saveGeminiKeyForUser(currentUser!.username, key);
    } else {
      await storage.saveGeminiKey(key);
    }
    geminiKey = key;

    if (key.isNotEmpty) {
      try {
        print("DEBUG: Fetching mobile config to init agent...");
        final config = await apiService.fetchMobileConfig(token: authToken);
        print("DEBUG: Init local agent with model: ${config.model}");
        localAgentService.init(key, config);
        print("DEBUG: Starting sync...");
        syncService.syncSummaries(token: authToken);
      } catch (e) {
        print("DEBUG: Failed to init agent after key update: $e");
      }
    }

    notifyListeners();
  }

  Future<String?> loadGeminiKey() async {
    if (currentUser == null) {
      geminiKey = null;
      return null;
    }
    geminiKey = await storage.readGeminiKeyForUser(currentUser!.username);
    return geminiKey;
  }

  Future<void> refreshChatRetention() async {
    if (currentUser?.role != "admin") {
      return;
    }
    final info = await apiService.fetchChatRetention(token: authToken);
    chatRetentionDays = info.days;
    chatRetentionMin = info.minDays;
    chatRetentionMax = info.maxDays;
    notifyListeners();
  }

  Future<void> updateChatRetentionDays(int days) async {
    if (currentUser?.role != "admin") {
      return;
    }
    final info = await apiService.updateChatRetentionDays(
      days,
      token: authToken,
    );
    chatRetentionDays = info.days;
    chatRetentionMin = info.minDays;
    chatRetentionMax = info.maxDays;
    notifyListeners();
  }

  Future<void> refreshTelegramPreferences() async {
    final prefs = await apiService.fetchTelegramPreferences(token: authToken);
    telegramPreferences = prefs;
    notifyListeners();
  }

  Future<TelegramPreferences> updateTelegramPreferences({
    bool? dailyEnabled,
    bool? weeklyEnabled,
    bool? monthlyEnabled,
  }) async {
    final prefs = await apiService.updateTelegramPreferences(
      dailyEnabled: dailyEnabled,
      weeklyEnabled: weeklyEnabled,
      monthlyEnabled: monthlyEnabled,
      token: authToken,
    );
    telegramPreferences = prefs;
    notifyListeners();
    return prefs;
  }

  Future<TelegramPreferences> unlinkTelegram() async {
    final prefs = await apiService.unlinkTelegram(token: authToken);
    telegramPreferences = prefs;
    notifyListeners();
    return prefs;
  }
}
