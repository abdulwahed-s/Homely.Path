import '../../documents/domain/local_document.dart';

enum ThresholdComparison { belowOrEqual, above, noFrozenThreshold, unavailable }

class IncomeSource {
  const IncomeSource({
    required this.kind,
    required this.amountCents,
    required this.multiplier,
    this.provisional = false,
  });
  final String kind;
  final int amountCents;
  final int multiplier;
  final bool provisional;
  int get annualCents => amountCents * multiplier;
}

class CalculationResult {
  const CalculationResult({
    required this.sources,
    required this.householdSize,
    required this.thresholdCents,
    required this.comparison,
    required this.isBlocked,
  });
  final List<IncomeSource> sources;
  final int? householdSize;
  final int? thresholdCents;
  final ThresholdComparison comparison;
  final bool isBlocked;
  int get annualIncomeCents =>
      sources.fold(0, (sum, source) => sum + source.annualCents);
}

class MtspThresholds {
  const MtspThresholds(this.byHouseholdSize);
  final Map<int, int> byHouseholdSize;
  static MtspThresholds fromCsv(String csv) {
    final lines = csv.trim().split('\n');
    final result = <int, int>{};
    for (final line in lines.skip(1)) {
      final cells = line.split(',');
      if (cells.length >= 8) {
        final size = int.tryParse(cells[4]);
        final dollars = int.tryParse(cells[7]);
        if (size != null && dollars != null) {
          result[size] = dollars * 100;
        }
      }
    }
    return MtspThresholds(result);
  }
}

class CalculationEngine {
  const CalculationEngine(this.thresholds);
  final MtspThresholds thresholds;
  CalculationResult calculate(
    List<LocalDocument> documents, {
    required bool hasBlockingConflict,
  }) {
    final confirmed = <String, List<Object?>>{};
    for (final document in documents) {
      final extraction = document.extraction;
      if (extraction == null) continue;
      for (final field in extraction.fields) {
        if (field.confirmationStatus == 'confirmed' ||
            field.confirmationStatus == 'user_edited') {
          (confirmed[field.fieldName] ??= []).add(
            field.normalizedValue ?? field.value,
          );
        }
      }
    }
    final householdSize = _asInt(confirmed['household_size']?.firstOrNull);
    final sources = <IncomeSource>[];
    for (final document in documents) {
      final extraction = document.extraction;
      if (extraction == null) continue;
      final fields = {
        for (final field in extraction.fields.where(
          (field) =>
              field.confirmationStatus == 'confirmed' ||
              field.confirmationStatus == 'user_edited',
        ))
          field.fieldName: field.normalizedValue ?? field.value,
      };
      switch (extraction.documentType) {
        case 'pay_stub':
          final cents = _asCents(fields['gross_pay']);
          final multiplier = _frequencyMultiplier(fields['pay_frequency']);
          if (cents != null && multiplier != null) {
            sources.add(
              IncomeSource(
                kind: 'pay_stub',
                amountCents: cents,
                multiplier: multiplier,
              ),
            );
          }
        case 'employment_letter':
          final hours = _asDecimal(fields['weekly_hours']);
          final rate = _asCents(fields['hourly_rate']);
          if (hours != null && rate != null) {
            sources.add(
              IncomeSource(
                kind: 'employment_letter',
                amountCents: (hours * rate).round(),
                multiplier: 52,
              ),
            );
          }
        case 'benefit_letter':
          final cents = _asCents(fields['monthly_benefit']);
          final multiplier =
              _frequencyMultiplier(fields['benefit_frequency']) ?? 12;
          if (cents != null) {
            sources.add(
              IncomeSource(
                kind: 'benefit_letter',
                amountCents: cents,
                multiplier: multiplier,
              ),
            );
          }
        case 'gig_statement':
          final cents = _asCents(fields['gross_receipts']);
          if (cents != null) {
            sources.add(
              IncomeSource(
                kind: 'gig_statement',
                amountCents: cents,
                multiplier: 12,
                provisional: true,
              ),
            );
          }
      }
    }
    final threshold = householdSize == null
        ? null
        : thresholds.byHouseholdSize[householdSize];
    final annual = sources.fold(0, (sum, source) => sum + source.annualCents);
    final comparison =
        householdSize != null && (householdSize < 1 || householdSize > 8)
        ? ThresholdComparison.noFrozenThreshold
        : threshold == null
        ? ThresholdComparison.unavailable
        : annual <= threshold
        ? ThresholdComparison.belowOrEqual
        : ThresholdComparison.above;
    return CalculationResult(
      sources: sources,
      householdSize: householdSize,
      thresholdCents: threshold,
      comparison: comparison,
      isBlocked: hasBlockingConflict,
    );
  }

  int? _asInt(Object? value) => _asDecimal(value)?.round();
  double? _asDecimal(Object? value) => value is num
      ? value.toDouble()
      : double.tryParse(
          value?.toString().replaceAll(RegExp('[^0-9.-]'), '') ?? '',
        );
  int? _asCents(Object? value) {
    final parsed = _asDecimal(value);
    return parsed == null ? null : (parsed * 100).round();
  }

  int? _frequencyMultiplier(Object? value) =>
      switch (value?.toString().toLowerCase()) {
        'weekly' => 52,
        'biweekly' => 26,
        'semimonthly' => 24,
        'monthly' => 12,
        'annual' => 1,
        _ => null,
      };
}
