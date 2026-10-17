import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../services/api_client.dart';
import '../theme/terminal_theme.dart';

class MobileOverviewScreen extends StatefulWidget {
  const MobileOverviewScreen({super.key});

  @override
  State<MobileOverviewScreen> createState() => _MobileOverviewScreenState();
}

class _MobileOverviewScreenState extends State<MobileOverviewScreen> {
  double _cashBalance = 100000.0;
  double _positionsMarketValue = 0.0;
  double _totalPortfolioValue = 100000.0;
  double _unrealizedPnl = 0.0;
  List<Map<String, dynamic>> _positions = [];
  bool _isLoading = false;

  final _currencyFmt = NumberFormat.currency(symbol: '₹ ', locale: 'en_IN', decimalDigits: 2);

  @override
  void initState() {
    super.initState();
    _loadAccountSummary();
  }

  Future<void> _loadAccountSummary() async {
    setState(() => _isLoading = true);
    try {
      final acct = await apiClient.getAccount();
      if (mounted) {
        final cash = (acct['cash_balance'] ?? acct['current_cash'] as num?)?.toDouble() ?? 100000.0;
        final mktVal = (acct['positions_market_value'] as num?)?.toDouble() ?? 0.0;
        final totalVal = (acct['total_portfolio_value'] ?? acct['total_equity'] as num?)?.toDouble() ?? (cash + mktVal);
        final pnl = (acct['unrealized_pnl'] as num?)?.toDouble() ?? 0.0;
        final posList = List<Map<String, dynamic>>.from(acct['positions'] ?? []);

        setState(() {
          _cashBalance = cash;
          _positionsMarketValue = mktVal;
          _totalPortfolioValue = totalVal;
          _unrealizedPnl = pnl;
          _positions = posList;
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      color: TerminalColors.action,
      backgroundColor: TerminalColors.surface,
      onRefresh: _loadAccountSummary,
      child: ListView(
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
                    "Personal Workspace · Reconciled",
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
                  "Virtual",
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Colors.black),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),

          // Portfolio Total Value Card
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
                      "TOTAL PORTFOLIO VALUE / INR",
                      style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.textMuted),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: TerminalColors.positiveBg,
                        borderRadius: BorderRadius.circular(3),
                      ),
                      child: Text(
                        _isLoading ? "Syncing..." : "Reconciled",
                        style: const TextStyle(fontSize: 10, fontFamily: 'monospace', color: TerminalColors.positive, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  _currencyFmt.format(_totalPortfolioValue),
                  style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w800, fontFamily: 'monospace', color: TerminalColors.textMain),
                ),
                const SizedBox(height: 6),
                Row(
                  children: [
                    Text(
                      "${_unrealizedPnl >= 0 ? '+' : ''}${_currencyFmt.format(_unrealizedPnl)}",
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        fontFamily: 'monospace',
                        color: _unrealizedPnl >= 0 ? TerminalColors.positive : TerminalColors.negative,
                      ),
                    ),
                    const SizedBox(width: 6),
                    const Text("unrealized P&L", style: TextStyle(fontSize: 12, color: TerminalColors.textMuted)),
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
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text("HOLDINGS", style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: TerminalColors.textMuted)),
                      const SizedBox(height: 6),
                      Text(
                        _currencyFmt.format(_positionsMarketValue),
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, fontFamily: 'monospace', color: TerminalColors.textMain),
                      ),
                      const SizedBox(height: 4),
                      Text("${_positions.length} Positions", style: const TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
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
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text("VIRTUAL CASH", style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: TerminalColors.action)),
                      const SizedBox(height: 6),
                      Text(
                        _currencyFmt.format(_cashBalance),
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, fontFamily: 'monospace', color: TerminalColors.action),
                      ),
                      const SizedBox(height: 4),
                      const Text("Deployable", style: TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),

          // Active Holdings List
          const Text(
            "PORTFOLIO HOLDINGS",
            style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.textMuted),
          ),
          const SizedBox(height: 10),
          if (_positions.isEmpty)
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: TerminalColors.surface,
                borderRadius: BorderRadius.circular(4),
                border: Border.all(color: TerminalColors.borderSubtle),
              ),
              alignment: Alignment.center,
              child: const Text(
                "No open positions. Use Paper Trading to execute simulated orders.",
                style: TextStyle(fontSize: 12, color: TerminalColors.textMuted),
                textAlign: TextAlign.center,
              ),
            )
          else
            ..._positions.map((p) {
              final sym = p['symbol'] ?? '';
              final qty = (p['quantity'] as num?)?.toDouble() ?? 0.0;
              final avgBuy = (p['average_buy_price'] ?? p['avg_cost'] as num?)?.toDouble() ?? 0.0;
              final curPrice = (p['current_price'] as num?)?.toDouble() ?? avgBuy;
              final mktVal = (p['market_value'] as num?)?.toDouble() ?? (qty * curPrice);
              final pnl = (p['unrealized_pnl'] as num?)?.toDouble() ?? 0.0;
              final isPos = pnl >= 0;

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
                        Text(sym, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
                        Text("$qty shares @ ₹${avgBuy.toStringAsFixed(2)}", style: const TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
                      ],
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text(_currencyFmt.format(mktVal), style: const TextStyle(fontSize: 13, fontFamily: 'monospace', fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
                        Text(
                          "${isPos ? '+' : ''}${_currencyFmt.format(pnl)}",
                          style: TextStyle(
                            fontSize: 11,
                            fontFamily: 'monospace',
                            fontWeight: FontWeight.w600,
                            color: isPos ? TerminalColors.positive : TerminalColors.negative,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              );
            }),
        ],
      ),
    );
  }
}
