import 'package:flutter/material.dart';
import '../services/api_client.dart';
import '../theme/terminal_theme.dart';

class MobilePaperTradingScreen extends StatefulWidget {
  const MobilePaperTradingScreen({super.key});

  @override
  State<MobilePaperTradingScreen> createState() => _MobilePaperTradingScreenState();
}

class _MobilePaperTradingScreenState extends State<MobilePaperTradingScreen> {
  // Virtual Account State from backend
  double _cashBalance = 100000.00;
  String _selectedSymbol = "RELIANCE";
  String _orderSide = "BUY"; // "BUY" or "SELL"
  int _quantity = 10;
  bool _isSubmitting = false;
  String? _pendingOrderIdempotencyKey;

  final Map<String, double> _marketPrices = {
    "RELIANCE": 2500.00,
    "TCS": 3600.00,
    "INFY": 1450.00,
    "HDFCBANK": 1600.00,
    "ICICIBANK": 1240.00,
    "TATAMOTORS": 924.50,
    "SBIN": 815.20,
    "ITC": 502.80,
  };

  final List<Map<String, dynamic>> _positions = [];
  final List<Map<String, dynamic>> _orderHistory = [];

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    await Future.wait([
      _loadAccountAndPositions(),
      _loadOrders(),
      _loadLiveQuotes(),
    ]);
  }

  Future<void> _loadAccountAndPositions() async {
    try {
      final acct = await apiClient.getAccount();
      if (mounted) {
        final cash = (acct['cash_balance'] ?? acct['current_cash'] as num?)?.toDouble() ?? 100000.0;
        final rawPos = List<Map<String, dynamic>>.from(acct['positions'] ?? []);
        final mapped = rawPos.map<Map<String, dynamic>>((p) {
          final sym = p['symbol'] ?? '';
          final qty = (p['quantity'] as num?)?.toDouble() ?? 0.0;
          final avgCost = (p['average_buy_price'] ?? p['avg_cost'] as num?)?.toDouble() ?? 0.0;
          final livePrice = (p['current_price'] as num?)?.toDouble() ?? (_marketPrices[sym] ?? avgCost);
          final mktVal = (p['market_value'] as num?)?.toDouble() ?? (qty * livePrice);
          final pnl = (p['unrealized_pnl'] as num?)?.toDouble() ?? (mktVal - (qty * avgCost));
          final pnlPct = (p['unrealized_pnl_pct'] as num?)?.toDouble() ?? (avgCost > 0 ? (pnl / (qty * avgCost)) * 100.0 : 0.0);

          return {
            "symbol": sym,
            "quantity": qty.toInt(),
            "avg_price": avgCost,
            "current_price": livePrice,
            "market_value": mktVal,
            "unrealized_pnl": pnl,
            "unrealized_pct": pnlPct,
          };
        }).toList();

        setState(() {
          _cashBalance = cash;
          _positions.clear();
          _positions.addAll(mapped);
        });
      }
    } catch (_) {}
  }

  Future<void> _loadOrders() async {
    try {
      final orders = await apiClient.getOrders(20);
      if (mounted && orders.isNotEmpty) {
        final mapped = orders.map<Map<String, dynamic>>((o) {
          return {
            "order_id": o['id'] ?? '',
            "symbol": o['symbol'] ?? '',
            "side": o['side'] ?? 'BUY',
            "quantity": (o['quantity'] as num?)?.toInt() ?? 0,
            "fill_price": (o['fill_price'] as num?)?.toDouble() ?? 0.0,
            "gross": (o['gross_value'] as num?)?.toDouble() ?? 0.0,
            "status": o['status'] ?? 'FILLED',
            "time": o['created_at'] != null ? o['created_at'].toString().split('T').first : 'Recent',
          };
        }).toList();

        setState(() {
          _orderHistory.clear();
          _orderHistory.addAll(mapped);
        });
      }
    } catch (_) {}
  }

  Future<void> _loadLiveQuotes() async {
    try {
      final insts = await apiClient.getInstruments();
      for (final inst in insts) {
        final sym = inst['symbol'];
        if (sym != null) {
          final q = await apiClient.getQuote(sym);
          if (q != null && q['price'] != null && mounted) {
            setState(() {
              _marketPrices[sym] = (q['price'] as num).toDouble();
            });
          }
        }
      }
    } catch (_) {}
  }

  double get _positionsMarketValue {
    return _positions.fold(0.0, (acc, item) => acc + (item["market_value"] as double));
  }

  double get _totalEquity => _cashBalance + _positionsMarketValue;

  double get _totalUnrealizedPnl {
    return _positions.fold(0.0, (acc, item) => acc + (item["unrealized_pnl"] as double));
  }

  Future<void> _submitOrder() async {
    if (_isSubmitting) return;

    // Preserve pending order identity through interruptions
    _pendingOrderIdempotencyKey ??= 'mob-ord-${DateTime.now().millisecondsSinceEpoch}';

    setState(() => _isSubmitting = true);

    try {
      final result = await apiClient.submitOrder(
        symbol: _selectedSymbol,
        side: _orderSide,
        orderType: "MARKET",
        quantity: _quantity.toDouble(),
        idempotencyKey: _pendingOrderIdempotencyKey,
      );

      // Order executed or replayed from backend
      final status = result['status'] ?? 'FILLED';
      final reason = result['rejection_reason'];
      final fillPrice = (result['fill_price'] as num?)?.toDouble() ?? (_marketPrices[_selectedSymbol] ?? 0.0);

      _pendingOrderIdempotencyKey = null; // Reconciled successfully

      await _loadAccountAndPositions();
      await _loadOrders();

      if (!mounted) return;

      if (status == 'REJECTED') {
        _showCoachingDialog(
          title: "Order Rejected: ${result['symbol']}",
          explanation: reason ?? "Order was rejected by the paper execution engine.",
          learning: "Pre-Trade Discipline: FinEx enforces strict cash verification and short-selling restrictions.",
          isSuccess: false,
        );
      } else {
        _showCoachingDialog(
          title: "$_orderSide Order Filled: $_quantity $_selectedSymbol @ ₹${fillPrice.toStringAsFixed(2)}",
          explanation: "Simulated order filled deterministically per live market quotes. Authoritative ledger updated.",
          learning: "Opportunity Cost: Trading virtual cash for equity stakes balances potential upside against liquidity flexibility.",
          isSuccess: true,
        );
      }
    } catch (e) {
      if (!mounted) return;
      _showCoachingDialog(
        title: "Order Interrupted",
        explanation: "Network or server failure: ${e.toString().replaceFirst("Exception: ", "")}. Pending key retained for safe retry.",
        learning: "Idempotent Recovery: Retrying this order will reconcile against the original receipt without double-executing.",
        isSuccess: false,
      );
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  void _showCoachingDialog({
    required String title,
    required String explanation,
    required String learning,
    required bool isSuccess,
  }) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: TerminalColors.surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(6),
          side: const BorderSide(color: TerminalColors.borderSubtle),
        ),
        title: Row(
          children: [
            Icon(
              isSuccess ? Icons.check_circle_outline : Icons.error_outline,
              color: isSuccess ? TerminalColors.positive : TerminalColors.negative,
              size: 20,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                title,
                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: TerminalColors.textMain),
              ),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(explanation, style: const TextStyle(fontSize: 12, height: 1.4, color: TerminalColors.textMuted)),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: TerminalColors.panel,
                borderRadius: BorderRadius.circular(4),
                border: const Border(left: BorderSide(color: TerminalColors.action, width: 3)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("EDUCATIONAL TAKEAWAY", style: TextStyle(fontSize: 9, fontWeight: FontWeight.w800, color: TerminalColors.action)),
                  const SizedBox(height: 4),
                  Text(learning, style: const TextStyle(fontSize: 11, fontStyle: FontStyle.italic, color: TerminalColors.textMain)),
                ],
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text("Understood", style: TextStyle(color: TerminalColors.action, fontWeight: FontWeight.w700)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final currentPrice = _marketPrices[_selectedSymbol] ?? 1000.0;
    final totalOrderValue = currentPrice * _quantity;

    return Scaffold(
      backgroundColor: TerminalColors.canvas,
      appBar: AppBar(
        backgroundColor: TerminalColors.canvas,
        title: const Text("Simulated Paper Trading", style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: TerminalColors.textMuted, size: 20),
            onPressed: _loadData,
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Virtual Capital Header
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
                const Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text("AUTHORITATIVE VIRTUAL EQUITY", style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.textMuted)),
                    Text("Zero-Risk Simulation", style: TextStyle(fontSize: 10, fontFamily: 'monospace', color: TerminalColors.action)),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  "₹ ${_totalEquity.toStringAsFixed(2)}",
                  style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w800, fontFamily: 'monospace', color: TerminalColors.textMain),
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text("Deployable Cash", style: TextStyle(fontSize: 10, color: TerminalColors.textMuted)),
                          const SizedBox(height: 2),
                          Text("₹ ${_cashBalance.toStringAsFixed(2)}", style: const TextStyle(fontSize: 13, fontFamily: 'monospace', fontWeight: FontWeight.w700, color: TerminalColors.action)),
                        ],
                      ),
                    ),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text("Unrealized P&L", style: TextStyle(fontSize: 10, color: TerminalColors.textMuted)),
                          const SizedBox(height: 2),
                          Text(
                            "${_totalUnrealizedPnl >= 0 ? '+' : ''}₹ ${_totalUnrealizedPnl.toStringAsFixed(2)}",
                            style: TextStyle(
                              fontSize: 13,
                              fontFamily: 'monospace',
                              fontWeight: FontWeight.w700,
                              color: _totalUnrealizedPnl >= 0 ? TerminalColors.positive : TerminalColors.negative,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Order Execution Ticket
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
                const Text("ORDER TICKET", style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.textMuted)),
                const SizedBox(height: 14),

                // Side Selection (BUY / SELL)
                Row(
                  children: [
                    Expanded(
                      child: GestureDetector(
                        onTap: () => setState(() => _orderSide = "BUY"),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          decoration: BoxDecoration(
                            color: _orderSide == "BUY" ? TerminalColors.positiveBg : TerminalColors.panel,
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(color: _orderSide == "BUY" ? TerminalColors.positive : TerminalColors.borderSubtle),
                          ),
                          alignment: Alignment.center,
                          child: Text(
                            "BUY",
                            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: _orderSide == "BUY" ? TerminalColors.positive : TerminalColors.textMuted),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: GestureDetector(
                        onTap: () => setState(() => _orderSide = "SELL"),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          decoration: BoxDecoration(
                            color: _orderSide == "SELL" ? TerminalColors.negativeBg : TerminalColors.panel,
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(color: _orderSide == "SELL" ? TerminalColors.negative : TerminalColors.borderSubtle),
                          ),
                          alignment: Alignment.center,
                          child: Text(
                            "SELL",
                            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: _orderSide == "SELL" ? TerminalColors.negative : TerminalColors.textMuted),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),

                // Instrument Dropdown
                DropdownButtonFormField<String>(
                  initialValue: _selectedSymbol,
                  dropdownColor: TerminalColors.surface,
                  style: const TextStyle(fontSize: 13, color: TerminalColors.textMain, fontWeight: FontWeight.w600),
                  decoration: const InputDecoration(
                    labelText: "Instrument",
                    labelStyle: TextStyle(fontSize: 11, color: TerminalColors.textMuted),
                    filled: true,
                    fillColor: TerminalColors.panel,
                    border: OutlineInputBorder(borderSide: BorderSide(color: TerminalColors.borderSubtle)),
                  ),
                  items: _marketPrices.keys.map((sym) {
                    return DropdownMenuItem(value: sym, child: Text(sym));
                  }).toList(),
                  onChanged: (val) {
                    if (val != null) setState(() => _selectedSymbol = val);
                  },
                ),
                const SizedBox(height: 12),

                // Quantity Row
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text("Quantity (Shares)", style: TextStyle(fontSize: 12, color: TerminalColors.textMuted)),
                    Row(
                      children: [
                        IconButton(
                          icon: const Icon(Icons.remove, size: 16, color: TerminalColors.action),
                          onPressed: _quantity > 1 ? () => setState(() => _quantity--) : null,
                        ),
                        Text("$_quantity", style: const TextStyle(fontSize: 15, fontFamily: 'monospace', fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
                        IconButton(
                          icon: const Icon(Icons.add, size: 16, color: TerminalColors.action),
                          onPressed: () => setState(() => _quantity++),
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 10),

                // Summary
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text("Indicative Total", style: TextStyle(fontSize: 12, color: TerminalColors.textMuted)),
                    Text("₹ ${totalOrderValue.toStringAsFixed(2)}", style: const TextStyle(fontSize: 14, fontFamily: 'monospace', fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
                  ],
                ),
                const SizedBox(height: 16),

                // Execute Button
                SizedBox(
                  width: double.infinity,
                  height: 42,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: _orderSide == "BUY" ? TerminalColors.positive : TerminalColors.negative,
                      foregroundColor: Colors.black,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                    ),
                    onPressed: _isSubmitting ? null : _submitOrder,
                    child: Text(
                      _isSubmitting ? "ROUTING ORDER..." : "EXECUTE $_orderSide (SIMULATED)",
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, letterSpacing: 0.5),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // Open Positions List
          const Text("OPEN POSITIONS", style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.textMuted)),
          const SizedBox(height: 10),
          if (_positions.isEmpty)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: TerminalColors.surface,
                borderRadius: BorderRadius.circular(4),
                border: Border.all(color: TerminalColors.borderSubtle),
              ),
              child: const Center(
                child: Text("No open simulated positions. Deploy virtual cash above.", style: TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
              ),
            )
          else
            ..._positions.map((p) {
              final pnl = p["unrealized_pnl"] as double;
              final pnlPct = p["unrealized_pct"] as double;
              final isPos = pnl >= 0;
              return Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.all(12),
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
                        Text(p["symbol"], style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
                        const SizedBox(height: 2),
                        Text("${p['quantity']} shares · Avg ₹${(p['avg_price'] as double).toStringAsFixed(2)}", style: const TextStyle(fontSize: 10, color: TerminalColors.textMuted)),
                      ],
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text("₹${(p['market_value'] as double).toStringAsFixed(2)}", style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, fontFamily: 'monospace', color: TerminalColors.textMain)),
                        const SizedBox(height: 2),
                        Text(
                          "${isPos ? '+' : ''}₹${pnl.toStringAsFixed(2)} (${isPos ? '+' : ''}${pnlPct.toStringAsFixed(2)}%)",
                          style: TextStyle(
                            fontSize: 10,
                            fontFamily: 'monospace',
                            fontWeight: FontWeight.w700,
                            color: isPos ? TerminalColors.positive : TerminalColors.negative,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              );
            }),

          const SizedBox(height: 20),

          // Order History
          const Text("ACTIVITY & LEDGER", style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.textMuted)),
          const SizedBox(height: 10),
          if (_orderHistory.isEmpty)
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: TerminalColors.surface,
                borderRadius: BorderRadius.circular(4),
                border: Border.all(color: TerminalColors.borderSubtle),
              ),
              child: const Center(
                child: Text("No recorded orders in ledger.", style: TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
              ),
            )
          else
            ..._orderHistory.map((o) {
              final isBuy = o["side"] == "BUY";
              return Container(
                margin: const EdgeInsets.only(bottom: 6),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: TerminalColors.panel,
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: TerminalColors.borderSubtle),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                          decoration: BoxDecoration(
                            color: isBuy ? TerminalColors.positive.withValues(alpha: 0.15) : TerminalColors.negative.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(2),
                          ),
                          child: Text(o["side"], style: TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: isBuy ? TerminalColors.positive : TerminalColors.negative)),
                        ),
                        const SizedBox(width: 8),
                        Text("${o['quantity']} ${o['symbol']} @ ₹${(o['fill_price'] as double).toStringAsFixed(2)}", style: const TextStyle(fontSize: 11, color: TerminalColors.textMain)),
                      ],
                    ),
                    Text(o["time"], style: const TextStyle(fontSize: 10, color: TerminalColors.textMuted)),
                  ],
                ),
              );
            }),
        ],
      ),
    );
  }
}
