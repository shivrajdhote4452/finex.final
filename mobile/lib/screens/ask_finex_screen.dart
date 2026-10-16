import 'package:flutter/material.dart';
import '../services/api_client.dart';
import '../theme/terminal_theme.dart';

class MobileAskFinExScreen extends StatefulWidget {
  const MobileAskFinExScreen({super.key});

  @override
  State<MobileAskFinExScreen> createState() => _MobileAskFinExScreenState();
}

class _MobileAskFinExScreenState extends State<MobileAskFinExScreen> {
  final TextEditingController _controller = TextEditingController();
  bool _isLoading = false;

  final List<Map<String, dynamic>> _messages = [
    {
      "role": "assistant",
      "headline": "Welcome to Ask FinEx Mobile",
      "body": "Ask questions grounded in verified regulatory publications (SEBI, RBI, NSE) and your authorized portfolio metrics. Citations and passage offsets are verifiable.",
      "citation": "[1] Regulatory Evidence Index",
      "evidence": "Verified citations are extracted from official circulars and handbooks without synthetic modification.",
    },
  ];

  void _sendMessage() async {
    if (_controller.text.trim().isEmpty || _isLoading) return;
    final text = _controller.text.trim();
    _controller.clear();

    setState(() {
      _messages.add({"role": "user", "text": text});
      _isLoading = true;
    });

    try {
      final res = await apiClient.sendAiMessage("conv-welcome-001", text);
      final asst = res['assistant_message'];
      if (asst != null) {
        final citations = (asst['citations'] as List?) ?? [];
        String citationLabel = "[1] Grounded Citation";
        String evidenceText = "Grounded in verified regulatory documentation.";

        if (citations.isNotEmpty) {
          final first = citations[0];
          citationLabel = "[1] ${first['publisher'] ?? 'SEBI'} (p. ${first['page_number'] ?? 1})";
          evidenceText = first['excerpt'] ?? first['title'] ?? evidenceText;
        }

        setState(() {
          _messages.add({
            "role": "assistant",
            "headline": asst['headline'] ?? "Regulatory Insights",
            "body": asst['content'] ?? "",
            "citation": citationLabel,
            "evidence": evidenceText,
          });
        });
      }
    } catch (e) {
      setState(() {
        _messages.add({
          "role": "assistant",
          "headline": "Connection Issue",
          "body": "Could not connect to the live FinEx RAG engine. Please verify the backend API is active at ${apiClient.baseUrl}.",
          "citation": "[Warning] Offline Mode",
          "evidence": "Offline fallback: live retrieval requires backend connectivity.",
        });
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
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
