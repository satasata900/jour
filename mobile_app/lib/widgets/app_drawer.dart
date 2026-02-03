import "package:flutter/material.dart";
import "package:provider/provider.dart";

import "../screens/about_screen.dart";
import "../screens/agents_screen.dart";
import "../screens/settings_screen.dart";
import "../screens/history_screen.dart";
import "../screens/summaries_screen.dart";
import "../state/app_state.dart";

class AppDrawer extends StatelessWidget {
  const AppDrawer({super.key});

  void _openScreen(BuildContext context, Widget screen) {
    Navigator.pop(context);
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));
  }

  Future<bool> _confirmLogout(BuildContext context) async {
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

  Widget _drawerItem({
    required BuildContext context,
    required IconData icon,
    required String label,
    VoidCallback? onTap,
  }) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(18),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: theme.colorScheme.surface.withOpacity(0.92),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(
              color: theme.colorScheme.outline.withOpacity(0.2),
            ),
          ),
          child: Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: theme.colorScheme.surfaceVariant.withOpacity(0.8),
                ),
                child: Icon(icon, size: 20, color: theme.colorScheme.onSurface),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  label,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
              const Icon(Icons.chevron_left_rounded, size: 20),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final user = context.watch<AppState>().currentUser;
    return Drawer(
      width: 320,
      child: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFF0B0F14), Color(0xFF111823)],
          ),
        ),
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 24, 20, 18),
                child: Row(
                  children: [
                    Container(
                      width: 52,
                      height: 52,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(18),
                        gradient: const LinearGradient(
                          colors: [Color(0xFF23C08B), Color(0xFF3BE7B0)],
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.2),
                            blurRadius: 16,
                            offset: const Offset(0, 8),
                          ),
                        ],
                      ),
                      child: const Icon(
                        Icons.auto_awesome_rounded,
                        color: Color(0xFF061511),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            user?.displayName ?? "غير مسجل",
                            style: theme.textTheme.titleMedium?.copyWith(
                              color: theme.colorScheme.onBackground,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            user?.role ?? "حساب مؤقت",
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: theme.colorScheme.onBackground.withOpacity(
                                0.6,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              _drawerItem(
                context: context,
                icon: Icons.add_comment_rounded,
                label: "محادثة جديدة",
                onTap: () {
                  context.read<AppState>().startNewChat();
                  Navigator.pop(context);
                },
              ),
              _drawerItem(
                context: context,
                icon: Icons.history_rounded,
                label: "المحادثات السابقة",
                onTap: () => _openScreen(context, const HistoryScreen()),
              ),
              _drawerItem(
                context: context,
                icon: Icons.smart_toy_rounded,
                label: "الوكلاء",
                onTap: () => _openScreen(context, const AgentsScreen()),
              ),
              _drawerItem(
                context: context,
                icon: Icons.newspaper_rounded,
                label: "ملخصات الأخبار",
                onTap: () => _openScreen(context, const SummariesScreen()),
              ),
              const Divider(height: 32, thickness: 1),
              _drawerItem(
                context: context,
                icon: Icons.info_outline_rounded,
                label: "حول التطبيق",
                onTap: () => _openScreen(context, const AboutScreen()),
              ),
              _drawerItem(
                context: context,
                icon: Icons.settings_rounded,
                label: "الإعدادات",
                onTap: () => _openScreen(context, const SettingsScreen()),
              ),
              Padding(
                padding: const EdgeInsets.all(16),
                child: OutlinedButton.icon(
                  onPressed: () async {
                    final confirmed = await _confirmLogout(context);
                    if (!confirmed) {
                      return;
                    }
                    await context.read<AppState>().logout();
                    if (context.mounted) {
                      Navigator.pop(context);
                    }
                  },
                  icon: const Icon(Icons.logout_rounded),
                  label: const Text("تسجيل الخروج"),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
