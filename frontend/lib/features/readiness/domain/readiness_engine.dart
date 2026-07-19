import '../../calculations/domain/calculation_engine.dart';
import '../../documents/domain/local_document.dart';

enum ReadinessStatus { readyToReview, needsReview }

enum ChecklistStatus {
  confirmed,
  needsReview,
  missing,
  expired,
  humanReviewRequired,
}

class ChecklistItem {
  const ChecklistItem({required this.id, required this.status, this.detail});
  final String id;
  final ChecklistStatus status;
  final String? detail;
}

class ReadinessResult {
  const ReadinessResult({required this.status, required this.items});
  final ReadinessStatus status;
  final List<ChecklistItem> items;
}

class ReadinessEngine {
  const ReadinessEngine({this.now});
  final DateTime? now;
  ReadinessResult evaluate(
    List<LocalDocument> documents,
    CalculationResult calculation,
  ) {
    final today = now ?? DateTime.now().toUtc();
    final fields = [
      for (final document in documents)
        if (document.extraction != null) ...document.extraction!.fields,
    ];
    bool isConfirmed(String name) => fields.any(
      (field) =>
          field.fieldName == name &&
          (field.confirmationStatus == 'confirmed' ||
              field.confirmationStatus == 'user_edited'),
    );
    final items = <ChecklistItem>[
      ChecklistItem(
        id: 'household_size',
        status: isConfirmed('household_size')
            ? ChecklistStatus.confirmed
            : ChecklistStatus.missing,
      ),
      ChecklistItem(
        id: 'identity',
        status: isConfirmed('person_name')
            ? ChecklistStatus.confirmed
            : ChecklistStatus.missing,
      ),
      ChecklistItem(
        id: 'income',
        status: calculation.sources.isEmpty
            ? ChecklistStatus.missing
            : ChecklistStatus.confirmed,
      ),
      if (calculation.isBlocked)
        const ChecklistItem(
          id: 'conflicts',
          status: ChecklistStatus.humanReviewRequired,
        ),
      if (calculation.sources.any((source) => source.provisional))
        const ChecklistItem(
          id: 'gig_income',
          status: ChecklistStatus.humanReviewRequired,
        ),
    ];
    for (final document in documents.where((item) => item.extraction != null)) {
      final date = _dateFor(document);
      if (date != null && today.difference(date).inDays > 60) {
        items.add(
          ChecklistItem(
            id: document.id,
            status: ChecklistStatus.expired,
            detail: date.toIso8601String().split('T').first,
          ),
        );
      }
    }
    final blocked = items.any(
      (item) =>
          item.status == ChecklistStatus.missing ||
          item.status == ChecklistStatus.needsReview ||
          item.status == ChecklistStatus.expired ||
          item.status == ChecklistStatus.humanReviewRequired,
    );
    return ReadinessResult(
      status: blocked
          ? ReadinessStatus.needsReview
          : ReadinessStatus.readyToReview,
      items: items,
    );
  }

  DateTime? _dateFor(LocalDocument document) {
    final field = document.extraction!.fields
        .where(
          (field) =>
              const {
                'pay_date',
                'document_date',
                'application_date',
                'statement_month',
              }.contains(field.fieldName) &&
              (field.confirmationStatus == 'confirmed' ||
                  field.confirmationStatus == 'user_edited'),
        )
        .firstOrNull;
    final value = field?.normalizedValue ?? field?.value;
    if (value == null) {
      return null;
    }
    return DateTime.tryParse(
      value.toString().length == 7
          ? '${value.toString()}-01'
          : value.toString(),
    )?.toUtc();
  }
}
