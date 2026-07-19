import 'dart:async';

import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../documents/application/documents_cubit.dart';
import '../../reconciliation/application/reconciliation_cubit.dart';
import '../domain/calculation_engine.dart';

class CalculationsCubit extends Cubit<CalculationResult?> {
  CalculationsCubit(this._documents, this._reconciliation) : super(null);
  final DocumentsCubit _documents;
  final ReconciliationCubit _reconciliation;
  StreamSubscription<DocumentsState>? _documentsSubscription;
  StreamSubscription<ReconciliationState>? _conflictsSubscription;
  Future<void> start() async {
    final csv = await rootBundle.loadString(
      'assets/data/mtsp_2026_boston_cambridge_quincy.csv',
    );
    _engine = CalculationEngine(MtspThresholds.fromCsv(csv));
    _documentsSubscription = _documents.stream.listen((_) => _recalculate());
    _conflictsSubscription = _reconciliation.stream.listen(
      (_) => _recalculate(),
    );
    _recalculate();
  }

  late CalculationEngine _engine;
  void _recalculate() => emit(
    _engine.calculate(
      _documents.state.documents,
      hasBlockingConflict: _reconciliation.state.hasBlockingConflict,
    ),
  );
  @override
  Future<void> close() async {
    await _documentsSubscription?.cancel();
    await _conflictsSubscription?.cancel();
    return super.close();
  }
}
