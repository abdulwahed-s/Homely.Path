import 'package:flutter_test/flutter_test.dart';
import 'package:homely_path/features/discovery/data/discovery_repository.dart';

void main() {
  test('public discovery response maps non-decisional property fields', () {
    final property = DiscoveryProperty.fromJson({
      'property_id': 'CA-1',
      'property_name': 'Public Homes',
      'state': 'CA',
      'city': 'Oakland',
      'total_units': 42,
      'low_income_units': 35,
      'fmr_reference': {'amount': 2450.0},
      'mtsp_reference': {'income_limit': 72000.0},
    });

    expect(property.id, 'CA-1');
    expect(property.name, 'Public Homes');
    expect(property.fmrAmount, 2450.0);
    expect(property.mtspLimit, 72000.0);
  });
}
