import 'local_document.dart';

abstract interface class DocumentWorkspaceStore {
  Future<List<LocalDocument>> read(String sessionId);
  Future<void> write(String sessionId, List<LocalDocument> documents);
  Future<void> deleteDocument(String sessionId, String documentId);
  Future<void> deleteSession(String sessionId);
}
