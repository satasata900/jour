class SummaryEntry {
  final int id;
  final String periodType;
  final DateTime periodStart;
  final DateTime periodEnd;
  final String content;
  final DateTime createdAt;

  SummaryEntry({
    required this.id,
    required this.periodType,
    required this.periodStart,
    required this.periodEnd,
    required this.content,
    required this.createdAt,
  });

  factory SummaryEntry.fromJson(Map<String, dynamic> json) {
    DateTime parseDate(String? value) {
      if (value == null || value.isEmpty) {
        return DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);
      }
      return DateTime.tryParse(value) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);
    }

    return SummaryEntry(
      id: (json["id"] as num?)?.toInt() ?? 0,
      periodType: json["period_type"] as String? ?? "",
      periodStart: parseDate(json["period_start"] as String?),
      periodEnd: parseDate(json["period_end"] as String?),
      content: json["content"] as String? ?? "",
      createdAt: parseDate(json["created_at"] as String?),
    );
  }

  // Convert for SQLite
  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'period_type': periodType,
      'period_start': periodStart.toIso8601String(),
      'period_end': periodEnd.toIso8601String(),
      'content': content,
      'created_at': createdAt.toIso8601String(),
    };
  }

  factory SummaryEntry.fromMap(Map<String, dynamic> map) {
    return SummaryEntry(
      id: map['id'] as int,
      periodType: map['period_type'] as String,
      periodStart: DateTime.parse(map['period_start'] as String),
      periodEnd: DateTime.parse(map['period_end'] as String),
      content: map['content'] as String,
      createdAt: DateTime.parse(map['created_at'] as String),
    );
  }
}
