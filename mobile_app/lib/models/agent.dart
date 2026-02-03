class Agent {
  final int id;
  final String key;
  final String name;
  final String? description;
  final String agentType;
  final bool isActive;
  final bool isSystem;

  Agent({
    required this.id,
    required this.key,
    required this.name,
    required this.description,
    required this.agentType,
    required this.isActive,
    required this.isSystem,
  });

  factory Agent.fromJson(Map<String, dynamic> json) {
    return Agent(
      id: (json["id"] as num).toInt(),
      key: json["key"] as String? ?? "",
      name: json["name"] as String? ?? "",
      description: json["description"] as String?,
      agentType: json["agent_type"] as String? ?? "",
      isActive: json["is_active"] as bool? ?? true,
      isSystem: json["is_system"] as bool? ?? false,
    );
  }
}
