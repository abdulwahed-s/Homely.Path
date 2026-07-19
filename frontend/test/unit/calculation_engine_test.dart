import 'package:flutter_test/flutter_test.dart';
import 'package:homely_path/features/calculations/domain/calculation_engine.dart';
import 'package:homely_path/features/documents/domain/local_document.dart';
import 'package:homely_path/infrastructure/ai_backend/extraction_dto.dart';

void main() {
  const source = SourceBoxDto(
    page: 1,
    x1: 0,
    y1: 0,
    x2: 1,
    y2: 1,
    sourceDescription: 'source',
  );
  ExtractedFieldDto field(String name, Object value) => ExtractedFieldDto(
    fieldName: name,
    value: value.toString(),
    normalizedValue: value,
    confidence: 1,
    confidenceLevel: 'high',
    confirmationStatus: 'confirmed',
    requiresManualEntry: false,
    source: source,
  );
  LocalDocument document(String type, List<ExtractedFieldDto> fields) =>
      LocalDocument(
        id: type,
        filename: '$type.pdf',
        byteLength: 1,
        status: LocalDocumentStatus.extracted,
        createdAt: DateTime(2026),
        extraction: DocumentExtractionDto(
          documentId: type,
          documentType: type,
          securityFlags: const [],
          fields: fields,
        ),
      );
  final engine = CalculationEngine(
    const MtspThresholds({1: 7200000, 2: 8232000}),
  );
  test('annualizes confirmed gross pay using its exact frequency', () {
    final result = engine.calculate([
      document('application_summary', [field('household_size', 1)]),
      document('pay_stub', [
        field('gross_pay', 1000),
        field('pay_frequency', 'biweekly'),
      ]),
    ], hasBlockingConflict: false);
    expect(result.annualIncomeCents, 2600000);
    expect(result.comparison, ThresholdComparison.belowOrEqual);
  });
  test('uses no frozen threshold outside the provided household sizes', () {
    final result = engine.calculate([
      document('application_summary', [field('household_size', 9)]),
    ], hasBlockingConflict: false);
    expect(result.comparison, ThresholdComparison.noFrozenThreshold);
  });
}
