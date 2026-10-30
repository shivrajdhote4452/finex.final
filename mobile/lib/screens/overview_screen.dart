import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../services/api_client.dart';
import '../theme/terminal_theme.dart';
import '../widgets/quick_trade_modal.dart';
import '../widgets/recent_transactions_feed.dart';
import '../widgets/skeleton_loader.dart';
import 'portfolio_screen.dart';
import 'transactions_screen.dart';
import 'ask_finex_screen.dart';
import 'chart_screen.dart';

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
  String _chartView = 'area'; // 'area' | 'candles'
  bool _quotesLoaded = false;
  bool _isMarketOpen = false;
  String _quotesFreshness = 'CONNECTING';

  // Top watched market instruments with default fallback quotes
  final List<Map<String, dynamic>> _quickWatchlist = [
    {'symbol': 'RELIANCE', 'name': 'Reliance Industries', 'price': 2984.50, 'change': 1.25, 'isPos': true},
    {'symbol': 'TCS', 'name': 'Tata Consultancy', 'price': 4125.00, 'change': 0.85, 'isPos': true},
    {'symbol': 'INFY', 'name': 'Infosys Limited', 'price': 1892.40, 'change': -0.42, 'isPos': false},
    {'symbol': 'HDFCBANK', 'name': 'HDFC Bank Ltd', 'price': 1642.10, 'change': 0.35, 'isPos': true},
  ];

  final _currencyFmt = NumberFormat.currency(symbol: '₹', locale: 'en_IN', decimalDigits: 2);

  @override
  void initState() {
    super.initState();
    _loadAccountSummary();
    _fetchLiveQuotes();
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
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _fetchLiveQuotes() async {
    for (int i = 0; i < _quickWatchlist.length; i++) {
      try {
        final q = await apiClient.getQuote(_quickWatchlist[i]['symbol'] as String);
        if (q != null && mounted) {
          final ltp = (q['last_price'] ?? q['price'] as num?)?.toDouble();
          final chgPct = (q['change_percent'] ?? q['change_pct'] as num?)?.toDouble();
          final isMktOpen = q['market_open'] == true;
          final freshness = (q['freshness'] ?? (isMktOpen ? 'LIVE' : 'CLOSED')).toString().toUpperCase();
          if (ltp != null) {
            setState(() {
              _quickWatchlist[i]['price'] = ltp;
              if (chgPct != null) {
                _quickWatchlist[i]['change'] = chgPct;
                _quickWatchlist[i]['isPos'] = chgPct >= 0;
              }
              _quotesLoaded = true;
              _isMarketOpen = isMktOpen;
              _quotesFreshness = freshness;
            });
          }
        }
      } catch (_) {}
    }
  }

  void _openInstantTrade([String symbol = 'RELIANCE']) {
    final item = _quickWatchlist.firstWhere(
      (w) => w['symbol'] == symbol,
      orElse: () => <String, dynamic>{'price': 2500.0},
    );
    final cardPrice = (item['price'] as num?)?.toDouble();
    QuickTradeModal.show(
      context,
      initialSymbol: symbol,
      initialPrice: cardPrice,
      onOrderPlaced: _loadAccountSummary,
    );
  }

  @override
  Widget build(BuildContext context) {
    final equityPct = _totalPortfolioValue > 0
        ? ((_positionsMarketValue / _totalPortfolioValue) * 100).round().clamp(0, 100)
        : 0;
    final cashPct = 100 - equityPct;
    final isProfit = _unrealizedPnl >= 0;
    final pnlPct = (_totalPortfolioValue - _unrealizedPnl > 0)
        ? ((_unrealizedPnl / (_totalPortfolioValue - _unrealizedPnl)) * 100).toStringAsFixed(2)
        : '0.00';

    if (_isLoading && _positions.isEmpty) {
      return const OverviewSkeleton();
    }

    return RefreshIndicator(
      color: TerminalColors.action,
      backgroundColor: TerminalColors.surface,
      onRefresh: () async {
        await _loadAccountSummary();
        await _fetchLiveQuotes();
      },
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Header & Quick Action Row
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "EXECUTIVE WORKSPACE",
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.8,
                        color: TerminalColors.action,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      ApiClient.getTimeOfDayGreeting(apiClient.displayName),
                      style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w800,
                        letterSpacing: -0.5,
                        color: TerminalColors.textMain,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      "Live NSE quotes · Double-entry ledger",
                      style: TextStyle(fontSize: 11, color: TerminalColors.textMuted.withValues(alpha: 0.8)),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: TerminalColors.action,
                  foregroundColor: Colors.black,
                  elevation: 0,
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                ),
                icon: const Icon(Icons.bolt, size: 16),
                label: const Text("Instant Trade", style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800)),
                onPressed: () => _openInstantTrade('RELIANCE'),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Quick Navigation Action Chips (Charts, Portfolio, Ledger, AI Diagnosis)
          Row(
            children: [
              Expanded(
                child: _QuickActionButton(
                  icon: Icons.show_chart,
                  label: "Charts",
                  highlight: true,
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (context) => const MobileChartScreen()),
                    );
                  },
                ),
              ),
              const SizedBox(width: 6),
              Expanded(
                child: _QuickActionButton(
                  icon: Icons.pie_chart,
                  label: "Portfolio",
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (context) => const MobilePortfolioScreen()),
                    );
                  },
                ),
              ),
              const SizedBox(width: 6),
              Expanded(
                child: _QuickActionButton(
                  icon: Icons.receipt_long,
                  label: "Ledger",
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (context) => const MobileTransactionsScreen()),
                    );
                  },
                ),
              ),
              const SizedBox(width: 6),
              Expanded(
                child: _QuickActionButton(
                  icon: Icons.smart_toy,
                  label: "AI Diagn.",
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (context) => const MobileAskFinExScreen()),
                    );
                  },
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Total Portfolio Value Hero Card
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
                        border: Border.all(color: const Color(0x334DD5AD)),
                      ),
                      child: Text(
                        _isLoading ? "Syncing..." : "Reconciled",
                        style: const TextStyle(fontSize: 10, fontFamily: 'monospace', color: TerminalColors.positive, fontWeight: FontWeight.w700),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  _currencyFmt.format(_totalPortfolioValue),
                  style: const TextStyle(fontSize: 30, fontWeight: FontWeight.w800, fontFamily: 'monospace', color: TerminalColors.textMain),
                ),
                const SizedBox(height: 6),
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: isProfit ? TerminalColors.positiveBg : TerminalColors.negativeBg,
                        borderRadius: BorderRadius.circular(3),
                      ),
                      child: Text(
                        "${isProfit ? '+' : ''}${_currencyFmt.format(_unrealizedPnl)} ($pnlPct%)",
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          fontFamily: 'monospace',
                          color: isProfit ? TerminalColors.positive : TerminalColors.negative,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    const Text("Unrealized Gain / Loss", style: TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),

          // 3-Metric Sub Ribbon: Holdings, Cash, Deterministic Risk
          Row(
            children: [
              Expanded(
                child: Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: TerminalColors.surface,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: TerminalColors.borderSubtle),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text("HOLDINGS", style: TextStyle(fontSize: 9, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.textMuted)),
                      const SizedBox(height: 4),
                      Text(
                        _currencyFmt.format(_positionsMarketValue),
                        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, fontFamily: 'monospace', color: TerminalColors.textMain),
                      ),
                      const SizedBox(height: 2),
                      Text("${_positions.length} Positions · $equityPct%", style: const TextStyle(fontSize: 10, color: TerminalColors.textMuted)),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: GestureDetector(
                  onTap: () => _openInstantTrade('RELIANCE'),
                  child: Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: const Color(0x15F29A60),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0x40F29A60)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text("VIRTUAL CASH", style: TextStyle(fontSize: 9, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.action)),
                        const SizedBox(height: 4),
                        Text(
                          _currencyFmt.format(_cashBalance),
                          style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, fontFamily: 'monospace', color: TerminalColors.action),
                        ),
                        const SizedBox(height: 2),
                        const Text("Deploy now →", style: TextStyle(fontSize: 10, color: TerminalColors.action, fontWeight: FontWeight.w600)),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: TerminalColors.surface,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: TerminalColors.borderSubtle),
                  ),
                  child: const Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text("RISK PROFILE", style: TextStyle(fontSize: 9, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: Color(0xFF60A5FA))),
                      SizedBox(height: 4),
                      Text(
                        "Moderate",
                        style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: Color(0xFF60A5FA)),
                      ),
                      SizedBox(height: 2),
                      Text("3–5 Yrs Horizon", style: TextStyle(fontSize: 10, color: TerminalColors.textMuted)),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),

          // Capital Deployment Split Bar (Equities vs Liquid Paper Cash)
          Container(
            padding: const EdgeInsets.all(14),
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
                    const Text("CAPITAL DEPLOYMENT SPLIT", style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.textMuted)),
                    Text(
                      "Equities: $equityPct% · Liquid Cash: $cashPct%",
                      style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: TerminalColors.textMain),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                ClipRRect(
                  borderRadius: BorderRadius.circular(3),
                  child: SizedBox(
                    height: 8,
                    child: Row(
                      children: [
                        if (equityPct > 0)
                          Expanded(
                            flex: equityPct,
                            child: Container(color: TerminalColors.action),
                          ),
                        if (cashPct > 0)
                          Expanded(
                            flex: cashPct,
                            child: Container(color: const Color(0xFF3B82F6)),
                          ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // Live NSE Market Active Instruments & 1-Click Order Execution
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Icon(
                    _isMarketOpen ? Icons.flash_on : Icons.access_time,
                    size: 14,
                    color: _isMarketOpen ? TerminalColors.action : const Color(0xFFFBBF24),
                  ),
                  const SizedBox(width: 4),
                  const Text(
                    "NSE WATCHLIST & 1-CLICK TRADE",
                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.textMuted),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: _isMarketOpen
                      ? TerminalColors.positiveBg
                      : (_quotesFreshness == 'CLOSED' ? const Color(0x22F59E0B) : TerminalColors.panel),
                  borderRadius: BorderRadius.circular(3),
                  border: Border.all(
                    color: _isMarketOpen
                        ? TerminalColors.positive
                        : (_quotesFreshness == 'CLOSED' ? const Color(0xFFF59E0B) : TerminalColors.borderSubtle),
                  ),
                ),
                child: Text(
                  _isMarketOpen
                      ? "NSE LIVE"
                      : (_quotesFreshness == 'CLOSED'
                          ? "SESSION CLOSE"
                          : (_quotesLoaded ? "CACHED" : "CONNECTING...")),
                  style: TextStyle(
                    fontSize: 9,
                    fontFamily: 'monospace',
                    fontWeight: FontWeight.w700,
                    color: _isMarketOpen
                        ? TerminalColors.positive
                        : (_quotesFreshness == 'CLOSED' ? const Color(0xFFFBBF24) : TerminalColors.textMuted),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),

          // 2x2 Grid of Top Stocks
          GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: _quickWatchlist.length,
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2,
              crossAxisSpacing: 10,
              mainAxisSpacing: 10,
              childAspectRatio: 1.5,
            ),
            itemBuilder: (context, idx) {
              final item = _quickWatchlist[idx];
              final sym = item['symbol'] as String;
              final price = (item['price'] as num).toDouble();
              final chg = (item['change'] as num).toDouble();
              final isPos = item['isPos'] == true;

              return Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: TerminalColors.surface,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: TerminalColors.borderSubtle),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        GestureDetector(
                          onTap: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(builder: (context) => MobileChartScreen(initialSymbol: sym)),
                            );
                          },
                          child: Row(
                            children: [
                              Text(sym, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: TerminalColors.textMain)),
                              const SizedBox(width: 4),
                              const Icon(Icons.show_chart, size: 13, color: TerminalColors.action),
                            ],
                          ),
                        ),
                        Text(
                          "${isPos ? '+' : ''}${chg.toStringAsFixed(2)}%",
                          style: TextStyle(
                            fontSize: 10,
                            fontFamily: 'monospace',
                            fontWeight: FontWeight.w700,
                            color: isPos ? TerminalColors.positive : TerminalColors.negative,
                          ),
                        ),
                      ],
                    ),
                    Text(
                      _currencyFmt.format(price),
                      style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800, fontFamily: 'monospace', color: TerminalColors.textMain),
                    ),
                    Row(
                      children: [
                        Expanded(
                          child: GestureDetector(
                            onTap: () => _openInstantTrade(sym),
                            child: Container(
                              padding: const EdgeInsets.symmetric(vertical: 4),
                              decoration: BoxDecoration(
                                color: TerminalColors.positiveBg,
                                borderRadius: BorderRadius.circular(3),
                                border: Border.all(color: const Color(0x334DD5AD)),
                              ),
                              alignment: Alignment.center,
                              child: const Text("BUY", style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: TerminalColors.positive)),
                            ),
                          ),
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: GestureDetector(
                            onTap: () => _openInstantTrade(sym),
                            child: Container(
                              padding: const EdgeInsets.symmetric(vertical: 4),
                              decoration: BoxDecoration(
                                color: TerminalColors.negativeBg,
                                borderRadius: BorderRadius.circular(3),
                                border: Border.all(color: const Color(0x33F48C7B)),
                              ),
                              alignment: Alignment.center,
                              child: const Text("SELL", style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: TerminalColors.negative)),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              );
            },
          ),
          const SizedBox(height: 20),

          // Portfolio Performance Curve Card
          Container(
            padding: const EdgeInsets.all(16),
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
                    const Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text("PORTFOLIO PERFORMANCE CURVE", style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.textMuted)),
                        SizedBox(height: 2),
                        Text("May – Oct 2026 Historical Valuation", style: TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
                      ],
                    ),
                    Container(
                      padding: const EdgeInsets.all(2),
                      decoration: BoxDecoration(
                        color: TerminalColors.canvas,
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: TerminalColors.borderSubtle),
                      ),
                      child: Row(
                        children: [
                          _buildChartToggle("area", "Area"),
                          _buildChartToggle("candles", "Candles"),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                // Custom Area Sparkline Graph
                SizedBox(
                  height: 100,
                  width: double.infinity,
                  child: CustomPaint(
                    painter: _PerformanceCurvePainter(
                      color: TerminalColors.action,
                      isCandles: _chartView == 'candles',
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                const Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text("May", style: TextStyle(fontSize: 10, fontFamily: 'monospace', color: TerminalColors.textMuted)),
                    Text("Jun", style: TextStyle(fontSize: 10, fontFamily: 'monospace', color: TerminalColors.textMuted)),
                    Text("Jul", style: TextStyle(fontSize: 10, fontFamily: 'monospace', color: TerminalColors.textMuted)),
                    Text("Aug", style: TextStyle(fontSize: 10, fontFamily: 'monospace', color: TerminalColors.textMuted)),
                    Text("Sep", style: TextStyle(fontSize: 10, fontFamily: 'monospace', color: TerminalColors.textMuted)),
                    Text("Oct (Live)", style: TextStyle(fontSize: 10, fontFamily: 'monospace', fontWeight: FontWeight.w700, color: TerminalColors.action)),
                  ],
                ),
                const SizedBox(height: 12),
                InkWell(
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (context) => const MobileChartScreen()),
                    );
                  },
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 10),
                    decoration: BoxDecoration(
                      color: const Color(0x15F29A60),
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(color: const Color(0x33F29A60)),
                    ),
                    child: const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.candlestick_chart, size: 14, color: TerminalColors.action),
                        SizedBox(width: 6),
                        Text(
                          "Launch TradingView Candlestick Workspace →",
                          style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: TerminalColors.action),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // Active Holdings Preview
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                "PORTFOLIO HOLDINGS",
                style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.textMuted),
              ),
              GestureDetector(
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => const MobilePortfolioScreen()),
                  );
                },
                child: const Text("View Full Architecture →", style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: TerminalColors.action)),
              ),
            ],
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
                "No open positions. Use Instant Trade above to test paper execution.",
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
                        Text("${qty.toStringAsFixed(0)} shares @ ₹${avgBuy.toStringAsFixed(2)}", style: const TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
                      ],
                    ),
                    Row(
                      children: [
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
                        const SizedBox(width: 10),
                        IconButton(
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(),
                          icon: const Icon(Icons.swap_horiz, size: 18, color: TerminalColors.action),
                          onPressed: () => _openInstantTrade(sym),
                        ),
                      ],
                    ),
                  ],
                ),
              );
            }),
          const SizedBox(height: 20),

          // Shared Recent Transactions Feed (Web PR #28 Parity)
          RecentTransactionsFeed(
            title: "ACTIVITY & RECENT EXECUTIONS",
            maxItems: 5,
            showFilters: true,
            onNavigateToPractice: () => _openInstantTrade('RELIANCE'),
            onNavigateToAudit: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const MobileTransactionsScreen()),
              );
            },
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  Widget _buildChartToggle(String mode, String label) {
    final isSelected = _chartView == mode;
    return GestureDetector(
      onTap: () => setState(() => _chartView = mode),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0x33F29A60) : Colors.transparent,
          borderRadius: BorderRadius.circular(3),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 10,
            fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
            color: isSelected ? TerminalColors.action : TerminalColors.textMuted,
          ),
        ),
      ),
    );
  }
}

