import 'dart:typed_data';

import 'package:dio/dio.dart';

import '../firebase_auth/firebase_token_provider.dart';
import 'ai_repository.dart';
import 'extraction_dto.dart';

class HttpAiRepository implements AiRepository {
  HttpAiRepository({
    required String baseUrl,
    required FirebaseTokenProvider tokenProvider,
  }) : _tokenProvider = tokenProvider,
       _dio = Dio(BaseOptions(baseUrl: baseUrl)) {
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          options.headers['Authorization'] =
              'Bearer ${await _tokenProvider.freshIdToken()}';
          handler.next(options);
        },
      ),
    );
  }
  final Dio _dio;
  final FirebaseTokenProvider _tokenProvider;
  @override
  Future<ExtractionResponseDto> extract({
    required String sessionId,
    required String documentId,
    required String filename,
    required Uint8List bytes,
    void Function(int sent, int total)? onSendProgress,
  }) async {
    final authenticatedUid = await _tokenProvider.activeUid();
    if (authenticatedUid != sessionId) {
      throw StateError(
        'The active anonymous UID does not match this local session.',
      );
    }
    final response = await _withBackendErrors(
      () => _dio.post<Map<String, dynamic>>(
        '/internal/ai/extract',
        data: FormData.fromMap({
          'session_id': sessionId,
          'document_id': documentId,
          'file': MultipartFile.fromBytes(
            bytes,
            filename: filename,
            contentType: DioMediaType('application', 'pdf'),
          ),
        }),
        onSendProgress: onSendProgress,
      ),
    );
    return ExtractionResponseDto.fromJson(response.data!);
  }

  @override
  Future<ReconcileResponseDto> reconcile({
    required String sessionId,
    required List<DocumentExtractionDto> documents,
  }) async {
    final authenticatedUid = await _tokenProvider.activeUid();
    if (authenticatedUid != sessionId) {
      throw StateError(
        'The active anonymous UID does not match this local session.',
      );
    }
    final response = await _withBackendErrors(
      () => _dio.post<Map<String, dynamic>>(
        '/internal/ai/reconcile',
        data: {
          'session_id': sessionId,
          'documents': documents.map((document) => document.toJson()).toList(),
        },
      ),
    );
    return ReconcileResponseDto.fromJson(response.data!);
  }

  @override
  Future<Map<String, dynamic>> ask({
    required String sessionId,
    required Map<String, dynamic> request,
    required Map<String, dynamic> context,
  }) => _postSessionJson('/internal/ai/ask', sessionId, {
    'request': {...request, 'session_id': sessionId},
    'context': {...context, 'session_id': sessionId},
  });

  @override
  Future<Map<String, dynamic>> readiness({
    required String sessionId,
    required Map<String, dynamic> payload,
  }) => _postSessionJson('/internal/ai/readiness', sessionId, {
    ...payload,
    'session_id': sessionId,
  });

  @override
  Future<Map<String, dynamic>> safetyCheck({
    required String sessionId,
    required Map<String, dynamic> payload,
  }) => _postSessionJson('/internal/ai/safety-check', sessionId, {
    ...payload,
    'session_id': sessionId,
  });

  Future<Map<String, dynamic>> _postSessionJson(
    String path,
    String sessionId,
    Map<String, dynamic> payload,
  ) async {
    final authenticatedUid = await _tokenProvider.activeUid();
    if (authenticatedUid != sessionId) {
      throw StateError(
        'The active anonymous UID does not match this local session.',
      );
    }
    final response = await _withBackendErrors(
      () => _dio.post<Map<String, dynamic>>(path, data: payload),
    );
    return response.data!;
  }

  Future<T> _withBackendErrors<T>(Future<T> Function() request) async {
    try {
      return await request();
    } on DioException catch (error) {
      final body = error.response?.data;
      if (body is Map) {
        final code = body['error_code'];
        final detail = body['detail'];
        if (code != null || detail != null) {
          throw StateError(
            '${code ?? 'BACKEND_ERROR'}: ${detail ?? 'Request failed.'}',
          );
        }
      }
      throw StateError(
        'Backend request failed (${error.response?.statusCode ?? 'network error'}).',
      );
    }
  }
}
