import 'local_conflict.dart';

abstract interface class ConflictStore {
  Future<List<LocalConflict>> read(String sessionId);
  Future<void> write(String sessionId, List<LocalConflict> conflicts);
  Future<void> deleteSession(String sessionId);
}
