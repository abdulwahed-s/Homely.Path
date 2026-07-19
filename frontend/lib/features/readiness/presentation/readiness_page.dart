import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../features/auth_session/application/session_cubit.dart';
import '../../../features/calculations/application/calculations_cubit.dart';
import '../../../features/calculations/domain/calculation_engine.dart';
import '../../../features/documents/application/documents_cubit.dart';
import '../../../features/reconciliation/application/reconciliation_cubit.dart';
import '../../../infrastructure/ai_backend/ai_repository.dart';
import '../../../l10n/app_localizations.dart';
import '../domain/readiness_engine.dart';
import '../../../core/widgets/app_ui.dart';

class ReadinessPage extends StatefulWidget {
  const ReadinessPage({super.key});
  @override
  State<ReadinessPage> createState() => _ReadinessPageState();
}

class _ReadinessPageState extends State<ReadinessPage> {
  bool _loading = false;
  String? _backendStatus;
  bool? _safeToDisplay;
  String? _error;
  List<String> _backendDetails = const [];

  Future<void> _requestBackendReview() async {
    final session = context.read<SessionCubit>().state;
    final calculation = context.read<CalculationsCubit>().state;
    final repository = context.read<AiRepository>();
    final localDocuments = context.read<DocumentsCubit>().state.documents;
    final localConflicts = context.read<ReconciliationCubit>().state.conflicts;
    if (session == null || calculation == null) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final calculationPayload = _calculation(session.id, calculation);
      if (calculationPayload == null) {
        final response = await repository.readiness(
          sessionId: session.id,
          payload: {
            'household_id': session.id,
            'consent_confirmed': session.consentAt != null,
            'calculation_result': {'calculation_status': 'INCOMPLETE'},
          },
        );
        _applyBackendResponse(response);
        return;
      }
      final ruleAnswer = await repository.ask(
        sessionId: session.id,
        request: {
          'household_id': session.id,
          'question':
              'What is the frozen 60% income threshold for this household size?',
        },
        context: {
          'active_household_id': session.id,
          'calculation': calculationPayload,
        },
      );
      final answer = Map<String, dynamic>.from(
        ruleAnswer['answer'] as Map? ?? const {},
      );
      final citations = (answer['citations'] as List? ?? const [])
          .whereType<Map>()
          .map((citation) => Map<String, dynamic>.from(citation))
          .toList();
      final readinessCalculation = {
        ...calculationPayload,
        'citations': citations,
      };
      final documents = localDocuments
          .where((item) => item.extraction != null)
          .map(
            (item) => {
              'document_id': item.id,
              'household_id': session.id,
              'document_type': item.extraction!.documentType,
              'file_name': item.filename,
              'synthetic': false,
              'fields': item.extraction!.fields
                  .map(
                    (field) => {
                      'field': field.fieldName,
                      'value': field.normalizedValue ?? field.value,
                      'page': field.source.page,
                      'bbox': [
                        field.source.x1,
                        field.source.y1,
                        field.source.x2,
                        field.source.y2,
                      ],
                      'bbox_units': 'pdf_points',
                    },
                  )
                  .toList(),
            },
          )
          .toList();
      final conflicts = localConflicts
          .where((item) => !item.isResolved)
          .map((item) => item.conflict.toJson())
          .toList();
      final confirmed = localDocuments
          .where((item) => item.extraction != null)
          .expand((item) => item.extraction!.fields)
          .where(
            (field) =>
                field.confirmationStatus == 'confirmed' ||
                field.confirmationStatus == 'user_edited',
          )
          .map(
            (field) => {
              'field_name': field.fieldName,
              'value': field.normalizedValue ?? field.value,
              'confirmed_by_user': true,
            },
          )
          .toList();
      final response = await repository.readiness(
        sessionId: session.id,
        payload: {
          'schema_version': '1.0',
          'request_id': 'flutter-${DateTime.now().microsecondsSinceEpoch}',
          'household_id': session.id,
          'consent_confirmed': session.consentAt != null,
          'reference_date': DateTime.now().toUtc().toIso8601String().substring(
            0,
            10,
          ),
          'document_summaries': documents,
          'confirmed_profile': {
            'household_id': session.id,
            'household_size': calculation.householdSize,
            'values': confirmed,
          },
          'conflicts': conflicts,
          'upstream_evidence_gaps': const [],
          'calculation_result': readinessCalculation,
        },
      );
      _applyBackendResponse(response);
    } catch (error) {
      setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _applyBackendResponse(Map<String, dynamic> response) {
    final safety = Map<String, dynamic>.from(
      response['safety_validation'] as Map? ?? const {},
    );
    setState(() {
      _backendStatus = response['readiness_status'] as String?;
      _safeToDisplay = safety['safe_to_display'] as bool?;
      final submission = Map<String, dynamic>.from(
        response['organizer_submission'] as Map? ?? const {},
      );
      final reasons = (submission['review_reasons'] as List? ?? const [])
          .whereType<Map>()
          .map((reason) {
            final value = Map<String, dynamic>.from(reason);
            return '${value['code'] ?? 'REVIEW'}: ${value['message'] ?? ''}';
          });
      final nextSteps = (submission['next_steps'] as List? ?? const [])
          .whereType<Map>()
          .map(
            (step) =>
                Map<String, dynamic>.from(step)['action']?.toString() ?? '',
          )
          .where((step) => step.isNotEmpty);
      final event = Map<String, dynamic>.from(
        response['activity_event'] as Map? ?? const {},
      );
      _backendDetails = [
        ...reasons,
        ...nextSteps,
        if (reasons.isEmpty && nextSteps.isEmpty && event['message'] != null)
          event['message'].toString(),
      ];
    });
  }

  Map<String, dynamic>? _calculation(
    String sessionId,
    CalculationResult value,
  ) {
    if (value.householdSize == null ||
        (value.comparison != ThresholdComparison.belowOrEqual &&
            value.comparison != ThresholdComparison.above &&
            value.comparison != ThresholdComparison.noFrozenThreshold) ||
        value.isBlocked) {
      return null;
    }
    return {
      'household_id': sessionId,
      'household_size': value.householdSize,
      'annualized_income': value.annualIncomeCents / 100,
      'threshold': value.thresholdCents == null
          ? null
          : value.thresholdCents! / 100,
      'comparison': switch (value.comparison) {
        ThresholdComparison.belowOrEqual => 'below_or_equal',
        ThresholdComparison.above => 'above',
        ThresholdComparison.noFrozenThreshold => 'no_frozen_threshold',
        _ => throw StateError('Invalid calculation comparison.'),
      },
      'formula_steps': const [],
      'calculation_source': 'deterministic',
      'rule_year': 2026,
      'citations': const [],
      'calculation_status': 'CALCULATED',
    };
  }

  @override
  Widget build(
    BuildContext context,
  ) => BlocBuilder<DocumentsCubit, DocumentsState>(
    builder: (context, documents) =>
        BlocBuilder<CalculationsCubit, CalculationResult?>(
          builder: (context, calculation) {
            final l10n = AppLocalizations.of(context)!;
            if (calculation == null) {
              return const Center(child: CircularProgressIndicator());
            }
            final local = const ReadinessEngine().evaluate(
              documents.documents,
              calculation,
            );
            return Padding(
              padding: const EdgeInsets.all(28),
              child: ListView(
                children: [
                  AppSectionHeader(
                    title: l10n.readiness,
                    subtitle: local.status == ReadinessStatus.readyToReview
                        ? l10n.readyToReview
                        : l10n.needsReview,
                    icon: Icons.checklist_outlined,
                  ),
                  for (final item in local.items)
                    ListTile(
                      leading: Icon(_icon(item.status)),
                      title: Text(item.id),
                      subtitle: item.detail == null ? null : Text(item.detail!),
                    ),
                  const Divider(height: 32),
                  FilledButton.icon(
                    onPressed: _loading ? null : _requestBackendReview,
                    icon: const Icon(Icons.refresh_outlined),
                    label: Text(_loading ? 'Checking…' : 'Check with backend'),
                  ),
                  if (_backendStatus != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: Text(
                        'Backend: $_backendStatus${_safeToDisplay == false ? ' (not safe to display)' : ''}',
                      ),
                    ),
                  for (final detail in _backendDetails)
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Text(detail),
                    ),
                  if (_error != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: Text(_error!),
                    ),
                ],
              ),
            );
          },
        ),
  );

  IconData _icon(ChecklistStatus status) => switch (status) {
    ChecklistStatus.confirmed => Icons.check_circle_outlined,
    ChecklistStatus.needsReview => Icons.warning_amber_outlined,
    ChecklistStatus.missing => Icons.remove_circle_outline,
    ChecklistStatus.expired => Icons.history_toggle_off_outlined,
    ChecklistStatus.humanReviewRequired => Icons.person_search_outlined,
  };
}
