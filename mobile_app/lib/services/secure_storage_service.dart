import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class SecureStorageService {
  static const _tokenKey = "auth_token";
  static const _emailKey = "auth_email";
  static const _legacyGeminiKey = "gemini_key";
  static const _geminiKeyPrefix = "gemini_key_user";
  static const _chatSessionKeyPrefix = "chat_session_id";

  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  Future<void> saveToken(String token) async {
    await _storage.write(key: _tokenKey, value: token);
  }

  Future<String?> readToken() async {
    return _storage.read(key: _tokenKey);
  }

  Future<void> saveEmail(String email) async {
    await _storage.write(key: _emailKey, value: email);
  }

  Future<String?> readEmail() async {
    return _storage.read(key: _emailKey);
  }

  String _geminiKeyForUser(String username) {
    return "${_geminiKeyPrefix}_${username.trim().toLowerCase()}";
  }

  Future<void> saveGeminiKeyForUser(String username, String key) async {
    await _storage.write(key: _geminiKeyForUser(username), value: key);
  }

  Future<String?> readGeminiKeyForUser(String username) async {
    return _storage.read(key: _geminiKeyForUser(username));
  }

  Future<void> clearGeminiKeyForUser(String username) async {
    await _storage.delete(key: _geminiKeyForUser(username));
  }

  Future<void> saveGeminiKey(String key) async {
    await _storage.write(key: _legacyGeminiKey, value: key);
  }

  Future<String?> readGeminiKey() async {
    return _storage.read(key: _legacyGeminiKey);
  }

  Future<void> clearLegacyGeminiKey() async {
    await _storage.delete(key: _legacyGeminiKey);
  }

  String _chatSessionKey(int userId) {
    return "${_chatSessionKeyPrefix}_$userId";
  }

  Future<void> saveChatSessionId(int userId, int sessionId) async {
    await _storage.write(
      key: _chatSessionKey(userId),
      value: sessionId.toString(),
    );
  }

  Future<int?> readChatSessionId(int userId) async {
    final value = await _storage.read(key: _chatSessionKey(userId));
    if (value == null || value.trim().isEmpty) {
      return null;
    }
    return int.tryParse(value.trim());
  }

  Future<void> clearChatSessionId(int userId) async {
    await _storage.delete(key: _chatSessionKey(userId));
  }

  Future<void> clear() async {
    await _storage.deleteAll();
  }

  Future<void> clearAuth() async {
    await _storage.delete(key: _tokenKey);
    await _storage.delete(key: _emailKey);
  }
}
