import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../activity_log/presentation/activity_log.dart';
import '../../auth_session/application/session_cubit.dart';
import '../../documents/application/documents_cubit.dart';
import '../../../l10n/app_localizations.dart';
import '../../../core/widgets/app_ui.dart';

class OverviewPage extends StatelessWidget {
  const OverviewPage({super.key});
  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final session = context.watch<SessionCubit>().state!;
    final documents = context.watch<DocumentsCubit>().state.documents;
    final extracted = documents.where((item) => item.extraction != null).length;
    final needsAttention = documents
        .where((item) => item.error != null || item.hasInjectionWarning)
        .length;
    return Padding(
      padding: const EdgeInsets.all(28),
      child: ListView(
        children: [
          AppSectionHeader(
            title: l10n.overview,
            subtitle:
                'Keep your documents, confirmations, and next steps in one clear place.',
            icon: Icons.grid_view_rounded,
          ),
          Wrap(
            spacing: 16,
            runSpacing: 16,
            children: [l10n.profile, l10n.understand, l10n.prepare]
                .map(
                  (stage) => SizedBox(
                    width: 220,
                    child: Card(
                      child: Padding(
                        padding: const EdgeInsets.all(20),
                        child: Text(stage),
                      ),
                    ),
                  ),
                )
                .toList(),
          ),
          const SizedBox(height: 28),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Wrap(
                spacing: 32,
                runSpacing: 12,
                children: [
                  _Count(label: 'Documents', value: '${documents.length}'),
                  _Count(label: 'Extracted', value: '$extracted'),
                  _Count(label: 'Needs attention', value: '$needsAttention'),
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),
          AppNotice(
            icon: Icons.arrow_forward_outlined,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  l10n.actionRequired,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 4),
                Text(l10n.uploadHint),
              ],
            ),
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: () => context.go('/session/${session.id}/documents'),
            child: Text(l10n.uploadDocuments),
          ),
          const SizedBox(height: 24),
          ActivityLog(documents: documents),
        ],
      ),
    );
  }
}

class _Count extends StatelessWidget {
  const _Count({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(value, style: Theme.of(context).textTheme.headlineSmall),
      Text(label, style: Theme.of(context).textTheme.labelLarge),
    ],
  );
}
