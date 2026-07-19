import 'package:dio/dio.dart';

class DiscoveryProperty {
  const DiscoveryProperty({
    required this.id,
    required this.name,
    required this.state,
    this.address,
    this.city,
    this.zipCode,
    this.totalUnits,
    this.lowIncomeUnits,
    this.distanceMiles,
    this.fmrAmount,
    this.mtspLimit,
  });

  final String id;
  final String name;
  final String state;
  final String? address;
  final String? city;
  final String? zipCode;
  final int? totalUnits;
  final int? lowIncomeUnits;
  final double? distanceMiles;
  final double? fmrAmount;
  final double? mtspLimit;

  factory DiscoveryProperty.fromJson(Map<String, dynamic> json) {
    final fmr = Map<String, dynamic>.from(
      json['fmr_reference'] as Map? ?? const {},
    );
    final mtsp = Map<String, dynamic>.from(
      json['mtsp_reference'] as Map? ?? const {},
    );
    return DiscoveryProperty(
      id: json['property_id']?.toString() ?? '',
      name: json['property_name']?.toString() ?? 'Unnamed property',
      state: json['state']?.toString() ?? '',
      address: json['address']?.toString(),
      city: json['city']?.toString(),
      zipCode: json['zip_code']?.toString(),
      totalUnits: (json['total_units'] as num?)?.toInt(),
      lowIncomeUnits: (json['low_income_units'] as num?)?.toInt(),
      distanceMiles: (json['distance_miles'] as num?)?.toDouble(),
      fmrAmount: (fmr['amount'] as num?)?.toDouble(),
      mtspLimit: (mtsp['income_limit'] as num?)?.toDouble(),
    );
  }
}

class DiscoveryResponse {
  const DiscoveryResponse({
    required this.properties,
    required this.disclaimer,
    required this.resultCount,
  });
  final List<DiscoveryProperty> properties;
  final String disclaimer;
  final int resultCount;
}

class DiscoveryRepository {
  DiscoveryRepository(String baseUrl)
    : _dio = Dio(BaseOptions(baseUrl: baseUrl));
  final Dio _dio;

  Future<DiscoveryResponse> search({
    required String state,
    String? city,
    int? bedrooms,
    int? householdSize,
  }) async {
    try {
      final query = <String, dynamic>{
        'state': state.trim().toUpperCase(),
        if (city != null && city.trim().isNotEmpty) 'city': city.trim(),
        'sort_by': 'alphabetical',
      };
      if (bedrooms != null) {
        query['bedrooms'] = bedrooms;
      }
      if (householdSize != null) {
        query['household_size'] = householdSize;
      }
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/discovery/properties',
        queryParameters: query,
      );
      final body = response.data ?? const <String, dynamic>{};
      return DiscoveryResponse(
        resultCount: (body['result_count'] as num?)?.toInt() ?? 0,
        disclaimer: body['disclaimer']?.toString() ?? '',
        properties: (body['properties'] as List? ?? const [])
            .whereType<Map>()
            .map(
              (item) =>
                  DiscoveryProperty.fromJson(Map<String, dynamic>.from(item)),
            )
            .toList(),
      );
    } on DioException catch (error) {
      final detail = error.response?.data is Map
          ? (error.response!.data as Map)['detail']?.toString()
          : null;
      throw StateError(detail ?? 'Could not retrieve public property results.');
    }
  }
}
