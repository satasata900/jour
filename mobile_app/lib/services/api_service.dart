import "dart:convert";

import "package:http/http.dart" as http;

import "../models/agent.dart";
import "../models/summary_entry.dart";
import "../models/mobile_config.dart";
import "../models/telegram_preferences.dart";
import "../models/user.dart";

class ApiException implements Exception {
  final String message;
  final int? statusCode;

  ApiException(this.message, {this.statusCode});

  @override
  String toString() {
    return "ApiException($statusCode): $message";
  }
}

class LoginResult {
  final User user;
  final String token;

  LoginResult({required this.user, required this.token});
}

class AgentRunResult {
  final String route;
  final String output;
  final Map<String, dynamic> meta;

  AgentRunResult({
    required this.route,
    required this.output,
    required this.meta,
  });
}

class ChatRetentionInfo {
  final int days;
  final int minDays;
  final int maxDays;
  final String source;

  ChatRetentionInfo({
    required this.days,
    required this.minDays,
    required this.maxDays,
    required this.source,
  });

  factory ChatRetentionInfo.fromJson(Map<String, dynamic>? json) {
    final data = json ?? {};
    return ChatRetentionInfo(
      days: (data["days"] as num?)?.toInt() ?? 7,
      minDays: (data["min_days"] as num?)?.toInt() ?? 1,
      maxDays: (data["max_days"] as num?)?.toInt() ?? 30,
      source: data["source"] as String? ?? "default",
    );
  }
}

class ApiService {
  final String baseUrl;

  ApiService(String baseUrl)
      : baseUrl = baseUrl.endsWith("/")
            ? baseUrl.substring(0, baseUrl.length - 1)
            : baseUrl;

  Map<String, String> _headers({String? token, String? geminiKey}) {
    final headers = <String, String>{"Content-Type": "application/json"};
    if (token != null && token.isNotEmpty) {
      headers["Authorization"] = "Bearer $token";
      headers["x-api-token"] = token;
    }
    if (geminiKey != null && geminiKey.trim().isNotEmpty) {
      headers["X-Gemini-Key"] = geminiKey.trim();
    }
    return headers;
  }

  Map<String, dynamic> _decode(http.Response response) {
    if (response.body.isEmpty) {
      return {};
    }
    try {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } catch (_) {
      return {"raw": response.body};
    }
  }

  ApiException _buildException(http.Response response) {
    if (response.statusCode == 422) {
      print("DEBUG: 422 Error Body: ${response.body}");
    }
    final payload = _decode(response);
    final detail = payload["detail"];
    if (detail is String && detail.isNotEmpty) {
      return ApiException(detail, statusCode: response.statusCode);
    }
    return ApiException(
      "Request failed with status ${response.statusCode}.",
      statusCode: response.statusCode,
    );
  }

  Future<LoginResult> login(String username, String password) async {
    final uri = Uri.parse("$baseUrl/auth/login");
    print("------------------------------------------------------------------");
    print("DEBUG: Attempting login to: $uri");
    print("DEBUG: Username: $username");

    try {
      final response = await http.post(
        uri,
        headers: _headers(),
        body: jsonEncode({"username": username, "password": password}),
      );

      print("DEBUG: Response Status: ${response.statusCode}");
      print("DEBUG: Response Body: ${response.body}");

      if (response.statusCode != 200) {
        throw _buildException(response);
      }
      final payload = _decode(response);
      return LoginResult(
        user: User.fromJson(payload["user"] as Map<String, dynamic>),
        token: payload["token"] as String? ?? "",
      );
    } catch (e) {
      print("DEBUG: Login Exception: $e");
      rethrow;
    } finally {
      print(
        "------------------------------------------------------------------",
      );
    }
  }

