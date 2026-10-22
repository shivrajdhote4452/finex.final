import 'package:flutter/material.dart';
import '../theme/terminal_theme.dart';
import '../theme/theme_controller.dart';

class MobileThemeSegmentedToggle extends StatelessWidget {
  const MobileThemeSegmentedToggle({super.key});

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: themeController,
      builder: (context, _) {
        final current = themeController.themeMode;
        final isDark = TerminalColors.isDark(context);

        return Container(
          padding: const EdgeInsets.all(3),
          decoration: BoxDecoration(
            color: isDark ? const Color(0xFF0A0A0A) : const Color(0xFFE9ECEF),
            borderRadius: BorderRadius.circular(6),
            border: Border.all(
              color: isDark ? TerminalColors.borderSubtle : LightColors.borderSubtle,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              _buildPill(
                context: context,
                label: "System",
                icon: Icons.computer_outlined,
                isSelected: current == ThemeMode.system,
                onTap: () => themeController.setThemeMode(ThemeMode.system),
              ),
              const SizedBox(width: 2),
              _buildPill(
                context: context,
                label: "Light",
                icon: Icons.wb_sunny_outlined,
                isSelected: current == ThemeMode.light,
                onTap: () => themeController.setThemeMode(ThemeMode.light),
              ),
              const SizedBox(width: 2),
              _buildPill(
                context: context,
                label: "Dark",
                icon: Icons.nightlight_round_outlined,
                isSelected: current == ThemeMode.dark,
                onTap: () => themeController.setThemeMode(ThemeMode.dark),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildPill({
    required BuildContext context,
    required String label,
    required IconData icon,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    final isDark = TerminalColors.isDark(context);
    final actionColor = isDark ? TerminalColors.action : LightColors.action;

    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? (isDark ? const Color(0x28F29A60) : const Color(0x28D96B27)) : Colors.transparent,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(
            color: isSelected ? actionColor : Colors.transparent,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 13,
              color: isSelected ? actionColor : (isDark ? TerminalColors.textMuted : LightColors.textMuted),
            ),
            const SizedBox(width: 4),
            Text(
              label,
              style: TextStyle(
                fontSize: 11,
                fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                color: isSelected ? actionColor : (isDark ? TerminalColors.textMuted : LightColors.textMuted),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class MobileThemeSelectionCards extends StatelessWidget {
  const MobileThemeSelectionCards({super.key});

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: themeController,
      builder: (context, _) {
        final current = themeController.themeMode;

        return Column(
          children: [
            _buildThemeCard(
              context: context,
              mode: ThemeMode.system,
              title: "System Default",
              icon: Icons.computer_outlined,
              description: "Automatically matches your device or computer operating system schedule.",
              isSelected: current == ThemeMode.system,
              onTap: () => themeController.setThemeMode(ThemeMode.system),
            ),
            const SizedBox(height: 10),
            _buildThemeCard(
              context: context,
              mode: ThemeMode.light,
              title: "Light Mode",
              icon: Icons.wb_sunny_outlined,
              description: "High-contrast daylight theme with clean white surfaces and warm amber accents.",
              isSelected: current == ThemeMode.light,
              onTap: () => themeController.setThemeMode(ThemeMode.light),
            ),
            const SizedBox(height: 10),
            _buildThemeCard(
              context: context,
              mode: ThemeMode.dark,
              title: "Dark Mode",
              icon: Icons.nightlight_round_outlined,
              description: "Pure black OLED terminal palette, easy on eyes in lower lighting.",
              isSelected: current == ThemeMode.dark,
              onTap: () => themeController.setThemeMode(ThemeMode.dark),
            ),
          ],
        );
      },
    );
  }

  Widget _buildThemeCard({
    required BuildContext context,
    required ThemeMode mode,
    required String title,
    required IconData icon,
    required String description,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    final isDark = TerminalColors.isDark(context);
    final actionColor = isDark ? TerminalColors.action : LightColors.action;
    final surfaceColor = isDark ? TerminalColors.surface : LightColors.surface;
    final borderColor = isSelected
        ? actionColor
        : (isDark ? TerminalColors.borderSubtle : LightColors.borderSubtle);
    final textColor = isDark ? TerminalColors.textMain : LightColors.textMain;
    final textMuted = isDark ? TerminalColors.textMuted : LightColors.textMuted;

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: isSelected
              ? (isDark ? const Color(0x1EF29A60) : const Color(0x18D96B27))
              : surfaceColor,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: borderColor, width: isSelected ? 1.5 : 1.0),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: isSelected ? actionColor.withValues(alpha: 0.2) : borderColor.withValues(alpha: 0.3),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Icon(icon, size: 20, color: isSelected ? actionColor : textMuted),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        title,
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                          color: textColor,
                        ),
                      ),
                      Container(
                        width: 18,
                        height: 18,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: isSelected ? actionColor : textMuted,
                            width: isSelected ? 5.0 : 1.5,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    description,
                    style: TextStyle(fontSize: 11, color: textMuted, height: 1.3),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
