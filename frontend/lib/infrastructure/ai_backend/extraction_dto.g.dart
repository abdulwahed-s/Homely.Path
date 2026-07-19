// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'extraction_dto.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

SourceBoxDto _$SourceBoxDtoFromJson(Map<String, dynamic> json) => SourceBoxDto(
  page: (json['page'] as num).toInt(),
  x1: (json['x1'] as num).toDouble(),
  y1: (json['y1'] as num).toDouble(),
  x2: (json['x2'] as num).toDouble(),
  y2: (json['y2'] as num).toDouble(),
  sourceDescription: json['source_description'] as String,
);

Map<String, dynamic> _$SourceBoxDtoToJson(SourceBoxDto instance) =>
    <String, dynamic>{
      'page': instance.page,
      'x1': instance.x1,
      'y1': instance.y1,
      'x2': instance.x2,
      'y2': instance.y2,
      'source_description': instance.sourceDescription,
    };

ExtractedFieldDto _$ExtractedFieldDtoFromJson(Map<String, dynamic> json) =>
    ExtractedFieldDto(
      fieldName: json['field_name'] as String,
      value: json['value'] as String?,
      normalizedValue: json['normalized_value'],
      confidence: (json['confidence'] as num).toDouble(),
      confidenceLevel: json['confidence_level'] as String,
      confirmationStatus: json['confirmation_status'] as String,
      requiresManualEntry: json['requires_manual_entry'] as bool,
      source: SourceBoxDto.fromJson(json['source'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$ExtractedFieldDtoToJson(ExtractedFieldDto instance) =>
    <String, dynamic>{
      'field_name': instance.fieldName,
      'value': instance.value,
      'normalized_value': instance.normalizedValue,
      'confidence': instance.confidence,
      'confidence_level': instance.confidenceLevel,
      'confirmation_status': instance.confirmationStatus,
      'requires_manual_entry': instance.requiresManualEntry,
      'source': instance.source.toJson(),
    };

DocumentExtractionDto _$DocumentExtractionDtoFromJson(
  Map<String, dynamic> json,
) => DocumentExtractionDto(
  documentId: json['document_id'] as String,
  documentType: json['document_type'] as String,
  securityFlags: (json['security_flags'] as List<dynamic>)
      .map((e) => e as String)
      .toList(),
  fields: (json['fields'] as List<dynamic>)
      .map((e) => ExtractedFieldDto.fromJson(e as Map<String, dynamic>))
      .toList(),
);

Map<String, dynamic> _$DocumentExtractionDtoToJson(
  DocumentExtractionDto instance,
) => <String, dynamic>{
  'document_id': instance.documentId,
  'document_type': instance.documentType,
  'security_flags': instance.securityFlags,
  'fields': instance.fields.map((e) => e.toJson()).toList(),
};

ActivityEventDto _$ActivityEventDtoFromJson(Map<String, dynamic> json) =>
    ActivityEventDto(
      timestamp: DateTime.parse(json['timestamp'] as String),
      agent: json['agent'] as String,
      action: json['action'] as String,
      status: json['status'] as String,
      metadata: json['metadata'] as Map<String, dynamic>,
    );

Map<String, dynamic> _$ActivityEventDtoToJson(ActivityEventDto instance) =>
    <String, dynamic>{
      'timestamp': instance.timestamp.toIso8601String(),
      'agent': instance.agent,
      'action': instance.action,
      'status': instance.status,
      'metadata': instance.metadata,
    };

ExtractionResponseDto _$ExtractionResponseDtoFromJson(
  Map<String, dynamic> json,
) => ExtractionResponseDto(
  sessionId: json['session_id'] as String,
  document: DocumentExtractionDto.fromJson(
    json['document'] as Map<String, dynamic>,
  ),
  activityEvents: (json['activity_events'] as List<dynamic>)
      .map((e) => ActivityEventDto.fromJson(e as Map<String, dynamic>))
      .toList(),
);

Map<String, dynamic> _$ExtractionResponseDtoToJson(
  ExtractionResponseDto instance,
) => <String, dynamic>{
  'session_id': instance.sessionId,
  'document': instance.document.toJson(),
  'activity_events': instance.activityEvents.map((e) => e.toJson()).toList(),
};

ConflictDto _$ConflictDtoFromJson(Map<String, dynamic> json) => ConflictDto(
  conflictId: json['conflict_id'] as String,
  code: json['code'] as String,
  severity: json['severity'] as String,
  message: json['message'] as String,
  documentIds: (json['document_ids'] as List<dynamic>)
      .map((e) => e as String)
      .toList(),
  fieldNames: (json['field_names'] as List<dynamic>)
      .map((e) => e as String)
      .toList(),
  observedValues: json['observed_values'] as Map<String, dynamic>,
  sourceRefs: (json['source_refs'] as List<dynamic>)
      .map((e) => SourceBoxDto.fromJson(e as Map<String, dynamic>))
      .toList(),
);

Map<String, dynamic> _$ConflictDtoToJson(ConflictDto instance) =>
    <String, dynamic>{
      'conflict_id': instance.conflictId,
      'code': instance.code,
      'severity': instance.severity,
      'message': instance.message,
      'document_ids': instance.documentIds,
      'field_names': instance.fieldNames,
      'observed_values': instance.observedValues,
      'source_refs': instance.sourceRefs.map((e) => e.toJson()).toList(),
    };

ReconcileResponseDto _$ReconcileResponseDtoFromJson(
  Map<String, dynamic> json,
) => ReconcileResponseDto(
  conflicts: (json['conflicts'] as List<dynamic>)
      .map((e) => ConflictDto.fromJson(e as Map<String, dynamic>))
      .toList(),
  activityEvents: (json['activity_events'] as List<dynamic>)
      .map((e) => ActivityEventDto.fromJson(e as Map<String, dynamic>))
      .toList(),
);

Map<String, dynamic> _$ReconcileResponseDtoToJson(
  ReconcileResponseDto instance,
) => <String, dynamic>{
  'conflicts': instance.conflicts.map((e) => e.toJson()).toList(),
  'activity_events': instance.activityEvents.map((e) => e.toJson()).toList(),
};
