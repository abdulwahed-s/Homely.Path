import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import '../features/auth_session/application/session_cubit.dart';
import '../features/calculations/application/calculations_cubit.dart';
import '../features/documents/application/documents_cubit.dart';
import '../features/reconciliation/application/reconciliation_cubit.dart';
import '../features/packet/application/packet_cubit.dart';
import '../infrastructure/ai_backend/ai_repository.dart';
import '../l10n/app_localizations.dart';
import 'config/app_config.dart';
import 'router.dart';
import 'theme/app_theme.dart';

class AppDependencies {
  const AppDependencies({
    required this.config,
    required this.sessionCubit,
    required this.documentsCubit,
    required this.reconciliationCubit,
    required this.calculationsCubit,
    required this.packetCubit,
    required this.aiRepository,
    required this.initialLocale,
    required this.onLocaleChanged,
  });
  final AppConfig config;
  final SessionCubit sessionCubit;
  final DocumentsCubit documentsCubit;
  final ReconciliationCubit reconciliationCubit;
  final CalculationsCubit calculationsCubit;
  final PacketCubit packetCubit;
  final AiRepository aiRepository;
  final Locale? initialLocale;
  final Future<void> Function(String) onLocaleChanged;
}

class HomelyPathApp extends StatefulWidget {
  const HomelyPathApp({super.key, required this.dependencies});
  final AppDependencies dependencies;
  @override
  State<HomelyPathApp> createState() => _HomelyPathAppState();
}

class _HomelyPathAppState extends State<HomelyPathApp> {
  late Locale? _locale = widget.dependencies.initialLocale;
  @override
  Widget build(BuildContext context) => MultiBlocProvider(
    providers: [
      RepositoryProvider<AiRepository>.value(
        value: widget.dependencies.aiRepository,
      ),
      BlocProvider.value(value: widget.dependencies.sessionCubit),
      BlocProvider.value(value: widget.dependencies.documentsCubit),
      BlocProvider.value(value: widget.dependencies.reconciliationCubit),
      BlocProvider.value(value: widget.dependencies.calculationsCubit),
      BlocProvider.value(value: widget.dependencies.packetCubit),
    ],
    child: MaterialApp.router(
      title: 'HomelyPath',
      theme: appTheme,
      darkTheme: appTheme,
      debugShowCheckedModeBanner: false,
      locale: _locale,
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      routerConfig: createRouter(
        config: widget.dependencies.config,
        onLocaleChanged: (locale) async {
          setState(() => _locale = locale);
          await widget.dependencies.onLocaleChanged(locale.languageCode);
        },
      ),
    ),
  );
}
