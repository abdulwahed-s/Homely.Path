enum AiMode { disabled, mock, http }

class AppConfig {
  const AppConfig({required this.aiMode, required this.aiBaseUrl});

  factory AppConfig.fromEnvironment() {
    const mode = String.fromEnvironment('AI_MODE', defaultValue: 'disabled');
    const baseUrl = String.fromEnvironment('AI_BASE_URL');
    return AppConfig(
      aiMode: switch (mode) {
        'http' => AiMode.http,
        'mock' => AiMode.mock,
        _ => AiMode.disabled,
      },
      aiBaseUrl: baseUrl,
    );
  }

  final AiMode aiMode;
  final String aiBaseUrl;

  bool get hasHttpBackend => aiMode == AiMode.http && aiBaseUrl.isNotEmpty;
}
