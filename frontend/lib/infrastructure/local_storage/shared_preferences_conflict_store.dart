import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../../features/reconciliation/domain/conflict_store.dart';
import '../../features/reconciliation/domain/local_conflict.dart';

class SharedPreferencesConflictStore implements ConflictStore {
  SharedPreferencesConflictStore(this._preferences);
  final SharedPreferences _preferences;
  String _key(String sessionId) => 'homelypath.conflicts.$sessionId.v1';
  @override
  Future<void> deleteSession(String sessionId) async =>
      _preferences.remove(_key(sessionId));
  @override
  Future<List<LocalConflict>> read(String sessionId) async {
    final encoded = _preferences.getString(_key(sessionId));
    if (encoded == null) return [];
    try {
      return (jsonDecode(encoded) as List)
          .map(
            (item) =>
                LocalConflict.fromJson(Map<String, dynamic>.from(item as Map)),
          )
          .toList();
    } catch (_) {
      await deleteSession(sessionId);
      return [];
    }
  }

  @override
  Future<void> write(String sessionId, List<LocalConflict> conflicts) async =>
      _preferences.setString(
        _key(sessionId),
        jsonEncode(conflicts.map((item) => item.toJson()).toList()),
      );
}
