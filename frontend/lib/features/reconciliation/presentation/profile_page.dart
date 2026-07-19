import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../documents/application/documents_cubit.dart';
import '../../documents/domain/local_document.dart';
import '../../../core/widgets/app_ui.dart';

class ProfilePage extends StatelessWidget {
  const ProfilePage({super.key});

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.all(28),
    child: BlocBuilder<DocumentsCubit, DocumentsState>(
      builder: (context, state) {
        final rows = <_ProfileValue>[
          for (final document in state.documents)
            if (document.extraction != null)
              for (final field in document.extraction!.fields)
                if (_isConfirmed(field.confirmationStatus))
                  _ProfileValue(
                    label: field.fieldName,
                    value:
                        (field.normalizedValue ?? field.value)?.toString() ??
                        '—',
                    document: document,
                    source: field.source.sourceDescription,
                  ),
        ];
        return ListView(
          children: [
            const AppSectionHeader(
              title: 'Confirmed profile',
              subtitle:
                  'Only values you confirmed are used downstream. Each value retains its document evidence.',
              icon: Icons.person_outline,
            ),
            if (rows.isEmpty)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(20),
                  child: Text(
                    'No confirmed profile values yet. Review extracted document fields first.',
                  ),
                ),
              )
            else
              Card(
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: DataTable(
                    columns: const [
                      DataColumn(label: Text('Field')),
                      DataColumn(label: Text('Confirmed value')),
                      DataColumn(label: Text('Source document')),
                      DataColumn(label: Text('Evidence location')),
                    ],
                    rows: [
                      for (final row in rows)
                        DataRow(
                          cells: [
                            DataCell(Text(row.label)),
                            DataCell(Text(row.value)),
                            DataCell(Text(row.document.filename)),
                            DataCell(Text(row.source)),
                          ],
                        ),
                    ],
                  ),
                ),
              ),
          ],
        );
      },
    ),
  );

  bool _isConfirmed(String value) =>
      value == 'confirmed' || value == 'user_edited';
}

class _ProfileValue {
  const _ProfileValue({
    required this.label,
    required this.value,
    required this.document,
    required this.source,
  });
  final String label;
  final String value;
  final LocalDocument document;
  final String source;
}
