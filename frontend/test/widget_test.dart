import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:homely_path/features/auth_session/application/session_cubit.dart';
import 'package:homely_path/features/overview/presentation/landing_page.dart';
import 'package:homely_path/infrastructure/local_storage/memory_local_session_store.dart';
import 'package:homely_path/l10n/app_localizations.dart';

void main() {
  testWidgets('landing page offers an anonymous session', (
    WidgetTester tester,
  ) async {
    final cubit = SessionCubit(MemoryLocalSessionStore());
    await cubit.restoreOrCreate(anonymousUid: 'test-session');
    await tester.pumpWidget(
      MaterialApp(
        locale: const Locale('en'),
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        home: BlocProvider.value(value: cubit, child: const LandingPage()),
      ),
    );
    expect(find.byType(LandingPage), findsOneWidget);
    expect(
      find.text('This tool did not approve, deny, score, or rank you.'),
      findsOneWidget,
    );
  });

  testWidgets('Arabic applies RTL directionality', (WidgetTester tester) async {
    final cubit = SessionCubit(MemoryLocalSessionStore());
    await cubit.restoreOrCreate(anonymousUid: 'test-session');
    await tester.pumpWidget(
      MaterialApp(
        locale: const Locale('ar'),
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        home: BlocProvider.value(value: cubit, child: const LandingPage()),
      ),
    );
    expect(
      Directionality.of(tester.element(find.byType(LandingPage))),
      TextDirection.rtl,
    );
  });
}