  Future<LoginResult> register(
    String username,
    String password,
    String displayName,
  ) async {
    final uri = Uri.parse("$baseUrl/auth/register");
    final response = await http.post(
      uri,
      headers: _headers(),
      body: jsonEncode({
        "username": username,
        "display_name": displayName,
        "password": password,
      }),
    );
    if (response.statusCode != 200) {
      throw _buildException(response);
    }
    final payload = _decode(response);
    return LoginResult(
      user: User.fromJson(payload["user"] as Map<String, dynamic>),
      token: payload["token"] as String? ?? "",
    );
  }

  Future<User> getProfile(String token) async {
    final uri = Uri.parse("$baseUrl/auth/me");
    final response = await http.get(uri, headers: _headers(token: token));
    if (response.statusCode != 200) {
      throw _buildException(response);
    }
    final payload = _decode(response);
    return User.fromJson(payload);
  }

  Future<List<Agent>> fetchAgents({String? token}) async {
    final uri = Uri.parse("$baseUrl/agents");
    final response = await http.get(uri, headers: _headers(token: token));
    if (response.statusCode != 200) {
      throw _buildException(response);
    }
    if (response.body.isEmpty) {
      return [];
    }
    final list = jsonDecode(response.body) as List<dynamic>;
    return list
        .map((item) => Agent.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<AgentRunResult> runAgent({
    required String task,
    String? context,
    String? route,
    String? token,
    String? geminiKey,
  }) async {
    final uri = Uri.parse("$baseUrl/agents/run");
    final payload = <String, dynamic>{"task": task};
    if (context != null && context.trim().isNotEmpty) {
      payload["context"] = context.trim();
    }
    if (route != null && route.trim().isNotEmpty) {
      payload["route"] = route.trim();
    }
    final response = await http.post(
      uri,
      headers: _headers(token: token, geminiKey: geminiKey),
      body: jsonEncode(payload),
    );
    if (response.statusCode != 200) {
      throw _buildException(response);
    }
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return AgentRunResult(
      route: data["route"] as String? ?? "",
      output: data["output"] as String? ?? "",
      meta: (data["meta"] as Map<String, dynamic>?) ?? {},
    );
  }

  Future<List<SummaryEntry>> fetchSummaries({
    String? periodType,
    DateTime? since,
    int limit = 30,
    int offset = 0,
    String? token,
  }) async {
    final query = <String, String>{
      "limit": limit.toString(),
      "offset": offset.toString(),
    };
    if (periodType != null && periodType.trim().isNotEmpty) {
      query["period_type"] = periodType.trim();
    }
    if (since != null) {
      query["since"] = since.toIso8601String();
    }
    final uri = Uri.parse("$baseUrl/summaries").replace(queryParameters: query);
    final response = await http.get(uri, headers: _headers(token: token));
    if (response.statusCode != 200) {
      throw _buildException(response);
    }
    if (response.body.isEmpty) {
      return [];
    }
    final list = jsonDecode(response.body) as List<dynamic>;
    return list
        .map((item) => SummaryEntry.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<void> updateGeminiKey(String key, {String? token}) async {
    final uri = Uri.parse("$baseUrl/settings");
    final response = await http.put(
      uri,
      headers: _headers(token: token),
      body: jsonEncode({
        "keys": {"gemini_api_key": key},
      }),
    );
    if (response.statusCode != 200) {
      throw _buildException(response);
    }
  }

  Future<ChatRetentionInfo> fetchChatRetention({String? token}) async {
    final uri = Uri.parse("$baseUrl/settings");
    final response = await http.get(uri, headers: _headers(token: token));
    if (response.statusCode != 200) {
      throw _buildException(response);
    }
    final payload = _decode(response);
    return ChatRetentionInfo.fromJson(
      payload["chat_retention"] as Map<String, dynamic>?,
    );
  }

  Future<ChatRetentionInfo> updateChatRetentionDays(
    int days, {
    String? token,
  }) async {
    final uri = Uri.parse("$baseUrl/settings");
    final response = await http.put(
      uri,
      headers: _headers(token: token),
      body: jsonEncode({
        "chat_retention": {"days": days},
      }),
    );
    if (response.statusCode != 200) {
      throw _buildException(response);
    }
    final payload = _decode(response);
    return ChatRetentionInfo.fromJson(
      payload["chat_retention"] as Map<String, dynamic>?,
    );
  }

  Future<TelegramPreferences> fetchTelegramPreferences({String? token}) async {
    final uri = Uri.parse("$baseUrl/notifications/telegram");
    final response = await http.get(uri, headers: _headers(token: token));
    if (response.statusCode != 200) {
      throw _buildException(response);
    }
    final payload = _decode(response);
    return TelegramPreferences.fromJson(payload);
  }

  Future<TelegramPreferences> updateTelegramPreferences({
    bool? dailyEnabled,
    bool? weeklyEnabled,
    bool? monthlyEnabled,
    String? token,
  }) async {
    final uri = Uri.parse("$baseUrl/notifications/telegram");
    final body = <String, dynamic>{};
    if (dailyEnabled != null) {
      body["daily_enabled"] = dailyEnabled;
    }
    if (weeklyEnabled != null) {
      body["weekly_enabled"] = weeklyEnabled;
    }
    if (monthlyEnabled != null) {
      body["monthly_enabled"] = monthlyEnabled;
    }
    final response = await http.put(
      uri,
      headers: _headers(token: token),
      body: jsonEncode(body),
    );
    if (response.statusCode != 200) {
      throw _buildException(response);
    }
    final payload = _decode(response);
    return TelegramPreferences.fromJson(payload);
  }

  Future<TelegramPreferences> unlinkTelegram({String? token}) async {
    final uri = Uri.parse("$baseUrl/notifications/telegram/unlink");
    final response = await http.post(uri, headers: _headers(token: token));
    if (response.statusCode != 200) {
      throw _buildException(response);
    }
    final payload = _decode(response);
    return TelegramPreferences.fromJson(payload);
  }

  Future<MobileConfig> fetchMobileConfig({String? token}) async {
    final uri = Uri.parse("$baseUrl/settings/mobile-config");
    final response = await http.get(uri, headers: _headers(token: token));
    if (response.statusCode != 200) {
      throw _buildException(response);
    }
    final payload = _decode(response);
    return MobileConfig.fromJson(payload);
  }

  // --- Chat Session Methods ---

  Future<List<Map<String, dynamic>>> getChatSessions(String token) async {
    final response = await http.get(
      Uri.parse("$baseUrl/chat/sessions"),
      headers: {
        "Authorization": "Bearer $token",
        "Content-Type": "application/json",
      },
    );
    if (response.statusCode != 200) {
      throw _buildException(response);
    }
    return List<Map<String, dynamic>>.from(jsonDecode(response.body));
  }

  Future<Map<String, dynamic>> createChatSession(
    String token, {
    String? title,
  }) async {
    final response = await http.post(
      Uri.parse("$baseUrl/chat/sessions"),
      headers: _headers(token: token),
      body: jsonEncode({"title": title}),
    );
    if (response.statusCode != 200) {
      throw _buildException(response);
    }
    return jsonDecode(response.body);
  }

  Future<Map<String, dynamic>> getChatSessionDetails(
    String token,
    int sessionId,
  ) async {
    final response = await http.get(
      Uri.parse("$baseUrl/chat/sessions/$sessionId"),
      headers: _headers(token: token),
    );
    if (response.statusCode != 200) {
      throw _buildException(response);
    }
    return jsonDecode(response.body);
  }

  Future<void> addChatMessage(
    String token,
    int sessionId,
    String role,
    String content,
  ) async {
    final response = await http.post(
      Uri.parse("$baseUrl/chat/sessions/$sessionId/messages"),
      headers: _headers(token: token),
      body: jsonEncode({"role": role, "content": content}),
    );
    if (response.statusCode != 200) {
      throw _buildException(response);
    }
  }

  Future<void> deleteChatSession(String token, int sessionId) async {
    final response = await http.delete(
      Uri.parse("$baseUrl/chat/sessions/$sessionId"),
      headers: _headers(token: token),
    );
    if (response.statusCode != 204) {
      throw _buildException(response);
    }
  }
}
