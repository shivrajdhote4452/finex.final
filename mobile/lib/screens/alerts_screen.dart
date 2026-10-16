import 'package:flutter/material.dart';
import '../theme/terminal_theme.dart';

class MobileAlertsScreen extends StatefulWidget {
  const MobileAlertsScreen({super.key});

  @override
  State<MobileAlertsScreen> createState() => _MobileAlertsScreenState();
}

class _MobileAlertsScreenState extends State<MobileAlertsScreen> {
  // Alert Rules State
  final List<Map<String, dynamic>> _rules = [
    {
      "id": "RULE-01",
      "symbol": "RELIANCE",
      "type": "PRICE_ABOVE",
      "threshold": 2600.00,
      "cooldown": "60 mins",
      "is_active": true,
    },
    {
      "id": "RULE-02",
      "symbol": "TCS",
      "type": "PRICE_ABOVE",
      "threshold": 3600.00,
      "cooldown": "60 mins",
      "is_active": true,
    },
    {
      "id": "RULE-03",
      "symbol": "PORTFOLIO",
      "type": "CONCENTRATION_EXCEEDED",
      "threshold": 30.0,
      "cooldown": "120 mins",
      "is_active": true,
    },
  ];

  // In-App Notifications State
  final List<Map<String, dynamic>> _notifications = [
    {
      "id": "NOTIF-01",
      "title": "Price Trigger: TCS reached ₹3,600.00",
      "message": "TCS traded at ₹3,600.00, surpassing your target threshold of ₹3,500.00.",
      "category": "PRICE_ALERT",
      "time": "16 Oct, 11:35 AM",
      "is_read": false,
    },
    {
      "id": "NOTIF-02",
      "title": "Portfolio Alert: Tech Sector Concentration",
      "message": "IT sector allocation stands at 35.0% of your equity portfolio.",
      "category": "PORTFOLIO_RISK",
      "time": "16 Oct, 10:15 AM",
      "is_read": false,
    },
    {
      "id": "NOTIF-03",
      "title": "EOD Market Bhavcopy Synchronized",
      "message": "Official NSE closing Bhavcopy records ingested and validated with zero discrepancies.",
      "category": "SYSTEM_NOTICE",
      "time": "15 Oct, 05:45 PM",
      "is_read": true,
    },
  ];

  String _newSymbol = "INFY";
  String _newRuleType = "PRICE_ABOVE";
  double _newThreshold = 1500.00;

  int get _unreadCount => _notifications.where((n) => !(n["is_read"] as bool)).length;

  void _markAllRead() {
    setState(() {
      for (var n in _notifications) {
        n["is_read"] = true;
      }
    });
  }

  void _toggleRule(int index) {
    setState(() {
      _rules[index]["is_active"] = !(_rules[index]["is_active"] as bool);
    });
  }

