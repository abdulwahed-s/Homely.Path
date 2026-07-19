import 'package:flutter_test/flutter_test.dart';
import 'package:homely_path/features/calculations/domain/calculation_engine.dart';
import 'package:homely_path/features/documents/domain/local_document.dart';
import 'package:homely_path/features/packet/domain/packet_configuration.dart';
import 'package:homely_path/features/packet/domain/packet_exporter.dart';
import 'package:homely_path/features/readiness/domain/readiness_engine.dart';

void main() {
  test('packet exports contain a PDF, local session JSON, and ZIP', () async {
    final exporter = PacketExporter();
    final configuration = PacketConfiguration.initial();
    final documents = <LocalDocument>[];
    final calculation = const CalculationResult(
      sources: [],
      householdSize: null,
      thresholdCents: null,
      comparison: ThresholdComparison.unavailable,
      isBlocked: false,
    );
    const readiness = ReadinessResult(
      status: ReadinessStatus.needsReview,
      items: [],
    );
    final pdf = await exporter.createPdf(
      configuration: configuration,
      documents: documents,
      calculation: calculation,
      readiness: readiness,
    );
    final json = exporter.createSessionJson(
      configuration: configuration,
      documents: documents,
    );
    final zip = await exporter.createZip(pdf: pdf, sessionJson: json);
    expect(String.fromCharCodes(pdf.take(4)), '%PDF');
    expect(json, isNotEmpty);
    expect(zip, isNotEmpty);
  });
}
