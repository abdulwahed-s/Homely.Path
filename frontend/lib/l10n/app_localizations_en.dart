// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'HomelyPath';

  @override
  String get startAnonymousSession => 'Start anonymous session';

  @override
  String get howItWorks => 'How it works';

  @override
  String get landingTitle => 'Prepare a renter-controlled review packet.';

  @override
  String get landingBody =>
      'Understand your documents, verify information, and prepare a packet you control.';

  @override
  String get understandDocuments => 'Understand documents';

  @override
  String get verifyInformation => 'Verify information';

  @override
  String get preparePacket => 'Prepare a review packet';

  @override
  String get privacyTitle => 'Private by design';

  @override
  String get privacyBody =>
      'Your application data stays on this device. Firebase is used only for an anonymous session identity.';

  @override
  String get disclaimer =>
      'This tool did not approve, deny, score, or rank you.';

  @override
  String get profile => 'Profile';

  @override
  String get understand => 'Understand';

  @override
  String get prepare => 'Prepare';

  @override
  String get consentTitle => 'Before you upload';

  @override
  String get consentBody =>
      'HomelyPath extracts document fields to help you review them. Important fields always need your confirmation. Uploads are not used for training.';

  @override
  String get consentRetention =>
      'Your session is temporary and can be deleted at any time.';

  @override
  String get consentCheck =>
      'I understand and agree to this temporary, local session.';

  @override
  String get continueLabel => 'Continue';

  @override
  String get sessionExpires => 'Session expires';

  @override
  String get overview => 'Overview';

  @override
  String get documents => 'Documents';

  @override
  String get confirmedProfile => 'Confirmed profile';

  @override
  String get conflicts => 'Conflicts';

  @override
  String get rules => 'Rules assistant';

  @override
  String get calculations => 'Calculations';

  @override
  String get readiness => 'Readiness';

  @override
  String get packet => 'Packet';

  @override
  String get uploadDocuments => 'Upload documents';

  @override
  String get uploadHint =>
      'PDF files only. You can add supported documents one at a time.';

  @override
  String get choosePdf => 'Choose PDF';

  @override
  String get aiUnavailable => 'AI backend is not configured.';

  @override
  String get deleteSession => 'Delete entire session';

  @override
  String get exportSession => 'Export session data';

  @override
  String get language => 'Language';

  @override
  String get english => 'English';

  @override
  String get arabic => 'Arabic';

  @override
  String get actionRequired => 'Action required';

  @override
  String get readyToReview => 'Ready to review';

  @override
  String get needsReview => 'Needs review';

  @override
  String get notUsedDownstream => 'Not used in calculations or readiness';

  @override
  String get securityWarning =>
      'Potential instruction in this document was ignored.';

  @override
  String get confirm => 'Confirm';

  @override
  String get edit => 'Edit';

  @override
  String get manualEntry => 'Enter manually';

  @override
  String get retry => 'Retry';

  @override
  String get unknown => 'Unknown';

  @override
  String get belowOrEqual => 'Below or equal to the frozen threshold';

  @override
  String get aboveThreshold => 'Above the frozen threshold';

  @override
  String get noFrozenThreshold =>
      'No frozen threshold is available for this household size';

  @override
  String get activity => 'Activity';

  @override
  String get forMe => 'For me';

  @override
  String get forCaseworker => 'For my caseworker';

  @override
  String get exportPdf => 'Export PDF';

  @override
  String get exportZip => 'Export ZIP';

  @override
  String get confirmedProfileSection => 'Confirmed profile';

  @override
  String get incomeSummarySection => 'Income summary';

  @override
  String get documentIndexSection => 'Document index';

  @override
  String get ruleReferencesSection => 'Rule references';

  @override
  String get calculationWorksheetSection => 'Calculation worksheet';

  @override
  String get missingReviewSection => 'Missing/review summary';

  @override
  String get activityReplaySection => 'Activity replay';
}
