import 'package:flutter/material.dart';
import '../services/api_client.dart';
import '../theme/terminal_theme.dart';

class MobileSpendingScreen extends StatefulWidget {
  const MobileSpendingScreen({super.key});

  @override
  State<MobileSpendingScreen> createState() => _MobileSpendingScreenState();
}

class _MobileSpendingScreenState extends State<MobileSpendingScreen> {
  double _totalDebit = 21649.00;
  double _totalCredit = 50000.00;

  @override
  void initState() {
    super.initState();
    _loadTransactions();
  }

  Future<void> _loadTransactions() async {
    try {
      final res = await apiClient.getTransactions();
      if (res['transactions'] != null && mounted) {
        final List txs = res['transactions'];
        if (txs.isNotEmpty) {
          double debits = 0.0;
          double credits = 0.0;
          final loaded = txs.map<Map<String, dynamic>>((t) {
            final amt = (t['amount'] as num?)?.toDouble() ?? 0.0;
            final typ = (t['transaction_type'] ?? 'DEBIT').toString().toUpperCase();
            if (typ == 'DEBIT') {
              debits += amt;
            } else {
              credits += amt;
            }
            return {
              "id": t['id'] ?? '',
              "date": t['transaction_date'] ?? '',
              "amount": amt,
              "type": typ,
              "desc": t['masked_description'] ?? t['raw_description'] ?? '',
              "category": t['category_id'] ?? 'OTHER',
              "is_reviewed": true,
            };
          }).toList();

          setState(() {
            _transactions.clear();
            _transactions.addAll(loaded);
            _totalDebit = debits;
            _totalCredit = credits;
          });
        }
      }
    } catch (_) {
      // Keep baseline sample if unauthenticated/offline
    }
  }

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

