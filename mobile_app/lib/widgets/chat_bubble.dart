import "package:flutter/material.dart";
import "package:flutter/services.dart";

import "../models/chat_message.dart";

class ChatBubble extends StatelessWidget {
  final ChatMessage message;

  const ChatBubble({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isUser = message.role == ChatRole.user;
    final isSystem = message.role == ChatRole.system;
    final maxWidth = MediaQuery.of(context).size.width * 0.78;

    final bubbleDecoration = BoxDecoration(
      color: isSystem
          ? theme.colorScheme.error.withOpacity(0.12)
          : isUser
              ? null
              : theme.colorScheme.surface.withOpacity(0.95),
      gradient: isUser
          ? const LinearGradient(
              colors: [
                Color(0xFF23C08B),
                Color(0xFF2FDBA3),
              ],
            )
          : null,
      borderRadius: BorderRadius.only(
        topLeft: const Radius.circular(22),
        topRight: const Radius.circular(22),
        bottomLeft: Radius.circular(isUser ? 22 : 8),
        bottomRight: Radius.circular(isUser ? 8 : 22),
      ),
      border: isUser || isSystem
          ? null
          : Border.all(
              color: theme.colorScheme.outline.withOpacity(0.18),
            ),
      boxShadow: [
        BoxShadow(
          color: Colors.black.withOpacity(0.18),
          blurRadius: 12,
          offset: const Offset(0, 6),
        ),
      ],
    );

    final textColor = isUser
        ? const Color(0xFF0A1512)
        : theme.colorScheme.onSurface;

    final alignment =
        isSystem ? Alignment.center : (isUser ? Alignment.centerRight : Alignment.centerLeft);

    return Align(
      alignment: alignment,
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: maxWidth),
        child: Column(
          crossAxisAlignment: isUser
              ? CrossAxisAlignment.end
              : isSystem
                  ? CrossAxisAlignment.center
                  : CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              decoration: bubbleDecoration,
              child: Text(
                message.content,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: textColor,
                  height: 1.5,
                ),
              ),
            ),
            const SizedBox(height: 4),
            TextButton.icon(
              onPressed: () async {
                await Clipboard.setData(ClipboardData(text: message.content));
                if (!context.mounted) {
                  return;
                }
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text("تم النسخ")),
                );
              },
              icon: const Icon(Icons.copy_rounded, size: 16),
              label: const Text("نسخ"),
              style: TextButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                minimumSize: Size.zero,
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                foregroundColor: theme.colorScheme.onSurface.withOpacity(0.7),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

