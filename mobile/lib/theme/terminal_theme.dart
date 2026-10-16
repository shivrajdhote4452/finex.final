import 'package:flutter/material.dart';

/// FinEx Graphite Terminal Design System (Pure Black Edition)
/// Derived from FinEx Graphite Terminal Full Frontend Guide
/// Canvas: Pure Black (#000000) with Warm Amber Action (#F29A60)
class TerminalColors {
  // Pure Black Canvas and Neutral Dark Surfaces (Zero Green Tint)
  static const Color canvas = Color(0xFF000000);
  static const Color surface = Color(0xFF111111);
  static const Color surfaceHover = Color(0xFF181818);
  static const Color panel = Color(0xFF161616);
  static const Color input = Color(0xFF0A0A0A);

  // Borders & Dividers
  static const Color borderSubtle = Color(0xFF222222);
  static const Color borderMedium = Color(0xFF2E2E2E);
  static const Color borderActive = Color(0xFFF29A60);

  // Graphite Terminal Semantic Accents
  static const Color action = Color(0xFFF29A60); // Warm Graphite Amber / Orange
  static const Color actionHover = Color(0xFFE0854B);
  static const Color actionBg = Color(0x1FF29A60);

  static const Color positive = Color(0xFF4DD5AD); // Mint Green
  static const Color positiveBg = Color(0x1F4DD5AD);

  static const Color negative = Color(0xFFF48C7B); // Salmon / Coral Red
  static const Color negativeBg = Color(0x1FF48C7B);

  static const Color textMain = Color(0xFFFFFFFF);
  static const Color textPrimary = Color(0xFFF4F4F5);
  static const Color textMuted = Color(0xFF8E8E93);
  static const Color textFaint = Color(0xFF52525B);
}

class TerminalTheme {
  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: TerminalColors.canvas,
      primaryColor: TerminalColors.action,
      cardColor: TerminalColors.surface,
      dividerColor: TerminalColors.borderSubtle,
      colorScheme: const ColorScheme.dark(
        primary: TerminalColors.action,
        secondary: TerminalColors.positive,
        surface: TerminalColors.surface,
        error: TerminalColors.negative,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: TerminalColors.canvas,
        elevation: 0,
        scrolledUnderElevation: 0,
        titleTextStyle: TextStyle(
          color: TerminalColors.textMain,
          fontSize: 16,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.2,
        ),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: TerminalColors.surface,
        selectedItemColor: TerminalColors.action,
        unselectedItemColor: TerminalColors.textMuted,
        type: BottomNavigationBarType.fixed,
        elevation: 8,
        selectedLabelStyle: TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
        unselectedLabelStyle: TextStyle(fontSize: 11, fontWeight: FontWeight.w500),
      ),
    );
  }
}
