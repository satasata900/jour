import "package:flutter/foundation.dart";

class AppConfig {
  static String get apiBaseUrl {
    const override = String.fromEnvironment("JOUR2_API_BASE");
    if (override.isNotEmpty) {
      return override;
    }
    if (kIsWeb) {
      return "http://206.189.18.29";
    }
    if (defaultTargetPlatform == TargetPlatform.android) {
      return "http://206.189.18.29";
    }
    return "http://206.189.18.29";
  }
}
