import 'package:flutter/material.dart';

/// FinEx Graphite Terminal Design System (Dual Light/Dark Edition)
/// Canvas: Pure Black (#000000) for Dark Mode, Clean Daylight (#F8F9FA) for Light Mode.
class TerminalColors {
  // Pure Black Canvas and Neutral Dark Surfaces
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

  // Dynamic Theme-Aware Color Resolvers
  static bool isDark(BuildContext context) {
    return Theme.of(context).brightness == Brightness.dark;
  }

  static Color getCanvas(BuildContext context) =>
      isDark(context) ? canvas : LightColors.canvas;

  static Color getSurface(BuildContext context) =>
      isDark(context) ? surface : LightColors.surface;

  static Color getSurfaceHover(BuildContext context) =>
      isDark(context) ? surfaceHover : LightColors.surfaceHover;

  static Color getBorderSubtle(BuildContext context) =>
      isDark(context) ? borderSubtle : LightColors.borderSubtle;

  static Color getBorderMedium(BuildContext context) =>
      isDark(context) ? borderMedium : LightColors.borderMedium;

  static Color getAction(BuildContext context) =>
      isDark(context) ? action : LightColors.action;

  static Color getTextMain(BuildContext context) =>
      isDark(context) ? textMain : LightColors.textMain;

  static Color getTextPrimary(BuildContext context) =>
      isDark(context) ? textPrimary : LightColors.textPrimary;

  static Color getTextMuted(BuildContext context) =>
      isDark(context) ? textMuted : LightColors.textMuted;
}

class LightColors {
  static const Color canvas = Color(0xFFF8F9FA);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color surfaceHover = Color(0xFFF1F3F5);
  static const Color panel = Color(0xFFF1F3F5);
  static const Color input = Color(0xFFFFFFFF);

  // Borders & Dividers
  static const Color borderSubtle = Color(0xFFE2E8F0);
  static const Color borderMedium = Color(0xFFCBD5E1);
  static const Color borderActive = Color(0xFFD96B27);

  // Semantic Accents
  static const Color action = Color(0xFFD96B27);
  static const Color actionHover = Color(0xFFBF5617);
  static const Color actionBg = Color(0x1FD96B27);

  static const Color positive = Color(0xFF059669);
  static const Color positiveBg = Color(0x1F059669);

  static const Color negative = Color(0xFFDC2626);
  static const Color negativeBg = Color(0x1FDC2626);

  static const Color textMain = Color(0xFF0F172A);
  static const Color textPrimary = Color(0xFF1E293B);
  static const Color textMuted = Color(0xFF64748B);
  static const Color textFaint = Color(0xFF94A3B8);
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

  static ThemeData get lightTheme {
    return ThemeData(
      brightness: Brightness.light,
      scaffoldBackgroundColor: LightColors.canvas,
      primaryColor: LightColors.action,
      cardColor: LightColors.surface,
      dividerColor: LightColors.borderSubtle,
      colorScheme: const ColorScheme.light(
        primary: LightColors.action,
        secondary: LightColors.positive,
        surface: LightColors.surface,
        error: LightColors.negative,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: LightColors.surface,
        elevation: 0,
        scrolledUnderElevation: 0,
        iconTheme: IconThemeData(color: LightColors.textMain),
        titleTextStyle: TextStyle(
          color: LightColors.textMain,
          fontSize: 16,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.2,
        ),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: LightColors.surface,
        selectedItemColor: LightColors.action,
        unselectedItemColor: LightColors.textMuted,
        type: BottomNavigationBarType.fixed,
        elevation: 8,
        selectedLabelStyle: TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
        unselectedLabelStyle: TextStyle(fontSize: 11, fontWeight: FontWeight.w500),
      ),
    );
  }
}