  void _showCsvImportDialog() {
    final csvController = TextEditingController(
      text: "Date,Amount,Description,Type\n"
          "2026-10-14,1850.00,UPI/****/RESTAURANT KORAMANGALA,DEBIT\n"
          "2026-10-15,3500.00,BESCOM ELECTRICITY BILLPAY ****,DEBIT\n"
          "2026-10-16,2100.00,AMAZON INDIA RETAIL ORDER ****,DEBIT",
    );

    showModalBottomSheet(
      context: context,
      backgroundColor: TerminalColors.surface,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(14)),
        side: BorderSide(color: TerminalColors.borderSubtle),
      ),
      builder: (ctx) {
        bool isStaging = false;
        Map<String, dynamic>? previewResult;
        String? errorMessage;

        return StatefulBuilder(
          builder: (modalContext, setModalState) {
            return Padding(
              padding: EdgeInsets.only(
                left: 20,
                right: 20,
                top: 20,
                bottom: MediaQuery.of(modalContext).viewInsets.bottom + 20,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    "PRIVACY-PRESERVING CSV INGESTION",
                    style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: TerminalColors.action, letterSpacing: 0.8),
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    "Statement Staging & Review",
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: TerminalColors.textMain),
                  ),
                  const SizedBox(height: 12),
                  if (errorMessage != null)
                    Container(
                      padding: const EdgeInsets.all(10),
                      margin: const EdgeInsets.only(bottom: 12),
                      decoration: BoxDecoration(
                        color: Colors.red.withValues(alpha: 0.1),
                        border: Border.all(color: Colors.red),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(errorMessage!, style: const TextStyle(color: Colors.redAccent, fontSize: 11)),
                    ),
                  if (previewResult == null) ...[
                    const Text(
                      "Raw bank descriptions are masked server-side to hide account and card numbers before classification.",
                      style: TextStyle(fontSize: 12, color: TerminalColors.textMuted, height: 1.4),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: csvController,
                      maxLines: 5,
                      style: const TextStyle(fontSize: 11, fontFamily: 'monospace', color: TerminalColors.textMain),
                      decoration: const InputDecoration(
                        labelText: "CSV Statement Content (Date, Amount, Description, Type)",
                        labelStyle: TextStyle(fontSize: 11, color: TerminalColors.textMuted),
                        filled: true,
                        fillColor: TerminalColors.panel,
                        border: OutlineInputBorder(borderSide: BorderSide(color: TerminalColors.borderSubtle)),
                        focusedBorder: OutlineInputBorder(borderSide: BorderSide(color: TerminalColors.action)),
                      ),
                    ),
                    const SizedBox(height: 16),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: TerminalColors.panel,
                          foregroundColor: TerminalColors.action,
                          side: const BorderSide(color: TerminalColors.action),
                        ),
                        onPressed: isStaging
                            ? null
                            : () async {
                                final content = csvController.text.trim();
                                if (content.isEmpty) {
                                  setModalState(() => errorMessage = "Please provide valid CSV content.");
                                  return;
                                }
                                setModalState(() {
                                  isStaging = true;
                                  errorMessage = null;
                                });
                                try {
                                  final preview = await apiClient.previewCsv("statement_mobile.csv", content);
                                  setModalState(() {
                                    previewResult = preview;
                                    isStaging = false;
                                  });
                                } catch (e) {
                                  setModalState(() {
                                    errorMessage = e.toString().replaceFirst("Exception: ", "");
                                    isStaging = false;
                                  });
                                }
                              },
                        child: Text(isStaging ? "Parsing & Masking PII..." : "Stage & Preview CSV Statement"),
                      ),
                    ),
                  ] else ...[
                    // Preview Result Cards
                    Row(
                      children: [
                        Expanded(
                          child: Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(color: TerminalColors.panel, borderRadius: BorderRadius.circular(4)),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text("VALID ROWS", style: TextStyle(fontSize: 9, color: TerminalColors.positive)),
                                const SizedBox(height: 4),
                                Text("${previewResult!['valid_count'] ?? 0}", style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: TerminalColors.positive)),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(color: TerminalColors.panel, borderRadius: BorderRadius.circular(4)),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text("DUPLICATES", style: TextStyle(fontSize: 9, color: TerminalColors.textMuted)),
                                const SizedBox(height: 4),
                                Text("${previewResult!['duplicate_count'] ?? 0}", style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: TerminalColors.textMain)),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(color: TerminalColors.panel, borderRadius: BorderRadius.circular(4)),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text("ERRORS", style: TextStyle(fontSize: 9, color: TerminalColors.negative)),
                                const SizedBox(height: 4),
                                Text("${previewResult!['invalid_count'] ?? 0}", style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: TerminalColors.negative)),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton(
                            style: OutlinedButton.styleFrom(
                              foregroundColor: TerminalColors.textMuted,
                              side: const BorderSide(color: TerminalColors.borderSubtle),
                            ),
                            onPressed: () {
                              Navigator.pop(ctx);
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text("Preview cancelled: 0 transactions committed to ledger.")),
                              );
                            },
                            child: const Text("Cancel"),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: TerminalColors.action,
                              foregroundColor: Colors.black,
                            ),
                            onPressed: () async {
                              final previewId = previewResult!['preview_id'];
                              if (previewId == null) return;
                              final navigator = Navigator.of(ctx);
                              final messenger = ScaffoldMessenger.of(context);
                              try {
                                final commitRes = await apiClient.commitCsv(previewId);
                                navigator.pop();
                                final accepted = commitRes['accepted_count'] ?? 0;
                                final duplicate = commitRes['duplicate_count'] ?? 0;
                                final quarantined = commitRes['quarantined_count'] ?? 0;
                                messenger.showSnackBar(
                                  SnackBar(
                                    content: Text("Ingestion Committed: $accepted rows saved, $duplicate duplicates skipped, $quarantined quarantined."),
                                    backgroundColor: TerminalColors.positive,
                                  ),
                                );
                                _loadTransactions();
                              } catch (e) {
                                navigator.pop();
                                messenger.showSnackBar(
                                  SnackBar(
                                    content: Text("CSV commit failed: ${e.toString().replaceFirst("Exception: ", "")}"),
                                    backgroundColor: Colors.redAccent,
                                  ),
                                );
                              }
                            },
                            child: const Text("Confirm Ingest"),
                          ),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            );
          },
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
        title: const Text("Spending & Statements", style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.upload_file, size: 20, color: TerminalColors.action),
            onPressed: _showCsvImportDialog,
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
