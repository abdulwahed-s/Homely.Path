import '../../features/auth_session/domain/session.dart';

abstract interface class LocalSessionStore {
  Future<LocalSession?> readActiveSession();
  Future<void> writeSession(LocalSession session);
  Future<void> deleteSession();
  Future<void> cleanupExpired();
  Future<String?> deleteExpiredSessionAndReturnId();
  Future<String?> readLocale();
  Future<void> writeLocale(String localeCode);
}
