import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../../l10n/app_localizations.dart';
import '../../auth_session/application/session_cubit.dart';
import '../application/documents_cubit.dart';
import '../domain/local_document.dart';
import '../../../core/widgets/app_ui.dart';

class DocumentsPage extends StatelessWidget {
  const DocumentsPage({super.key});
  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final session = context.watch<SessionCubit>().state!;
    return Padding(
      padding: const EdgeInsets.all(28),
      child: BlocBuilder<DocumentsCubit, DocumentsState>(
        builder: (context, state) => ListView(
          children: [
            AppSectionHeader(
              title: l10n.uploadDocuments,
              subtitle: l10n.uploadHint,
              icon: Icons.upload_file_outlined,
            ),
            const SizedBox(height: 20),
            const Card(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Accepted PDF document types',
                      style: TextStyle(fontWeight: FontWeight.w600),
                    ),
                    SizedBox(height: 8),
                    Text(
                      'Pay stub · Employment letter · Benefit letter · Gig statement · Application summary',
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            Semantics(
              label: l10n.choosePdf,
              button: true,
              child: OutlinedButton.icon(
                onPressed: () => _choose(context, session.id),
                icon: const Icon(Icons.upload_file_outlined),
                label: Text(l10n.choosePdf),
              ),
            ),
            const SizedBox(height: 24),
            Text(
              'Document inventory (${state.documents.length})',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            for (final document in state.documents)
              _DocumentTile(
                document: document,
                progress: state.progress[document.id],
                onRetry: () => context.read<DocumentsCubit>().retry(
                  sessionId: session.id,
                  documentId: document.id,
                ),
                onDelete: () => context.read<DocumentsCubit>().delete(
                  session.id,
                  document.id,
                ),
                onReview: document.extraction == null
                    ? null
                    : () => context.go(
                        '/session/${session.id}/documents/${document.id}/review',
                      ),
              ),
          ],
        ),
      ),
    );
  }

  Future<void> _choose(BuildContext context, String sessionId) async {
    final l10n = AppLocalizations.of(context)!;
    final documentsCubit = context.read<DocumentsCubit>();
    final messenger = ScaffoldMessenger.of(context);
    final picked = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['pdf'],
      withData: true,
    );
    final file = picked?.files.singleOrNull;
    if (file?.bytes == null) {
      return;
    }
    try {
      await documentsCubit.selectAndExtract(
        sessionId: sessionId,
        filename: file!.name,
        bytes: file.bytes!,
      );
    } catch (_) {
      if (!context.mounted) {
        return;
      }
      messenger.showSnackBar(SnackBar(content: Text(l10n.retry)));
    }
  }
}

class _DocumentTile extends StatelessWidget {
  const _DocumentTile({
    required this.document,
    required this.progress,
    required this.onRetry,
    required this.onDelete,
    required this.onReview,
  });
  final LocalDocument document;
  final double? progress;
  final VoidCallback onRetry;
  final VoidCallback onDelete;
  final VoidCallback? onReview;
  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        onTap: onReview,
        leading: const Icon(Icons.picture_as_pdf_outlined),
        title: Text(document.filename),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${document.byteLength} bytes'),
            Text('Added ${document.createdAt.toLocal()}'),
            if (document.status == LocalDocumentStatus.extracting)
              LinearProgressIndicator(value: progress),
            if (document.hasInjectionWarning) Text(l10n.securityWarning),
            if (document.error != null) Text(document.error!),
          ],
        ),
        trailing: Wrap(
          spacing: 4,
          children: [
            if (document.status == LocalDocumentStatus.failed)
              IconButton(
                onPressed: onRetry,
                tooltip: l10n.retry,
                icon: const Icon(Icons.refresh),
              ),
            IconButton(
              onPressed: onDelete,
              tooltip: l10n.deleteSession,
              icon: const Icon(Icons.delete_outline),
            ),
          ],
        ),
      ),
    );
  }
}
