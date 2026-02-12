import "package:flutter/material.dart";
import "package:provider/provider.dart";

import "../models/agent.dart";
import "../models/chat_message.dart";
import "../models/summary_entry.dart";
import "../state/app_state.dart";
import "../widgets/chat_bubble.dart";

enum PostInputMode { ideas, summary }

class PostWriterScreen extends StatefulWidget {
  final Agent agent;

  const PostWriterScreen({super.key, required this.agent});

  @override
  State<PostWriterScreen> createState() => _PostWriterScreenState();
}

class _PostWriterScreenState extends State<PostWriterScreen> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();
  final List<ChatMessage> _messages = [];

  PostInputMode _mode = PostInputMode.ideas;
  String _draft = "";
  bool _isSending = false;
  bool _loadingSummary = false;
  SummaryEntry? _summary;
  String? _summaryError;

  @override
  void initState() {
    super.initState();
    _loadSummary();
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadSummary() async {
    setState(() {
      _loadingSummary = true;
      _summaryError = null;
    });
    try {
      final state = context.read<AppState>();
      final summaries = await state.apiService.fetchSummaries(
        periodType: "daily",
        limit: 1,
        token: state.authToken,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _summary = summaries.isNotEmpty ? summaries.first : null;
      });
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _summaryError = "تعذر تحميل الملخص اليومي.";
      });
    } finally {
      if (mounted) {
        setState(() => _loadingSummary = false);
      }
    }
  }

  bool get _canSend {
    if (_isSending) {
      return false;
    }
    if (_mode == PostInputMode.ideas) {
      return _draft.trim().isNotEmpty;
    }
    return _summary != null;
  }

  void _scrollToBottom() {
    if (!_scrollController.hasClients) {
      return;
    }
    _scrollController.animateTo(
      _scrollController.position.maxScrollExtent + 160,
      duration: const Duration(milliseconds: 240),
      curve: Curves.easeOut,
    );
  }

  String _formatDate(DateTime date) {
    final local = date.toLocal();
    final year = local.year.toString().padLeft(4, "0");
    final month = local.month.toString().padLeft(2, "0");
    final day = local.day.toString().padLeft(2, "0");
    return "$year-$month-$day";
  }

  String _cleanOutput(String text) {
    var cleaned = text.replaceAll("*", "").replaceAll("```", "").trim();
    final lines = cleaned.split("\n");
    final filtered = <String>[];
    for (final line in lines) {
      final trimmed = line.trim();
      if (trimmed.isEmpty) {
        filtered.add("");
        continue;
      }
      final lower = trimmed.toLowerCase();
      if (lower.contains("كذكاء") ||
          lower.contains("كمساعد") ||
          lower.contains("كنموذج")) {
        continue;
      }
      final bullet = trimmed.startsWith("- ")
          ? trimmed.substring(2)
          : trimmed.startsWith("• ")
          ? trimmed.substring(2)
          : trimmed.startsWith("– ")
          ? trimmed.substring(2)
          : trimmed;
      filtered.add(bullet.trim());
    }
    cleaned = filtered.join("\n").trim();
    return cleaned;
  }

  Future<void> _send() async {
    final state = context.read<AppState>();
    final prompt = _draft.trim();
    String task = prompt;
    String? contextText;
    String userMessage = prompt;

    if (_mode == PostInputMode.summary) {
      if (_summary == null) {
        return;
      }
      contextText = _summary?.content ?? "";
      if (task.isEmpty) {
        task = "حوّل الملخص التالي إلى بوست جاهز للنشر.";
        userMessage = "توليد بوست من الملخص";
      }
    }

    if (task.trim().isEmpty) {
      return;
    }

    setState(() {
      _isSending = true;
      _draft = "";
      _controller.clear();
      _messages.add(ChatMessage.user(userMessage));
    });
    _scrollToBottom();

    try {
      final result = await state.apiService.runAgent(
        task: task,
        context: contextText,
        route: widget.agent.key,
        token: state.authToken,
        geminiKey: state.llmProvider == "gemini" ? state.geminiKey : null,
        groqKey: state.llmProvider == "groq" ? state.groqKey : null,
      );
      if (!mounted) {
        return;
      }
      final output = _cleanOutput(result.output);
      setState(() {
        _messages.add(
          ChatMessage.assistant(output.isEmpty ? result.output : output),
        );
      });
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _messages.add(ChatMessage.system("تعذر إنشاء البوست حالياً."));
      });
    } finally {
      if (mounted) {
        setState(() => _isSending = false);
        _scrollToBottom();
      }
    }
  }

  Widget _buildSummaryCard(ThemeData theme) {
    if (_loadingSummary) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: theme.colorScheme.surface.withOpacity(0.9),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: theme.colorScheme.outline.withOpacity(0.25),
          ),
        ),
        child: Row(
          children: [
            const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            const SizedBox(width: 12),
            Text("جارٍ تحميل الملخص...", style: theme.textTheme.bodyMedium),
          ],
        ),
      );
    }

    if (_summaryError != null) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: theme.colorScheme.surface.withOpacity(0.9),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: theme.colorScheme.outline.withOpacity(0.25),
          ),
        ),
        child: Row(
          children: [
            Expanded(
              child: Text(
                _summaryError!,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.error,
                ),
              ),
            ),
            TextButton(
              onPressed: _loadSummary,
              child: const Text("إعادة المحاولة"),
            ),
          ],
        ),
      );
    }

    if (_summary == null) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: theme.colorScheme.surface.withOpacity(0.9),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: theme.colorScheme.outline.withOpacity(0.25),
          ),
        ),
        child: Row(
          children: [
            Expanded(
              child: Text(
                "لا يوجد ملخص يومي متاح حالياً.",
                style: theme.textTheme.bodyMedium,
              ),
            ),
            TextButton(onPressed: _loadSummary, child: const Text("تحديث")),
          ],
        ),
      );
    }

    final summary = _summary!;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface.withOpacity(0.95),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: theme.colorScheme.outline.withOpacity(0.25)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  "آخر ملخص يومي (${_formatDate(summary.periodStart)})",
                  style: theme.textTheme.titleSmall,
                ),
              ),
              TextButton(onPressed: _loadSummary, child: const Text("تحديث")),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            summary.content,
            maxLines: 4,
            overflow: TextOverflow.ellipsis,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurface.withOpacity(0.7),
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(widget.agent.name), centerTitle: true),
      body: Stack(
        children: [
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Color(0xFF0B0F14),
                  Color(0xFF0F141B),
                  Color(0xFF0B0F14),
                ],
              ),
            ),
          ),
          Positioned(
            right: -60,
            top: 140,
            child: Container(
              width: 160,
              height: 160,
              decoration: BoxDecoration(
                color: const Color(0xFF23C08B).withOpacity(0.07),
                shape: BoxShape.circle,
              ),
            ),
          ),
          Positioned(
            left: -40,
            bottom: 120,
            child: Container(
              width: 140,
              height: 140,
              decoration: BoxDecoration(
                color: const Color(0xFFD7B46A).withOpacity(0.08),
                shape: BoxShape.circle,
              ),
            ),
          ),
          Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    SegmentedButton<PostInputMode>(
                      segments: const [
                        ButtonSegment(
                          value: PostInputMode.ideas,
                          label: Text("أفكارك"),
                        ),
                        ButtonSegment(
                          value: PostInputMode.summary,
                          label: Text("استيراد ملخص"),
                        ),
                      ],
                      selected: {_mode},
                      onSelectionChanged: (value) {
                        setState(() => _mode = value.first);
                      },
                    ),
                    const SizedBox(height: 12),
                    if (_mode == PostInputMode.summary)
                      _buildSummaryCard(theme),
                  ],
                ),
              ),
              Expanded(
                child: _messages.isEmpty
                    ? Center(
                        child: Container(
                          padding: const EdgeInsets.all(20),
                          margin: const EdgeInsets.symmetric(horizontal: 24),
                          decoration: BoxDecoration(
                            color: theme.colorScheme.surface.withOpacity(0.85),
                            borderRadius: BorderRadius.circular(22),
                            border: Border.all(
                              color: theme.colorScheme.outline.withOpacity(0.2),
                            ),
                          ),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(
                                Icons.edit_rounded,
                                size: 28,
                                color: Color(0xFFD7B46A),
                              ),
                              const SizedBox(height: 10),
                              Text(
                                "اكتب فكرتك أو استخدم الملخص لإنشاء بوست",
                                style: theme.textTheme.titleSmall,
                                textAlign: TextAlign.center,
                              ),
                              const SizedBox(height: 6),
                              Text(
                                "الناتج سيكون جاهزاً للنسخ والنشر مباشرة",
                                style: theme.textTheme.bodySmall?.copyWith(
                                  color: theme.colorScheme.onSurface
                                      .withOpacity(0.6),
                                ),
                                textAlign: TextAlign.center,
                              ),
                            ],
                          ),
                        ),
                      )
                    : ListView.separated(
                        controller: _scrollController,
                        padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
                        physics: const BouncingScrollPhysics(),
                        itemCount: _messages.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 10),
                        itemBuilder: (context, index) {
                          return ChatBubble(message: _messages[index]);
                        },
                      ),
              ),
              AnimatedOpacity(
                opacity: _isSending ? 1 : 0,
                duration: const Duration(milliseconds: 200),
                child: Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                      const SizedBox(width: 10),
                      Text(
                        "جارٍ توليد البوست...",
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onSurface.withOpacity(0.7),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              SafeArea(
                top: false,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 10,
                    ),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.surface.withOpacity(0.92),
                      borderRadius: BorderRadius.circular(26),
                      border: Border.all(
                        color: theme.colorScheme.outline.withOpacity(0.25),
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.25),
                          blurRadius: 18,
                          offset: const Offset(0, 10),
                        ),
                      ],
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _controller,
                            minLines: 1,
                            maxLines: 4,
                            textInputAction: TextInputAction.send,
                            onChanged: (value) =>
                                setState(() => _draft = value),
                            onSubmitted: (_) => _canSend ? _send() : null,
                            decoration: InputDecoration(
                              hintText: _mode == PostInputMode.summary
                                  ? "أضف توجيهاً اختيارياً للبوست..."
                                  : "اكتب أفكارك للبوست هنا...",
                              border: InputBorder.none,
                              filled: false,
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Container(
                          width: 44,
                          height: 44,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            gradient: const LinearGradient(
                              colors: [Color(0xFF23C08B), Color(0xFF3BE7B0)],
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: const Color(
                                  0xFF23C08B,
                                ).withOpacity(0.35),
                                blurRadius: 12,
                                offset: const Offset(0, 6),
                              ),
                            ],
                          ),
                          child: IconButton(
                            onPressed: _canSend ? _send : null,
                            icon: const Icon(
                              Icons.arrow_upward_rounded,
                              color: Color(0xFF0A1512),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
