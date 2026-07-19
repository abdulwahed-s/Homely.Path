import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../features/consent/presentation/consent_page.dart';
import '../features/calculations/presentation/calculations_page.dart';
import '../features/documents/presentation/documents_page.dart';
import '../features/documents/presentation/document_review_page.dart';
import '../features/discovery/presentation/discovery_page.dart';
import '../features/reconciliation/presentation/conflicts_page.dart';
import '../features/reconciliation/presentation/profile_page.dart';
import '../features/readiness/presentation/readiness_page.dart';
import '../features/packet/presentation/packet_page.dart';
import '../features/rules_chat/presentation/rules_page.dart';
import '../features/overview/presentation/landing_page.dart';
import '../features/overview/presentation/overview_page.dart';
import '../features/overview/presentation/session_shell.dart';
import 'config/app_config.dart';

GoRouter createRouter({
  required AppConfig config,
  required ValueChanged<Locale> onLocaleChanged,
}) => GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(path: '/', builder: (context, state) => const LandingPage()),
    GoRoute(path: '/consent', builder: (context, state) => const ConsentPage()),
    ShellRoute(
      builder: (context, state, child) => SessionShell(
        currentPath: state.uri.path,
        config: config,
        onLocaleChanged: onLocaleChanged,
        child: child,
      ),
      routes: [
        GoRoute(
          path: '/session/:sessionId/overview',
          builder: (context, state) => const OverviewPage(),
        ),
        GoRoute(
          path: '/session/:sessionId/documents',
          builder: (context, state) => const DocumentsPage(),
        ),
        GoRoute(
          path: '/session/:sessionId/discovery',
          builder: (context, state) => DiscoveryPage(config: config),
        ),
        GoRoute(
          path: '/session/:sessionId/documents/:documentId/review',
          builder: (context, state) => DocumentReviewPage(
            documentId: state.pathParameters['documentId']!,
          ),
        ),
        GoRoute(
          path: '/session/:sessionId/profile',
          builder: (context, state) => const ProfilePage(),
        ),
        GoRoute(
          path: '/session/:sessionId/conflicts',
          builder: (context, state) => const ConflictsPage(),
        ),
        GoRoute(
          path: '/session/:sessionId/rules',
          builder: (context, state) => const RulesPage(),
        ),
        GoRoute(
          path: '/session/:sessionId/calculations',
          builder: (context, state) => const CalculationsPage(),
        ),
        GoRoute(
          path: '/session/:sessionId/readiness',
          builder: (context, state) => const ReadinessPage(),
        ),
        GoRoute(
          path: '/session/:sessionId/packet',
          builder: (context, state) => const PacketPage(),
        ),
      ],
    ),
  ],
);
