import "package:flutter/material.dart";
import "package:provider/provider.dart";

import "../models/agent.dart";
import "../services/api_service.dart";
import "../state/app_state.dart";
import "agent_chat_screen.dart";

class AgentsScreen extends StatefulWidget {
  const AgentsScreen({super.key});

  @override
  State<AgentsScreen> createState() => _AgentsScreenState();
}

class _AgentsScreenState extends State<AgentsScreen> {
  bool _loading = true;
  String? _error;
  List<Agent> _agents = [];

  @override
  void initState() {
    super.initState();
    _loadAgents();
  }

  Future<void> _loadAgents() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final state = context.read<AppState>();
      final agents = await state.apiService.fetchAgents(token: state.authToken);
      setState(() {
        _agents = agents.where((agent) => agent.isActive).toList();
      });
    } catch (_) {
      setState(() {
        _error = "تعذر تحميل الوكلاء حالياً.";
      });
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  void _openAgent(Agent agent) {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => AgentChatScreen(agent: agent)),
    );
  }

  void _showRunSheet(Agent agent) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) {
        final controller = TextEditingController();
        bool running = false;
        return StatefulBuilder(
          builder: (context, setModalState) {
            return Padding(
              padding: EdgeInsets.only(
                left: 20,
                right: 20,
                top: 16,
                bottom: MediaQuery.of(context).viewInsets.bottom + 20,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    "تشغيل الوكيل",
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    agent.name,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: Theme.of(
                            context,
                          ).colorScheme.onSurface.withOpacity(0.7),
                        ),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: controller,
                    minLines: 2,
                    maxLines: 4,
                    decoration: const InputDecoration(
                      hintText: "اكتب التوجيه أو المهمة هنا...",
                    ),
                  ),
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: running
                        ? null
                        : () async {
                            final prompt = controller.text.trim();
                            if (prompt.isEmpty) {
                              return;
                            }
                            setModalState(() => running = true);
                            try {
                              final state = context.read<AppState>();
                              final result = await state.apiService.runAgent(
                                task: prompt,
                                route: agent.key,
                                token: state.authToken,
                                geminiKey: state.geminiKey,
                              );
                              if (mounted) {
                                Navigator.pop(context);
                                _showOutput(result.output);
                              }
                            } on ApiException catch (_) {
                              if (mounted) {
                                setModalState(() => running = false);
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                    content: Text("فشل تشغيل الوكيل."),
                                  ),
                                );
                              }
                            }
                          },
                    child: running
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text("تشغيل الآن"),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  void _showOutput(String output) {
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text("نتيجة الوكيل"),
          content: SingleChildScrollView(child: SelectableText(output)),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text("إغلاق"),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text("الوكلاء")),
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
          _loading
              ? const Center(child: CircularProgressIndicator())
              : _error != null
                  ? Center(
                      child: Text(
                        _error!,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: theme.colorScheme.error,
                        ),
                      ),
                    )
                  : RefreshIndicator(
                      onRefresh: _loadAgents,
                      child: ListView.separated(
                        padding: const EdgeInsets.all(16),
                        physics: const BouncingScrollPhysics(),
                        itemCount: _agents.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 12),
                        itemBuilder: (context, index) {
                          final agent = _agents[index];
                          return InkWell(
                            onTap: () => _openAgent(agent),
                            borderRadius: BorderRadius.circular(22),
                            child: Container(
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(
                                color:
                                    theme.colorScheme.surface.withOpacity(0.95),
                                borderRadius: BorderRadius.circular(22),
                                border: Border.all(
                                  color: theme.colorScheme.outline
                                      .withOpacity(0.2),
                                ),
                              ),
                              child: Row(
                                children: [
                                  Container(
                                    width: 46,
                                    height: 46,
                                    decoration: BoxDecoration(
                                      borderRadius: BorderRadius.circular(16),
                                      color: theme.colorScheme.surfaceVariant
                                          .withOpacity(0.8),
                                    ),
                                    child: const Icon(Icons.smart_toy_rounded),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          agent.name,
                                          style: theme.textTheme.titleMedium,
                                        ),
                                        const SizedBox(height: 6),
                                        Text(
                                          agent.description ?? "بدون وصف",
                                          maxLines: 2,
                                          overflow: TextOverflow.ellipsis,
                                          style: theme.textTheme.bodySmall
                                              ?.copyWith(
                                            color: theme.colorScheme.onSurface
                                                .withOpacity(0.6),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                  Column(
                                    children: [
                                      Container(
                                        padding: const EdgeInsets.symmetric(
                                          horizontal: 10,
                                          vertical: 6,
                                        ),
                                        decoration: BoxDecoration(
                                          color: theme
                                              .colorScheme.surfaceVariant
                                              .withOpacity(0.7),
                                          borderRadius:
                                              BorderRadius.circular(12),
                                        ),
                                        child: Text(
                                          agent.agentType,
                                          style: theme.textTheme.labelSmall
                                              ?.copyWith(
                                            color: theme.colorScheme.onSurface,
                                          ),
                                        ),
                                      ),
                                      const SizedBox(height: 8),
                                      Row(
                                        children: [
                                          Icon(
                                            Icons.circle,
                                            size: 10,
                                            color: agent.isActive
                                                ? const Color(0xFF23C08B)
                                                : theme.colorScheme.outline,
                                          ),
                                          const SizedBox(width: 4),
                                          Text(
                                            agent.isActive ? "نشط" : "موقوف",
                                            style: theme.textTheme.labelSmall
                                                ?.copyWith(
                                              color: theme.colorScheme.onSurface
                                                  .withOpacity(0.7),
                                            ),
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
                    ),
        ],
      ),
    );
  }
}
