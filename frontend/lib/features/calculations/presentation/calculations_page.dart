import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../l10n/app_localizations.dart';
import '../../auth_session/application/session_cubit.dart';
import '../application/calculations_cubit.dart';
import '../domain/calculation_engine.dart';
import '../../../core/widgets/app_ui.dart';

class CalculationsPage extends StatelessWidget {
  const CalculationsPage({super.key});
  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final money = NumberFormat.currency(
      locale: Localizations.localeOf(context).toLanguageTag(),
      symbol: r'$',
    );
    return Padding(
      padding: const EdgeInsets.all(28),
      child: BlocBuilder<CalculationsCubit, CalculationResult?>(
        builder: (context, result) {
          if (result == null) {
            return const Center(child: CircularProgressIndicator());
          }
          return ListView(
            children: [
              AppSectionHeader(
                title: l10n.calculations,
                subtitle:
                    'A clear, traceable view of the information you confirmed.',
                icon: Icons.calculate_outlined,
              ),
              if (result.isBlocked)
                Card(
                  color: Theme.of(context).colorScheme.errorContainer,
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          l10n.needsReview,
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'Income and threshold results are hidden until every required conflict and confirmation is resolved.',
                        ),
                        const SizedBox(height: 12),
                        FilledButton.tonalIcon(
                          onPressed: () => context.go(
                            '/session/${context.read<SessionCubit>().state!.id}/conflicts',
                          ),
                          icon: const Icon(Icons.fact_check_outlined),
                          label: const Text('Resolve outstanding review'),
                        ),
                      ],
                    ),
                  ),
                )
              else ...[
                _SummaryCard(money: money, result: result, l10n: l10n),
                const SizedBox(height: 20),
              ],
              if (!result.isBlocked) const SizedBox(height: 20),
              if (!result.isBlocked)
                Text(
                  'Step-by-step income calculation',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              if (!result.isBlocked) const SizedBox(height: 8),
              if (!result.isBlocked)
                for (final source in result.sources)
                  Card(
                    child: ListTile(
                      title: Text(source.kind),
                      subtitle: Text(
                        '${money.format(source.amountCents / 100)} × ${source.multiplier}${source.provisional ? ' · provisional' : ''}',
                      ),
                      trailing: Text(money.format(source.annualCents / 100)),
                    ),
                  ),
            ],
          );
        },
      ),
    );
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({
    required this.money,
    required this.result,
    required this.l10n,
  });

  final NumberFormat money;
  final CalculationResult result;
  final AppLocalizations l10n;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(20),
      child: Wrap(
        spacing: 32,
        runSpacing: 16,
        children: [
          _Metric(
            'Calculated annual income',
            money.format(result.annualIncomeCents / 100),
          ),
          _Metric(
            'Household size',
            result.householdSize == null
                ? l10n.unknown
                : '${result.householdSize} persons',
          ),
          _Metric(
            'Frozen threshold',
            result.thresholdCents == null
                ? l10n.unknown
                : money.format(result.thresholdCents! / 100),
          ),
          _Metric('Comparison', _comparisonLabel(l10n, result.comparison)),
        ],
      ),
    ),
  );

  String _comparisonLabel(
    AppLocalizations l10n,
    ThresholdComparison comparison,
  ) => switch (comparison) {
    ThresholdComparison.belowOrEqual => l10n.belowOrEqual,
    ThresholdComparison.above => l10n.aboveThreshold,
    ThresholdComparison.noFrozenThreshold => l10n.noFrozenThreshold,
    ThresholdComparison.unavailable => l10n.actionRequired,
  };
}

class _Metric extends StatelessWidget {
  const _Metric(this.label, this.value);
  final String label;
  final String value;
  @override
  Widget build(BuildContext context) => SizedBox(
    width: 190,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: Theme.of(context).textTheme.labelLarge),
        const SizedBox(height: 4),
        Text(value, style: Theme.of(context).textTheme.titleLarge),
      ],
    ),
  );
}
