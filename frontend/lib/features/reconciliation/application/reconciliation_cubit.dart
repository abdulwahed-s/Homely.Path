import 'dart:async';

import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../features/documents/application/documents_cubit.dart';
import '../../../infrastructure/ai_backend/ai_repository.dart';
import '../domain/conflict_store.dart';
import '../domain/local_conflict.dart';

class ReconciliationState {
  const ReconciliationState({
    this.conflicts = const [],
    this.isReconciling = false,
    this.error,
  });
  final List<LocalConflict> conflicts;
  final bool isReconciling;
  final String? error;
  bool get hasBlockingConflict =>
      conflicts.any((conflict) => conflict.isBlocking && !conflict.isResolved);
  ReconciliationState copyWith({
    List<LocalConflict>? conflicts,
    bool? isReconciling,
    String? error,
    bool clearError = false,
  }) => ReconciliationState(
    conflicts: conflicts ?? this.conflicts,
    isReconciling: isReconciling ?? this.isReconciling,
    error: clearError ? null : error ?? this.error,
  );
}

class ReconciliationCubit extends Cubit<ReconciliationState> {
  ReconciliationCubit(this._store, this._repository, this._documents)
    : super(const ReconciliationState());
  final ConflictStore _store;
  final AiRepository _repository;
  final DocumentsCubit _documents;
  StreamSubscription<DocumentsState>? _subscription;
  String? _sessionId;
  Future<void> start(String sessionId) async {
    _sessionId = sessionId;
    emit(state.copyWith(conflicts: await _store.read(sessionId)));
    _subscription = _documents.stream.listen((_) => _maybeReconcile());
    await _maybeReconcile();
  }

  Future<void> _maybeReconcile() async {
    final sessionId = _sessionId;
    final documents = _documents.state.documents
        .where((item) => item.extraction != null)
        .map((item) => item.extraction!)
        .toList();
    if (sessionId == null || state.isReconciling) {
      return;
    }
    if (documents.length < 2) {
      await _store.write(sessionId, const []);
      emit(state.copyWith(conflicts: const [], clearError: true));
      return;
    }
    await reconcile(sessionId, documents);
  }

  Future<void> reconcile(String sessionId, List<dynamic> documents) async {
    emit(state.copyWith(isReconciling: true, clearError: true));
    try {
      final response = await _repository.reconcile(
        sessionId: sessionId,
        documents: documents.cast(),
      );
      final previous = {
        for (final item in state.conflicts) item.conflict.conflictId: item,
      };
      final conflicts = response.conflicts
          .map(
            (conflict) =>
                previous[conflict.conflictId] ??
                LocalConflict(conflict: conflict),
          )
          .toList();
      await _store.write(sessionId, conflicts);
      emit(state.copyWith(conflicts: conflicts, isReconciling: false));
    } catch (error) {
      emit(state.copyWith(isReconciling: false, error: error.toString()));
    }
  }

  Future<void> resolve({
    required String sessionId,
    required String conflictId,
    required Object resolution,
    String? reason,
  }) async {
    final updated = state.conflicts
        .map(
          (conflict) => conflict.conflict.conflictId == conflictId
              ? conflict.copyWith(
                  resolution: resolution,
                  resolutionReason: reason,
                )
              : conflict,
        )
        .toList();
    await _store.write(sessionId, updated);
    emit(state.copyWith(conflicts: updated));
  }

  Future<void> deleteSession(String sessionId) async {
    await _store.deleteSession(sessionId);
    emit(const ReconciliationState());
  }

  @override
  Future<void> close() async {
    await _subscription?.cancel();
    return super.close();
  }
}
