import "package:flutter/material.dart";
import "package:flutter/services.dart";
import "package:flutter_localizations/flutter_localizations.dart";
import "package:google_fonts/google_fonts.dart";
import "package:provider/provider.dart";

import "app_config.dart";
import "screens/chat_screen.dart";
import "screens/login_screen.dart";
import "services/api_service.dart";
import "services/secure_storage_service.dart";
import "state/app_state.dart";

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.light,
      statusBarBrightness: Brightness.dark,
    ),
  );
  final appState = AppState(
    apiService: ApiService(AppConfig.apiBaseUrl),
    storage: SecureStorageService(),
  );
  await appState.loadSession();
  runApp(JournalistAssistantApp(appState: appState));
}

class JournalistAssistantApp extends StatelessWidget {
  final AppState appState;

  const JournalistAssistantApp({super.key, required this.appState});

  ThemeData _buildTheme() {
    const colorScheme = ColorScheme.dark(
      primary: Color(0xFF23C08B),
      secondary: Color(0xFFD7B46A),
      background: Color(0xFF0A0C10),
      surface: Color(0xFF151A21),
      onPrimary: Color(0xFF071512),
      onSecondary: Color(0xFF1C1406),
      onBackground: Color(0xFFEAF0F6),
      onSurface: Color(0xFFEAF0F6),
      outline: Color(0xFF2B3242),
      error: Color(0xFFFF6B6B),
    );
    final scheme = colorScheme.copyWith(
      surfaceVariant: const Color(0xFF1C232E),
      onSurfaceVariant: const Color(0xFFB8C2D0),
    );
    final base = ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: scheme.background,
      dividerColor: scheme.outline.withOpacity(0.2),
    );
    final textTheme =
        GoogleFonts.ibmPlexSansArabicTextTheme(base.textTheme).copyWith(
      displaySmall: GoogleFonts.notoKufiArabic(
        textStyle: base.textTheme.displaySmall,
        fontWeight: FontWeight.w600,
      ),
      headlineMedium: GoogleFonts.notoKufiArabic(
        textStyle: base.textTheme.headlineMedium,
        fontWeight: FontWeight.w600,
      ),
      titleLarge: GoogleFonts.notoKufiArabic(
        textStyle: base.textTheme.titleLarge,
        fontWeight: FontWeight.w600,
      ),
    );

    return base.copyWith(
      textTheme: textTheme,
      appBarTheme: AppBarTheme(
        backgroundColor: scheme.background,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        centerTitle: true,
        iconTheme: IconThemeData(color: scheme.onBackground),
        titleTextStyle: textTheme.titleLarge?.copyWith(
          color: scheme.onBackground,
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: scheme.surface.withOpacity(0.9),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(20),
          borderSide: BorderSide(
            color: scheme.outline.withOpacity(0.3),
          ),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(20),
          borderSide: BorderSide(
            color: scheme.outline.withOpacity(0.25),
          ),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(20),
          borderSide: BorderSide(color: scheme.primary, width: 1.4),
        ),
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
        hintStyle: textTheme.bodyMedium?.copyWith(
          color: scheme.onSurface.withOpacity(0.5),
        ),
        labelStyle: textTheme.bodyMedium?.copyWith(
          color: scheme.onSurface.withOpacity(0.7),
        ),
      ),
      cardTheme: CardThemeData(
        color: scheme.surface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(22),
          side: BorderSide(color: scheme.outline.withOpacity(0.2)),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: scheme.primary,
          foregroundColor: scheme.onPrimary,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: scheme.primary,
          foregroundColor: scheme.onPrimary,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: scheme.onSurface,
          side: BorderSide(color: scheme.outline.withOpacity(0.35)),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
        ),
      ),
      listTileTheme: ListTileThemeData(
        iconColor: scheme.onSurface,
        textColor: scheme.onSurface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: scheme.surface,
        surfaceTintColor: Colors.transparent,
        showDragHandle: true,
        dragHandleColor: scheme.outline.withOpacity(0.5),
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: scheme.surface,
        contentTextStyle: textTheme.bodyMedium?.copyWith(
          color: scheme.onSurface,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider.value(
      value: appState,
      child: MaterialApp(
        title: "المساعد الصحفي",
        theme: _buildTheme(),
        locale: const Locale("ar"),
        supportedLocales: const [Locale("ar"), Locale("en")],
        localizationsDelegates: const [
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        builder: (context, child) {
          return Directionality(
            textDirection: TextDirection.rtl,
            child: child ?? const SizedBox.shrink(),
          );
        },
        home: const RootScreen(),
      ),
    );
  }
}

class RootScreen extends StatelessWidget {
  const RootScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<AppState>(
      builder: (context, state, _) {
        if (state.initializing) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }
        if (!state.isAuthenticated) {
          return const LoginScreen();
        }
        return const ChatScreen();
      },
    );
  }
}
