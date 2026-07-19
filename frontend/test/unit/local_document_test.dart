import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:homely_path/features/documents/application/documents_cubit.dart';
import 'package:homely_path/infrastructure/ai_backend/mock_ai_repository.dart';
import 'package:homely_path/infrastructure/local_storage/memory_document_workspace_store.dart';

void main() {
  test('a PDF is extracted and persisted locally', () async {
    final store = MemoryDocumentWorkspaceStore();
    final cubit = DocumentsCubit(store, const MockAiRepository());
    await cubit.selectAndExtract(
      sessionId: 'session-a',
      filename: 'document.pdf',
      bytes: Uint8List.fromList('%PDF-1.7'.codeUnits),
    );
    expect(
      cubit.state.documents.single.extraction?.documentId,
      cubit.state.documents.single.id,
    );
    expect((await store.read('session-a')).single.status.name, 'extracted');
  });
  test('a non-PDF never reaches the AI client', () async {
    final cubit = DocumentsCubit(
      MemoryDocumentWorkspaceStore(),
      const MockAiRepository(),
    );
    expect(
      () => cubit.selectAndExtract(
        sessionId: 'session-a',
        filename: 'bad.txt',
        bytes: Uint8List.fromList('not a PDF'.codeUnits),
      ),
      throwsArgumentError,
    );
  });
}
