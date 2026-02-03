import "package:flutter/material.dart";
import "package:provider/provider.dart";
import "package:url_launcher/url_launcher.dart";

import "../state/app_state.dart";

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _geminiController = TextEditingController();
  bool _hideKey = true;
  bool _savingKey = false;
  bool _loadingRetention = true;
  bool _savingRetention = false;
  int _chatRetentionDays = 7;
  int _chatRetentionMin = 1;
  int _chatRetentionMax = 30;

  @override
  void initState() {
    super.initState();
    _loadKey();
    final user = context.read<AppState>().currentUser;
    if (user?.role == "admin") {
      _loadChatRetention();
    } else {
      _loadingRetention = false;
    }
  }

  Future<void> _loadKey() async {
    final key = await context.read<AppState>().loadGeminiKey();
    if (mounted && key != null) {
      setState(() => _geminiController.text = key);
    }
  }

  Future<void> _loadChatRetention() async {
    setState(() => _loadingRetention = true);
    try {
      final state = context.read<AppState>();
      await state.refreshChatRetention();
      if (mounted) {
        setState(() {
          _chatRetentionDays = state.chatRetentionDays;
          _chatRetentionMin = state.chatRetentionMin;
          _chatRetentionMax = state.chatRetentionMax;
        });
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("تعذر تحميل إعدادات الاحتفاظ.")),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _loadingRetention = false);
      }
    }
  }

  Future<void> _saveKey() async {
    if (_savingKey) {
      return;
    }
    setState(() => _savingKey = true);
    try {
      await context.read<AppState>().updateGeminiKey(
            _geminiController.text.trim(),
          );
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text("تم حفظ المفتاح بنجاح.")));
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("تعذر حفظ المفتاح حالياً.")),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _savingKey = false);
      }
    }
  }

  Future<void> _saveChatRetention() async {
    if (_savingRetention) {
      return;
    }
    final clamped =
        _chatRetentionDays.clamp(_chatRetentionMin, _chatRetentionMax).toInt();
    setState(() => _savingRetention = true);
    try {
      await context.read<AppState>().updateChatRetentionDays(clamped);
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text("تم تحديث مدة الاحتفاظ.")));
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("تعذر تحديث مدة الاحتفاظ.")),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _savingRetention = false);
      }
    }
  }

  Future<void> _openGeminiKeyPage() async {
    final uri = Uri.parse("https://aistudio.google.com/app/apikey");
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } else if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("تعذر فتح الرابط حالياً.")),
      );
    }
  }

  Future<bool> _confirmLogout() async {
    final theme = Theme.of(context);
    final result = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text("تأكيد تسجيل الخروج"),
          content: Text(
            "سيتم إنهاء الجلسة الحالية. يمكنك تسجيل الدخول مجددا في أي وقت.",
            style: theme.textTheme.bodyMedium,
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text("إلغاء"),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: const Text("تسجيل الخروج"),
            ),
          ],
        );
      },
    );
    return result ?? false;
  }

  Future<void> _logout() async {
    final confirmed = await _confirmLogout();
    if (!confirmed) {
      return;
    }
    await context.read<AppState>().logout();
    if (mounted) {
      Navigator.of(context).pop();
    }
  }

  @override
  void dispose() {
    _geminiController.dispose();
    super.dispose();
  }

  Widget _sectionTitle(BuildContext context, String text) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Text(
        text,
        style: theme.textTheme.titleMedium?.copyWith(
          color: theme.colorScheme.onBackground,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final user = context.watch<AppState>().currentUser;
    final isAdmin = user?.role == "admin";
    return Scaffold(
      appBar: AppBar(title: const Text("الإعدادات")),
      body: Stack(
        children: [
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [Color(0xFF0B0F14), Color(0xFF0F141B)],
              ),
            ),
          ),
          ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _sectionTitle(context, "مفاتيح الذكاء"),
              Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: theme.colorScheme.surface.withOpacity(0.95),
                  borderRadius: BorderRadius.circular(22),
                  border: Border.all(
                    color: theme.colorScheme.outline.withOpacity(0.2),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            "ادخل مفتاح Gemini الخاص بك",
                            style: theme.textTheme.titleSmall?.copyWith(
                              color: theme.colorScheme.onSurface,
                            ),
                          ),
                        ),
                        TextButton(
                          onPressed: _openGeminiKeyPage,
                          child: const Text("اضغط هنا لجلب المفتاح"),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    TextField(
                      controller: _geminiController,
                      obscureText: _hideKey,
                      decoration: InputDecoration(
                        labelText: "Gemini API Key",
                        prefixIcon: const Icon(Icons.key_rounded),
                        suffixIcon: IconButton(
                          onPressed: () => setState(() => _hideKey = !_hideKey),
                          icon: Icon(
                            _hideKey
                                ? Icons.visibility_rounded
                                : Icons.visibility_off_rounded,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 14),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: FilledButton(
                        onPressed: _savingKey ? null : _saveKey,
                        child: _savingKey
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Text("حفظ المفتاح"),
                      ),
                    ),
                  ],
                ),
              ),
              if (isAdmin) ...[
                const SizedBox(height: 24),
                _sectionTitle(context, "احتفاظ المحادثات"),
                Container(
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surface.withOpacity(0.95),
                    borderRadius: BorderRadius.circular(22),
                    border: Border.all(
                      color: theme.colorScheme.outline.withOpacity(0.2),
                    ),
                  ),
                  child: _loadingRetention
                      ? const Center(child: CircularProgressIndicator())
                      : Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              "حدد عدد الأيام التي نحتفظ فيها برسائل المحادثة.",
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: theme.colorScheme.onSurface.withOpacity(
                                  0.7,
                                ),
                              ),
                            ),
                            const SizedBox(height: 16),
                            Row(
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 12,
                                    vertical: 8,
                                  ),
                                  decoration: BoxDecoration(
                                    color: theme.colorScheme.surfaceVariant
                                        .withOpacity(0.8),
                                    borderRadius: BorderRadius.circular(14),
                                  ),
                                  child: Text(
                                    "$_chatRetentionDays يوم",
                                    style: theme.textTheme.titleSmall,
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Text(
                                  "الحد الأعلى $_chatRetentionMax يوم",
                                  style: theme.textTheme.bodySmall?.copyWith(
                                    color: theme.colorScheme.onSurface
                                        .withOpacity(0.6),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 12),
                            Slider(
                              value: _chatRetentionDays.toDouble(),
                              min: _chatRetentionMin.toDouble(),
                              max: _chatRetentionMax.toDouble(),
                              divisions: _chatRetentionMax - _chatRetentionMin,
                              label: "$_chatRetentionDays",
                              onChanged: (value) {
                                setState(
                                  () => _chatRetentionDays = value.round(),
                                );
                              },
                            ),
                            Align(
                              alignment: Alignment.centerLeft,
                              child: FilledButton(
                                onPressed: _savingRetention
                                    ? null
                                    : _saveChatRetention,
                                child: _savingRetention
                                    ? const SizedBox(
                                        width: 18,
                                        height: 18,
                                        child: CircularProgressIndicator(
                                          strokeWidth: 2,
                                        ),
                                      )
                                    : const Text("حفظ المدة"),
                              ),
                            ),
                          ],
                        ),
                ),
              ],
              const SizedBox(height: 24),
              _sectionTitle(context, "الحساب"),
              Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: theme.colorScheme.surface.withOpacity(0.95),
                  borderRadius: BorderRadius.circular(22),
                  border: Border.all(
                    color: theme.colorScheme.outline.withOpacity(0.2),
                  ),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 52,
                      height: 52,
                      decoration: BoxDecoration(
                        color: theme.colorScheme.surfaceVariant.withOpacity(
                          0.7,
                        ),
                        borderRadius: BorderRadius.circular(18),
                      ),
                      child: const Icon(Icons.person_rounded),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(user?.username ?? "غير مسجل"),
                          const SizedBox(height: 6),
                          Text(
                            user?.role ?? "",
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: theme.colorScheme.onSurface.withOpacity(
                                0.6,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    OutlinedButton(
                      onPressed: _logout,
                      child: const Text("تسجيل الخروج"),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
