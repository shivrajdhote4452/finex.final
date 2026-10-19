import 'package:flutter/material.dart';
import '../theme/terminal_theme.dart';
import 'chart_screen.dart';
import 'paper_trading_screen.dart';
import 'portfolio_screen.dart';
import 'transactions_screen.dart';
import 'alerts_screen.dart';
import 'goals_screen.dart';
import 'spending_screen.dart';
import 'settings_screen.dart';

class MobileMoreScreen extends StatelessWidget {
  final VoidCallback? onLogout;

  const MobileMoreScreen({super.key, this.onLogout});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // User Profile Header
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: TerminalColors.surface,
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: TerminalColors.borderSubtle),
          ),
          child: Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: TerminalColors.action,
                  borderRadius: BorderRadius.circular(4),
                ),
                alignment: Alignment.center,
                child: const Text(
                  "SD",
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: Colors.black),
                ),
              ),
              const SizedBox(width: 14),
              const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text("Shivraj Dhote", style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
                  SizedBox(height: 2),
                  Text("Personal Workspace · Pure Black Edition", style: TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),

        const Text(
          "WORKSPACE MODULES",
          style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.textMuted),
        ),
        const SizedBox(height: 10),

        _buildModuleItem(
          icon: Icons.pie_chart_outline,
          title: "Portfolio & Asset Allocation",
          subtitle: "Holdings distribution, rebalance simulator & valuation",
          badge: "Equities",
          badgeColor: TerminalColors.positive,
          onTap: () {
            Navigator.push(
              context,
              MaterialPageRoute(builder: (context) => const MobilePortfolioScreen()),
            );
          },
        ),
        _buildModuleItem(
          icon: Icons.show_chart,
          title: "TradingView Chart Workspace",
          subtitle: "Interactive candlesticks, technical indicators & paper orders",
          badge: "Charts",
          badgeColor: TerminalColors.action,
          onTap: () {
            Navigator.push(
              context,
              MaterialPageRoute(builder: (context) => const MobileChartScreen()),
            );
          },
        ),
        _buildModuleItem(
          icon: Icons.candlestick_chart_outlined,
          title: "Paper Trading: Order Ticket",
          subtitle: "Simulated Level-2 execution & virtual ledger",
          badge: "Virtual Only",
          badgeColor: TerminalColors.action,
          onTap: () {
            Navigator.push(
              context,
              MaterialPageRoute(builder: (context) => const MobilePaperTradingScreen()),
            );
          },
        ),
        _buildModuleItem(
          icon: Icons.receipt_long_outlined,
          title: "Order Activity & Cash Ledger",
          subtitle: "Audit trail, trade receipts, contract notes & statements",
          badge: "Atomic Ledger",
          badgeColor: TerminalColors.positive,
          onTap: () {
            Navigator.push(
              context,
              MaterialPageRoute(builder: (context) => const MobileTransactionsScreen()),
            );
          },
        ),
        _buildModuleItem(
          icon: Icons.notifications_none_outlined,
          title: "Alerts & Notifications",
          subtitle: "Price thresholds, triggers & market alerts",
          onTap: () {
            Navigator.push(
              context,
              MaterialPageRoute(builder: (context) => const MobileAlertsScreen()),
            );
          },
        ),
        _buildModuleItem(
          icon: Icons.flag_outlined,
          title: "Financial Goals",
          subtitle: "Targets, contribution scenarios & projections",
          onTap: () {
            Navigator.push(
              context,
              MaterialPageRoute(builder: (context) => const MobileGoalsScreen()),
            );
          },
        ),
        _buildModuleItem(
          icon: Icons.account_balance_wallet_outlined,
          title: "Spending Analytics",
          subtitle: "Category breakdown & CSV import preview",
          onTap: () {
            Navigator.push(
              context,
              MaterialPageRoute(builder: (context) => const MobileSpendingScreen()),
            );
          },
        ),
        _buildModuleItem(
          icon: Icons.settings_outlined,
          title: "Settings & Risk Profile",
          subtitle: "Account, sandbox reset, consent & disclosures",
          badge: "Admin",
          badgeColor: const Color(0xFF60A5FA),
          onTap: () {
            Navigator.push(
              context,
              MaterialPageRoute(builder: (context) => MobileSettingsScreen(onLogout: onLogout)),
            );
          },
        ),
        _buildModuleItem(
          icon: Icons.logout,
          title: "Sign Out",
          subtitle: "Revoke session token and return to authentication",
          onTap: () {
            if (onLogout != null) {
              onLogout!();
            }
          },
        ),

        const SizedBox(height: 20),

        // Legal Educational Notice (Per Page 3 & Page 15)
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: TerminalColors.panel,
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: TerminalColors.borderSubtle),
          ),
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                "Virtual Trading Disclaimer",
                style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: TerminalColors.action),
              ),
              SizedBox(height: 4),
              Text(
                "FinEx is an educational platform. All orders are executed in a simulated sandbox with atomic virtual ledger balances. No real-money brokerage orders are submitted.",
                style: TextStyle(fontSize: 11, height: 1.4, color: TerminalColors.textMuted),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildModuleItem({
    required IconData icon,
    required String title,
    required String subtitle,
    String? badge,
    Color? badgeColor,
    VoidCallback? onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: TerminalColors.surface,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: TerminalColors.borderSubtle),
        ),
        child: Row(
        children: [
          Icon(icon, size: 20, color: TerminalColors.action),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: TerminalColors.textMain)),
                    if (badge != null) ...[
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                        decoration: BoxDecoration(
                          color: badgeColor != null ? badgeColor.withValues(alpha: 0.15) : const Color(0x26F29A60),
                          borderRadius: BorderRadius.circular(2),
                        ),
                        child: Text(
                          badge,
                          style: TextStyle(fontSize: 9, fontFamily: 'monospace', fontWeight: FontWeight.w700, color: badgeColor ?? TerminalColors.action),
                        ),
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 2),
                Text(subtitle, style: const TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
              ],
            ),
          ),
          const Icon(Icons.arrow_forward_ios, size: 12, color: TerminalColors.textMuted),
        ],
      ),
    ),
  );
}
}
