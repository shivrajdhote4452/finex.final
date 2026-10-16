import 'package:flutter/material.dart';
import '../theme/terminal_theme.dart';

class MobileSpendingScreen extends StatefulWidget {
  const MobileSpendingScreen({super.key});

  @override
  State<MobileSpendingScreen> createState() => _MobileSpendingScreenState();
}

class _MobileSpendingScreenState extends State<MobileSpendingScreen> {
  final double _totalDebit = 21649.00;
  final double _totalCredit = 50000.00;

  final List<Map<String, dynamic>> _transactions = [
    {
      "id": "TX-01",
      "date": "10 Oct",
      "amount": 15000.00,
      "type": "DEBIT",
      "desc": "ZERODHA BROKING MUTUAL FUND SIP",
      "category": "INVESTMENTS",
      "is_reviewed": true,
    },
    {
      "id": "TX-02",
      "date": "08 Oct",
      "amount": 1999.00,
      "type": "DEBIT",
      "desc": "AIRTEL FIBER BROADBAND BILLPAY ****",
      "category": "UTILITIES",
      "is_reviewed": true,
    },
    {
      "id": "TX-03",
      "date": "05 Oct",
      "amount": 3400.00,
      "type": "DEBIT",
      "desc": "BLINKIT 10 MIN GROCERIES INDIRANAGAR",
      "category": "GROCERIES",
      "is_reviewed": true,
    },
    {
      "id": "TX-04",
      "date": "02 Oct",
      "amount": 1250.00,
      "type": "DEBIT",
      "desc": "UPI/****/SWIGGY BANGALORE",
      "category": "FOOD_DINING",
      "is_reviewed": true,
    },
    {
      "id": "TX-05",
      "date": "01 Oct",
      "amount": 50000.00,
      "type": "CREDIT",
      "desc": "SALARY CREDIT FROM ACME CORP",
      "category": "INCOME",
      "is_reviewed": true,
    },
  ];

  double get _netSavings => _totalCredit - _totalDebit;
  double get _savingsRate => _totalCredit > 0 ? (_netSavings / _totalCredit) * 100.0 : 0.0;

  void _showCategoryCorrectionDialog(int index) {
    final curCat = _transactions[index]["category"];
    final categories = ["FOOD_DINING", "GROCERIES", "UTILITIES", "TRAVEL", "SHOPPING", "HEALTHCARE", "INVESTMENTS", "OTHER"];

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
              Text("Correct Category: ${_transactions[index]['desc']}", style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
              const SizedBox(height: 6),
              const Text("User corrections permanently override automated rule categorization.", style: TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
              const SizedBox(height: 14),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: categories.map((cat) {
                  final isSel = cat == curCat;
                  return ChoiceChip(
                    label: Text(cat, style: TextStyle(fontSize: 10, color: isSel ? Colors.black : TerminalColors.textMain)),
                    selected: isSel,
                    selectedColor: TerminalColors.action,
                    backgroundColor: TerminalColors.panel,
                    onSelected: (val) {
                      setState(() {
                        _transactions[index]["category"] = cat;
                      });
                      Navigator.pop(ctx);
                    },
                  );
                }).toList(),
              ),
            ],
          ),
        );
      },
    );
  }

  void _simulateCsvImport() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text("Bank Statement CSV parsed: 5 rows validated, PII masked, 0 quarantined")),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: TerminalColors.canvas,
      appBar: AppBar(
        backgroundColor: TerminalColors.canvas,
        title: const Text("Spending & Statements", style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.upload_file, size: 20, color: TerminalColors.action),
            onPressed: _simulateCsvImport,
            tooltip: "Import Statement CSV",
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Monthly Summary Card
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
                    Text("OCTOBER 2026 CASHFLOW", style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.textMuted)),
                    Text("PRIVACY MASKED", style: TextStyle(fontSize: 9, fontFamily: 'monospace', color: TerminalColors.positive, fontWeight: FontWeight.w700)),
                  ],
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text("Total Inflow", style: TextStyle(fontSize: 10, color: TerminalColors.textMuted)),
                          const SizedBox(height: 2),
                          Text("₹${_totalCredit.toStringAsFixed(2)}", style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, fontFamily: 'monospace', color: TerminalColors.positive)),
                        ],
                      ),
                    ),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text("Total Outflow", style: TextStyle(fontSize: 10, color: TerminalColors.textMuted)),
                          const SizedBox(height: 2),
                          Text("₹${_totalDebit.toStringAsFixed(2)}", style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, fontFamily: 'monospace', color: TerminalColors.negative)),
                        ],
                      ),
                    ),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text("Savings Rate", style: TextStyle(fontSize: 10, color: TerminalColors.textMuted)),
                          const SizedBox(height: 2),
                          Text("${_savingsRate.toStringAsFixed(1)}%", style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, fontFamily: 'monospace', color: TerminalColors.action)),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),

          const Text("MASKED TRANSACTIONS", style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.textMuted)),
          const SizedBox(height: 10),

          ..._transactions.asMap().entries.map((entry) {
            final idx = entry.key;
            final t = entry.value;
            final isCredit = t["type"] == "CREDIT";

            return GestureDetector(
              onTap: () => _showCategoryCorrectionDialog(idx),
              child: Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                decoration: BoxDecoration(
                  color: TerminalColors.panel,
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: TerminalColors.borderSubtle),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(t["desc"], style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: TerminalColors.textMain), maxLines: 1, overflow: TextOverflow.ellipsis),
                          const SizedBox(height: 3),
                          Row(
                            children: [
                              Text(t["date"], style: const TextStyle(fontSize: 10, color: TerminalColors.textMuted)),
                              const SizedBox(width: 8),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                                decoration: BoxDecoration(
                                  color: TerminalColors.action.withValues(alpha: 0.15),
                                  borderRadius: BorderRadius.circular(2),
                                ),
                                child: Text(t["category"], style: const TextStyle(fontSize: 8, fontFamily: 'monospace', fontWeight: FontWeight.w700, color: TerminalColors.action)),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    Text(
                      "${isCredit ? '+' : '-'}₹${(t['amount'] as double).toStringAsFixed(2)}",
                      style: TextStyle(
                        fontSize: 12,
                        fontFamily: 'monospace',
                        fontWeight: FontWeight.w700,
                        color: isCredit ? TerminalColors.positive : TerminalColors.negative,
                      ),
                    ),
                  ],
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}
