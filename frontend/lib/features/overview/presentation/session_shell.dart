import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../../app/config/app_config.dart';
import '../../../features/auth_session/application/session_cubit.dart';
import '../../../l10n/app_localizations.dart';
import '../../../core/widgets/app_ui.dart';
import '../../../app/theme/app_theme.dart';

class SessionShell extends StatelessWidget {
  const SessionShell({
    super.key,
    required this.child,
    required this.currentPath,
    required this.config,
    required this.onLocaleChanged,
  });
  final Widget child;
  final String currentPath;
  final AppConfig config;
  final ValueChanged<Locale> onLocaleChanged;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final session = context.watch<SessionCubit>().state;
    if (session == null) return const SizedBox.shrink();
    final destinations = <_Destination>[
      _Destination('overview', l10n.overview, Icons.dashboard_outlined),
      _Destination('documents', l10n.documents, Icons.upload_file_outlined),
      const _Destination(
        'discovery',
        'Find properties',
        Icons.apartment_outlined,
      ),
      _Destination('profile', l10n.confirmedProfile, Icons.person_outline),
      _Destination('conflicts', l10n.conflicts, Icons.warning_amber_outlined),
      _Destination('rules', l10n.rules, Icons.menu_book_outlined),
      _Destination('calculations', l10n.calculations, Icons.calculate_outlined),
      _Destination('readiness', l10n.readiness, Icons.checklist_outlined),
      _Destination('packet', l10n.packet, Icons.folder_copy_outlined),
    ];
    final selected = destinations
        .indexWhere(
          (destination) => currentPath.endsWith('/${destination.path}'),
        )
        .clamp(0, destinations.length - 1);
    void navigate(int index) =>
        context.go('/session/${session.id}/${destinations[index].path}');
    final nav = NavigationRail(
      backgroundColor: Colors.white,
      selectedIndex: selected,
      onDestinationSelected: navigate,
      labelType: NavigationRailLabelType.all,
      selectedIconTheme: const IconThemeData(color: appTeal),
      selectedLabelTextStyle: const TextStyle(
        color: appInk,
        fontWeight: FontWeight.w700,
      ),
      destinations: destinations
          .map(
            (item) => NavigationRailDestination(
              icon: Icon(item.icon),
              label: Text(item.label),
            ),
          )
          .toList(),
    );
    return Scaffold(
      appBar: AppBar(
        title: const AppBrand(),
        surfaceTintColor: Colors.transparent,
        backgroundColor: Colors.white,
        actions: [
          PopupMenuButton<String>(
            tooltip: l10n.language,
            onSelected: (code) => onLocaleChanged(Locale(code)),
            itemBuilder: (_) => [
              PopupMenuItem(value: 'en', child: Text(l10n.english)),
              PopupMenuItem(value: 'ar', child: Text(l10n.arabic)),
            ],
          ),
          PopupMenuButton<String>(
            onSelected: (action) async {
              if (action == 'delete') {
                await context.read<SessionCubit>().delete();
                if (context.mounted) context.go('/');
              }
            },
            itemBuilder: (_) => [
              PopupMenuItem(value: 'export', child: Text(l10n.exportSession)),
              PopupMenuItem(value: 'delete', child: Text(l10n.deleteSession)),
            ],
          ),
        ],
      ),
      body: Column(
        children: [
          if (!config.hasHttpBackend && config.aiMode == AiMode.disabled)
            Container(
              width: double.infinity,
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              padding: const EdgeInsets.all(8),
              child: Text(l10n.aiUnavailable, textAlign: TextAlign.center),
            ),
          Expanded(
            child: LayoutBuilder(
              builder: (context, constraints) => constraints.maxWidth >= 720
                  ? Row(
                      children: [
                        nav,
                        const VerticalDivider(width: 1),
                        Expanded(child: child),
                      ],
                    )
                  : child,
            ),
          ),
          const AppFooter(),
        ],
      ),
      bottomNavigationBar: MediaQuery.sizeOf(context).width < 720
          ? NavigationBar(
              selectedIndex: selected,
              onDestinationSelected: navigate,
              destinations: destinations
                  .take(5)
                  .map(
                    (item) => NavigationDestination(
                      icon: Icon(item.icon),
                      label: item.label,
                    ),
                  )
                  .toList(),
            )
          : null,
    );
  }
}

class _Destination {
  const _Destination(this.path, this.label, this.icon);
  final String path;
  final String label;
  final IconData icon;
}
