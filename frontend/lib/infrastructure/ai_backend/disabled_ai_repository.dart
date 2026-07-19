import 'dart:typed_data';
import 'ai_repository.dart';
import 'extraction_dto.dart';

class DisabledAiRepository implements AiRepository {
  const DisabledAiRepository();
  Never _unavailable() => throw StateError('AI backend is not configured.');
  @override
  Future<ExtractionResponseDto> extract({
    required String sessionId,
    required String documentId,
    required String filename,
    required Uint8List bytes,
    void Function(int sent, int total)? onSendProgress,
  }) async => _unavailable();
  @override
  Future<ReconcileResponseDto> reconcile({
    required String sessionId,
    required List<DocumentExtractionDto> documents,
  }) async => _unavailable();
  @override
  Future<Map<String, dynamic>> ask({
    required String sessionId,
    required Map<String, dynamic> request,
    required Map<String, dynamic> context,
  }) async => _unavailable();
  @override
  Future<Map<String, dynamic>> readiness({
    required String sessionId,
    required Map<String, dynamic> payload,
  }) async => _unavailable();
  @override
  Future<Map<String, dynamic>> safetyCheck({
    required String sessionId,
    required Map<String, dynamic> payload,
  }) async => _unavailable();
}
