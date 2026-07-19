import 'package:flutter/material.dart';

import '../../../l10n/app_localizations.dart';
import '../../documents/domain/local_document.dart';

class ActivityLog extends StatelessWidget {
  const ActivityLog({super.key, required this.documents});
  final List<LocalDocument> documents;
  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final events = [
      for (final document in documents) ...document.activityEvents,
    ]..sort((a, b) => b.timestamp.compareTo(a.timestamp));
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.activity, style: Theme.of(context).textTheme.titleMedium),
            for (final event in events.take(5))
              ListTile(
                dense: true,
                title: Text(event.action),
                subtitle: Text('${event.agent} · ${event.timestamp.toLocal()}'),
                trailing: Text(event.status),
              ),
          ],
        ),
      ),
    );
  }
}
