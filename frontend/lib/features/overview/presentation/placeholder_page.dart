import 'package:flutter/material.dart';

import '../../../l10n/app_localizations.dart';
import '../../../core/widgets/app_ui.dart';

enum SessionPage {
  documents,
  profile,
  conflicts,
  rules,
  calculations,
  readiness,
  packet,
}

class PlaceholderPage extends StatelessWidget {
  const PlaceholderPage({super.key, required this.kind});
  final SessionPage kind;
  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final title = switch (kind) {
      SessionPage.documents => l10n.documents,
      SessionPage.profile => l10n.confirmedProfile,
      SessionPage.conflicts => l10n.conflicts,
      SessionPage.rules => l10n.rules,
      SessionPage.calculations => l10n.calculations,
      SessionPage.readiness => l10n.readiness,
      SessionPage.packet => l10n.packet,
    };
    return Padding(
      padding: const EdgeInsets.all(28),
      child: ListView(
        children: [
          AppSectionHeader(title: title, icon: Icons.inbox_outlined),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Text(
                kind == SessionPage.documents
                    ? l10n.uploadHint
                    : l10n.actionRequired,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
