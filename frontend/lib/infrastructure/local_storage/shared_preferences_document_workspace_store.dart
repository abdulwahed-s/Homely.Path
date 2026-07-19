import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../../features/documents/domain/document_workspace_store.dart';
import '../../features/documents/domain/local_document.dart';

class SharedPreferencesDocumentWorkspaceStore
    implements DocumentWorkspaceStore {
  SharedPreferencesDocumentWorkspaceStore(this._preferences);
  final SharedPreferences _preferences;
  String _key(String sessionId) => 'homelypath.documents.$sessionId.v1';
  @override
  Future<void> deleteDocument(String sessionId, String documentId) async {
    final documents = await read(sessionId);
    await write(
      sessionId,
      documents.where((item) => item.id != documentId).toList(),
    );
  }

  @override
  Future<void> deleteSession(String sessionId) async =>
      _preferences.remove(_key(sessionId));
  @override
  Future<List<LocalDocument>> read(String sessionId) async {
    final value = _preferences.getString(_key(sessionId));
    if (value == null) return [];
    try {
      return (jsonDecode(value) as List)
          .map(
            (item) =>
                LocalDocument.fromJson(Map<String, dynamic>.from(item as Map)),
          )
          .toList();
    } catch (_) {
      await deleteSession(sessionId);
      return [];
    }
  }

  @override
  Future<void> write(String sessionId, List<LocalDocument> documents) async =>
      _preferences.setString(
        _key(sessionId),
        jsonEncode(documents.map((item) => item.toJson()).toList()),
      );
}
