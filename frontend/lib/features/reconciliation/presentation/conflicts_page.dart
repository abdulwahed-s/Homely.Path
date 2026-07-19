import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../l10n/app_localizations.dart';
import '../../auth_session/application/session_cubit.dart';
import '../application/reconciliation_cubit.dart';
import '../domain/local_conflict.dart';
import '../../../core/widgets/app_ui.dart';

class ConflictsPage extends StatelessWidget {
  const ConflictsPage({super.key});
  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Padding(
      padding: const EdgeInsets.all(28),
      child: BlocBuilder<ReconciliationCubit, ReconciliationState>(
        builder: (context, state) => ListView(
          children: [
            AppSectionHeader(
              title: l10n.conflicts,
              subtitle:
                  'Resolve any differences between documents before you continue.',
              icon: Icons.warning_amber_outlined,
            ),
            if (state.isReconciling) const LinearProgressIndicator(),
            if (state.error != null) Text(state.error!),
            if (state.conflicts.isEmpty && !state.isReconciling)
              Text(l10n.readyToReview),
            for (final conflict in state.conflicts)
              _ConflictCard(conflict: conflict),
          ],
        ),
      ),
    );
  }
}

class _ConflictCard extends StatelessWidget {
  const _ConflictCard({required this.conflict});
  final LocalConflict conflict;
  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final sessionId = context.read<SessionCubit>().state!.id;
    return Card(
      margin: const EdgeInsets.only(top: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              conflict.conflict.code,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(conflict.conflict.message),
            const SizedBox(height: 8),
            Text(conflict.conflict.observedValues.toString()),
            for (final source in conflict.conflict.sourceRefs)
              Text(source.sourceDescription),
            if (conflict.isResolved)
              Text(l10n.confirm)
            else if (conflict.isBlocking)
              Align(
                alignment: AlignmentDirectional.centerEnd,
                child: ElevatedButton(
                  onPressed: () => context.read<ReconciliationCubit>().resolve(
                    sessionId: sessionId,
                    conflictId: conflict.conflict.conflictId,
                    resolution: conflict.conflict.observedValues,
                  ),
                  child: Text(l10n.confirm),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
