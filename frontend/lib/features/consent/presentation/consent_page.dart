import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../auth_session/application/session_cubit.dart';
import '../../../l10n/app_localizations.dart';
import '../../../core/widgets/app_ui.dart';

class ConsentPage extends StatefulWidget {
  const ConsentPage({super.key});
  @override
  State<ConsentPage> createState() => _ConsentPageState();
}

class _ConsentPageState extends State<ConsentPage> {
  bool _accepted = false;
  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(42, 30, 42, 0),
              child: Align(alignment: Alignment.centerLeft, child: AppBrand()),
            ),
            Expanded(
              child: Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(24),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 680),
                    child: Card(
                      child: Padding(
                        padding: const EdgeInsets.all(36),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            AppSectionHeader(
                              title: l10n.consentTitle,
                              subtitle:
                                  'A short confirmation before you begin.',
                              icon: Icons.verified_user_outlined,
                            ),
                            const SizedBox(height: 4),
                            Text(l10n.consentBody),
                            const SizedBox(height: 20),
                            AppNotice(child: Text(l10n.consentRetention)),
                            const SizedBox(height: 20),
                            Container(
                              decoration: BoxDecoration(
                                color: Theme.of(
                                  context,
                                ).colorScheme.surfaceContainerLowest,
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: CheckboxListTile(
                                value: _accepted,
                                onChanged: (value) =>
                                    setState(() => _accepted = value ?? false),
                                title: Text(l10n.consentCheck),
                                controlAffinity:
                                    ListTileControlAffinity.leading,
                                contentPadding: const EdgeInsets.symmetric(
                                  horizontal: 12,
                                ),
                              ),
                            ),
                            const SizedBox(height: 20),
                            Align(
                              alignment: AlignmentDirectional.centerEnd,
                              child: FilledButton.icon(
                                onPressed: !_accepted
                                    ? null
                                    : () async {
                                        await context
                                            .read<SessionCubit>()
                                            .grantConsent();
                                        if (!context.mounted) return;
                                        final session = context
                                            .read<SessionCubit>()
                                            .state;
                                        context.go(
                                          '/session/${session!.id}/overview',
                                        );
                                      },
                                icon: const Icon(Icons.arrow_forward),
                                label: Text(l10n.continueLabel),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
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
