import "dart:ui";

import "package:flutter/material.dart";
import "package:provider/provider.dart";

import "../state/app_state.dart";
import "register_screen.dart";

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _showPassword = false;
  String? _error;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    FocusScope.of(context).unfocus();
    setState(() => _error = null);
    final email = _emailController.text.trim();
    final password = _passwordController.text;
    if (email.isEmpty || password.isEmpty) {
      setState(() => _error = "يرجى إدخال البريد وكلمة المرور.");
      return;
    }
    final error = await context.read<AppState>().login(email, password);
    if (error != null && mounted) {
      if (error.contains("SocketException") ||
          error.contains("Connection refused")) {
        setState(() => _error = "تعذر الاتصال بالخادم. تأكد من تشغيل السيرفر.");
      } else if (error.contains("401")) {
        setState(() => _error = "بيانات الدخول غير صحيحة.");
      } else if (error.contains("403") || error.contains("disabled")) {
        setState(() => _error = "الحساب موقوف. يرجى التواصل مع الإدارة.");
      } else {
        setState(() => _error = error);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isBusy = context.watch<AppState>().isBusy;
    return Scaffold(
      body: Stack(
        children: [
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topRight,
                end: Alignment.bottomLeft,
                colors: [
                  Color(0xFF0B0F14),
                  Color(0xFF111823),
                  Color(0xFF0D1118),
                ],
              ),
            ),
          ),
          Positioned(
            right: -120,
            top: -80,
            child: Container(
              width: 240,
              height: 240,
              decoration: BoxDecoration(
                color: const Color(0xFF23C08B).withOpacity(0.18),
                shape: BoxShape.circle,
              ),
            ),
          ),
          Positioned(
            left: -100,
            bottom: -70,
            child: Container(
              width: 220,
              height: 220,
              decoration: BoxDecoration(
                color: const Color(0xFFD7B46A).withOpacity(0.16),
                shape: BoxShape.circle,
              ),
            ),
          ),
          SafeArea(
            child: LayoutBuilder(
              builder: (context, constraints) {
                return SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 24,
                    vertical: 32,
                  ),
                  child: ConstrainedBox(
                    constraints: BoxConstraints(
                      minHeight: constraints.maxHeight - 64,
                    ),
                    child: IntrinsicHeight(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Container(
                                width: 44,
                                height: 44,
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(14),
                                  gradient: const LinearGradient(
                                    colors: [
                                      Color(0xFF23C08B),
                                      Color(0xFF3BE7B0),
                                    ],
                                  ),
                                  boxShadow: [
                                    BoxShadow(
                                      color: Colors.black.withOpacity(0.2),
                                      blurRadius: 16,
                                      offset: const Offset(0, 8),
                                    ),
                                  ],
                                ),
                                child: ClipRRect(
                                  borderRadius: BorderRadius.circular(12),
                                  child: Image.asset(
                                    "assets/app_icon.png",
                                    fit: BoxFit.cover,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 12),
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.center,
                                children: [
                                  Text(
                                    "مساعد الصحفي",
                                    style:
                                        theme.textTheme.headlineSmall?.copyWith(
                                      color: theme.colorScheme.onBackground,
                                      letterSpacing: 0.6,
                                    ),
                                  ),
                                  Text(
                                    "محرر الأخبار الذكي",
                                    style: theme.textTheme.bodySmall?.copyWith(
                                      color: theme.colorScheme.onBackground
                                          .withOpacity(0.6),
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                          const SizedBox(height: 32),
                          ClipRRect(
                            borderRadius: BorderRadius.circular(28),
                            child: BackdropFilter(
                              filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
                              child: Container(
                                padding: const EdgeInsets.all(24),
                                decoration: BoxDecoration(
                                  color: theme.colorScheme.surface.withOpacity(
                                    0.78,
                                  ),
                                  borderRadius: BorderRadius.circular(28),
                                  border: Border.all(
                                    color: theme.colorScheme.outline
                                        .withOpacity(0.25),
                                  ),
                                ),
                                child: Column(
                                  crossAxisAlignment:
                                      CrossAxisAlignment.stretch,
                                  children: [
                                    Text(
                                      "تسجيل الدخول",
                                      style: theme.textTheme.titleLarge,
                                      textAlign: TextAlign.center,
                                    ),
                                    const SizedBox(height: 6),
                                    Text(
                                      "ادخل إلى غرفة الأخبار الخاصة بك",
                                      textAlign: TextAlign.center,
                                      style:
                                          theme.textTheme.bodySmall?.copyWith(
                                        color: theme.colorScheme.onSurface
                                            .withOpacity(0.65),
                                      ),
                                    ),
                                    const SizedBox(height: 22),
                                    TextField(
                                      controller: _emailController,
                                      keyboardType: TextInputType.emailAddress,
                                      textInputAction: TextInputAction.next,
                                      decoration: const InputDecoration(
                                        labelText: "البريد الإلكتروني",
                                        hintText: "name@jour2.local",
                                        prefixIcon: Icon(
                                          Icons.alternate_email_rounded,
                                        ),
                                      ),
                                    ),
                                    const SizedBox(height: 16),
                                    TextField(
                                      controller: _passwordController,
                                      obscureText: !_showPassword,
                                      onSubmitted: (_) => _submit(),
                                      decoration: InputDecoration(
                                        labelText: "كلمة المرور",
                                        prefixIcon: const Icon(
                                          Icons.lock_rounded,
                                        ),
                                        suffixIcon: IconButton(
                                          onPressed: () => setState(() {
                                            _showPassword = !_showPassword;
                                          }),
                                          icon: Icon(
                                            _showPassword
                                                ? Icons.visibility_off_rounded
                                                : Icons.visibility_rounded,
                                          ),
                                        ),
                                      ),
                                    ),
                                    if (_error != null) ...[
                                      const SizedBox(height: 12),
                                      Text(
                                        _error!,
                                        textAlign: TextAlign.center,
                                        style:
                                            theme.textTheme.bodySmall?.copyWith(
                                          color: theme.colorScheme.error,
                                        ),
                                      ),
                                    ],
                                    const SizedBox(height: 22),
                                    FilledButton(
                                      onPressed: isBusy ? null : _submit,
                                      child: isBusy
                                          ? const SizedBox(
                                              height: 18,
                                              width: 18,
                                              child: CircularProgressIndicator(
                                                strokeWidth: 2,
                                              ),
                                            )
                                          : const Text("تسجيل الدخول"),
                                    ),
                                    const SizedBox(height: 12),
                                    TextButton(
                                      onPressed: () =>
                                          Navigator.of(context).push(
                                        MaterialPageRoute(
                                          builder: (_) =>
                                              const RegisterScreen(),
                                        ),
                                      ),
                                      child: const Text("إنشاء حساب جديد"),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                          const Spacer(),
                          Padding(
                            padding: const EdgeInsets.only(top: 24),
                            child: Text(
                              "كل الحقوق محفوظة ل HQ",
                              textAlign: TextAlign.center,
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: theme.colorScheme.onBackground
                                    .withOpacity(0.5),
                              ),
                            ),
                          ),
                        ],
                      ),
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
