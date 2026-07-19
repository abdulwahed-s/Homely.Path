import 'package:json_annotation/json_annotation.dart';

part 'extraction_dto.g.dart';

@JsonSerializable()
class SourceBoxDto {
  const SourceBoxDto({
    required this.page,
    required this.x1,
    required this.y1,
    required this.x2,
    required this.y2,
    required this.sourceDescription,
  });
  factory SourceBoxDto.fromJson(Map<String, dynamic> json) =>
      _$SourceBoxDtoFromJson(json);
  final int page;
  final double x1;
  final double y1;
  final double x2;
  final double y2;
  @JsonKey(name: 'source_description')
  final String sourceDescription;
  Map<String, dynamic> toJson() => _$SourceBoxDtoToJson(this);
}

@JsonSerializable(explicitToJson: true)
class ExtractedFieldDto {
  const ExtractedFieldDto({
    required this.fieldName,
    required this.value,
    required this.normalizedValue,
    required this.confidence,
    required this.confidenceLevel,
    required this.confirmationStatus,
    required this.requiresManualEntry,
    required this.source,
  });
  factory ExtractedFieldDto.fromJson(Map<String, dynamic> json) =>
      _$ExtractedFieldDtoFromJson(json);
  @JsonKey(name: 'field_name')
  final String fieldName;
  final String? value;
  @JsonKey(name: 'normalized_value')
  final Object? normalizedValue;
  final double confidence;
  @JsonKey(name: 'confidence_level')
  final String confidenceLevel;
  @JsonKey(name: 'confirmation_status')
  final String confirmationStatus;
  @JsonKey(name: 'requires_manual_entry')
  final bool requiresManualEntry;
  final SourceBoxDto source;
  Map<String, dynamic> toJson() => _$ExtractedFieldDtoToJson(this);
}

@JsonSerializable(explicitToJson: true)
class DocumentExtractionDto {
  const DocumentExtractionDto({
    required this.documentId,
    required this.documentType,
    required this.securityFlags,
    required this.fields,
  });
  factory DocumentExtractionDto.fromJson(Map<String, dynamic> json) =>
      _$DocumentExtractionDtoFromJson(json);
  @JsonKey(name: 'document_id')
  final String documentId;
  @JsonKey(name: 'document_type')
  final String documentType;
  @JsonKey(name: 'security_flags')
  final List<String> securityFlags;
  final List<ExtractedFieldDto> fields;
  Map<String, dynamic> toJson() => _$DocumentExtractionDtoToJson(this);
}

@JsonSerializable(explicitToJson: true)
class ActivityEventDto {
  const ActivityEventDto({
    required this.timestamp,
    required this.agent,
    required this.action,
    required this.status,
    required this.metadata,
  });
  factory ActivityEventDto.fromJson(Map<String, dynamic> json) =>
      _$ActivityEventDtoFromJson(json);
  final DateTime timestamp;
  final String agent;
  final String action;
  final String status;
  final Map<String, Object?> metadata;
  Map<String, dynamic> toJson() => _$ActivityEventDtoToJson(this);
}

@JsonSerializable(explicitToJson: true)
class ExtractionResponseDto {
  const ExtractionResponseDto({
    required this.sessionId,
    required this.document,
    required this.activityEvents,
  });
  factory ExtractionResponseDto.fromJson(Map<String, dynamic> json) =>
      _$ExtractionResponseDtoFromJson(json);
  @JsonKey(name: 'session_id')
  final String sessionId;
  final DocumentExtractionDto document;
  @JsonKey(name: 'activity_events')
  final List<ActivityEventDto> activityEvents;
  Map<String, dynamic> toJson() => _$ExtractionResponseDtoToJson(this);
}

@JsonSerializable(explicitToJson: true)
class ConflictDto {
  const ConflictDto({
    required this.conflictId,
    required this.code,
    required this.severity,
    required this.message,
    required this.documentIds,
    required this.fieldNames,
    required this.observedValues,
    required this.sourceRefs,
  });
  factory ConflictDto.fromJson(Map<String, dynamic> json) =>
      _$ConflictDtoFromJson(json);
  @JsonKey(name: 'conflict_id')
  final String conflictId;
  final String code;
  final String severity;
  final String message;
  @JsonKey(name: 'document_ids')
  final List<String> documentIds;
  @JsonKey(name: 'field_names')
  final List<String> fieldNames;
  @JsonKey(name: 'observed_values')
  final Map<String, Object?> observedValues;
  @JsonKey(name: 'source_refs')
  final List<SourceBoxDto> sourceRefs;
  Map<String, dynamic> toJson() => _$ConflictDtoToJson(this);
}

@JsonSerializable(explicitToJson: true)
class ReconcileResponseDto {
  const ReconcileResponseDto({
    required this.conflicts,
    required this.activityEvents,
  });
  factory ReconcileResponseDto.fromJson(Map<String, dynamic> json) =>
      _$ReconcileResponseDtoFromJson(json);
  final List<ConflictDto> conflicts;
  @JsonKey(name: 'activity_events')
  final List<ActivityEventDto> activityEvents;
  Map<String, dynamic> toJson() => _$ReconcileResponseDtoToJson(this);
}
