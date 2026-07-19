import '../../features/auth_session/domain/session.dart';
import 'local_session_store.dart';

class MemoryLocalSessionStore implements LocalSessionStore {
  LocalSession? _session;
  String? _locale;
  @override
  Future<void> cleanupExpired() async {
    await deleteExpiredSessionAndReturnId();
  }

  @override
  Future<String?> deleteExpiredSessionAndReturnId() async {
    if (_session?.isExpired ?? false) {
      final id = _session!.id;
      _session = null;
      return id;
    }
    return null;
  }

  @override
  Future<void> deleteSession() async => _session = null;
  @override
  Future<LocalSession?> readActiveSession() async {
    await cleanupExpired();
    return _session;
  }

  @override
  Future<String?> readLocale() async => _locale;
  @override
  Future<void> writeLocale(String localeCode) async => _locale = localeCode;
  @override
  Future<void> writeSession(LocalSession session) async => _session = session;
}
