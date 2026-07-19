import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/widgets.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../firebase_options.dart';
import '../features/auth_session/application/session_cubit.dart';
import '../features/calculations/application/calculations_cubit.dart';
import '../features/documents/application/documents_cubit.dart';
import '../features/reconciliation/application/reconciliation_cubit.dart';
import '../features/packet/application/packet_cubit.dart';
import '../infrastructure/ai_backend/ai_repository.dart';
import '../infrastructure/ai_backend/disabled_ai_repository.dart';
import '../infrastructure/ai_backend/http_ai_repository.dart';
import '../infrastructure/ai_backend/mock_ai_repository.dart';
import '../infrastructure/firebase_auth/firebase_token_provider.dart';
import '../infrastructure/local_storage/shared_preferences_document_workspace_store.dart';
import '../infrastructure/local_storage/shared_preferences_conflict_store.dart';
import '../infrastructure/local_storage/shared_preferences_local_session_store.dart';
import 'app.dart';
import 'config/app_config.dart';

Future<AppDependencies> bootstrap() async {
  final preferences = await SharedPreferences.getInstance();
  final store = SharedPreferencesLocalSessionStore(preferences);
  final documentStore = SharedPreferencesDocumentWorkspaceStore(preferences);
  final conflictStore = SharedPreferencesConflictStore(preferences);
  String? uid;
  try {
    await Firebase.initializeApp(
      options: DefaultFirebaseOptions.currentPlatform,
    );
    if (FirebaseAuth.instance.currentUser == null) {
      await FirebaseAuth.instance.setPersistence(Persistence.SESSION);
      await FirebaseAuth.instance.signInAnonymously();
    }
    uid = FirebaseAuth.instance.currentUser?.uid;
  } on FirebaseException {
    uid = null;
  } catch (_) {
    uid = null;
  }
  final config = AppConfig.fromEnvironment();
  late DocumentsCubit documentsCubit;
  late ReconciliationCubit reconciliationCubit;
  final sessionCubit = SessionCubit(
    store,
    onSessionDeleted: (sessionId) async {
      await documentsCubit.deleteSession(sessionId);
      await reconciliationCubit.deleteSession(sessionId);
      await _deleteAnonymousFirebaseUser();
    },
    onSessionExpired: (sessionId) async {
      await documentStore.deleteSession(sessionId);
      await conflictStore.deleteSession(sessionId);
    },
  );
  await sessionCubit.restoreOrCreate(anonymousUid: uid);
  final savedLocale = await store.readLocale();
  final AiRepository aiRepository = switch (config.aiMode) {
    AiMode.mock => const MockAiRepository(),
    AiMode.http when config.hasHttpBackend => HttpAiRepository(
      baseUrl: config.aiBaseUrl,
      tokenProvider: FirebaseAuthTokenProvider(FirebaseAuth.instance),
    ),
    _ => const DisabledAiRepository(),
  };
  documentsCubit = DocumentsCubit(documentStore, aiRepository);
  await documentsCubit.restore(sessionCubit.state!.id);
  reconciliationCubit = ReconciliationCubit(
    conflictStore,
    aiRepository,
    documentsCubit,
  );
  await reconciliationCubit.start(sessionCubit.state!.id);
  final calculationsCubit = CalculationsCubit(
    documentsCubit,
    reconciliationCubit,
  );
  await calculationsCubit.start();
  return AppDependencies(
    config: config,
    sessionCubit: sessionCubit,
    documentsCubit: documentsCubit,
    reconciliationCubit: reconciliationCubit,
    calculationsCubit: calculationsCubit,
    packetCubit: PacketCubit(),
    aiRepository: aiRepository,
    initialLocale: savedLocale == null ? null : Locale(savedLocale),
    onLocaleChanged: store.writeLocale,
  );
}

Future<void> _deleteAnonymousFirebaseUser() async {
  try {
    final user = FirebaseAuth.instance.currentUser;
    if (user?.isAnonymous ?? false) {
      await user!.delete();
    } else {
      await FirebaseAuth.instance.signOut();
    }
  } on FirebaseException {
    try {
      await FirebaseAuth.instance.signOut();
    } on FirebaseException {
      return;
    }
  } catch (_) {
    return;
  }
}
