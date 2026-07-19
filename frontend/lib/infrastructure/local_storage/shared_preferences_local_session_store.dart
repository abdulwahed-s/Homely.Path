import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../../features/auth_session/domain/session.dart';
import 'local_session_store.dart';

class SharedPreferencesLocalSessionStore implements LocalSessionStore {
  SharedPreferencesLocalSessionStore(this._preferences);

  static const _sessionKey = 'homelypath.active_session.v1';
  static const _localeKey = 'homelypath.locale.v1';
  final SharedPreferences _preferences;

  @override
  Future<void> cleanupExpired() async {
    await deleteExpiredSessionAndReturnId();
  }

  @override
  Future<String?> deleteExpiredSessionAndReturnId() async {
    final encoded = _preferences.getString(_sessionKey);
    if (encoded == null) return null;
    try {
      final session = LocalSession.fromJson(
        Map<String, Object?>.from(jsonDecode(encoded) as Map),
      );
      if (session != null && session.isExpired) {
        await deleteSession();
        return session.id;
      }
    } catch (_) {
      await deleteSession();
    }
    return null;
  }

  @override
  Future<void> deleteSession() async => _preferences.remove(_sessionKey);

  @override
  Future<LocalSession?> readActiveSession() async {
    final encoded = _preferences.getString(_sessionKey);
    if (encoded == null) return null;
    final value = LocalSession.fromJson(
      Map<String, Object?>.from(jsonDecode(encoded) as Map),
    );
    if (value == null || value.isExpired) {
      await deleteSession();
      return null;
    }
    return value;
  }

  @override
  Future<String?> readLocale() async => _preferences.getString(_localeKey);

  @override
  Future<void> writeLocale(String localeCode) async =>
      _preferences.setString(_localeKey, localeCode);

  @override
  Future<void> writeSession(LocalSession session) async =>
      _preferences.setString(_sessionKey, jsonEncode(session.toJson()));
}
