enum ChatRole { user, assistant, system }


class ChatMessage {
  final String id;
  final ChatRole role;
  final String content;
  final DateTime createdAt;

  ChatMessage({
    required this.id,
    required this.role,
    required this.content,
    required this.createdAt,
  });

  bool get isUser => role == ChatRole.user;

  static ChatMessage user(String content) {
    return ChatMessage(
      id: DateTime.now().microsecondsSinceEpoch.toString(),
      role: ChatRole.user,
      content: content,
      createdAt: DateTime.now(),
    );
  }

  static ChatMessage assistant(String content) {
    return ChatMessage(
      id: DateTime.now().microsecondsSinceEpoch.toString(),
      role: ChatRole.assistant,
      content: content,
      createdAt: DateTime.now(),
    );
  }

  static ChatMessage system(String content) {
    return ChatMessage(
      id: DateTime.now().microsecondsSinceEpoch.toString(),
      role: ChatRole.system,
      content: content,
      createdAt: DateTime.now(),
    );
  }
}
