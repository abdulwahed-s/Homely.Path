import 'package:firebase_auth/firebase_auth.dart';

abstract interface class FirebaseTokenProvider {
  Future<String> freshIdToken();
  Future<String> activeUid();
}

class FirebaseAuthTokenProvider implements FirebaseTokenProvider {
  FirebaseAuthTokenProvider(this._auth);
  final FirebaseAuth _auth;
  @override
  Future<String> activeUid() async {
    final user = _auth.currentUser;
    if (user == null || !user.isAnonymous) {
      throw StateError('Anonymous Firebase authentication is unavailable.');
    }
    return user.uid;
  }

  @override
  Future<String> freshIdToken() async {
    final user = _auth.currentUser;
    final token = await user?.getIdToken(true);
    if (token == null || token.isEmpty) {
      throw StateError('A Firebase ID token is unavailable.');
    }
    return token;
  }
}
