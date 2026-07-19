import 'package:equatable/equatable.dart';

import '../../../infrastructure/ai_backend/extraction_dto.dart';

enum LocalDocumentStatus { queued, extracting, extracted, failed, cancelled }

class LocalDocument extends Equatable {
  const LocalDocument({
    required this.id,
    required this.filename,
    required this.byteLength,
    required this.status,
    required this.createdAt,
    this.extraction,
    this.activityEvents = const [],
    this.error,
  });
  final String id;
  final String filename;
  final int byteLength;
  final LocalDocumentStatus status;
  final DateTime createdAt;
  final DocumentExtractionDto? extraction;
  final List<ActivityEventDto> activityEvents;
  final String? error;
  bool get hasInjectionWarning =>
      extraction?.securityFlags.contains('prompt_injection_detected') ?? false;
  LocalDocument copyWith({
    LocalDocumentStatus? status,
    DocumentExtractionDto? extraction,
    List<ActivityEventDto>? activityEvents,
    String? error,
    bool clearError = false,
  }) => LocalDocument(
    id: id,
    filename: filename,
    byteLength: byteLength,
    status: status ?? this.status,
    createdAt: createdAt,
    extraction: extraction ?? this.extraction,
    activityEvents: activityEvents ?? this.activityEvents,
    error: clearError ? null : error ?? this.error,
  );
  Map<String, dynamic> toJson() => {
    'id': id,
    'filename': filename,
    'byteLength': byteLength,
    'status': status.name,
    'createdAt': createdAt.toIso8601String(),
    'extraction': extraction?.toJson(),
    'activityEvents': activityEvents.map((item) => item.toJson()).toList(),
    'error': error,
  };
  factory LocalDocument.fromJson(Map<String, dynamic> json) => LocalDocument(
    id: json['id'] as String,
    filename: json['filename'] as String,
    byteLength: json['byteLength'] as int,
    status: LocalDocumentStatus.values.byName(json['status'] as String),
    createdAt: DateTime.parse(json['createdAt'] as String),
    extraction: json['extraction'] == null
        ? null
        : DocumentExtractionDto.fromJson(
            Map<String, dynamic>.from(json['extraction'] as Map),
          ),
    activityEvents: (json['activityEvents'] as List? ?? const [])
        .map(
          (item) =>
              ActivityEventDto.fromJson(Map<String, dynamic>.from(item as Map)),
        )
        .toList(),
    error: json['error'] as String?,
  );
  @override
  List<Object?> get props => [
    id,
    filename,
    byteLength,
    status,
    createdAt,
    extraction,
    activityEvents,
    error,
  ];
}
