import 'package:equatable/equatable.dart';

enum SessionStage { consent, profile, understand, prepare }

class LocalSession extends Equatable {
  const LocalSession({
    required this.id,
    required this.createdAt,
    required this.expiresAt,
    this.consentAt,
    this.localeCode,
  });

  final String id;
  final DateTime createdAt;
  final DateTime expiresAt;
  final DateTime? consentAt;
  final String? localeCode;

  bool get hasConsent => consentAt != null;
  bool get isExpired => !DateTime.now().isBefore(expiresAt);
  SessionStage get stage =>
      hasConsent ? SessionStage.profile : SessionStage.consent;

  LocalSession copyWith({DateTime? consentAt, String? localeCode}) =>
      LocalSession(
        id: id,
        createdAt: createdAt,
        expiresAt: expiresAt,
        consentAt: consentAt ?? this.consentAt,
        localeCode: localeCode ?? this.localeCode,
      );

  Map<String, Object?> toJson() => {
    'id': id,
    'createdAt': createdAt.toIso8601String(),
    'expiresAt': expiresAt.toIso8601String(),
    'consentAt': consentAt?.toIso8601String(),
    'localeCode': localeCode,
  };

  static LocalSession? fromJson(Map<String, Object?> json) {
    try {
      return LocalSession(
        id: json['id']! as String,
        createdAt: DateTime.parse(json['createdAt']! as String),
        expiresAt: DateTime.parse(json['expiresAt']! as String),
        consentAt: json['consentAt'] == null
            ? null
            : DateTime.parse(json['consentAt']! as String),
        localeCode: json['localeCode'] as String?,
      );
    } on FormatException {
      return null;
    }
  }

  @override
  List<Object?> get props => [id, createdAt, expiresAt, consentAt, localeCode];
}
