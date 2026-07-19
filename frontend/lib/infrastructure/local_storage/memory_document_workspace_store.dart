import '../../features/documents/domain/document_workspace_store.dart';
import '../../features/documents/domain/local_document.dart';

class MemoryDocumentWorkspaceStore implements DocumentWorkspaceStore {
  final Map<String, List<LocalDocument>> _documents = {};
  @override
  Future<void> deleteDocument(String sessionId, String documentId) async =>
      _documents[sessionId] = [
        ...?_documents[sessionId],
      ].where((item) => item.id != documentId).toList();
  @override
  Future<void> deleteSession(String sessionId) async =>
      _documents.remove(sessionId);
  @override
  Future<List<LocalDocument>> read(String sessionId) async =>
      List.unmodifiable(_documents[sessionId] ?? const []);
  @override
  Future<void> write(String sessionId, List<LocalDocument> documents) async =>
      _documents[sessionId] = List.of(documents);
}
