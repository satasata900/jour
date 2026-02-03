import "package:flutter/material.dart";
import "package:provider/provider.dart";

import "../state/app_state.dart";
import "../widgets/app_drawer.dart";
import "../widgets/chat_bubble.dart";

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();
  String _draft = "";
  AppState? _appState;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final state = context.read<AppState>();
    if (_appState != state) {
      _appState?.removeListener(_handleStateChanged);
      _appState = state;
      _appState?.addListener(_handleStateChanged);
    }
  }

  @override
  void dispose() {
    _appState?.removeListener(_handleStateChanged);
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _handleStateChanged() {
    if (!mounted) {
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToBottom());
  }

  void _scrollToBottom() {
    if (!_scrollController.hasClients) {
      return;
    }
    // With reverse: true, offset 0 is the bottom!
    _scrollController.animateTo(
      0.0,
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeOutCubic,
    );
  }

  Future<void> _send(AppState state) async {
    final text = _draft.trim();
    if (text.isEmpty || state.isSending) {
      return;
    }
    _controller.clear();
    setState(() => _draft = "");
    await state.sendMessage(text);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      endDrawer: const AppDrawer(),
      appBar: AppBar(
        title: Column(
          children: [
            Text("المساعد الصحفي", style: theme.textTheme.titleLarge),
            const SizedBox(height: 2),
            Text(
              "استوديو الأخبار الذكي",
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onBackground.withOpacity(0.6),
              ),
            ),
          ],
        ),
        actions: [
          Builder(
            builder: (context) {
              return Padding(
                padding: const EdgeInsets.only(left: 8, right: 4),
                child: IconButton(
                  icon: const Icon(Icons.grid_view_rounded),
                  onPressed: () => Scaffold.of(context).openEndDrawer(),
                ),
              );
            },
          ),
        ],
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
          Consumer<AppState>(
            builder: (context, state, _) {
              final messages = state.messages;
              return Column(
                children: [
                  Expanded(
                    child: Stack(
                      children: [
                        ListView.separated(
                          controller: _scrollController,
                          padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
                          physics: const BouncingScrollPhysics(),
                          itemCount: messages.length,
                          reverse: true,
                          separatorBuilder: (_, __) =>
                              const SizedBox(height: 8),
                          itemBuilder: (context, index) {
                            // index 0 is at the bottom (newest message)
                            final message =
                                messages[messages.length - 1 - index];
                            return ChatBubble(message: message);
                          },
                        ),
                        if (messages.isEmpty)
                          Center(
                            child: Container(
                              margin: const EdgeInsets.symmetric(
                                horizontal: 40,
                              ),
                              padding: const EdgeInsets.all(24),
                              decoration: BoxDecoration(
                                color: theme.colorScheme.surface.withOpacity(
                                  0.8,
                                ),
                                borderRadius: BorderRadius.circular(24),
                                border: Border.all(
                                  color: theme.colorScheme.outline.withOpacity(
                                    0.2,
                                  ),
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
                                    "ابدأ محادثة تحريرية الآن",
                                    style: theme.textTheme.titleMedium,
                                  ),
                                  const SizedBox(height: 6),
                                  Text(
                                    "صف ما تحتاجه وسنقترح معالجة سريعة",
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
                  // Fixed height container avoids jumping when loading starts/stops
                  SizedBox(
                    height: 4,
                    child: state.isSending
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
                                onSubmitted: (_) => _send(state),
                                decoration: const InputDecoration(
                                  hintText: "اكتب رسالتك التحريرية...",
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
                                    color: const Color(
                                      0xFF23C08B,
                                    ).withOpacity(0.35),
                                    blurRadius: 12,
                                    offset: const Offset(0, 6),
                                  ),
                                ],
                              ),
                              child: IconButton(
                                onPressed:
                                    _draft.trim().isEmpty || state.isSending
                                        ? null
                                        : () => _send(state),
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
              );
            },
          ),
        ],
      ),
    );
  }
}
