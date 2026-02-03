import "package:flutter/foundation.dart";

class AppConfig {
  static String get apiBaseUrl {
    const override = String.fromEnvironment("JOUR2_API_BASE");
    if (override.isNotEmpty) {
      return override;
    }
    if (kIsWeb) {
      return "http://localhost:8000";
    }
    if (defaultTargetPlatform == TargetPlatform.android) {
      return "http://localhost:8000";
    }
    return "http://localhost:8000";
  }
}
