import 'dart:typed_data';

import 'ai_repository.dart';
import 'extraction_dto.dart';

class MockAiRepository implements AiRepository {
  const MockAiRepository();
  @override
  Future<ExtractionResponseDto> extract({
    required String sessionId,
    required String documentId,
    required String filename,
    required Uint8List bytes,
    void Function(int sent, int total)? onSendProgress,
  }) async {
    onSendProgress?.call(bytes.lengthInBytes, bytes.lengthInBytes);
    return ExtractionResponseDto(
      sessionId: sessionId,
      document: DocumentExtractionDto(
        documentId: documentId,
        documentType: 'unknown',
        securityFlags: const ['unsupported_document'],
        fields: const [],
      ),
      activityEvents: const [],
    );
  }

  @override
  Future<ReconcileResponseDto> reconcile({
    required String sessionId,
    required List<DocumentExtractionDto> documents,
  }) async => const ReconcileResponseDto(conflicts: [], activityEvents: []);
  @override
  Future<Map<String, dynamic>> ask({
    required String sessionId,
    required Map<String, dynamic> request,
    required Map<String, dynamic> context,
  }) async => {
    'answer': {
      'status': 'ABSTAINED',
      'answer': 'Mock mode has no rules corpus.',
      'citations': const [],
    },
    'safety': {'safe_to_display': true},
  };
  @override
  Future<Map<String, dynamic>> readiness({
    required String sessionId,
    required Map<String, dynamic> payload,
  }) async => {
    'readiness_status': 'NEEDS_REVIEW',
    'safety_validation': {'safe_to_display': true},
  };
  @override
  Future<Map<String, dynamic>> safetyCheck({
    required String sessionId,
    required Map<String, dynamic> payload,
  }) async => {'status': 'PASS', 'safe_to_display': true};
}
