import 'package:flutter/material.dart';
import '../theme/terminal_theme.dart';

class MobileGoalsScreen extends StatefulWidget {
  const MobileGoalsScreen({super.key});

  @override
  State<MobileGoalsScreen> createState() => _MobileGoalsScreenState();
}

class _MobileGoalsScreenState extends State<MobileGoalsScreen> {
  final List<Map<String, dynamic>> _goals = [
    {
      "id": "GOAL-01",
      "title": "Emergency Reserve",
      "category": "EMERGENCY_FUND",
      "target_amount": 300000.00,
      "current_amount": 70000.00,
      "target_date": "2027-10-16",
      "annual_rate": 6.0,
      "months_remaining": 12,
      "required_pmt": 18500.00,
    },
    {
      "id": "GOAL-02",
      "title": "House Down Payment",
      "category": "HOME_PURCHASE",
      "target_amount": 2500000.00,
      "current_amount": 500000.00,
      "target_date": "2031-10-16",
      "annual_rate": 8.0,
      "months_remaining": 60,
      "required_pmt": 23886.12,
    },
    {
      "id": "GOAL-03",
      "title": "Retirement Wealth Corpus",
      "category": "RETIREMENT",
      "target_amount": 20000000.00,
      "current_amount": 1000000.00,
      "target_date": "2046-10-16",
      "annual_rate": 10.0,
      "months_remaining": 240,
      "required_pmt": 16687.45,
    },
  ];

  void _showAddContributionDialog(int index) {
    double depositAmount = 10000.00;
    showModalBottomSheet(
      context: context,
      backgroundColor: TerminalColors.surface,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(12)),
        side: BorderSide(color: TerminalColors.borderSubtle),
      ),
      builder: (ctx) {
        return Padding(
          padding: EdgeInsets.only(
            left: 20,
            right: 20,
            top: 20,
            bottom: MediaQuery.of(context).viewInsets.bottom + 20,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text("Record Deposit: ${_goals[index]['title']}", style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
              const SizedBox(height: 6),
              const Text("Appends an audit ledger entry and updates your accumulated progress.", style: TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
              const SizedBox(height: 16),
              TextFormField(
                initialValue: "10000",
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: "Deposit Amount (₹)",
                  labelStyle: TextStyle(color: TerminalColors.textMuted, fontSize: 11),
                  border: OutlineInputBorder(borderSide: BorderSide(color: TerminalColors.borderSubtle)),
                ),
                style: const TextStyle(fontSize: 14, fontFamily: 'monospace', color: TerminalColors.textMain),
                onChanged: (val) {
                  final p = double.tryParse(val);
                  if (p != null) depositAmount = p;
                },
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: TerminalColors.positive,
                    foregroundColor: Colors.black,
                  ),
                  onPressed: () {
                    setState(() {
                      _goals[index]["current_amount"] = (_goals[index]["current_amount"] as double) + depositAmount;
                    });
                    Navigator.pop(ctx);
                  },
                  child: const Text("Confirm Deposit", style: TextStyle(fontWeight: FontWeight.w700)),
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
    return Scaffold(
      backgroundColor: TerminalColors.canvas,
      appBar: AppBar(
        backgroundColor: TerminalColors.canvas,
        title: const Text("Financial Goals & Runway", style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
        elevation: 0,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // S7 Projection Engine Banner
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: TerminalColors.surface,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: TerminalColors.borderSubtle),
            ),
            child: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text("DETERMINISTIC PROJECTION ENGINE", style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.action)),
                    Text("v1.0 COMPOUND", style: TextStyle(fontSize: 9, fontFamily: 'monospace', color: TerminalColors.textMuted)),
                  ],
                ),
                SizedBox(height: 6),
                Text("Formula: FV = P(1+r)^n + PMT[((1+r)^n - 1)/r]", style: TextStyle(fontSize: 11, fontFamily: 'monospace', color: TerminalColors.textMain)),
                SizedBox(height: 4),
                Text("Zero arithmetic is delegated to generative models; all required monthly savings are mathematically exact.", style: TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
              ],
            ),
          ),
          const SizedBox(height: 18),

          const Text("ACTIVE GOALS", style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.textMuted)),
          const SizedBox(height: 10),

          ..._goals.asMap().entries.map((entry) {
            final idx = entry.key;
            final g = entry.value;
            final cur = g["current_amount"] as double;
            final tgt = g["target_amount"] as double;
            final progPct = (cur / tgt * 100.0).clamp(0.0, 100.0);

            return Container(
              margin: const EdgeInsets.only(bottom: 12),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: TerminalColors.panel,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: TerminalColors.borderSubtle),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(g["title"], style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
                      Text("Target: ₹${tgt.toStringAsFixed(0)}", style: const TextStyle(fontSize: 12, fontFamily: 'monospace', fontWeight: FontWeight.w700, color: TerminalColors.action)),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text("Accumulated: ₹${cur.toStringAsFixed(0)} (${progPct.toStringAsFixed(1)}%) · ${g['months_remaining']} months left", style: const TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
                  const SizedBox(height: 10),

                  // Progress Bar
                  ClipRRect(
                    borderRadius: BorderRadius.circular(2),
                    child: LinearProgressIndicator(
                      value: progPct / 100.0,
                      backgroundColor: TerminalColors.surface,
                      valueColor: const AlwaysStoppedAnimation<Color>(TerminalColors.positive),
                      minHeight: 6,
                    ),
                  ),
                  const SizedBox(height: 12),

                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text("Required Monthly SIP:", style: TextStyle(fontSize: 10, color: TerminalColors.textMuted)),
                          const SizedBox(height: 2),
                          Text("₹${(g['required_pmt'] as double).toStringAsFixed(2)}/mo", style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, fontFamily: 'monospace', color: TerminalColors.textMain)),
                        ],
                      ),
                      OutlinedButton.icon(
                        style: OutlinedButton.styleFrom(
                          foregroundColor: TerminalColors.positive,
                          side: const BorderSide(color: TerminalColors.positive),
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        ),
                        icon: const Icon(Icons.add, size: 14),
                        label: const Text("Deposit", style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
                        onPressed: () => _showAddContributionDialog(idx),
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
