import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_ar.dart';
import 'app_localizations_en.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('ar'),
    Locale('en'),
  ];

  /// No description provided for @appTitle.
  ///
  /// In en, this message translates to:
  /// **'HomelyPath'**
  String get appTitle;

  /// No description provided for @startAnonymousSession.
  ///
  /// In en, this message translates to:
  /// **'Start anonymous session'**
  String get startAnonymousSession;

  /// No description provided for @howItWorks.
  ///
  /// In en, this message translates to:
  /// **'How it works'**
  String get howItWorks;

  /// No description provided for @landingTitle.
  ///
  /// In en, this message translates to:
  /// **'Prepare a renter-controlled review packet.'**
  String get landingTitle;

  /// No description provided for @landingBody.
  ///
  /// In en, this message translates to:
  /// **'Understand your documents, verify information, and prepare a packet you control.'**
  String get landingBody;

  /// No description provided for @understandDocuments.
  ///
  /// In en, this message translates to:
  /// **'Understand documents'**
  String get understandDocuments;

  /// No description provided for @verifyInformation.
  ///
  /// In en, this message translates to:
  /// **'Verify information'**
  String get verifyInformation;

  /// No description provided for @preparePacket.
  ///
  /// In en, this message translates to:
  /// **'Prepare a review packet'**
  String get preparePacket;

  /// No description provided for @privacyTitle.
  ///
  /// In en, this message translates to:
  /// **'Private by design'**
  String get privacyTitle;

  /// No description provided for @privacyBody.
  ///
  /// In en, this message translates to:
  /// **'Your application data stays on this device. Firebase is used only for an anonymous session identity.'**
  String get privacyBody;

  /// No description provided for @disclaimer.
  ///
  /// In en, this message translates to:
  /// **'This tool did not approve, deny, score, or rank you.'**
  String get disclaimer;

  /// No description provided for @profile.
  ///
  /// In en, this message translates to:
  /// **'Profile'**
  String get profile;

  /// No description provided for @understand.
  ///
  /// In en, this message translates to:
  /// **'Understand'**
  String get understand;

  /// No description provided for @prepare.
  ///
  /// In en, this message translates to:
  /// **'Prepare'**
  String get prepare;

  /// No description provided for @consentTitle.
  ///
  /// In en, this message translates to:
  /// **'Before you upload'**
  String get consentTitle;

  /// No description provided for @consentBody.
  ///
  /// In en, this message translates to:
  /// **'HomelyPath extracts document fields to help you review them. Important fields always need your confirmation. Uploads are not used for training.'**
  String get consentBody;

  /// No description provided for @consentRetention.
  ///
  /// In en, this message translates to:
  /// **'Your session is temporary and can be deleted at any time.'**
  String get consentRetention;

  /// No description provided for @consentCheck.
  ///
  /// In en, this message translates to:
  /// **'I understand and agree to this temporary, local session.'**
  String get consentCheck;

  /// No description provided for @continueLabel.
  ///
  /// In en, this message translates to:
  /// **'Continue'**
  String get continueLabel;

  /// No description provided for @sessionExpires.
  ///
  /// In en, this message translates to:
  /// **'Session expires'**
  String get sessionExpires;

  /// No description provided for @overview.
  ///
  /// In en, this message translates to:
  /// **'Overview'**
  String get overview;

  /// No description provided for @documents.
  ///
  /// In en, this message translates to:
  /// **'Documents'**
  String get documents;

  /// No description provided for @confirmedProfile.
  ///
  /// In en, this message translates to:
  /// **'Confirmed profile'**
  String get confirmedProfile;

  /// No description provided for @conflicts.
  ///
  /// In en, this message translates to:
  /// **'Conflicts'**
  String get conflicts;

  /// No description provided for @rules.
  ///
  /// In en, this message translates to:
  /// **'Rules assistant'**
  String get rules;

  /// No description provided for @calculations.
  ///
  /// In en, this message translates to:
  /// **'Calculations'**
  String get calculations;

  /// No description provided for @readiness.
  ///
  /// In en, this message translates to:
  /// **'Readiness'**
  String get readiness;

  /// No description provided for @packet.
  ///
  /// In en, this message translates to:
  /// **'Packet'**
  String get packet;

  /// No description provided for @uploadDocuments.
  ///
  /// In en, this message translates to:
  /// **'Upload documents'**
  String get uploadDocuments;

  /// No description provided for @uploadHint.
  ///
  /// In en, this message translates to:
  /// **'PDF files only. You can add supported documents one at a time.'**
  String get uploadHint;

  /// No description provided for @choosePdf.
  ///
  /// In en, this message translates to:
  /// **'Choose PDF'**
  String get choosePdf;

  /// No description provided for @aiUnavailable.
  ///
  /// In en, this message translates to:
  /// **'AI backend is not configured.'**
  String get aiUnavailable;

  /// No description provided for @deleteSession.
  ///
  /// In en, this message translates to:
  /// **'Delete entire session'**
  String get deleteSession;

  /// No description provided for @exportSession.
  ///
  /// In en, this message translates to:
  /// **'Export session data'**
  String get exportSession;

  /// No description provided for @language.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get language;

  /// No description provided for @english.
  ///
  /// In en, this message translates to:
  /// **'English'**
  String get english;

  /// No description provided for @arabic.
  ///
  /// In en, this message translates to:
  /// **'Arabic'**
  String get arabic;

  /// No description provided for @actionRequired.
  ///
  /// In en, this message translates to:
  /// **'Action required'**
  String get actionRequired;

  /// No description provided for @readyToReview.
  ///
  /// In en, this message translates to:
  /// **'Ready to review'**
  String get readyToReview;

  /// No description provided for @needsReview.
  ///
  /// In en, this message translates to:
  /// **'Needs review'**
  String get needsReview;

  /// No description provided for @notUsedDownstream.
  ///
  /// In en, this message translates to:
  /// **'Not used in calculations or readiness'**
  String get notUsedDownstream;

  /// No description provided for @securityWarning.
  ///
  /// In en, this message translates to:
  /// **'Potential instruction in this document was ignored.'**
  String get securityWarning;

  /// No description provided for @confirm.
  ///
  /// In en, this message translates to:
  /// **'Confirm'**
  String get confirm;

  /// No description provided for @edit.
  ///
  /// In en, this message translates to:
  /// **'Edit'**
  String get edit;

  /// No description provided for @manualEntry.
  ///
  /// In en, this message translates to:
  /// **'Enter manually'**
  String get manualEntry;

  /// No description provided for @retry.
  ///
  /// In en, this message translates to:
  /// **'Retry'**
  String get retry;

  /// No description provided for @unknown.
  ///
  /// In en, this message translates to:
  /// **'Unknown'**
  String get unknown;

  /// No description provided for @belowOrEqual.
  ///
  /// In en, this message translates to:
  /// **'Below or equal to the frozen threshold'**
  String get belowOrEqual;

  /// No description provided for @aboveThreshold.
  ///
  /// In en, this message translates to:
  /// **'Above the frozen threshold'**
  String get aboveThreshold;

  /// No description provided for @noFrozenThreshold.
  ///
  /// In en, this message translates to:
  /// **'No frozen threshold is available for this household size'**
  String get noFrozenThreshold;

  /// No description provided for @activity.
  ///
  /// In en, this message translates to:
  /// **'Activity'**
  String get activity;

  /// No description provided for @forMe.
  ///
  /// In en, this message translates to:
  /// **'For me'**
  String get forMe;

  /// No description provided for @forCaseworker.
  ///
  /// In en, this message translates to:
  /// **'For my caseworker'**
  String get forCaseworker;

  /// No description provided for @exportPdf.
  ///
  /// In en, this message translates to:
  /// **'Export PDF'**
  String get exportPdf;

  /// No description provided for @exportZip.
  ///
  /// In en, this message translates to:
  /// **'Export ZIP'**
  String get exportZip;

  /// No description provided for @confirmedProfileSection.
  ///
  /// In en, this message translates to:
  /// **'Confirmed profile'**
  String get confirmedProfileSection;

  /// No description provided for @incomeSummarySection.
  ///
  /// In en, this message translates to:
  /// **'Income summary'**
  String get incomeSummarySection;

  /// No description provided for @documentIndexSection.
  ///
  /// In en, this message translates to:
  /// **'Document index'**
  String get documentIndexSection;

  /// No description provided for @ruleReferencesSection.
  ///
  /// In en, this message translates to:
  /// **'Rule references'**
  String get ruleReferencesSection;

  /// No description provided for @calculationWorksheetSection.
  ///
  /// In en, this message translates to:
  /// **'Calculation worksheet'**
  String get calculationWorksheetSection;

  /// No description provided for @missingReviewSection.
  ///
  /// In en, this message translates to:
  /// **'Missing/review summary'**
  String get missingReviewSection;

  /// No description provided for @activityReplaySection.
  ///
  /// In en, this message translates to:
  /// **'Activity replay'**
  String get activityReplaySection;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['ar', 'en'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'ar':
      return AppLocalizationsAr();
    case 'en':
      return AppLocalizationsEn();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
