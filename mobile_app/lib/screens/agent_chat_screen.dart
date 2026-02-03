import "package:flutter/material.dart";
import "package:provider/provider.dart";

import "../models/agent.dart";
import "../models/chat_message.dart";
import "../state/app_state.dart";
import "../widgets/chat_bubble.dart";

class AgentChatScreen extends StatefulWidget {
  final Agent agent;

  const AgentChatScreen({super.key, required this.agent});

  @override
  State<AgentChatScreen> createState() => _AgentChatScreenState();
}

class _AgentChatScreenState extends State<AgentChatScreen> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();
  final List<ChatMessage> _messages = [];
  String _draft = "";
  bool _isSending = false;
  int? _sessionId;

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    if (!_scrollController.hasClients) {
      return;
    }
    _scrollController.animateTo(
      0.0,
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeOutCubic,
    );
  }

  String _buildSessionTitle(String prompt) {
    final trimmed = prompt.trim();
    if (trimmed.isEmpty) {
      return widget.agent.name;
    }
    final snippet =
        trimmed.length > 30 ? "${trimmed.substring(0, 30)}..." : trimmed;
    return "${widget.agent.name} - $snippet";
  }

  Future<void> _send() async {
    final state = context.read<AppState>();
    final prompt = _draft.trim();
    if (prompt.isEmpty || _isSending) {
      return;
    }
    if (state.authToken == null) {
      setState(() {
        _messages.add(ChatMessage.system("يرجى تسجيل الدخول أولاً."));
      });
      return;
    }
    if (state.geminiKey == null || state.geminiKey!.isEmpty) {
      setState(() {
        _messages.add(
          ChatMessage.system(
            "يرجى إدخال مفتاح Gemini في الإعدادات لتفعيل الوكيل.",
          ),
        );
      });
      return;
    }

    _controller.clear();
    setState(() {
      _draft = "";
      _isSending = true;
      _messages.add(ChatMessage.user(prompt));
    });
    _scrollToBottom();

    try {
      if (_sessionId == null) {
        final session = await state.apiService.createChatSession(
          state.authToken!,
          title: _buildSessionTitle(prompt),
        );
        final id = session["id"];
        if (id is int) {
          _sessionId = id;
        } else if (id is num) {
          _sessionId = id.toInt();
        } else if (id is String) {
          _sessionId = int.tryParse(id.trim());
        }
      }

      if (_sessionId != null) {
        state.apiService
            .addChatMessage(state.authToken!, _sessionId!, "user", prompt)
            .catchError((e) => print("Log error: $e"));
      }

      final result = await state.apiService.runAgent(
        task: prompt,
        route: widget.agent.key,
        token: state.authToken,
        geminiKey: state.geminiKey,
      );

      if (!mounted) {
        return;
      }

      final output = result.output.trim();
      setState(() {
        _messages.add(
          ChatMessage.assistant(output.isEmpty ? "رد فارغ." : output),
        );
      });

      if (_sessionId != null) {
        state.apiService
            .addChatMessage(state.authToken!, _sessionId!, "model", output)
            .catchError((e) => print("Log error: $e"));
      }
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _messages.add(ChatMessage.system("تعذر تشغيل الوكيل حالياً."));
      });
    } finally {
      if (mounted) {
        setState(() => _isSending = false);
        _scrollToBottom();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.agent.name),
        centerTitle: true,
      ),
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
            right: -80,
            top: 120,
            child: Container(
              width: 180,
              height: 180,
              decoration: BoxDecoration(
                color: const Color(0xFF23C08B).withOpacity(0.08),
                shape: BoxShape.circle,
              ),
            ),
          ),
          Positioned(
            left: -60,
            bottom: 160,
            child: Container(
              width: 160,
              height: 160,
              decoration: BoxDecoration(
                color: const Color(0xFFD7B46A).withOpacity(0.08),
                shape: BoxShape.circle,
              ),
            ),
          ),
          Column(
            children: [
              Expanded(
                child: Stack(
                  children: [
                    ListView.separated(
                      controller: _scrollController,
                      padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
                      physics: const BouncingScrollPhysics(),
                      itemCount: _messages.length,
                      reverse: true,
                      separatorBuilder: (_, __) => const SizedBox(height: 8),
                      itemBuilder: (context, index) {
                        final message = _messages[_messages.length - 1 - index];
                        return ChatBubble(message: message);
                      },
                    ),
                    if (_messages.isEmpty)
                      Center(
                        child: Container(
                          margin: const EdgeInsets.symmetric(horizontal: 40),
                          padding: const EdgeInsets.all(24),
                          decoration: BoxDecoration(
                            color: theme.colorScheme.surface.withOpacity(0.8),
                            borderRadius: BorderRadius.circular(24),
                            border: Border.all(
                              color: theme.colorScheme.outline.withOpacity(0.2),
                            ),
                          ),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(
                                Icons.chat_bubble_outline_rounded,
                                size: 32,
                                color: Color(0xFF23C08B),
                              ),
                              const SizedBox(height: 12),
                              Text(
                                "ابدأ محادثة مع ${widget.agent.name}",
                                style: theme.textTheme.titleMedium,
                                textAlign: TextAlign.center,
                              ),
                              const SizedBox(height: 6),
                              Text(
                                "اكتب طلبك وسيقوم الوكيل بالرد",
                                style: theme.textTheme.bodySmall?.copyWith(
                                  color: theme.colorScheme.onSurface
                                      .withOpacity(0.6),
                                ),
                                textAlign: TextAlign.center,
                              ),
                            ],
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              SizedBox(
                height: 4,
                child: _isSending
                    ? const LinearProgressIndicator(
                        backgroundColor: Colors.transparent,
                      )
                    : const SizedBox.shrink(),
              ),
              const SizedBox(height: 4),
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
                            onSubmitted: (_) => _send(),
                            decoration: const InputDecoration(
                              hintText: "اكتب رسالتك...",
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
                              colors: [
                                Color(0xFF23C08B),
                                Color(0xFF3BE7B0),
                              ],
                            ),
                            boxShadow: [
                              BoxShadow(
                                color:
                                    const Color(0xFF23C08B).withOpacity(0.35),
                                blurRadius: 12,
                                offset: const Offset(0, 6),
                              ),
                            ],
                          ),
                          child: IconButton(
                            onPressed: _draft.trim().isEmpty || _isSending
                                ? null
                                : _send,
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
