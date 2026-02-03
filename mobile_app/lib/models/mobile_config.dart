class MobileConfig {
  final String systemPrompt;
  final String model;
  final int maxTokens;
  final double temperature;
  final Map<String, bool> features;

  MobileConfig({
    required this.systemPrompt,
    required this.model,
    required this.maxTokens,
    required this.temperature,
    required this.features,
  });

  factory MobileConfig.fromJson(Map<String, dynamic> json) {
    return MobileConfig(
      systemPrompt: json['system_prompt'] as String? ?? "",
      model: json['model'] as String? ?? "gemini-flash-lite-latest",
      maxTokens: (json['max_tokens'] as num?)?.toInt() ?? 1000,
      temperature: (json['temperature'] as num?)?.toDouble() ?? 0.3,
      features: Map<String, bool>.from(json['features'] ?? {}),
    );
  }
}
