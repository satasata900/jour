import "package:flutter/material.dart";
import "package:intl/intl.dart";
import "package:provider/provider.dart";

import "../database_helper.dart";
import "../models/summary_entry.dart";
import "../state/app_state.dart";

class SummariesScreen extends StatefulWidget {
  const SummariesScreen({super.key});

  @override
  State<SummariesScreen> createState() => _SummariesScreenState();
}

class _SummariesScreenState extends State<SummariesScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final DatabaseHelper _db = DatabaseHelper();
  bool _isLoading = true;
  List<SummaryEntry> _allSummaries = [];

  final List<Map<String, String>> _categories = [
    {"id": "interval", "label": "نصف ساعي"},
    {"id": "daily", "label": "يومي"},
    {"id": "weekly", "label": "أسبوعي"},
    {"id": "monthly", "label": "شهري"},
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: _categories.length, vsync: this);
    _loadSummaries();
  }

  Future<void> _loadSummaries() async {
    setState(() => _isLoading = true);
    try {
      // Get all summaries from DB
      final db = await _db.database;
      final List<Map<String, dynamic>> maps = await db.query(
        'summaries',
        orderBy: 'period_end DESC',
      );
      _allSummaries = maps.map((m) => SummaryEntry.fromMap(m)).toList();
    } catch (e) {
      debugPrint("Error loading summaries: $e");
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _refreshSummaries() async {
    final state = context.read<AppState>();
    if (state.authToken == null) {
      return;
    }
    await state.syncService.syncSummaries(token: state.authToken!);
    await _loadSummaries();
  }

  List<SummaryEntry> _getFilteredSummaries(String type) {
    return _allSummaries.where((s) => s.periodType == type).toList();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      backgroundColor: const Color(0xFF0B0F14),
      appBar: AppBar(
        title: const Text("ملخصات الأخبار"),
        bottom: TabBar(
          controller: _tabController,
          isScrollable: true,
          indicatorColor: const Color(0xFF23C08B),
          labelColor: const Color(0xFF23C08B),
          unselectedLabelColor: Colors.white60,
          tabs: _categories.map((cat) => Tab(text: cat["label"])).toList(),
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : TabBarView(
              controller: _tabController,
              children: _categories.map((cat) {
                final summaries = _getFilteredSummaries(cat["id"]!);
                if (summaries.isEmpty) {
                  return _buildEmptyState(theme, cat["label"]!);
                }
                return RefreshIndicator(
                  onRefresh: _refreshSummaries,
                  child: ListView.separated(
                    padding: const EdgeInsets.all(16),
                    itemCount: summaries.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 12),
                    itemBuilder: (context, index) {
                      return _buildSummaryCard(theme, summaries[index]);
                    },
                  ),
                );
              }).toList(),
            ),
    );
  }

  Widget _buildEmptyState(ThemeData theme, String label) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.inventory_2_outlined,
            size: 64,
            color: theme.colorScheme.outline,
          ),
          const SizedBox(height: 16),
          Text(
            "لا توجد ملخصات لقسم $label",
            style: theme.textTheme.titleMedium?.copyWith(color: Colors.white70),
          ),
          const SizedBox(height: 8),
          Text(
            "سيتم عرض الملخصات هنا بمجرد استيرادها.",
            style: theme.textTheme.bodySmall?.copyWith(color: Colors.white38),
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryCard(ThemeData theme, SummaryEntry summary) {
    final dateFormat = DateFormat('yyyy/MM/dd HH:mm');
    final timeRange =
        "${DateFormat('HH:mm').format(summary.periodStart)} - ${DateFormat('HH:mm').format(summary.periodEnd)}";

    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surface.withOpacity(0.92),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: theme.colorScheme.outline.withOpacity(0.15)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: _getTypeColor(summary.periodType).withOpacity(0.15),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    _getTypeLabel(summary.periodType),
                    style: theme.textTheme.labelSmall?.copyWith(
                      color: _getTypeColor(summary.periodType),
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                Text(
                  summary.periodType == 'interval'
                      ? timeRange
                      : DateFormat('yyyy/MM/dd').format(summary.periodEnd),
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: Colors.white38,
                  ),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            child: Text(
              summary.content,
              style: theme.textTheme.bodyMedium?.copyWith(
                height: 1.5,
                color: Colors.white70,
              ),
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.03),
              borderRadius: const BorderRadius.only(
                bottomLeft: Radius.circular(18),
                bottomRight: Radius.circular(18),
              ),
            ),
            child: Text(
              "تم الاستيراد: ${dateFormat.format(summary.createdAt)}",
              style: theme.textTheme.labelSmall?.copyWith(
                fontSize: 9,
                color: Colors.white24,
              ),
              textAlign: TextAlign.end,
            ),
          ),
        ],
      ),
    );
  }

  Color _getTypeColor(String type) {
    switch (type) {
      case 'interval':
        return const Color(0xFF23C08B);
      case 'daily':
        return const Color(0xFF3B82F6);
      case 'weekly':
        return const Color(0xFF8B5CF6);
      case 'monthly':
        return const Color(0xFFEC4899);
      default:
        return Colors.grey;
    }
  }

  String _getTypeLabel(String type) {
    switch (type) {
      case 'interval':
        return "نصف ساعة";
      case 'daily':
        return "يومي";
      case 'weekly':
        return "أسبوعي";
      case 'monthly':
        return "شهري";
      default:
        return type;
    }
  }
}
