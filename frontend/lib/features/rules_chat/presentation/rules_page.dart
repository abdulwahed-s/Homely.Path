import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../features/auth_session/application/session_cubit.dart';
import '../../../features/calculations/application/calculations_cubit.dart';
import '../../../features/calculations/domain/calculation_engine.dart';
import '../../../infrastructure/ai_backend/ai_repository.dart';
import '../../../l10n/app_localizations.dart';
import '../../../core/widgets/app_ui.dart';

class RulesPage extends StatefulWidget {
  const RulesPage({super.key});
  @override
  State<RulesPage> createState() => _RulesPageState();
}

class _RulesPageState extends State<RulesPage> {
  final _question = TextEditingController(
    text: 'What is the frozen 60% income threshold for this household size?',
  );
  bool _loading = false;
  String? _answer;
  String? _error;
  String? _guidance;
  List<String> _citations = const [];

  @override
  void dispose() {
    _question.dispose();
    super.dispose();
  }

  Future<void> _ask() async {
    final sessionId = context.read<SessionCubit>().state?.id;
    if (sessionId == null || _question.text.trim().isEmpty) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final calculation = context.read<CalculationsCubit>().state;
      final calculationContext = _calculation(calculation);
      final result = await context.read<AiRepository>().ask(
        sessionId: sessionId,
        request: {'household_id': sessionId, 'question': _question.text.trim()},
        context: {
          'active_household_id': sessionId,
          'calculation': ?calculationContext,
        },
      );
      final answer = Map<String, dynamic>.from(
        result['answer'] as Map? ?? const {},
      );
      final safety = Map<String, dynamic>.from(
        result['safety'] as Map? ?? const {},
      );
      if (safety['safe_to_display'] != true) {
        throw StateError(
          'The backend safety gate did not approve this response.',
        );
      }
      final reasons = (answer['reasons'] as List? ?? const [])
          .map((reason) => reason.toString())
          .toList();
      final nextAction = answer['next_action'] as String?;
      final citations = (answer['citations'] as List? ?? const [])
          .whereType<Map>()
          .map((citation) {
            final value = Map<String, dynamic>.from(citation);
            final ruleId = value['rule_id'];
            final effectiveDate = value['effective_date'];
            return [?ruleId, ?effectiveDate].join(' · ');
          })
          .where((citation) => citation.isNotEmpty)
          .toList();
      setState(() {
        _answer = answer['answer'] as String? ?? answer['status'] as String?;
        _guidance = [...reasons, ?nextAction].join('\n');
        _citations = citations;
      });
    } catch (error) {
      setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Map<String, dynamic>? _calculation(CalculationResult? value) {
    if (value == null || value.householdSize == null) {
      return null;
    }
    final comparison = switch (value.comparison) {
      ThresholdComparison.belowOrEqual => 'below_or_equal',
      ThresholdComparison.above => 'above',
      ThresholdComparison.noFrozenThreshold => 'no_frozen_threshold',
      _ => null,
    };
    if (comparison == null) return null;
    return {
      'household_id': context.read<SessionCubit>().state?.id,
      'household_size': value.householdSize,
      'annualized_income': value.annualIncomeCents / 100,
      'threshold': value.thresholdCents == null
          ? null
          : value.thresholdCents! / 100,
      'comparison': comparison,
      'formula_steps': const [],
      'calculation_source': 'deterministic',
      'rule_year': 2026,
      'citations': const [],
    };
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Padding(
      padding: const EdgeInsets.all(28),
      child: ListView(
        children: [
          AppSectionHeader(
            title: l10n.rules,
            subtitle:
                'Ask about housing requirements and get plain-language guidance.',
            icon: Icons.menu_book_outlined,
          ),
          TextField(controller: _question, minLines: 2, maxLines: 4),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: _loading ? null : _ask,
            icon: const Icon(Icons.send_outlined),
            label: Text(_loading ? 'Asking…' : 'Ask rules assistant'),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(_error!),
            ),
          if (_answer != null)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(_answer!),
                    if (_guidance?.isNotEmpty ?? false) ...[
                      const SizedBox(height: 8),
                      Text(_guidance!),
                    ],
                    for (final citation in _citations)
                      Padding(
                        padding: const EdgeInsets.only(top: 8),
                        child: Text(citation),
                      ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}
