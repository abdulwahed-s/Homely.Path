import 'package:flutter_test/flutter_test.dart';
import 'package:homely_path/features/calculations/domain/calculation_engine.dart';
import 'package:homely_path/features/documents/domain/local_document.dart';
import 'package:homely_path/features/readiness/domain/readiness_engine.dart';
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
  LocalDocument document(List<ExtractedFieldDto> fields) => LocalDocument(
    id: 'doc',
    filename: 'doc.pdf',
    byteLength: 1,
    status: LocalDocumentStatus.extracted,
    createdAt: DateTime(2026),
    extraction: DocumentExtractionDto(
      documentId: 'doc',
      documentType: 'pay_stub',
      securityFlags: const [],
      fields: fields,
    ),
  );
  test('gig income remains human review required even when calculated', () {
    final result = ReadinessEngine(now: DateTime.utc(2026, 7, 19)).evaluate(
      [
        document([
          field('person_name', 'A'),
          field('household_size', 1),
          field('pay_date', '2026-07-01'),
        ]),
      ],
      const CalculationResult(
        sources: [
          IncomeSource(
            kind: 'gig_statement',
            amountCents: 10000,
            multiplier: 12,
            provisional: true,
          ),
        ],
        householdSize: 1,
        thresholdCents: 7200000,
        comparison: ThresholdComparison.belowOrEqual,
        isBlocked: false,
      ),
    );
    expect(result.status, ReadinessStatus.needsReview);
  });
}
