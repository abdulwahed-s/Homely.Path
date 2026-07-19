import 'dart:typed_data';

import 'extraction_dto.dart';

abstract interface class AiRepository {
  Future<ExtractionResponseDto> extract({
    required String sessionId,
    required String documentId,
    required String filename,
    required Uint8List bytes,
    void Function(int sent, int total)? onSendProgress,
  });
  Future<ReconcileResponseDto> reconcile({
    required String sessionId,
    required List<DocumentExtractionDto> documents,
  });

  Future<Map<String, dynamic>> ask({
    required String sessionId,
    required Map<String, dynamic> request,
    required Map<String, dynamic> context,
  });

  Future<Map<String, dynamic>> readiness({
    required String sessionId,
    required Map<String, dynamic> payload,
  });

  Future<Map<String, dynamic>> safetyCheck({
    required String sessionId,
    required Map<String, dynamic> payload,
  });
}
