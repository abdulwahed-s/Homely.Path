enum PacketTemplate { forMe, forCaseworker }

enum PacketSection {
  confirmedProfile,
  incomeSummary,
  documentIndex,
  ruleReferences,
  calculationWorksheet,
  missingReviewSummary,
  activityReplay,
}

class PacketConfiguration {
  const PacketConfiguration({required this.template, required this.sections});
  final PacketTemplate template;
  final List<PacketSection> sections;
  factory PacketConfiguration.initial() => const PacketConfiguration(
    template: PacketTemplate.forMe,
    sections: PacketSection.values,
  );
  PacketConfiguration copyWith({
    PacketTemplate? template,
    List<PacketSection>? sections,
  }) => PacketConfiguration(
    template: template ?? this.template,
    sections: sections ?? this.sections,
  );
}