class _QuickActionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final bool highlight;

  const _QuickActionButton({
    required this.icon,
    required this.label,
    required this.onTap,
    this.highlight = false,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 6),
        decoration: BoxDecoration(
          color: highlight ? const Color(0x18F29A60) : TerminalColors.surface,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: highlight ? const Color(0x50F29A60) : TerminalColors.borderSubtle),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 14, color: highlight ? TerminalColors.action : TerminalColors.action),
            const SizedBox(width: 4),
            Flexible(
              child: Text(
                label,
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  color: highlight ? TerminalColors.action : TerminalColors.textMain,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PerformanceCurvePainter extends CustomPainter {
  final Color color;
  final bool isCandles;

  _PerformanceCurvePainter({required this.color, required this.isCandles});

  @override
  void paint(Canvas canvas, Size size) {
    // Relative data points: May, Jun, Jul, Aug, Sep, Oct
    final points = [0.35, 0.45, 0.40, 0.65, 0.75, 0.88];
    final wStep = size.width / (points.length - 1);

    if (isCandles) {
      final candlePaint = Paint()
        ..style = PaintingStyle.fill
        ..strokeWidth = 1.5;

      for (int i = 0; i < points.length; i++) {
        final cx = i * wStep;
        final base = points[i];
        final isGreen = i % 2 == 0 || i == points.length - 1;
        candlePaint.color = isGreen ? TerminalColors.positive : TerminalColors.negative;

        final cy = size.height - (base * size.height * 0.8) - 10;
        const h = 18.0;

        // Wick
        canvas.drawLine(Offset(cx, cy - 8), Offset(cx, cy + h + 8), candlePaint);
        // Body
        canvas.drawRect(Rect.fromCenter(center: Offset(cx, cy + h / 2), width: 8, height: h), candlePaint);
      }
      return;
    }

    final path = Path();
    final fillPath = Path();

    path.moveTo(0, size.height - (points[0] * size.height * 0.8) - 10);
    fillPath.moveTo(0, size.height);
    fillPath.lineTo(0, size.height - (points[0] * size.height * 0.8) - 10);

    for (int i = 1; i < points.length; i++) {
      final x = i * wStep;
      final y = size.height - (points[i] * size.height * 0.8) - 10;
      path.lineTo(x, y);
      fillPath.lineTo(x, y);
    }

    fillPath.lineTo(size.width, size.height);
    fillPath.close();

    // Fill gradient
    final fillPaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          color.withValues(alpha: 0.35),
          color.withValues(alpha: 0.0),
        ],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height));

    canvas.drawPath(fillPath, fillPaint);

    // Line stroke
    final linePaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0;

    canvas.drawPath(path, linePaint);

    // End point circle
    final lastX = size.width;
    final lastY = size.height - (points.last * size.height * 0.8) - 10;
    canvas.drawCircle(Offset(lastX, lastY), 4, Paint()..color = color);
  }

  @override
  bool shouldRepaint(covariant _PerformanceCurvePainter oldDelegate) {
    return oldDelegate.color != color || oldDelegate.isCandles != isCandles;
  }
}
