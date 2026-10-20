import 'package:flutter/material.dart';

class AppTheme {
  static const Color black = Color(0xFF09090B); // Zinc 950
  static const Color white = Color(0xFFFFFFFF);
  static const Color gray = Color(0xFF71717A); // Zinc 500
  static const Color border = Color(0xFFE4E4E7); // Zinc 200
  static const Color background = Color(0xFFFAFAFA); // Zinc 50
  static const Color accent = Color(0xFF059669); // Emerald 600 (SellFlow brand)
  static const Color error = Color(0xFFDC2626); // Red 600

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: false,
      scaffoldBackgroundColor: background,
      colorScheme: const ColorScheme.light(primary: accent, surface: white, error: error),
      appBarTheme: const AppBarTheme(
        backgroundColor: background,
        elevation: 0,
        iconTheme: IconThemeData(color: black),
        titleTextStyle: TextStyle(color: black, fontSize: 16, fontWeight: FontWeight.w600, letterSpacing: -0.5),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: false,
        contentPadding: const EdgeInsets.symmetric(vertical: 12, horizontal: 0),
        border: const UnderlineInputBorder(borderSide: BorderSide(color: border, width: 1)),
        enabledBorder: const UnderlineInputBorder(borderSide: BorderSide(color: border, width: 1)),
        focusedBorder: const UnderlineInputBorder(borderSide: BorderSide(color: black, width: 1.5)),
        errorBorder: const UnderlineInputBorder(borderSide: BorderSide(color: error, width: 1)),
        labelStyle: const TextStyle(color: gray, fontSize: 11, fontWeight: FontWeight.w600, letterSpacing: 0.5),
        hintStyle: const TextStyle(color: gray, fontSize: 14),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: black,
          foregroundColor: white,
          elevation: 0,
          minimumSize: const Size(double.infinity, 48),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
          textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, letterSpacing: 0.2),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: gray,
          textStyle: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
        ),
      ),
    );
  }
}
