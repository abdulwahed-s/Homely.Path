import 'package:flutter/widgets.dart';

import 'app/bootstrap.dart';
import 'app/app.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final dependencies = await bootstrap();
  runApp(HomelyPathApp(dependencies: dependencies));
}
