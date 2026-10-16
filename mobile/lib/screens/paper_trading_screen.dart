import 'package:flutter/material.dart';
import '../theme/terminal_theme.dart';

class MobilePaperTradingScreen extends StatefulWidget {
  const MobilePaperTradingScreen({super.key});

  @override
  State<MobilePaperTradingScreen> createState() => _MobilePaperTradingScreenState();
}

class _MobilePaperTradingScreenState extends State<MobilePaperTradingScreen> {
  // Virtual Account State
  double _cashBalance = 100000.00;
  String _selectedSymbol = "RELIANCE";
  String _orderSide = "BUY"; // "BUY" or "SELL"
  int _quantity = 10;

  final Map<String, double> _marketPrices = {
    "RELIANCE": 2500.00,
    "TCS": 3500.00,
    "INFY": 1600.00,
    "HDFCBANK": 1500.00,
    "ICICIBANK": 1050.00,
  };

  final List<Map<String, dynamic>> _positions = [
    {
      "symbol": "RELIANCE",
      "quantity": 10,
      "avg_price": 2450.00,
      "current_price": 2500.00,
      "market_value": 25000.00,
      "unrealized_pnl": 500.00,
      "unrealized_pct": 2.04,
    },
    {
      "symbol": "TCS",
      "quantity": 5,
      "avg_price": 3400.00,
      "current_price": 3500.00,
      "market_value": 17500.00,
      "unrealized_pnl": 500.00,
      "unrealized_pct": 2.94,
    },
  ];

  final List<Map<String, dynamic>> _orderHistory = [
    {
      "order_id": "ORD-PT-001",
      "symbol": "RELIANCE",
      "side": "BUY",
      "quantity": 10,
      "fill_price": 2450.00,
      "gross": 24500.00,
      "status": "FILLED",
      "time": "16 Oct, 11:30 AM",
    },
    {
      "order_id": "ORD-PT-002",
      "symbol": "TCS",
      "side": "BUY",
      "quantity": 5,
      "fill_price": 3400.00,
      "gross": 17000.00,
      "status": "FILLED",
      "time": "16 Oct, 12:15 PM",
    },
  ];

  double get _positionsMarketValue {
    return _positions.fold(0.0, (acc, item) => acc + (item["market_value"] as double));
  }

  double get _totalEquity => _cashBalance + _positionsMarketValue;

  double get _totalUnrealizedPnl {
    return _positions.fold(0.0, (acc, item) => acc + (item["unrealized_pnl"] as double));
  }

