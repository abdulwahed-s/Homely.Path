import 'package:flutter/material.dart';

const appInk = Color(0xff173e52);
const appTeal = Color(0xff2d728f);
const appMint = Color(0xffaedcc0);
const appCanvas = Color(0xfff8f8fa);
const appLine = Color(0xffa9dec2);

final appTheme = ThemeData(
  useMaterial3: true,
  fontFamily: 'Plus Jakarta Sans',
  scaffoldBackgroundColor: appCanvas,
  colorScheme:
      ColorScheme.fromSeed(
        seedColor: appTeal,
        brightness: Brightness.light,
      ).copyWith(
        primary: appTeal,
        secondary: appMint,
        surface: Colors.white,
        onSurface: appInk,
        outline: appLine,
      ),
  textTheme: const TextTheme(
    displaySmall: TextStyle(
      fontSize: 38,
      height: 1.18,
      fontWeight: FontWeight.w700,
      color: appInk,
    ),
    headlineMedium: TextStyle(
      fontSize: 28,
      height: 1.25,
      fontWeight: FontWeight.w700,
      color: appInk,
    ),
    headlineSmall: TextStyle(
      fontSize: 24,
      fontWeight: FontWeight.w700,
      color: appInk,
    ),
    titleLarge: TextStyle(
      fontSize: 20,
      fontWeight: FontWeight.w700,
      color: appInk,
    ),
    titleMedium: TextStyle(
      fontSize: 16,
      fontWeight: FontWeight.w600,
      color: appInk,
    ),
    bodyLarge: TextStyle(fontSize: 16, height: 1.5, color: appInk),
    bodyMedium: TextStyle(fontSize: 14, height: 1.45, color: appTeal),
    labelLarge: TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
  ),
  cardTheme: const CardThemeData(
    color: Colors.white,
    elevation: 0,
    margin: EdgeInsets.zero,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.all(Radius.circular(10)),
      side: BorderSide(color: appLine),
    ),
  ),
  elevatedButtonTheme: ElevatedButtonThemeData(
    style: ElevatedButton.styleFrom(
      backgroundColor: appTeal,
      foregroundColor: Colors.white,
      elevation: 0,
      minimumSize: const Size(0, 48),
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
    ),
  ),
  outlinedButtonTheme: OutlinedButtonThemeData(
    style: OutlinedButton.styleFrom(
      foregroundColor: appTeal,
      minimumSize: const Size(0, 48),
      side: const BorderSide(color: appTeal),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
    ),
  ),
  filledButtonTheme: FilledButtonThemeData(
    style: FilledButton.styleFrom(
      backgroundColor: appTeal,
      foregroundColor: Colors.white,
      minimumSize: const Size(0, 48),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
    ),
  ),
  inputDecorationTheme: InputDecorationTheme(
    filled: true,
    fillColor: Colors.white,
    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(8),
      borderSide: const BorderSide(color: appLine),
    ),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(8),
      borderSide: const BorderSide(color: appLine),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(8),
      borderSide: const BorderSide(color: appTeal, width: 2),
    ),
  ),
  chipTheme: const ChipThemeData(backgroundColor: appMint),
);
