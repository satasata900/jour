import 'package:path/path.dart';
import 'package:sqflite/sqflite.dart';
import '../models/summary_entry.dart';

class DatabaseHelper {
  static final DatabaseHelper _instance = DatabaseHelper._internal();
  static Database? _database;

  factory DatabaseHelper() {
    return _instance;
  }

  DatabaseHelper._internal();

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDatabase();
    return _database!;
  }

  Future<Database> _initDatabase() async {
    String path = join(await getDatabasesPath(), 'jour2_local.db');
    return await openDatabase(path, version: 1, onCreate: _onCreate);
  }

  Future<void> _onCreate(Database db, int version) async {
    await db.execute('''
      CREATE TABLE summaries(
        id INTEGER PRIMARY KEY,
        period_type TEXT,
        period_start TEXT,
        period_end TEXT,
        content TEXT,
        created_at TEXT
      )
    ''');
    // Index for faster time-based queries
    await db.execute('CREATE INDEX idx_period_end ON summaries(period_end)');
  }

  Future<void> insertSummary(SummaryEntry summary) async {
    final db = await database;
    await db.insert(
      'summaries',
      summary.toMap(),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<void> insertSummaries(List<SummaryEntry> summaries) async {
    final db = await database;
    final batch = db.batch();
    for (var s in summaries) {
      batch.insert(
        'summaries',
        s.toMap(),
        conflictAlgorithm: ConflictAlgorithm.replace,
      );
    }
    await batch.commit(noResult: true);
  }

  Future<DateTime?> getLastSummaryDate() async {
    final db = await database;
    final List<Map<String, dynamic>> maps = await db.query(
      'summaries',
      orderBy: 'period_end DESC',
      limit: 1,
    );
    if (maps.isEmpty) return null;
    return DateTime.parse(maps.first['period_end'] as String);
  }

  Future<List<SummaryEntry>> searchSummaries(String queryStr) async {
    if (queryStr.trim().length < 3) return [];

    final db = await database;
    // Simple LIKE search for now. FTS (Full Text Search) would be better for larger datasets.
    final List<Map<String, dynamic>> maps = await db.query(
      'summaries',
      where: 'content LIKE ?',
      whereArgs: ['%${queryStr.trim()}%'],
      orderBy: 'period_end DESC',
      limit: 20, // Limit context
    );
    return List.generate(maps.length, (i) => SummaryEntry.fromMap(maps[i]));
  }

  Future<List<SummaryEntry>> getSummariesByDateRange(
    DateTime start,
    DateTime end,
  ) async {
    final db = await database;
    final List<Map<String, dynamic>> maps = await db.query(
      'summaries',
      where: 'period_start >= ? AND period_start <= ?',
      whereArgs: [start.toIso8601String(), end.toIso8601String()],
      orderBy: 'period_start ASC', // Chronological order for events
      limit: 50,
    );
    return List.generate(maps.length, (i) => SummaryEntry.fromMap(maps[i]));
  }

  // Get recent summaries for general context
  Future<List<SummaryEntry>> getRecentSummaries({int limit = 10}) async {
    final db = await database;
    final List<Map<String, dynamic>> maps = await db.query(
      'summaries',
      orderBy: 'period_end DESC',
      limit: limit,
    );
    return List.generate(maps.length, (i) => SummaryEntry.fromMap(maps[i]));
  }
}
