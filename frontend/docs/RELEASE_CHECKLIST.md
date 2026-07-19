# Release checklist

## Verified locally

- `dart format lib test`
- `flutter analyze`
- `flutter test` (16 passing tests)
- `flutter build web --no-tree-shake-icons`

The application uses Firebase only for anonymous authentication/session identity. No Firestore, Firebase Storage, Realtime Database, or Cloud Functions client integration is present.

## Deployment prerequisites

Before enabling `AI_MODE=http`, the external AI service must verify the Firebase ID token and reject requests unless `session_id` exactly equals the token UID. Configure CORS for the deployed Flutter web origin. These requirements are based on the inspected backend contract in `BACKEND_CONTRACT_NOTES.md`.

## Packet font note

The generated packet uses the PDF package's built-in font. Add a licensed Arabic-capable TTF asset and configure it in `PacketExporter` before declaring Arabic PDF exports release-quality.
