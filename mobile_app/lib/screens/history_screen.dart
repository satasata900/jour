import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../state/app_state.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  bool _loading = true;
  List<Map<String, dynamic>> _sessions = [];
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadSessions();
  }

  Future<void> _loadSessions() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final state = context.read<AppState>();
      if (state.authToken == null) {
        throw Exception("يرجى تسجيل الدخول أولاً.");
      }
      final sessions = await state.apiService.getChatSessions(state.authToken!);
      if (mounted) {
        setState(() {
          _sessions = sessions;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _loading = false;
        });
      }
    }
  }

  String _formatDate(String dateStr) {
    try {
      final date = DateTime.parse(dateStr).toLocal();
      return "${date.year}/${date.month}/${date.day} ${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}";
    } catch (_) {
      return dateStr;
    }
  }

  int? _parseSessionId(dynamic value) {
    if (value is int) {
      return value;
    }
    if (value is num) {
      return value.toInt();
    }
    if (value is String) {
      return int.tryParse(value.trim());
    }
    return null;
  }

  Future<void> _deleteSession(Map<String, dynamic> session) async {
    final sessionId = _parseSessionId(session['id']);
    if (sessionId == null) {
      return;
    }
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text("حذف المحادثة"),
        content: const Text("هل أنت متأكد من حذف هذه المحادثة؟"),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text("إلغاء"),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text("حذف"),
          ),
        ],
      ),
    );
    if (confirmed != true) {
      return;
    }

    try {
      final state = context.read<AppState>();
      if (state.authToken == null) {
        throw Exception("يرجى تسجيل الدخول أولاً.");
      }
      await state.apiService.deleteChatSession(state.authToken!, sessionId);
      if (state.currentSessionId == sessionId) {
        await state.startNewChat();
      }
      if (mounted) {
        setState(() {
          _sessions.removeWhere(
            (item) => _parseSessionId(item['id']) == sessionId,
          );
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("فشل حذف المحادثة: $e")),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("المحادثات السابقة")),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text("خطأ: $_error"))
              : _sessions.isEmpty
                  ? const Center(child: Text("لا توجد محادثات سابقة."))
                  : ListView.builder(
                      itemCount: _sessions.length,
                      itemBuilder: (context, index) {
                        final session = _sessions[index];
                        final title = session['title'] ?? "محادثة بدون عنوان";
                        final dateStr = session['updated_at'];

                        return ListTile(
                          title: Text(
                            title,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          subtitle: Text(
                            _formatDate(dateStr),
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          leading: const Icon(Icons.history),
                          trailing: IconButton(
                            icon: const Icon(Icons.delete_outline_rounded),
                            onPressed: () => _deleteSession(session),
                          ),
                          onTap: () async {
                            final sessionId = _parseSessionId(session['id']);
                            if (sessionId == null) {
                              return;
                            }
                            await context
                                .read<AppState>()
                                .loadChatSession(sessionId);
                            if (mounted) {
                              Navigator.pop(context); // Close history screen
                            }
                          },
                        );
                      },
                    ),
    );
  }
}
