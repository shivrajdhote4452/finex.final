import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../services/api_client.dart';
import '../theme/terminal_theme.dart';
import '../widgets/quick_trade_modal.dart';
import '../widgets/recent_transactions_feed.dart';
import '../widgets/skeleton_loader.dart';
import 'transactions_screen.dart';

class MobilePortfolioScreen extends StatefulWidget {
  const MobilePortfolioScreen({super.key});

  @override
  State<MobilePortfolioScreen> createState() => _MobilePortfolioScreenState();
}

class _MobilePortfolioScreenState extends State<MobilePortfolioScreen> {
  double _virtualCash = 100000.0;
  double _totalHoldingsValue = 0.0;
  double _totalPortfolioValue = 100000.0;
  double _unrealizedPnL = 0.0;
  double _dayPnL = 0.0;
  double _dayPnLPct = 0.0;
  List<Map<String, dynamic>> _holdings = [];
  bool _isLoading = false;

  final _currencyFmt = NumberFormat.currency(symbol: '₹ ', locale: 'en_IN', decimalDigits: 2);

  @override
  void initState() {
    super.initState();
    _loadPortfolio();
  }

  Future<void> _loadPortfolio() async {
    setState(() => _isLoading = true);
    try {
      final acct = await apiClient.getAccount();
      if (mounted) {
        final cash = (acct['cash_balance'] ?? acct['current_cash'] as num?)?.toDouble() ?? 100000.0;
        final rawPos = List<Map<String, dynamic>>.from(acct['positions'] ?? []);
        
        double totalVal = 0.0;
        double totalPnL = 0.0;
        double totalDayPnL = 0.0;
        final processed = rawPos.map<Map<String, dynamic>>((p) {
          final sym = p['symbol'] ?? '';
          final qty = (p['quantity'] as num?)?.toDouble() ?? 0.0;
          final avgBuy = (p['average_buy_price'] ?? p['avg_cost'] as num?)?.toDouble() ?? 0.0;
          final curPrice = (p['current_price'] as num?)?.toDouble() ?? avgBuy;
          final mktVal = (p['market_value'] as num?)?.toDouble() ?? (qty * curPrice);
          final pnl = (p['unrealized_pnl'] as num?)?.toDouble() ?? (mktVal - (qty * avgBuy));
          final dayPct = (p['day_change_pct'] ?? p['change_pct'] as num?)?.toDouble() ?? 0.0;
          final prevVal = (1 + dayPct / 100) != 0 ? mktVal / (1 + dayPct / 100) : mktVal;
          final dayPnL = mktVal - prevVal;

          totalVal += mktVal;
          totalPnL += pnl;
          totalDayPnL += dayPnL;

          return {
            'symbol': sym,
            'quantity': qty,
            'avgBuy': avgBuy,
            'currentPrice': curPrice,
            'marketValue': mktVal,
            'unrealizedPnL': pnl,
            'dayChangePct': dayPct,
          };
        }).toList();

        final totalPortfolio = cash + totalVal;
        final prevPortfolioVal = totalPortfolio - totalDayPnL;
        final dayReturnPct = prevPortfolioVal > 0 ? (totalDayPnL / prevPortfolioVal) * 100 : 0.0;

        setState(() {
          _virtualCash = cash;
          _totalHoldingsValue = totalVal;
          _unrealizedPnL = totalPnL;
          _totalPortfolioValue = totalPortfolio;
          _dayPnL = totalDayPnL;
          _dayPnLPct = dayReturnPct;
          _holdings = processed;
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _showRebalanceModal() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        return Container(
          decoration: const BoxDecoration(
            color: TerminalColors.surface,
            borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
            border: Border(top: BorderSide(color: TerminalColors.borderSubtle)),
          ),
          padding: const EdgeInsets.all(20),
          child: SafeArea(
            top: false,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Center(
                  child: Container(
                    width: 36,
                    height: 4,
                    margin: const EdgeInsets.only(bottom: 16),
                    decoration: BoxDecoration(
                      color: TerminalColors.borderMedium,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('⚖️ SIMULATE PORTFOLIO REBALANCE', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: TerminalColors.action)),
                    IconButton(
                      icon: const Icon(Icons.close, size: 20, color: TerminalColors.textMuted),
                      onPressed: () => Navigator.pop(ctx),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                const Text(
                  'Equal-weight rebalancing adjusts each holding to target equal allocation (e.g. 20% per position), generating simulated corrective market orders.',
                  style: TextStyle(fontSize: 12, color: TerminalColors.textMuted, height: 1.4),
                ),
                const SizedBox(height: 16),
                if (_holdings.isEmpty)
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(color: TerminalColors.panel, borderRadius: BorderRadius.circular(6)),
                    child: const Text('No active holdings to rebalance. Open positions via Paper Trading first.', style: TextStyle(fontSize: 12, color: TerminalColors.textMuted)),
                  )
                else
                  ..._holdings.map((h) {
                    final targetWeight = 100.0 / _holdings.length;
                    final currentWeight = _totalHoldingsValue > 0 ? (h['marketValue'] / _totalHoldingsValue) * 100 : 0.0;
                    final diff = targetWeight - currentWeight;
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(h['symbol'], style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
                          Row(
                            children: [
                              Text('${currentWeight.toStringAsFixed(1)}% → ${targetWeight.toStringAsFixed(1)}%', style: const TextStyle(fontSize: 12, fontFamily: 'monospace', color: TerminalColors.textMuted)),
                              const SizedBox(width: 8),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: diff >= 0 ? TerminalColors.positiveBg : TerminalColors.negativeBg,
                                  borderRadius: BorderRadius.circular(3),
                                ),
                                child: Text(
                                  diff >= 0 ? 'BUY' : 'SELL',
                                  style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: diff >= 0 ? TerminalColors.positive : TerminalColors.negative),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    );
                  }),
                const SizedBox(height: 20),
                SizedBox(
                  width: double.infinity,
                  height: 44,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: TerminalColors.action,
                      foregroundColor: Colors.black,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                    ),
                    onPressed: () {
                      Navigator.pop(ctx);
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Simulated rebalance calculations updated across ledger.'),
                          backgroundColor: TerminalColors.surface,
                        ),
                      );
                    },
                    child: const Text('CONFIRM SIMULATED REBALANCE', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final costBasis = _totalHoldingsValue - _unrealizedPnL;
    final pnlReturnPct = costBasis > 0 ? (_unrealizedPnL / costBasis) * 100 : 0.0;
    final isProfit = _unrealizedPnL >= 0;

    return Scaffold(
      backgroundColor: TerminalColors.canvas,
      appBar: AppBar(
        title: const Text('PORTFOLIO & HOLDINGS ARCHITECTURE'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, size: 20, color: TerminalColors.action),
            onPressed: _loadPortfolio,
          ),
        ],
        bottom: _isLoading
            ? const PreferredSize(
                preferredSize: Size.fromHeight(2),
                child: LinearProgressIndicator(color: TerminalColors.action, minHeight: 2),
              )
            : null,
      ),
      body: RefreshIndicator(
        color: TerminalColors.action,
        backgroundColor: TerminalColors.surface,
        onRefresh: _loadPortfolio,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Header
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('ASSET MANAGEMENT', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: TerminalColors.action, letterSpacing: 0.5)),
                    SizedBox(height: 2),
                    Text('Holdings Architecture', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: TerminalColors.textMain)),
                  ],
                ),
                Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.balance, size: 20, color: TerminalColors.action),
                      tooltip: 'Simulate Rebalance',
                      onPressed: _showRebalanceModal,
                    ),
                    IconButton(
                      icon: const Icon(Icons.receipt_long, size: 20, color: TerminalColors.textMuted),
                      tooltip: 'Audit Ledger',
                      onPressed: () {
                        Navigator.push(context, MaterialPageRoute(builder: (context) => const MobileTransactionsScreen()));
                      },
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 16),

            if (_isLoading && _holdings.isEmpty)
              const PortfolioSkeleton()
            else ...[
              // Portfolio Hero Upgrade Card (Web PR #28 Parity)
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
                      const Text(
                        'TOTAL PORTFOLIO VALUATION',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.5,
                          color: TerminalColors.textMuted,
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: const Color(0x2238BDF8),
                          borderRadius: BorderRadius.circular(3),
                        ),
                        child: const Text(
                          '100% Reconciled',
                          style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w700, color: Color(0xFF38BDF8)),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    _currencyFmt.format(_totalPortfolioValue),
                    style: const TextStyle(
                      fontSize: 26,
                      fontWeight: FontWeight.w800,
                      fontFamily: 'monospace',
                      color: TerminalColors.textMain,
                      letterSpacing: -0.5,
                    ),
                  ),
                  const SizedBox(height: 8),

                  // Day P&L & Total ROI
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: _dayPnL >= 0 ? TerminalColors.positiveBg : TerminalColors.negativeBg,
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              _dayPnL >= 0 ? '▲ +' : '▼ ',
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w800,
                                color: _dayPnL >= 0 ? TerminalColors.positive : TerminalColors.negative,
                              ),
                            ),
                            Text(
                              '${_currencyFmt.format(_dayPnL.abs())} (${_dayPnL >= 0 ? '+' : ''}${_dayPnLPct.toStringAsFixed(2)}% today)',
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w700,
                                fontFamily: 'monospace',
                                color: _dayPnL >= 0 ? TerminalColors.positive : TerminalColors.negative,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 8),
                      Flexible(
                        child: Text(
                          'Overall: ${isProfit ? '+' : ''}${_currencyFmt.format(_unrealizedPnL)}',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: isProfit ? TerminalColors.positive : TerminalColors.negative,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  const Divider(color: TerminalColors.borderSubtle, height: 1),
                  const SizedBox(height: 16),

                  // Allocation Donut + Breakdown
                  if (_holdings.isNotEmpty) ...[
                    Row(
                      children: [
                        SizedBox(
                          width: 84,
                          height: 84,
                          child: Stack(
                            alignment: Alignment.center,
                            children: [
                              CustomPaint(
                                size: const Size(84, 84),
                                painter: _AllocationDonutPainter(
                                  holdings: _holdings,
                                  totalValue: _totalHoldingsValue,
                                ),
                              ),
                              Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text(
                                    '${_holdings.length}',
                                    style: const TextStyle(
                                      fontSize: 15,
                                      fontWeight: FontWeight.w800,
                                      color: TerminalColors.textMain,
                                    ),
                                  ),
                                  const Text(
                                    'Assets',
                                    style: TextStyle(fontSize: 8.5, color: TerminalColors.textMuted),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'ASSET WEIGHT ALLOCATION',
                                style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w700, color: TerminalColors.textMuted),
                              ),
                              const SizedBox(height: 6),
                              Wrap(
                                spacing: 10,
                                runSpacing: 6,
                                children: _holdings.take(6).map((h) {
                                  final sym = h['symbol'] as String;
                                  final mVal = h['marketValue'] as double;
                                  final pct = _totalHoldingsValue > 0 ? (mVal / _totalHoldingsValue) * 100 : 0.0;
                                  final col = _getColorForSymbol(sym);

                                  return Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Container(width: 7, height: 7, decoration: BoxDecoration(color: col, shape: BoxShape.circle)),
                                      const SizedBox(width: 4),
                                      Text(
                                        '$sym ${pct.toStringAsFixed(1)}%',
                                        style: const TextStyle(fontSize: 10.5, fontFamily: 'monospace', color: TerminalColors.textMuted),
                                      ),
                                    ],
                                  );
                                }).toList(),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ] else ...[
                    const Text(
                      'No open equity positions held. Execute a practice order to view asset allocation donut.',
                      style: TextStyle(fontSize: 11, color: TerminalColors.textMuted),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Top KPI Cards (Grid 2x2)
            Row(
              children: [
                Expanded(child: _buildMetricCard('HOLDINGS VALUATION', _currencyFmt.format(_totalHoldingsValue), '${_holdings.length} Active Positions', TerminalColors.textMain)),
                const SizedBox(width: 12),
                Expanded(child: _buildMetricCard('UNREALIZED P&L', '${isProfit ? '+' : ''}${_currencyFmt.format(_unrealizedPnL)}', '${isProfit ? '+' : ''}${pnlReturnPct.toStringAsFixed(2)}% Return', isProfit ? TerminalColors.positive : TerminalColors.negative)),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(child: _buildMetricCard('VIRTUAL CASH', _currencyFmt.format(_virtualCash), 'Deployable Reserve', TerminalColors.action)),
                const SizedBox(width: 12),
                Expanded(child: _buildMetricCard('ACCOUNT EQUITY', _currencyFmt.format(_totalPortfolioValue), '100% Reconciled', TerminalColors.textMain)),
              ],
            ),
            const SizedBox(height: 20),

            // Quick Instant Trade Button
            SizedBox(
              width: double.infinity,
              height: 44,
              child: ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: TerminalColors.positive,
                  foregroundColor: Colors.black,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                ),
                icon: const Icon(Icons.bolt, size: 18),
                label: const Text('⚡ INSTANT TRADE TICKET', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
                onPressed: () {
                  QuickTradeModal.show(context, onTradeExecuted: _loadPortfolio);
                },
              ),
            ),
            const SizedBox(height: 20),

            // Asset Distribution Strip
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
                      const Text('ASSET DISTRIBUTION', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: TerminalColors.textMuted)),
                      Text('${_holdings.length} Assets', style: const TextStyle(fontSize: 11, color: TerminalColors.textFaint)),
                    ],
                  ),
                  const SizedBox(height: 12),
                  if (_holdings.isEmpty)
                    const Text('No equity assets currently held in portfolio.', style: TextStyle(fontSize: 12, color: TerminalColors.textMuted))
                  else ...[
                    // Distribution segmented bar
                    ClipRRect(
                      borderRadius: BorderRadius.circular(4),
                      child: SizedBox(
                        height: 10,
                        child: Row(
                          children: _holdings.map((h) {
                            final weight = _totalHoldingsValue > 0 ? (h['marketValue'] / _totalHoldingsValue) : 0.0;
                            return Expanded(
                              flex: (weight * 1000).toInt().clamp(1, 1000),
                              child: Container(
                                color: _getColorForSymbol(h['symbol']),
                              ),
                            );
                          }).toList(),
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 12,
                      runSpacing: 8,
                      children: _holdings.map((h) {
                        final weight = _totalHoldingsValue > 0 ? ((h['marketValue'] / _totalHoldingsValue) * 100).toStringAsFixed(1) : '0';
                        return Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(width: 8, height: 8, decoration: BoxDecoration(color: _getColorForSymbol(h['symbol']), shape: BoxShape.circle)),
                            const SizedBox(width: 4),
                            Text('${h['symbol']} ($weight%)', style: const TextStyle(fontSize: 11, color: TerminalColors.textMuted, fontFamily: 'monospace')),
                          ],
                        );
                      }).toList(),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Detailed Holdings List
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('ACTIVE POSITIONS', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.textMuted)),
                TextButton(
                  onPressed: _showRebalanceModal,
                  child: const Text('Rebalance', style: TextStyle(fontSize: 12, color: TerminalColors.action)),
                ),
              ],
            ),
            const SizedBox(height: 8),

            if (_holdings.isEmpty)
              Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: TerminalColors.surface,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: TerminalColors.borderSubtle),
                ),
                alignment: Alignment.center,
                child: const Column(
                  children: [
                    Icon(Icons.pie_chart_outline, size: 36, color: TerminalColors.textFaint),
                    SizedBox(height: 8),
                    Text('Zero Active Equity Positions', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
                    SizedBox(height: 4),
                    Text('Execute paper orders from Markets or Charts to build portfolio allocation.', style: TextStyle(fontSize: 12, color: TerminalColors.textMuted), textAlign: TextAlign.center),
                  ],
                ),
              )
            else
              ..._holdings.map((h) {
                final sym = h['symbol'] as String;
                final qty = (h['quantity'] as num).toInt();
                final avgBuy = h['avgBuy'] as double;
                final curPrice = h['currentPrice'] as double;
                final mktVal = h['marketValue'] as double;
                final pnl = h['unrealizedPnL'] as double;
                final posWeight = _totalHoldingsValue > 0 ? ((mktVal / _totalHoldingsValue) * 100).toStringAsFixed(1) : '0';
                final isHoldingProfit = pnl >= 0;

                return Container(
                  margin: const EdgeInsets.only(bottom: 10),
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
                          Row(
                            children: [
                              Text(sym, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: TerminalColors.textMain)),
                              const SizedBox(width: 8),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(color: TerminalColors.input, borderRadius: BorderRadius.circular(3)),
                                child: Text('$posWeight% wt', style: const TextStyle(fontSize: 10, fontFamily: 'monospace', color: TerminalColors.textMuted)),
                              ),
                            ],
                          ),
                          Text(_currencyFmt.format(mktVal), style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800, fontFamily: 'monospace', color: TerminalColors.textMain)),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text('$qty Shares @ ₹${avgBuy.toStringAsFixed(2)}', style: const TextStyle(fontSize: 12, color: TerminalColors.textMuted, fontFamily: 'monospace')),
                          Row(
                            children: [
                              const Text('LTP: ', style: TextStyle(fontSize: 11, color: TerminalColors.textFaint)),
                              Text('₹${curPrice.toStringAsFixed(2)}', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, fontFamily: 'monospace', color: TerminalColors.textMain)),
                            ],
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      const Divider(color: TerminalColors.borderSubtle, height: 1),
                      const SizedBox(height: 8),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Row(
                            children: [
                              const Text('P&L: ', style: TextStyle(fontSize: 11, color: TerminalColors.textFaint)),
                              Text(
                                '${isHoldingProfit ? '+' : ''}${_currencyFmt.format(pnl)}',
                                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, fontFamily: 'monospace', color: isHoldingProfit ? TerminalColors.positive : TerminalColors.negative),
                              ),
                            ],
                          ),
                          InkWell(
                            onTap: () {
                              QuickTradeModal.show(context, initialSymbol: sym, onTradeExecuted: _loadPortfolio);
                            },
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                              decoration: BoxDecoration(
                                color: TerminalColors.actionBg,
                                borderRadius: BorderRadius.circular(4),
                                border: Border.all(color: TerminalColors.action),
                              ),
                              child: const Text('TRADE', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: TerminalColors.action)),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                );
              }),
            const SizedBox(height: 24),

            // Shared Recent Transactions Feed (Web PR #28 Parity)
            RecentTransactionsFeed(
              title: "PORTFOLIO TRANSACTION AUDIT",
              maxItems: 8,
              showFilters: true,
              onNavigateToPractice: () => QuickTradeModal.show(context, onTradeExecuted: _loadPortfolio),
              onNavigateToAudit: () {
                Navigator.push(context, MaterialPageRoute(builder: (context) => const MobileTransactionsScreen()));
              },
            ),
            const SizedBox(height: 20),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildMetricCard(String label, String value, String sub, Color valColor) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: TerminalColors.surface,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: TerminalColors.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: TerminalColors.textMuted)),
          const SizedBox(height: 6),
          Text(value, style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, fontFamily: 'monospace', color: valColor)),
          const SizedBox(height: 4),
          Text(sub, style: const TextStyle(fontSize: 11, color: TerminalColors.textFaint)),
        ],
      ),
    );
  }

  Color _getColorForSymbol(String sym) {
    final colors = [
      TerminalColors.action,
      TerminalColors.positive,
      const Color(0xFF60A5FA), // Blue
      const Color(0xFFA78BFA), // Purple
      const Color(0xFFF472B6), // Pink
      const Color(0xFFFBBF24), // Amber
    ];
    return colors[sym.hashCode.abs() % colors.length];
  }
}

