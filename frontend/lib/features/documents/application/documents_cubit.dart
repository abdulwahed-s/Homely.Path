import 'dart:typed_data';

import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:uuid/uuid.dart';

import '../../../infrastructure/ai_backend/ai_repository.dart';
import '../../../infrastructure/ai_backend/extraction_dto.dart';
import '../domain/document_workspace_store.dart';
import '../domain/local_document.dart';

class DocumentsState {
  const DocumentsState({this.documents = const [], this.progress = const {}});
  final List<LocalDocument> documents;
  final Map<String, double> progress;
  DocumentsState copyWith({
    List<LocalDocument>? documents,
    Map<String, double>? progress,
  }) => DocumentsState(
    documents: documents ?? this.documents,
    progress: progress ?? this.progress,
  );
}

class DocumentsCubit extends Cubit<DocumentsState> {
  DocumentsCubit(this._store, this._aiRepository)
    : super(const DocumentsState());
  final DocumentWorkspaceStore _store;
  final AiRepository _aiRepository;
  final _bytes = <String, Uint8List>{};
  Future<void> restore(String sessionId) async =>
      emit(state.copyWith(documents: await _store.read(sessionId)));
  Future<void> selectAndExtract({
    required String sessionId,
    required String filename,
    required Uint8List bytes,
  }) async {
    if (!_isPdf(bytes)) {
      throw ArgumentError('Only PDF documents can be uploaded.');
    }
    if (state.documents.any(
      (document) =>
          document.filename == filename &&
          document.byteLength == bytes.lengthInBytes,
    )) {
      throw ArgumentError('This document was already selected.');
    }
    final id = const Uuid().v4();
    _bytes[id] = bytes;
    final document = LocalDocument(
      id: id,
      filename: filename,
      byteLength: bytes.lengthInBytes,
      status: LocalDocumentStatus.extracting,
      createdAt: DateTime.now().toUtc(),
    );
    await _replace(sessionId, document);
    try {
      final response = await _aiRepository.extract(
        sessionId: sessionId,
        documentId: id,
        filename: filename,
        bytes: bytes,
        onSendProgress: (sent, total) =>
            _setProgress(id, total == 0 ? 0 : sent / total),
      );
      if (response.sessionId != sessionId ||
          response.document.documentId != id) {
        throw StateError(
          'The AI response did not belong to this local session or document.',
        );
      }
      await _replace(
        sessionId,
        document.copyWith(
          status: LocalDocumentStatus.extracted,
          extraction: response.document,
          activityEvents: response.activityEvents,
          clearError: true,
        ),
      );
    } catch (error) {
      await _replace(
        sessionId,
        document.copyWith(
          status: LocalDocumentStatus.failed,
          error: error.toString(),
        ),
      );
    }
  }

  Future<void> retry({
    required String sessionId,
    required String documentId,
  }) async {
    final document = state.documents
        .where((item) => item.id == documentId)
        .firstOrNull;
    final bytes = _bytes[documentId];
    if (document == null || bytes == null) {
      return;
    }
    await delete(sessionId, documentId);
    await selectAndExtract(
      sessionId: sessionId,
      filename: document.filename,
      bytes: bytes,
    );
  }

  Future<void> delete(String sessionId, String documentId) async {
    _bytes.remove(documentId);
    await _store.deleteDocument(sessionId, documentId);
    emit(
      state.copyWith(
        documents: state.documents
            .where((item) => item.id != documentId)
            .toList(),
      ),
    );
  }

  Future<void> deleteSession(String sessionId) async {
    _bytes.clear();
    await _store.deleteSession(sessionId);
    emit(const DocumentsState());
  }

  Uint8List? bytesFor(String documentId) => _bytes[documentId];
  Future<void> confirmField({
    required String sessionId,
    required String documentId,
    required String fieldName,
    required Object? value,
    required bool userEdited,
  }) async {
    final document = state.documents
        .where((item) => item.id == documentId)
        .firstOrNull;
    final extraction = document?.extraction;
    if (document == null || extraction == null) {
      return;
    }
    final fields = extraction.fields
        .map(
          (field) => field.fieldName == fieldName
              ? ExtractedFieldDto(
                  fieldName: field.fieldName,
                  value: value?.toString(),
                  normalizedValue: value,
                  confidence: field.confidence,
                  confidenceLevel: field.confidenceLevel,
                  confirmationStatus: userEdited ? 'user_edited' : 'confirmed',
                  requiresManualEntry: field.requiresManualEntry,
                  source: field.source,
                )
              : field,
        )
        .toList();
    final updated = DocumentExtractionDto(
      documentId: extraction.documentId,
      documentType: extraction.documentType,
      securityFlags: extraction.securityFlags,
      fields: fields,
    );
    await _replace(sessionId, document.copyWith(extraction: updated));
  }

  Future<void> _replace(String sessionId, LocalDocument replacement) async {
    final items = [
      ...state.documents.where((item) => item.id != replacement.id),
      replacement,
    ];
    await _store.write(sessionId, items);
    emit(state.copyWith(documents: items));
  }

  void _setProgress(String id, double value) => emit(
    state.copyWith(progress: {...state.progress, id: value.clamp(0, 1)}),
  );
  bool _isPdf(Uint8List bytes) =>
      bytes.lengthInBytes >= 5 &&
      String.fromCharCodes(bytes.take(5)) == '%PDF-';
}
