const canonicalFields = <String, Set<String>>{
  'application_summary': {
    'person_name',
    'household_size',
    'address',
    'application_date',
  },
  'pay_stub': {
    'person_name',
    'pay_date',
    'pay_period_start',
    'pay_period_end',
    'pay_frequency',
    'regular_hours',
    'hourly_rate',
    'gross_pay',
    'net_pay',
  },
  'employment_letter': {
    'person_name',
    'document_date',
    'weekly_hours',
    'hourly_rate',
  },
  'benefit_letter': {
    'person_name',
    'document_date',
    'monthly_benefit',
    'benefit_frequency',
  },
  'gig_statement': {
    'person_name',
    'statement_month',
    'gross_receipts',
    'platform_fees',
  },
};

bool isSupportedDocumentType(String type) => canonicalFields.containsKey(type);
bool isAllowlistedField(String documentType, String fieldName) =>
    canonicalFields[documentType]?.contains(fieldName) ?? false;
