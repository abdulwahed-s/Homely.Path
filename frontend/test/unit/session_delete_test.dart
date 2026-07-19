import 'package:flutter_test/flutter_test.dart';
import 'package:homely_path/features/auth_session/application/session_cubit.dart';
import 'package:homely_path/features/auth_session/domain/session.dart';
import 'package:homely_path/infrastructure/local_storage/memory_local_session_store.dart';

void main() {
  test(
    'hard deletion clears the active session and invokes local cleanup',
    () async {
      final store = MemoryLocalSessionStore();
      var cleanedSessionId = '';
      final cubit = SessionCubit(
        store,
        onSessionDeleted: (id) async => cleanedSessionId = id,
      );
      await cubit.restoreOrCreate(anonymousUid: 'anonymous-id');
      await cubit.delete();
      expect(cleanedSessionId, 'anonymous-id');
      expect(cubit.state, isNull);
      expect(await store.readActiveSession(), isNull);
    },
  );

  test(
    'expired sessions trigger local workspace cleanup before replacement',
    () async {
      final store = MemoryLocalSessionStore();
      await store.writeSession(
        LocalSession(
          id: 'expired-id',
          createdAt: DateTime.utc(2020),
          expiresAt: DateTime.utc(2020, 1, 2),
        ),
      );
      var cleanedSessionId = '';
      final cubit = SessionCubit(
        store,
        onSessionExpired: (id) async => cleanedSessionId = id,
      );
      await cubit.restoreOrCreate(anonymousUid: 'fresh-id');
      expect(cleanedSessionId, 'expired-id');
      expect(cubit.state!.id, 'fresh-id');
    },
  );
}