  void _submitOrder() {
    final price = _marketPrices[_selectedSymbol] ?? 1000.0;
    final totalOrderValue = price * _quantity;

    if (_orderSide == "BUY") {
      if (totalOrderValue > _cashBalance) {
        _showCoachingDialog(
          title: "Order Rejected: Insufficient Cash",
          explanation: "Required ₹${totalOrderValue.toStringAsFixed(2)}, but available virtual balance is ₹${_cashBalance.toStringAsFixed(2)}.",
          learning: "Capital Discipline: Always verify available buying power before placing equity orders.",
          isSuccess: false,
        );
        return;
      }

      setState(() {
        _cashBalance -= totalOrderValue;
        // Check if position exists
        final existingIdx = _positions.indexWhere((p) => p["symbol"] == _selectedSymbol);
        if (existingIdx >= 0) {
          final p = _positions[existingIdx];
          final oldQty = p["quantity"] as int;
          final newQty = oldQty + _quantity;
          final oldCost = (p["avg_price"] as double) * oldQty;
          final newAvg = (oldCost + totalOrderValue) / newQty;
          _positions[existingIdx] = {
            "symbol": _selectedSymbol,
            "quantity": newQty,
            "avg_price": newAvg,
            "current_price": price,
            "market_value": price * newQty,
            "unrealized_pnl": (price - newAvg) * newQty,
            "unrealized_pct": ((price - newAvg) / newAvg) * 100.0,
          };
        } else {
          _positions.add({
            "symbol": _selectedSymbol,
            "quantity": _quantity,
            "avg_price": price,
            "current_price": price,
            "market_value": totalOrderValue,
            "unrealized_pnl": 0.0,
            "unrealized_pct": 0.0,
          });
        }

        _orderHistory.insert(0, {
          "order_id": "ORD-PT-00${_orderHistory.length + 1}",
          "symbol": _selectedSymbol,
          "side": "BUY",
          "quantity": _quantity,
          "fill_price": price,
          "gross": totalOrderValue,
          "status": "FILLED",
          "time": "Just now",
        });
      });

      _showCoachingDialog(
        title: "Buy Order Filled: $_quantity $_selectedSymbol @ ₹${price.toStringAsFixed(2)}",
        explanation: "Simulated order filled immediately. ₹${totalOrderValue.toStringAsFixed(2)} deducted from virtual cash balance.",
        learning: "Opportunity Cost: Trading virtual cash for equity stakes balances potential upside against liquid cash flexibility.",
        isSuccess: true,
      );
    } else {
      // SELL
      final existingIdx = _positions.indexWhere((p) => p["symbol"] == _selectedSymbol);
      if (existingIdx < 0 || (_positions[existingIdx]["quantity"] as int) < _quantity) {
        _showCoachingDialog(
          title: "Order Rejected: Insufficient Shares",
          explanation: "You do not hold $_quantity shares of $_selectedSymbol to execute this sell order.",
          learning: "Short Selling Restriction: Cash equities do not permit naked shorting. Acquire shares first.",
          isSuccess: false,
        );
        return;
      }

      setState(() {
        _cashBalance += totalOrderValue;
        final p = _positions[existingIdx];
        final oldQty = p["quantity"] as int;
        final remainingQty = oldQty - _quantity;
        if (remainingQty == 0) {
          _positions.removeAt(existingIdx);
        } else {
          final avg = p["avg_price"] as double;
          _positions[existingIdx] = {
            "symbol": _selectedSymbol,
            "quantity": remainingQty,
            "avg_price": avg,
            "current_price": price,
            "market_value": price * remainingQty,
            "unrealized_pnl": (price - avg) * remainingQty,
            "unrealized_pct": ((price - avg) / avg) * 100.0,
          };
        }

        _orderHistory.insert(0, {
          "order_id": "ORD-PT-00${_orderHistory.length + 1}",
          "symbol": _selectedSymbol,
          "side": "SELL",
          "quantity": _quantity,
          "fill_price": price,
          "gross": totalOrderValue,
          "status": "FILLED",
          "time": "Just now",
        });
      });

      _showCoachingDialog(
        title: "Sell Order Filled: $_quantity $_selectedSymbol @ ₹${price.toStringAsFixed(2)}",
        explanation: "Liquidated $_quantity shares, crediting ₹${totalOrderValue.toStringAsFixed(2)} virtual proceeds.",
        learning: "Capital Realization: Locking in simulated returns converts fluctuating paper gains into stable cash.",
        isSuccess: true,
      );
    }
  }

