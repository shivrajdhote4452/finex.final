import 'package:flutter/material.dart';
import '../theme/terminal_theme.dart';

class MobileAskFinExScreen extends StatefulWidget {
  const MobileAskFinExScreen({super.key});

  @override
  State<MobileAskFinExScreen> createState() => _MobileAskFinExScreenState();
}

class _MobileAskFinExScreenState extends State<MobileAskFinExScreen> {
  final TextEditingController _controller = TextEditingController();

  final List<Map<String, dynamic>> _messages = [
    {
      "role": "user",
      "text": "Which holding is the largest in my portfolio?",
    },
    {
      "role": "assistant",
      "headline": "TCS is your largest holding.",
      "body": "In this illustrated portfolio, TCS is valued at ₹ 36,000. That is 36.2% of invested holdings worth ₹ 99,500. Cash is excluded. [1]",
      "citation": "[1] Open holdings snapshot",
      "evidence": "TCS: ₹ 36,000 / Holdings: ₹ 99,500 (36.2%). SEBI guideline: avoid single-stock concentration above 30%.",
    },
  ];

  void _sendMessage() {
    if (_controller.text.trim().isEmpty) return;
    final text = _controller.text;
    _controller.clear();

    setState(() {
      _messages.add({"role": "user", "text": text});
    });

    Future.delayed(const Duration(milliseconds: 400), () {
      setState(() {
        _messages.add({
          "role": "assistant",
          "headline": "Asset allocation balances risk across sectors.",
          "body": "According to the SEBI Investor Education Handbook, diversifying into multiple sectors reduces drawdown impact. [2]",
          "citation": "[2] SEBI Investor Education Handbook (p. 14)",
          "evidence": "Sector weights: Technology (42%), Energy (25%), Financials (24%).",
        });
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Top Evidence Status
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          color: TerminalColors.panel,
          child: const Row(
            children: [
              Icon(Icons.verified_outlined, size: 14, color: TerminalColors.positive),
              SizedBox(width: 6),
              Text(
                "Grounded in SEBI & RBI regulatory guides",
                style: TextStyle(fontSize: 11, color: TerminalColors.textMuted),
              ),
            ],
          ),
        ),

        // Chat Messages Stream
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: _messages.length,
            itemBuilder: (context, idx) {
              final msg = _messages[idx];
              final isUser = msg['role'] == 'user';

              if (isUser) {
                return Align(
                  alignment: Alignment.centerRight,
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 12),
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    decoration: BoxDecoration(
                      color: TerminalColors.actionBg,
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(color: const Color(0x4DF29A60)),
                    ),
                    child: Text(
                      msg['text'],
                      style: const TextStyle(fontSize: 13, color: TerminalColors.textMain),
                    ),
                  ),
                );
              }

              return Container(
                margin: const EdgeInsets.only(bottom: 16),
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
                      children: [
                        Text(
                          "FINEX ASSISTANT",
                          style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.action),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      msg['headline'],
                      style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: TerminalColors.textMain),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      msg['body'],
                      style: const TextStyle(fontSize: 12, height: 1.5, color: TerminalColors.textMuted),
                    ),
                    const SizedBox(height: 10),
                    // Evidence Card
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: TerminalColors.panel,
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: TerminalColors.borderMedium),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.menu_book_outlined, size: 14, color: TerminalColors.action),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              msg['citation'] ?? '',
                              style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: TerminalColors.action),
                            ),
                          ),
                          const Icon(Icons.arrow_forward, size: 12, color: TerminalColors.action),
                        ],
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
        ),

        // Input Composer
        Container(
          padding: const EdgeInsets.all(12),
          decoration: const BoxDecoration(
            color: TerminalColors.surface,
            border: Border(top: BorderSide(color: TerminalColors.borderSubtle)),
          ),
          child: Row(
            children: [
              Expanded(
                child: Container(
                  height: 38,
                  decoration: BoxDecoration(
                    color: TerminalColors.input,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: TerminalColors.borderSubtle),
                  ),
                  child: TextField(
                    controller: _controller,
                    onSubmitted: (_) => _sendMessage(),
                    style: const TextStyle(fontSize: 12, color: TerminalColors.textMain),
                    decoration: const InputDecoration(
                      hintText: "Ask a follow-up question...",
                      hintStyle: TextStyle(fontSize: 12, color: TerminalColors.textMuted),
                      border: InputBorder.none,
                      contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              GestureDetector(
                onTap: _sendMessage,
                child: Container(
                  height: 38,
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  decoration: BoxDecoration(
                    color: TerminalColors.action,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  alignment: Alignment.center,
                  child: const Text(
                    "Send",
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Colors.black),
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
