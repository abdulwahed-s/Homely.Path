import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:uuid/uuid.dart';

import '../../../infrastructure/local_storage/local_session_store.dart';
import '../domain/session.dart';

class SessionCubit extends Cubit<LocalSession?> {
  SessionCubit(
    this._store, {
    Future<void> Function(String sessionId)? onSessionDeleted,
    Future<void> Function(String sessionId)? onSessionExpired,
  }) : _onSessionDeleted = onSessionDeleted,
       _onSessionExpired = onSessionExpired,
       super(null);
  final LocalSessionStore _store;
  final Future<void> Function(String sessionId)? _onSessionDeleted;
  final Future<void> Function(String sessionId)? _onSessionExpired;

  Future<void> restoreOrCreate({String? anonymousUid}) async {
    final expiredSessionId = await _store.deleteExpiredSessionAndReturnId();
    if (expiredSessionId != null) {
      await _onSessionExpired?.call(expiredSessionId);
    }
    final existing = await _store.readActiveSession();
    if (existing != null) return emit(existing);
    final now = DateTime.now().toUtc();
    final session = LocalSession(
      id: anonymousUid ?? const Uuid().v4(),
      createdAt: now,
      expiresAt: now.add(const Duration(hours: 24)),
    );
    await _store.writeSession(session);
    emit(session);
  }

  Future<void> grantConsent() async {
    final session = state;
    if (session == null) return;
    final updated = session.copyWith(consentAt: DateTime.now().toUtc());
    await _store.writeSession(updated);
    emit(updated);
  }

  Future<void> delete() async {
    final sessionId = state?.id;
    if (sessionId != null) {
      await _onSessionDeleted?.call(sessionId);
    }
    await _store.deleteSession();
    emit(null);
  }
}
