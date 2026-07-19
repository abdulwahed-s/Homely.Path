import '../../../infrastructure/ai_backend/extraction_dto.dart';

class LocalConflict {
  const LocalConflict({
    required this.conflict,
    this.resolution,
    this.resolutionReason,
  });
  final ConflictDto conflict;
  final Object? resolution;
  final String? resolutionReason;
  bool get isBlocking => conflict.severity == 'blocking_for_confirmation';
  bool get isResolved => resolution != null;
  LocalConflict copyWith({Object? resolution, String? resolutionReason}) =>
      LocalConflict(
        conflict: conflict,
        resolution: resolution ?? this.resolution,
        resolutionReason: resolutionReason ?? this.resolutionReason,
      );
  Map<String, dynamic> toJson() => {
    'conflict': conflict.toJson(),
    'resolution': resolution,
    'resolutionReason': resolutionReason,
  };
  factory LocalConflict.fromJson(Map<String, dynamic> json) => LocalConflict(
    conflict: ConflictDto.fromJson(
      Map<String, dynamic>.from(json['conflict'] as Map),
    ),
    resolution: json['resolution'],
    resolutionReason: json['resolutionReason'] as String?,
  );
}
