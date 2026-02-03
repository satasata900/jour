class User {
  final int id;
  final String username;
  final String? displayNameValue;
  final String role;
  final DateTime createdAt;

  User({
    required this.id,
    required this.username,
    required this.displayNameValue,
    required this.role,
    required this.createdAt,
  });

  String get displayName {
    if (displayNameValue != null && displayNameValue!.trim().isNotEmpty) {
      return displayNameValue!.trim();
    }
    final parts = username.split("@");
    return parts.isNotEmpty ? parts.first : username;
  }

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: (json["id"] as num).toInt(),
      username: json["username"] as String? ?? "",
      displayNameValue: json["display_name"] as String?,
      role: json["role"] as String? ?? "journalist",
      createdAt: DateTime.tryParse(json["created_at"] as String? ?? "") ??
          DateTime.now(),
    );
  }
}
