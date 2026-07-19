import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:pdfrx/pdfrx.dart';

import '../../../core/widgets/pdf_source_overlay.dart';
import '../../../l10n/app_localizations.dart';
import '../../auth_session/application/session_cubit.dart';
import '../application/documents_cubit.dart';
import '../domain/field_registry.dart';
import '../../../core/widgets/app_ui.dart';

class DocumentReviewPage extends StatelessWidget {
  const DocumentReviewPage({super.key, required this.documentId});
  final String documentId;
  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final state = context.watch<DocumentsCubit>().state;
    final document = state.documents
        .where((item) => item.id == documentId)
        .firstOrNull;
    final extraction = document?.extraction;
    if (document == null || extraction == null) {
      return Padding(
        padding: const EdgeInsets.all(28),
        child: Text(l10n.unknown),
      );
    }
    final supported = extraction.fields.where(
      (field) => isAllowlistedField(extraction.documentType, field.fieldName),
    );
    final additional = extraction.fields.where(
      (field) => !isAllowlistedField(extraction.documentType, field.fieldName),
    );
    return Padding(
      padding: const EdgeInsets.all(28),
      child: ListView(
        children: [
          AppSectionHeader(
            title: document.filename,
            subtitle: 'Review each extracted value before it is used.',
            icon: Icons.fact_check_outlined,
          ),
          if (context.read<DocumentsCubit>().bytesFor(documentId)
              case final bytes?)
            SizedBox(
              height: 480,
              child: PdfViewer.data(
                bytes,
                sourceName: document.filename,
                params: PdfViewerParams(
                  pageOverlaysBuilder: (context, pageRect, page) => [
                    for (final field in extraction.fields.where(
                      (field) => field.source.page == page.pageNumber,
                    ))
                      PdfSourceOverlay(
                        source: field.source,
                        pageWidth: page.width,
                        pageHeight: page.height,
                      ),
                  ],
                ),
              ),
            ),
          if (document.hasInjectionWarning)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Text(l10n.securityWarning),
                ),
              ),
            ),
          const SizedBox(height: 12),
          for (final field in supported)
            _FieldCard(documentId: documentId, field: field),
          if (additional.isNotEmpty) ...[
            const SizedBox(height: 24),
            Text(
              l10n.notUsedDownstream,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            for (final field in additional)
              _FieldCard(
                documentId: documentId,
                field: field,
                supported: false,
              ),
          ],
        ],
      ),
    );
  }
}

class _FieldCard extends StatefulWidget {
  const _FieldCard({
    required this.documentId,
    required this.field,
    this.supported = true,
  });
  final String documentId;
  final dynamic field;
  final bool supported;
  @override
  State<_FieldCard> createState() => _FieldCardState();
}

class _FieldCardState extends State<_FieldCard> {
  late final TextEditingController _controller = TextEditingController(
    text: _requiresTypedEntry(widget.field)
        ? ''
        : widget.field.value?.toString() ?? '',
  );

  bool _requiresTypedEntry(dynamic field) =>
      field.requiresManualEntry || field.confidenceLevel == 'low';
  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final field = widget.field;
    final confirmed =
        field.confirmationStatus == 'confirmed' ||
        field.confirmationStatus == 'user_edited';
    final requiresTypedEntry = _requiresTypedEntry(field);
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              field.fieldName,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Semantics(
              label:
                  '${field.fieldName}. Evidence location: ${field.source.sourceDescription}',
              textField: true,
              child: TextField(
                controller: _controller,
                enabled: widget.supported && !confirmed,
                decoration: InputDecoration(
                  helperText: requiresTypedEntry
                      ? 'Low-confidence extraction. Type the value shown in the document; it was not prefilled. ${field.source.sourceDescription}'
                      : field.source.sourceDescription,
                  labelText:
                      '${(field.confidence * 100).round()}% · ${field.confidenceLevel}',
                ),
              ),
            ),
            if (widget.supported && !confirmed)
              Align(
                alignment: AlignmentDirectional.centerEnd,
                child: ElevatedButton(
                  onPressed: () {
                    final value = _controller.text.trim();
                    if (value.isEmpty) return;
                    context.read<DocumentsCubit>().confirmField(
                      sessionId: context.read<SessionCubit>().state!.id,
                      documentId: widget.documentId,
                      fieldName: field.fieldName,
                      value: value,
                      userEdited: value != (field.value?.toString() ?? ''),
                    );
                  },
                  child: Text(
                    requiresTypedEntry ? l10n.manualEntry : l10n.confirm,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
