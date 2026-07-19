import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../auth_session/application/session_cubit.dart';
import '../../../l10n/app_localizations.dart';
import '../../../core/widgets/app_ui.dart';
import '../../../app/theme/app_theme.dart';

class LandingPage extends StatelessWidget {
  const LandingPage({super.key});
  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(42, 36, 42, 0),
              child: Align(alignment: Alignment.centerLeft, child: AppBrand()),
            ),
            Expanded(
              child: AppContent(
                maxWidth: 1000,
                child: ListView(
                  children: [
                    const SizedBox(height: 58),
                    Text(
                      l10n.landingTitle,
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.displaySmall,
                    ),
                    const SizedBox(height: 12),
                    Center(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 560),
                        child: Text(
                          l10n.landingBody,
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.bodyLarge,
                        ),
                      ),
                    ),
                    const SizedBox(height: 56),
                    Wrap(
                      alignment: WrapAlignment.center,
                      spacing: 20,
                      runSpacing: 20,
                      children: const [
                        _Feature(
                          icon: Icons.description_outlined,
                          title: 'Organize your documents',
                          body:
                              'Upload your files and see clearly what was found and what still needs attention.',
                        ),
                        _Feature(
                          icon: Icons.menu_book_outlined,
                          title: 'Explain the rules',
                          body:
                              'Understand housing program requirements in plain language, step by step.',
                        ),
                        _Feature(
                          icon: Icons.inventory_2_outlined,
                          title: 'Build your packet',
                          body:
                              'Prepare a complete, organized packet for your housing office.',
                        ),
                      ],
                    ),
                    const SizedBox(height: 44),
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(28),
                        child: Column(
                          children: [
                            Text(
                              l10n.privacyTitle,
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                            const SizedBox(height: 18),
                            ...[
                              'Your uploaded documents are used only to organize your session.',
                              'You review and confirm information before it is used.',
                              'Your files are temporary and are not used to train AI.',
                              'You remain in control; HomelyPath does not make application decisions.',
                            ].map(
                              (item) => Padding(
                                padding: const EdgeInsets.only(bottom: 12),
                                child: Row(
                                  children: [
                                    const Icon(Icons.check, color: appInk),
                                    const SizedBox(width: 12),
                                    Expanded(child: Text(item)),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 28),
                    AppNotice(
                      child: Text(
                        l10n.privacyBody,
                        style: Theme.of(
                          context,
                        ).textTheme.bodyMedium?.copyWith(color: appInk),
                      ),
                    ),
                    const SizedBox(height: 26),
                    Center(
                      child: OutlinedButton(
                        onPressed: () {
                          final session = context.read<SessionCubit>().state;
                          if (session != null) context.go('/consent');
                        },
                        child: Text(l10n.startAnonymousSession),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const AppFooter(),
          ],
        ),
      ),
    );
  }
}

class _Feature extends StatelessWidget {
  const _Feature({required this.icon, required this.title, required this.body});
  final IconData icon;
  final String title;
  final String body;
  @override
  Widget build(BuildContext context) => SizedBox(
    width: 285,
    child: Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            Icon(icon, size: 34, color: appTeal),
            const SizedBox(height: 16),
            Text(
              title,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(
              body,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    ),
  );
}
