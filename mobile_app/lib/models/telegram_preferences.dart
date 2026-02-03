class TelegramPreferences {
  final bool linked;
  final int? chatId;
  final String? username;
  final String? botUsername;
  final String? linkUrl;
  final bool dailyEnabled;
  final bool weeklyEnabled;
  final bool monthlyEnabled;

  TelegramPreferences({
    required this.linked,
    required this.chatId,
    required this.username,
    required this.botUsername,
    required this.linkUrl,
    required this.dailyEnabled,
    required this.weeklyEnabled,
    required this.monthlyEnabled,
  });

  factory TelegramPreferences.fromJson(Map<String, dynamic>? json) {
    final data = json ?? {};
    return TelegramPreferences(
      linked: data["linked"] as bool? ?? false,
      chatId: (data["chat_id"] as num?)?.toInt(),
      username: data["username"] as String?,
      botUsername: data["bot_username"] as String?,
      linkUrl: data["link_url"] as String?,
      dailyEnabled: data["daily_enabled"] as bool? ?? false,
      weeklyEnabled: data["weekly_enabled"] as bool? ?? false,
      monthlyEnabled: data["monthly_enabled"] as bool? ?? false,
    );
  }
}
