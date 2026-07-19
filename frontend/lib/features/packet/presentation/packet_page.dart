import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:printing/printing.dart';

import '../../../l10n/app_localizations.dart';
import '../../calculations/application/calculations_cubit.dart';
import '../../documents/application/documents_cubit.dart';
import '../../readiness/domain/readiness_engine.dart';
import '../application/packet_cubit.dart';
import '../domain/packet_configuration.dart';
import '../domain/packet_exporter.dart';
import '../../../core/widgets/app_ui.dart';

class PacketPage extends StatelessWidget {
  const PacketPage({super.key});
  @override
  Widget build(
    BuildContext context,
  ) => BlocBuilder<DocumentsCubit, DocumentsState>(
    builder: (context, documents) => BlocBuilder<CalculationsCubit, dynamic>(
      builder: (context, calculation) =>
          BlocBuilder<PacketCubit, PacketConfiguration>(
            builder: (context, configuration) {
              final l10n = AppLocalizations.of(context)!;
              if (calculation == null) {
                return const Center(child: CircularProgressIndicator());
              }
              final readiness = const ReadinessEngine().evaluate(
                documents.documents,
                calculation,
              );
              return Padding(
                padding: const EdgeInsets.all(28),
                child: ListView(
                  children: [
                    AppSectionHeader(
                      title: l10n.packet,
                      subtitle:
                          'Choose the materials you want to organize and export.',
                      icon: Icons.folder_copy_outlined,
                    ),
                    SegmentedButton<PacketTemplate>(
                      segments: [
                        ButtonSegment(
                          value: PacketTemplate.forMe,
                          label: Text(l10n.forMe),
                        ),
                        ButtonSegment(
                          value: PacketTemplate.forCaseworker,
                          label: Text(l10n.forCaseworker),
                        ),
                      ],
                      selected: {configuration.template},
                      onSelectionChanged: (items) =>
                          context.read<PacketCubit>().setTemplate(items.single),
                    ),
                    const SizedBox(height: 16),
                    ReorderableListView(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      onReorder: context.read<PacketCubit>().move,
                      children: [
                        for (final section in configuration.sections)
                          CheckboxListTile(
                            key: ValueKey(section),
                            value: true,
                            onChanged: (selected) => context
                                .read<PacketCubit>()
                                .toggle(section, selected ?? false),
                            title: Text(_sectionLabel(l10n, section)),
                          ),
                      ],
                    ),
                    Wrap(
                      spacing: 12,
                      children: [
                        ElevatedButton(
                          onPressed: () => _exportPdf(
                            configuration,
                            documents.documents,
                            calculation,
                            readiness,
                          ),
                          child: Text(l10n.exportPdf),
                        ),
                        OutlinedButton(
                          onPressed: () => _exportZip(
                            configuration,
                            documents.documents,
                            calculation,
                            readiness,
                          ),
                          child: Text(l10n.exportZip),
                        ),
                        OutlinedButton(
                          onPressed: () =>
                              _exportJson(configuration, documents.documents),
                          child: Text(l10n.exportSession),
                        ),
                      ],
                    ),
                  ],
                ),
              );
            },
          ),
    ),
  );
  String _sectionLabel(AppLocalizations l10n, PacketSection section) =>
      switch (section) {
        PacketSection.confirmedProfile => l10n.confirmedProfileSection,
        PacketSection.incomeSummary => l10n.incomeSummarySection,
        PacketSection.documentIndex => l10n.documentIndexSection,
        PacketSection.ruleReferences => l10n.ruleReferencesSection,
        PacketSection.calculationWorksheet => l10n.calculationWorksheetSection,
        PacketSection.missingReviewSummary => l10n.missingReviewSection,
        PacketSection.activityReplay => l10n.activityReplaySection,
      };
  Future<void> _exportPdf(
    PacketConfiguration configuration,
    List documents,
    dynamic calculation,
    ReadinessResult readiness,
  ) async {
    final bytes = await PacketExporter().createPdf(
      configuration: configuration,
      documents: documents.cast(),
      calculation: calculation,
      readiness: readiness,
    );
    await Printing.sharePdf(bytes: bytes, filename: 'homelypath_packet.pdf');
  }

  Future<void> _exportZip(
    PacketConfiguration configuration,
    List documents,
    dynamic calculation,
    ReadinessResult readiness,
  ) async {
    final exporter = PacketExporter();
    final pdf = await exporter.createPdf(
      configuration: configuration,
      documents: documents.cast(),
      calculation: calculation,
      readiness: readiness,
    );
    final zip = await exporter.createZip(
      pdf: pdf,
      sessionJson: exporter.createSessionJson(
        configuration: configuration,
        documents: documents.cast(),
      ),
    );
    await Printing.sharePdf(bytes: zip, filename: 'homelypath_packet.zip');
  }

  Future<void> _exportJson(
    PacketConfiguration configuration,
    List documents,
  ) async {
    final bytes = PacketExporter().createSessionJson(
      configuration: configuration,
      documents: documents.cast(),
    );
    await Printing.sharePdf(bytes: bytes, filename: 'homelypath_session.json');
  }
}
