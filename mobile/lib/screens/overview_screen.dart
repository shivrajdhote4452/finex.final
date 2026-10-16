import 'package:flutter/material.dart';
import '../theme/terminal_theme.dart';

class MobileOverviewScreen extends StatelessWidget {
  const MobileOverviewScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Brand & Greeting
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "FinEx.",
                  style: TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w900,
                    letterSpacing: -0.5,
                    color: TerminalColors.textMain,
                  ),
                ),
                Text(
                  "Good afternoon, Shivraj",
                  style: TextStyle(fontSize: 12, color: TerminalColors.textMuted),
                ),
              ],
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: TerminalColors.action,
                borderRadius: BorderRadius.circular(4),
              ),
              child: const Text(
                "+ Trade",
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Colors.black),
              ),
            ),
          ],
        ),
        const SizedBox(height: 20),

        // Portfolio Total Value Card (From Page 7 Screen 04)
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: TerminalColors.surface,
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: TerminalColors.borderSubtle),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    "VIRTUAL PORTFOLIO / INR",
                    style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.textMuted),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: TerminalColors.positiveBg,
                      borderRadius: BorderRadius.circular(3),
                    ),
                    child: const Text(
                      "Reconciled",
                      style: TextStyle(fontSize: 10, fontFamily: 'monospace', color: TerminalColors.positive, fontWeight: FontWeight.w600),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              const Text(
                "₹ 1,24,500",
                style: TextStyle(fontSize: 32, fontWeight: FontWeight.w800, fontFamily: 'monospace', color: TerminalColors.textMain),
              ),
              const SizedBox(height: 6),
              const Row(
                children: [
                  Text(
                    "+ ₹ 5,500",
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, fontFamily: 'monospace', color: TerminalColors.positive),
                  ),
                  SizedBox(width: 6),
                  Text("unrealized P&L", style: TextStyle(fontSize: 12, color: TerminalColors.textMuted)),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),

        // Split Metrics Row (Holdings & Virtual Cash)
        Row(
          children: [
            Expanded(
              child: Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: TerminalColors.surface,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: TerminalColors.borderSubtle),
                ),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text("HOLDINGS", style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: TerminalColors.textMuted)),
                    SizedBox(height: 6),
                    Text("₹ 99,500", style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, fontFamily: 'monospace', color: TerminalColors.textMain)),
                    SizedBox(height: 4),
                    Text("4 Positions (80%)", style: TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: TerminalColors.surface,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: TerminalColors.borderSubtle),
                ),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text("VIRTUAL CASH", style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: TerminalColors.action)),
                    SizedBox(height: 6),
                    Text("₹ 25,000", style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, fontFamily: 'monospace', color: TerminalColors.action)),
                    SizedBox(height: 4),
                    Text("Deployable (20%)", style: TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
                  ],
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),

        // Portfolio Concentration Insight (From Page 7)
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: TerminalColors.panel,
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: TerminalColors.borderSubtle),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: TerminalColors.actionBg,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: const Text("36.2%", style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: TerminalColors.action)),
              ),
              const SizedBox(width: 12),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text("TCS share of invested holdings.", style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: TerminalColors.textMain)),
                    Text("Cash excluded. Concentration insight.", style: TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
                  ],
                ),
              ),
              const Icon(Icons.arrow_forward_ios, size: 12, color: TerminalColors.textMuted),
            ],
          ),
        ),
        const SizedBox(height: 20),

        // Active Watchlist / Holdings Quick List
        const Text(
          "PORTFOLIO HOLDINGS",
          style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.textMuted),
        ),
        const SizedBox(height: 10),
        _buildHoldingTile("TCS", "Tata Consultancy", "₹ 36,000", "+ ₹ 1,500", true),
        _buildHoldingTile("RELIANCE", "Reliance Industries", "₹ 25,000", "+ ₹ 2,000", true),
        _buildHoldingTile("HDFCBANK", "HDFC Bank", "₹ 24,000", "+ ₹ 1,000", true),
        _buildHoldingTile("INFY", "Infosys Ltd", "₹ 14,500", "+ ₹ 1,000", true),
      ],
    );
  }

  Widget _buildHoldingTile(String symbol, String name, String value, String pnl, bool isPositive) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: TerminalColors.surface,
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: TerminalColors.borderSubtle),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(symbol, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
              Text(name, style: const TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
            ],
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(value, style: const TextStyle(fontSize: 13, fontFamily: 'monospace', fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
              Text(pnl, style: TextStyle(fontSize: 11, fontFamily: 'monospace', fontWeight: FontWeight.w600, color: isPositive ? TerminalColors.positive : TerminalColors.negative)),
            ],
          ),
        ],
      ),
    );
  }
}