  void _showCreateRuleDialog() {
    showModalBottomSheet(
      context: context,
      backgroundColor: TerminalColors.surface,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(12)),
        side: BorderSide(color: TerminalColors.borderSubtle),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setModalState) {
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
                  const Text("Create Trigger Rule", style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
                  const SizedBox(height: 6),
                  const Text("Evaluated deterministically against verified market observations.", style: TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
                  const SizedBox(height: 16),

                  // Symbol Dropdown
                  DropdownButtonFormField<String>(
                    initialValue: _newSymbol,
                    dropdownColor: TerminalColors.surface,
                    decoration: const InputDecoration(
                      labelText: "Target Security",
                      labelStyle: TextStyle(color: TerminalColors.textMuted, fontSize: 11),
                      border: OutlineInputBorder(borderSide: BorderSide(color: TerminalColors.borderSubtle)),
                    ),
                    items: const [
                      DropdownMenuItem(value: "RELIANCE", child: Text("RELIANCE", style: TextStyle(fontSize: 12, color: TerminalColors.textMain, fontFamily: 'monospace'))),
                      DropdownMenuItem(value: "TCS", child: Text("TCS", style: TextStyle(fontSize: 12, color: TerminalColors.textMain, fontFamily: 'monospace'))),
                      DropdownMenuItem(value: "INFY", child: Text("INFY", style: TextStyle(fontSize: 12, color: TerminalColors.textMain, fontFamily: 'monospace'))),
                      DropdownMenuItem(value: "HDFCBANK", child: Text("HDFCBANK", style: TextStyle(fontSize: 12, color: TerminalColors.textMain, fontFamily: 'monospace'))),
                    ],
                    onChanged: (val) {
                      if (val != null) setModalState(() => _newSymbol = val);
                    },
                  ),
                  const SizedBox(height: 12),

                  // Rule Type
                  DropdownButtonFormField<String>(
                    initialValue: _newRuleType,
                    dropdownColor: TerminalColors.surface,
                    decoration: const InputDecoration(
                      labelText: "Condition",
                      labelStyle: TextStyle(color: TerminalColors.textMuted, fontSize: 11),
                      border: OutlineInputBorder(borderSide: BorderSide(color: TerminalColors.borderSubtle)),
                    ),
                    items: const [
                      DropdownMenuItem(value: "PRICE_ABOVE", child: Text("Price >= Threshold", style: TextStyle(fontSize: 12, color: TerminalColors.textMain))),
                      DropdownMenuItem(value: "PRICE_BELOW", child: Text("Price <= Threshold", style: TextStyle(fontSize: 12, color: TerminalColors.textMain))),
                    ],
                    onChanged: (val) {
                      if (val != null) setModalState(() => _newRuleType = val);
                    },
                  ),
                  const SizedBox(height: 12),

                  // Threshold
                  TextFormField(
                    initialValue: _newThreshold.toString(),
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(
                      labelText: "Threshold Price (₹)",
                      labelStyle: TextStyle(color: TerminalColors.textMuted, fontSize: 11),
                      border: OutlineInputBorder(borderSide: BorderSide(color: TerminalColors.borderSubtle)),
                    ),
                    style: const TextStyle(fontSize: 13, fontFamily: 'monospace', color: TerminalColors.textMain),
                    onChanged: (val) {
                      final parsed = double.tryParse(val);
                      if (parsed != null) _newThreshold = parsed;
                    },
                  ),
                  const SizedBox(height: 16),

                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: TerminalColors.action,
                        foregroundColor: Colors.black,
                      ),
                      onPressed: () {
                        setState(() {
                          _rules.insert(0, {
                            "id": "RULE-0${_rules.length + 1}",
                            "symbol": _newSymbol,
                            "type": _newRuleType,
                            "threshold": _newThreshold,
                            "cooldown": "60 mins",
                            "is_active": true,
                          });
                        });
                        Navigator.pop(ctx);
                      },
                      child: const Text("Save Alert Rule", style: TextStyle(fontWeight: FontWeight.w700)),
                    ),
                  ),
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
        title: const Text("Smart Alerts & Feed", style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
        elevation: 0,
        actions: [
          if (_unreadCount > 0)
            TextButton(
              onPressed: _markAllRead,
              child: const Text("Mark all read", style: TextStyle(fontSize: 11, color: TerminalColors.action)),
            ),
          IconButton(
            icon: const Icon(Icons.add, size: 20, color: TerminalColors.action),
            onPressed: _showCreateRuleDialog,
            tooltip: "Add Trigger Rule",
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // S6 Scenario Drawdown Stress Test Card
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
                    Text("S6 SCENARIO STRESS TEST", style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.action)),
                    Text("HYPOTHETICAL", style: TextStyle(fontSize: 9, fontFamily: 'monospace', color: TerminalColors.textMuted)),
                  ],
                ),
                const SizedBox(height: 6),
                const Text("15% Sector Drawdown Stress Test", style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
                const SizedBox(height: 4),
                const Text("Simulates instantaneous deterministic drawdown on IT holdings.", style: TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: TerminalColors.panel,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: TerminalColors.borderSubtle),
                  ),
                  child: const Column(
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text("Target Sector:", style: TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
                          Text("Information Technology", style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: TerminalColors.textMain)),
                        ],
                      ),
                      SizedBox(height: 6),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text("Baseline Portfolio:", style: TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
                          Text("₹1,00,000.00", style: TextStyle(fontSize: 11, fontFamily: 'monospace', color: TerminalColors.textMain)),
                        ],
                      ),
                      SizedBox(height: 6),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text("Estimated Impact (-15%):", style: TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
                          Text("-₹5,250.00", style: TextStyle(fontSize: 11, fontFamily: 'monospace', fontWeight: FontWeight.w700, color: TerminalColors.negative)),
                        ],
                      ),
                      SizedBox(height: 6),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text("Post-Shock Equity:", style: TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
                          Text("₹94,750.00", style: TextStyle(fontSize: 11, fontFamily: 'monospace', fontWeight: FontWeight.w700, color: TerminalColors.action)),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  "HYPOTHETICAL STRESS TEST ONLY: Tests an isolated sector shock. Not an investment forecast.",
                  style: TextStyle(fontSize: 9, color: TerminalColors.textMuted, fontStyle: FontStyle.italic),
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),

          // Active Trigger Rules Header
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text("TRIGGER RULES", style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.textMuted)),
              Text("${_rules.length} Active Rules", style: const TextStyle(fontSize: 10, color: TerminalColors.textMuted)),
            ],
          ),
          const SizedBox(height: 10),

          // Rules List
          ..._rules.asMap().entries.map((entry) {
            final idx = entry.key;
            final r = entry.value;
            final isActive = r["is_active"] as bool;
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
                      Row(
                        children: [
                          Text(r["symbol"], style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                            decoration: BoxDecoration(
                              color: TerminalColors.action.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(2),
                            ),
                            child: Text(r["type"], style: const TextStyle(fontSize: 8, fontFamily: 'monospace', fontWeight: FontWeight.w700, color: TerminalColors.action)),
                          ),
                        ],
                      ),
                      const SizedBox(height: 3),
                      Text("Threshold: ₹${r['threshold']} · Cooldown: ${r['cooldown']}", style: const TextStyle(fontSize: 10, color: TerminalColors.textMuted)),
                    ],
                  ),
                  Switch(
                    value: isActive,
                    activeThumbColor: TerminalColors.action,
                    onChanged: (val) => _toggleRule(idx),
                  ),
                ],
              ),
            );
          }),

          const SizedBox(height: 18),

          // Notification Center Feed
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text("IN-APP NOTIFICATIONS", style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.textMuted)),
              if (_unreadCount > 0)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: TerminalColors.action,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text("$_unreadCount UNREAD", style: const TextStyle(fontSize: 8, fontWeight: FontWeight.w800, color: Colors.black)),
                ),
            ],
          ),
          const SizedBox(height: 10),

          ..._notifications.map((n) {
            final isRead = n["is_read"] as bool;
            return Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: isRead ? TerminalColors.surface : TerminalColors.panel,
                borderRadius: BorderRadius.circular(4),
                border: Border.all(color: isRead ? TerminalColors.borderSubtle : TerminalColors.action.withValues(alpha: 0.5)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          if (!isRead)
                            Container(
                              width: 6,
                              height: 6,
                              margin: const EdgeInsets.only(right: 6),
                              decoration: const BoxDecoration(color: TerminalColors.action, shape: BoxShape.circle),
                            ),
                          Text(n["title"], style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
                        ],
                      ),
                      Text(n["time"], style: const TextStyle(fontSize: 9, color: TerminalColors.textMuted)),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(n["message"], style: const TextStyle(fontSize: 11, color: TerminalColors.textMuted, height: 1.3)),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }
}