  void _showCoachingDialog({
    required String title,
    required String explanation,
    required String learning,
    required bool isSuccess,
  }) {
    showModalBottomSheet(
      context: context,
      backgroundColor: TerminalColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(12)),
        side: BorderSide(color: TerminalColors.borderSubtle),
      ),
      builder: (ctx) {
        return Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
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
              const SizedBox(height: 12),
              Text(explanation, style: const TextStyle(fontSize: 12, color: TerminalColors.textMuted, height: 1.4)),
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: TerminalColors.panel,
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: TerminalColors.borderSubtle),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.lightbulb_outline, size: 14, color: TerminalColors.action),
                        SizedBox(width: 6),
                        Text("AI COACHING LESSON", style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: TerminalColors.action)),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(learning, style: const TextStyle(fontSize: 11, color: TerminalColors.textMain, height: 1.3)),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              const Text(
                "SIMULATION NOTICE: This trade execution was simulated on FinEx using verified EOD closing data. No real funds were moved.",
                style: TextStyle(fontSize: 9, color: TerminalColors.textMuted, fontStyle: FontStyle.italic),
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: TerminalColors.action,
                    foregroundColor: Colors.black,
                  ),
                  onPressed: () => Navigator.pop(ctx),
                  child: const Text("Acknowledge & Continue", style: TextStyle(fontWeight: FontWeight.w700)),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final curPrice = _marketPrices[_selectedSymbol] ?? 1000.0;
    final totalOrderValue = curPrice * _quantity;

    return Scaffold(
      backgroundColor: TerminalColors.canvas,
      appBar: AppBar(
        backgroundColor: TerminalColors.canvas,
        title: const Text("Paper Trading Desk", style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, size: 18, color: TerminalColors.textMuted),
            onPressed: () {
              setState(() {
                _cashBalance = 100000.00;
                _positions.clear();
                _orderHistory.clear();
              });
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text("Virtual paper trading account reset to ₹1,00,000 cash")),
              );
            },
            tooltip: "Reset Account",
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Virtual Account Summary Card
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
                    Text("TOTAL SIMULATED EQUITY", style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: TerminalColors.textMuted, letterSpacing: 0.5)),
                    Text("SHIVRAJ DHOTE · VIRTUAL", style: TextStyle(fontSize: 9, fontFamily: 'monospace', color: TerminalColors.action, fontWeight: FontWeight.w700)),
                  ],
                ),
                const SizedBox(height: 6),
                Text("₹${_totalEquity.toStringAsFixed(2)}", style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w800, color: TerminalColors.textMain, fontFamily: 'monospace')),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text("Cash Balance", style: TextStyle(fontSize: 10, color: TerminalColors.textMuted)),
                          const SizedBox(height: 2),
                          Text("₹${_cashBalance.toStringAsFixed(2)}", style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, fontFamily: 'monospace', color: TerminalColors.textMain)),
                        ],
                      ),
                    ),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text("Holdings Value", style: TextStyle(fontSize: 10, color: TerminalColors.textMuted)),
                          const SizedBox(height: 2),
                          Text("₹${_positionsMarketValue.toStringAsFixed(2)}", style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, fontFamily: 'monospace', color: TerminalColors.textMain)),
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
                            "${_totalUnrealizedPnl >= 0 ? '+' : ''}₹${_totalUnrealizedPnl.toStringAsFixed(2)}",
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              fontFamily: 'monospace',
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
          const SizedBox(height: 18),

          // Order Ticket Box
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: TerminalColors.panel,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: TerminalColors.borderSubtle),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text("ORDER EXECUTION TICKET", style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.textMain)),
                    Text("MARKET ORDER · ZERO SLIPPAGE", style: TextStyle(fontSize: 9, color: TerminalColors.action, fontFamily: 'monospace')),
                  ],
                ),
                const SizedBox(height: 14),

                // Side Toggle (BUY / SELL)
                Row(
                  children: [
                    Expanded(
                      child: GestureDetector(
                        onTap: () => setState(() => _orderSide = "BUY"),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          decoration: BoxDecoration(
                            color: _orderSide == "BUY" ? TerminalColors.positive.withValues(alpha: 0.2) : TerminalColors.surface,
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(color: _orderSide == "BUY" ? TerminalColors.positive : TerminalColors.borderSubtle),
                          ),
                          alignment: Alignment.center,
                          child: Text("BUY (LONG)", style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: _orderSide == "BUY" ? TerminalColors.positive : TerminalColors.textMuted)),
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
                            color: _orderSide == "SELL" ? TerminalColors.negative.withValues(alpha: 0.2) : TerminalColors.surface,
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(color: _orderSide == "SELL" ? TerminalColors.negative : TerminalColors.borderSubtle),
                          ),
                          alignment: Alignment.center,
                          child: Text("SELL (EXIT)", style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: _orderSide == "SELL" ? TerminalColors.negative : TerminalColors.textMuted)),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),

                // Symbol Dropdown
                DropdownButtonFormField<String>(
                  initialValue: _selectedSymbol,
                  dropdownColor: TerminalColors.surface,
                  decoration: const InputDecoration(
                    labelText: "Security",
                    labelStyle: TextStyle(color: TerminalColors.textMuted, fontSize: 11),
                    contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    border: OutlineInputBorder(borderSide: BorderSide(color: TerminalColors.borderSubtle)),
                  ),
                  items: _marketPrices.keys.map((sym) {
                    final p = _marketPrices[sym]!;
                    return DropdownMenuItem(
                      value: sym,
                      child: Text("$sym (₹${p.toStringAsFixed(2)})", style: const TextStyle(fontSize: 12, color: TerminalColors.textMain, fontFamily: 'monospace')),
                    );
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
                    const Text("Quantity (Shares):", style: TextStyle(fontSize: 12, color: TerminalColors.textMuted)),
                    Row(
                      children: [
                        IconButton(
                          icon: const Icon(Icons.remove, size: 16, color: TerminalColors.textMain),
                          onPressed: () {
                            if (_quantity > 1) setState(() => _quantity--);
                          },
                        ),
                        Container(
                          width: 44,
                          alignment: Alignment.center,
                          child: Text("$_quantity", style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, fontFamily: 'monospace', color: TerminalColors.textMain)),
                        ),
                        IconButton(
                          icon: const Icon(Icons.add, size: 16, color: TerminalColors.textMain),
                          onPressed: () => setState(() => _quantity++),
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 12),

                // Total Estimated Value
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text("Estimated Gross:", style: TextStyle(fontSize: 12, color: TerminalColors.textMuted)),
                    Text("₹${totalOrderValue.toStringAsFixed(2)}", style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, fontFamily: 'monospace', color: TerminalColors.action)),
                  ],
                ),
                const SizedBox(height: 16),

                // Execute Button
                SizedBox(
                  width: double.infinity,
                  height: 40,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: _orderSide == "BUY" ? TerminalColors.positive : TerminalColors.negative,
                      foregroundColor: Colors.black,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                    ),
                    onPressed: _submitOrder,
                    child: Text(
                      "EXECUTE $_orderSide (SIMULATED)",
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
