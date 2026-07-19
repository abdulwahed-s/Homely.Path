class RulesChatContext {
  const RulesChatContext({this.subjectId, this.subjectType});
  final String? subjectId;
  final String? subjectType;
}

abstract interface class RulesChatRepository {
  Future<void> ask({required String question, RulesChatContext? context});
}
