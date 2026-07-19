import 'dart:convert';
import 'dart:typed_data';

import 'package:archive/archive.dart';
import 'package:pdf/widgets.dart' as pw;

import '../../calculations/domain/calculation_engine.dart';
import '../../documents/domain/local_document.dart';
import '../../readiness/domain/readiness_engine.dart';
import 'packet_configuration.dart';

class PacketExporter {
  Future<Uint8List> createPdf({
    required PacketConfiguration configuration,
    required List<LocalDocument> documents,
    required CalculationResult calculation,
    required ReadinessResult readiness,
  }) async {
    final document = pw.Document();
    final content = <pw.Widget>[
      pw.Text(
        'HomelyPath',
        style: pw.TextStyle(fontSize: 24, fontWeight: pw.FontWeight.bold),
      ),
      pw.SizedBox(height: 12),
      pw.Text('This tool did not approve, deny, score, or rank you.'),
    ];
    for (final section in configuration.sections) {
      content.add(pw.SizedBox(height: 16));
      content.add(
        pw.Text(
          _title(section),
          style: pw.TextStyle(fontSize: 16, fontWeight: pw.FontWeight.bold),
        ),
      );
      content.addAll(_section(section, documents, calculation, readiness));
    }
    document.addPage(pw.MultiPage(build: (_) => content));
    return document.save();
  }

  Uint8List createSessionJson({
    required PacketConfiguration configuration,
    required List<LocalDocument> documents,
  }) => Uint8List.fromList(
    utf8.encode(
      jsonEncode({
        'packet': {
          'template': configuration.template.name,
          'sections': configuration.sections.map((item) => item.name).toList(),
        },
        'documents': documents.map((item) => item.toJson()).toList(),
      }),
    ),
  );
  Future<Uint8List> createZip({
    required Uint8List pdf,
    required Uint8List sessionJson,
  }) async {
    final archive = Archive()
      ..addFile(ArchiveFile('homelypath_packet.pdf', pdf.length, pdf))
      ..addFile(
        ArchiveFile('homelypath_session.json', sessionJson.length, sessionJson),
      );
    return Uint8List.fromList(ZipEncoder().encode(archive));
  }

  String _title(PacketSection section) => switch (section) {
    PacketSection.confirmedProfile => 'Confirmed profile',
    PacketSection.incomeSummary => 'Income summary',
    PacketSection.documentIndex => 'Document index',
    PacketSection.ruleReferences => 'Rule references',
    PacketSection.calculationWorksheet => 'Calculation worksheet',
    PacketSection.missingReviewSummary => 'Missing/review summary',
    PacketSection.activityReplay => 'Activity replay',
  };
  List<pw.Widget> _section(
    PacketSection section,
    List<LocalDocument> documents,
    CalculationResult calculation,
    ReadinessResult readiness,
  ) => switch (section) {
    PacketSection.documentIndex => [
      for (final item in documents) pw.Text(item.filename),
    ],
    PacketSection.incomeSummary || PacketSection.calculationWorksheet => [
      pw.Text(
        'Annualized amount: ${(calculation.annualIncomeCents / 100).toStringAsFixed(2)}',
      ),
      for (final item in calculation.sources)
        pw.Text('${item.kind}: ${(item.annualCents / 100).toStringAsFixed(2)}'),
    ],
    PacketSection.missingReviewSummary => [
      pw.Text(readiness.status.name),
      for (final item in readiness.items)
        pw.Text('${item.id}: ${item.status.name}'),
    ],
    PacketSection.ruleReferences => [
      pw.Text('HUD-MTSP-001; HUD-MTSP-002; CH-READINESS-001'),
    ],
    PacketSection.confirmedProfile => [
      pw.Text('Confirmed fields are sourced from renter-reviewed documents.'),
    ],
    PacketSection.activityReplay => [
      for (final document in documents)
        for (final event in document.activityEvents)
          pw.Text(
            '${event.timestamp.toIso8601String()}: ${event.agent} — ${event.action} (${event.status})',
          ),
      if (documents.every((document) => document.activityEvents.isEmpty))
        pw.Text('Activity remains local to this session.'),
    ],
  };
}