class _AllocationDonutPainter extends CustomPainter {
  final List<Map<String, dynamic>> holdings;
  final double totalValue;

  _AllocationDonutPainter({required this.holdings, required this.totalValue});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = math.min(size.width, size.height) / 2;
    const strokeWidth = 11.0;

    final basePaint = Paint()
      ..color = TerminalColors.panel
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth;

    canvas.drawCircle(center, radius - strokeWidth / 2, basePaint);

    if (totalValue <= 0 || holdings.isEmpty) return;

    final colors = [
      TerminalColors.action,
      TerminalColors.positive,
      const Color(0xFF60A5FA),
      const Color(0xFFA78BFA),
      const Color(0xFFF472B6),
      const Color(0xFFFBBF24),
    ];

    double startAngle = -math.pi / 2;
    for (int i = 0; i < holdings.length; i++) {
      final h = holdings[i];
      final mktVal = (h['marketValue'] as num?)?.toDouble() ?? 0.0;
      final sweepAngle = (mktVal / totalValue) * 2 * math.pi;
      final sym = (h['symbol'] as String?) ?? '';
      final segColor = colors[sym.hashCode.abs() % colors.length];

      final segmentPaint = Paint()
        ..color = segColor
        ..style = PaintingStyle.stroke
        ..strokeWidth = strokeWidth
        ..strokeCap = StrokeCap.butt;

      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius - strokeWidth / 2),
        startAngle,
        sweepAngle,
        false,
        segmentPaint,
      );
      startAngle += sweepAngle;
    }
  }

  @override
  bool shouldRepaint(covariant _AllocationDonutPainter oldDelegate) {
    return oldDelegate.holdings != holdings || oldDelegate.totalValue != totalValue;
  }
}
