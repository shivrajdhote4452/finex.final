import 'package:flutter/material.dart';
import '../theme/terminal_theme.dart';
import '../services/api_client.dart';

class MobileChartScreen extends StatefulWidget {
  final String initialSymbol;

  const MobileChartScreen({super.key, this.initialSymbol = 'RELIANCE'});

  @override
  State<MobileChartScreen> createState() => _MobileChartScreenState();
}

class _MobileChartScreenState extends State<MobileChartScreen> {
  late String _symbol;
  String _timeframe = '1D';
  String _range = '1Y';
  bool _showCandlesticks = true;
  bool _showSma20 = true;
  final bool _showVolume = true;

  bool _loading = true;
  String? _error;
  List<Map<String, dynamic>> _bars = [];
  Map<String, dynamic>? _modeInfo;
  int? _hoverIndex;

  // Order Ticket state
  String _orderSide = 'BUY';
  double _orderQty = 5;
  String _orderType = 'MARKET';
  double? _limitPrice;
  bool _orderSubmitting = false;
  String? _orderFeedback;

  static const List<Map<String, String>> _popularSymbols = [
    {'symbol': 'RELIANCE', 'name': 'Reliance Industries', 'sector': 'Energy'},
    {'symbol': 'TCS', 'name': 'Tata Consultancy Services', 'sector': 'Technology'},
    {'symbol': 'INFY', 'name': 'Infosys Limited', 'sector': 'Technology'},
    {'symbol': 'HDFCBANK', 'name': 'HDFC Bank', 'sector': 'Banking'},
    {'symbol': 'ICICIBANK', 'name': 'ICICI Bank', 'sector': 'Banking'},
    {'symbol': 'SBIN', 'name': 'State Bank of India', 'sector': 'Banking'},
    {'symbol': 'KOTAKBANK', 'name': 'Kotak Mahindra Bank', 'sector': 'Banking'},
    {'symbol': 'AXISBANK', 'name': 'Axis Bank', 'sector': 'Banking'},
    {'symbol': 'TATAMOTORS', 'name': 'Tata Motors', 'sector': 'Automobile'},
    {'symbol': 'MARUTI', 'name': 'Maruti Suzuki', 'sector': 'Automobile'},
    {'symbol': 'BAJFINANCE', 'name': 'Bajaj Finance', 'sector': 'Financial'},
    {'symbol': 'BHARTIARTL', 'name': 'Bharti Airtel', 'sector': 'Telecom'},
    {'symbol': 'ITC', 'name': 'ITC Limited', 'sector': 'Consumer'},
    {'symbol': 'HINDUNILVR', 'name': 'Hindustan Unilever', 'sector': 'Consumer'},
    {'symbol': 'LT', 'name': 'Larsen & Toubro', 'sector': 'Infrastructure'},
    {'symbol': 'SUNPHARMA', 'name': 'Sun Pharma', 'sector': 'Pharma'},
    {'symbol': 'TITAN', 'name': 'Titan Company', 'sector': 'Consumer'},
    {'symbol': 'TATASTEEL', 'name': 'Tata Steel', 'sector': 'Metals'},
    {'symbol': 'JSWSTEEL', 'name': 'JSW Steel', 'sector': 'Metals'},
    {'symbol': 'ADANIENT', 'name': 'Adani Enterprises', 'sector': 'Energy'},
    {'symbol': 'NTPC', 'name': 'NTPC Limited', 'sector': 'Power'},
    {'symbol': 'ONGC', 'name': 'Oil & Natural Gas Corp', 'sector': 'Energy'},
    {'symbol': 'POWERGRID', 'name': 'Power Grid Corp', 'sector': 'Power'},
    {'symbol': 'COALINDIA', 'name': 'Coal India', 'sector': 'Mining'},
    {'symbol': 'HAL', 'name': 'Hindustan Aeronautics', 'sector': 'Defense'},
    {'symbol': 'BEL', 'name': 'Bharat Electronics', 'sector': 'Defense'},
    {'symbol': 'ZOMATO', 'name': 'Zomato Limited', 'sector': 'Consumer'},
    {'symbol': 'PAYTM', 'name': 'One97 Communications', 'sector': 'Fintech'},
  ];

  @override
  void initState() {
    super.initState();
    _symbol = widget.initialSymbol;
    _fetchChartData();
  }

  Future<void> _fetchChartData() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final modeRes = await apiClient.getMarketMode();
      final historyRes = await apiClient.getMarketHistory(
        _symbol,
        interval: _timeframe,
        range: _range,
      );

      final rawBars = List<Map<String, dynamic>>.from(historyRes['bars'] ?? []);
      // Sort bars chronologically
      rawBars.sort((a, b) => (a['date'] ?? '').compareTo(b['date'] ?? ''));

      setState(() {
        _modeInfo = modeRes;
        _bars = rawBars;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  void _openStockSearchModal() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: TerminalColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) {
        String filterQuery = '';
        String selectedSector = 'All';
        final sectors = ['All', 'Banking', 'Technology', 'Energy', 'Automobile', 'Consumer', 'Metals', 'Defense'];

        return StatefulBuilder(
          builder: (context, setModalState) {
            final filtered = _popularSymbols.where((s) {
              final matchQuery = s['symbol']!.toLowerCase().contains(filterQuery.toLowerCase()) ||
                  s['name']!.toLowerCase().contains(filterQuery.toLowerCase());
              final matchSector = selectedSector == 'All' || s['sector'] == selectedSector;
              return matchQuery && matchSector;
            }).toList();

            return Padding(
              padding: EdgeInsets.only(
                bottom: MediaQuery.of(context).viewInsets.bottom + 16,
                top: 16,
                left: 16,
                right: 16,
              ),
              child: SizedBox(
                height: 520,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          "Select Stock",
                          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: TerminalColors.textMain),
                        ),
                        IconButton(
                          icon: const Icon(Icons.close, size: 20, color: TerminalColors.textMuted),
                          onPressed: () => Navigator.pop(ctx),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      autofocus: true,
                      style: const TextStyle(fontSize: 14, color: Colors.white),
                      decoration: InputDecoration(
                        hintText: "Search 40+ stocks (e.g. TATASTEEL, INFY)...",
                        hintStyle: const TextStyle(fontSize: 13, color: TerminalColors.textMuted),
                        prefixIcon: const Icon(Icons.search, color: TerminalColors.action, size: 20),
                        filled: true,
                        fillColor: TerminalColors.panel,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8),
                          borderSide: const BorderSide(color: TerminalColors.borderSubtle),
                        ),
                      ),
                      onChanged: (val) => setModalState(() => filterQuery = val),
                    ),
                    const SizedBox(height: 10),
                    SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: Row(
                        children: [
                          for (final sec in sectors)
                            Padding(
                              padding: const EdgeInsets.only(right: 6),
                              child: ChoiceChip(
                                label: Text(sec, style: const TextStyle(fontSize: 11)),
                                selected: selectedSector == sec,
                                selectedColor: TerminalColors.action.withValues(alpha: 0.2),
                                labelStyle: TextStyle(
                                  color: selectedSector == sec ? TerminalColors.action : TerminalColors.textMuted,
                                  fontWeight: FontWeight.w600,
                                ),
                                backgroundColor: TerminalColors.panel,
                                onSelected: (sel) {
                                  if (sel) setModalState(() => selectedSector = sec);
                                },
                              ),
                            ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 10),
                    Expanded(
                      child: ListView.separated(
                        itemCount: filtered.length,
                        separatorBuilder: (_, __) => const Divider(color: TerminalColors.borderSubtle, height: 1),
                        itemBuilder: (context, idx) {
                          final item = filtered[idx];
                          final isSelected = item['symbol'] == _symbol;
                          return ListTile(
                            dense: true,
                            contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            leading: CircleAvatar(
                              radius: 16,
                              backgroundColor: isSelected ? TerminalColors.action : TerminalColors.panel,
                              child: Text(
                                item['symbol']!.substring(0, 2),
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.bold,
                                  color: isSelected ? Colors.black : Colors.white,
                                ),
                              ),
                            ),
                            title: Text(
                              item['symbol']!,
                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white),
                            ),
                            subtitle: Text(
                              item['name']!,
                              style: const TextStyle(fontSize: 11, color: TerminalColors.textMuted),
                            ),
                            trailing: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: TerminalColors.panel,
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                item['sector']!,
                                style: const TextStyle(fontSize: 10, color: TerminalColors.textMuted),
                              ),
                            ),
                            onTap: () {
                              Navigator.pop(ctx);
                              setState(() {
                                _symbol = item['symbol']!;
                              });
                              _fetchChartData();
                            },
                          );
                        },
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  void _openOrderSheet() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: TerminalColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(12)),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setSheetState) {
            final latestBar = _bars.isNotEmpty ? _bars.last : null;
            final double currentPrice = latestBar != null
                ? double.tryParse(latestBar['close'].toString()) ?? 2500.0
                : 2500.0;
            final effectivePrice = _orderType == 'LIMIT' && _limitPrice != null ? _limitPrice! : currentPrice;
            final total = _orderQty * effectivePrice;

            return Padding(
              padding: EdgeInsets.only(
                bottom: MediaQuery.of(context).viewInsets.bottom + 16,
                top: 16,
                left: 16,
                right: 16,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        "Paper Order Ticket: $_symbol",
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: TerminalColors.textMain),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close, size: 18, color: TerminalColors.textMuted),
                        onPressed: () => Navigator.pop(ctx),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  // Buy / Sell Selector
                  Row(
                    children: [
                      Expanded(
                        child: ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: _orderSide == 'BUY' ? TerminalColors.positive : TerminalColors.panel,
                            foregroundColor: Colors.white,
                          ),
                          onPressed: () => setSheetState(() => _orderSide = 'BUY'),
                          child: const Text("PAPER BUY", style: TextStyle(fontWeight: FontWeight.bold)),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: _orderSide == 'SELL' ? TerminalColors.negative : TerminalColors.panel,
                            foregroundColor: Colors.white,
                          ),
                          onPressed: () => setSheetState(() => _orderSide = 'SELL'),
                          child: const Text("PAPER SELL", style: TextStyle(fontWeight: FontWeight.bold)),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  // Order Type & Quantity
                  Row(
                    children: [
                      Expanded(
                        child: DropdownButtonFormField<String>(
                          initialValue: _orderType,
                          dropdownColor: TerminalColors.surface,
                          decoration: const InputDecoration(
                            labelText: "Order Type",
                            labelStyle: TextStyle(fontSize: 12, color: TerminalColors.textMuted),
                          ),
                          items: const [
                            DropdownMenuItem(value: 'MARKET', child: Text("Market")),
                            DropdownMenuItem(value: 'LIMIT', child: Text("Limit")),
                          ],
                          onChanged: (val) => setSheetState(() => _orderType = val ?? 'MARKET'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TextFormField(
                          initialValue: _orderQty.toStringAsFixed(0),
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(
                            labelText: "Quantity (Shares)",
                            labelStyle: TextStyle(fontSize: 12, color: TerminalColors.textMuted),
                          ),
                          onChanged: (val) {
                            final parsed = double.tryParse(val);
                            if (parsed != null && parsed > 0) {
                              setSheetState(() => _orderQty = parsed);
                            }
                          },
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  // Estimated Total
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: TerminalColors.panel,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: TerminalColors.borderSubtle),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text("Estimated Total:", style: TextStyle(fontSize: 12, color: TerminalColors.textMuted)),
                        Text(
                          "₹${total.toStringAsFixed(2)}",
                          style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: TerminalColors.textMain),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                  if (_orderFeedback != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Text(
                        _orderFeedback!,
                        style: TextStyle(
                          fontSize: 11,
                          color: _orderFeedback!.contains('success') ? TerminalColors.positive : TerminalColors.negative,
                        ),
                      ),
                    ),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: _orderSide == 'BUY' ? TerminalColors.positive : TerminalColors.negative,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                      onPressed: _orderSubmitting
                          ? null
                          : () async {
                              setSheetState(() => _orderSubmitting = true);
                              try {
                                await apiClient.submitOrder(
                                  symbol: _symbol,
                                  side: _orderSide,
                                  orderType: _orderType,
                                  quantity: _orderQty,
                                  limitPrice: _orderType == 'LIMIT' ? _limitPrice : null,
                                );
                                setSheetState(() {
                                  _orderSubmitting = false;
                                  _orderFeedback = "Simulated fill recorded successfully!";
                                });
                                if (ctx.mounted) {
                                  Navigator.pop(ctx);
                                }
                              } catch (e) {
                                setSheetState(() {
                                  _orderSubmitting = false;
                                  _orderFeedback = "Order rejected: ${e.toString()}";
                                });
                              }
                            },
                      child: Text(
                        _orderSubmitting ? "Submitting..." : "Submit Paper $_orderSide",
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
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

  void _openAiAssistantSheet() {
    final textController = TextEditingController();
    String? aiReply;
    bool aiThinking = false;
    Map<String, dynamic>? activeProposal;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: TerminalColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(12)),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setSheetState) {
            return Padding(
              padding: EdgeInsets.only(
                bottom: MediaQuery.of(context).viewInsets.bottom + 16,
                top: 16,
                left: 16,
                right: 16,
              ),
              child: SizedBox(
                height: 420,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Row(
                          children: [
                            Icon(Icons.auto_awesome, color: TerminalColors.action, size: 18),
                            SizedBox(width: 8),
                            Text(
                              "FinEx Gemini Assistant",
                              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: TerminalColors.textMain),
                            ),
                          ],
                        ),
                        IconButton(
                          icon: const Icon(Icons.close, size: 18, color: TerminalColors.textMuted),
                          onPressed: () => Navigator.pop(ctx),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Expanded(
                      child: Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: TerminalColors.panel,
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: TerminalColors.borderSubtle),
                        ),
                        child: SingleChildScrollView(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                aiReply ??
                                    "Ask about this $_symbol chart in English, Hindi, or Hinglish, or ask to allocate virtual paper investments.",
                                style: const TextStyle(fontSize: 12, color: TerminalColors.textMain, height: 1.4),
                              ),
                              if (activeProposal != null) ...[
                                const SizedBox(height: 12),
                                Container(
                                  padding: const EdgeInsets.all(8),
                                  decoration: BoxDecoration(
                                    color: Colors.black,
                                    borderRadius: BorderRadius.circular(4),
                                    border: Border.all(color: TerminalColors.action),
                                  ),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      const Text("📋 Paper Investment Proposal",
                                          style: TextStyle(
                                              fontSize: 11,
                                              fontWeight: FontWeight.bold,
                                              color: TerminalColors.action)),
                                      const SizedBox(height: 4),
                                      Text(
                                          "Budget: ${activeProposal!['currency']} ${activeProposal!['total_budget']}",
                                          style: const TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
                                      const SizedBox(height: 8),
                                      ElevatedButton(
                                        style: ElevatedButton.styleFrom(
                                          backgroundColor: TerminalColors.action,
                                          foregroundColor: Colors.black,
                                        ),
                                        onPressed: () async {
                                          try {
                                            await apiClient.executeProposal(activeProposal!['proposal_id']);
                                            setSheetState(() {
                                              aiReply = "Proposal executed successfully! Paper orders recorded in ledger.";
                                              activeProposal = null;
                                            });
                                          } catch (err) {
                                            setSheetState(() => aiReply = "Execution failed: $err");
                                          }
                                        },
                                        child: const Text("Execute Paper Proposal",
                                            style: TextStyle(fontWeight: FontWeight.bold)),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: textController,
                            style: const TextStyle(fontSize: 12, color: Colors.white),
                            decoration: const InputDecoration(
                              hintText: "Explain RSI or say 'Invest INR 10,000'...",
                              hintStyle: TextStyle(fontSize: 11, color: TerminalColors.textMuted),
                              isDense: true,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        IconButton(
                          icon: aiThinking
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2, color: TerminalColors.action),
                                )
                              : const Icon(Icons.send, color: TerminalColors.action, size: 20),
                          onPressed: aiThinking
                              ? null
                              : () async {
                                  final text = textController.text.trim();
                                  if (text.isEmpty) return;
                                  textController.clear();
                                  setSheetState(() => aiThinking = true);
                                  try {
                                    final res = await apiClient.sendGeminiAssistantMessage(
                                      text,
                                      chartContext: {
                                        'symbol': _symbol,
                                        'timeframe': _timeframe,
                                        'data_mode': _modeInfo?['mode'],
                                      },
                                    );
                                    setSheetState(() {
                                      aiReply = res['reply'];
                                      activeProposal = res['proposal'];
                                      aiThinking = false;
                                    });
                                  } catch (e) {
                                    setSheetState(() {
                                      aiReply = "Assistant error: ${e.toString()}";
                                      aiThinking = false;
                                    });
                                  }
                                },
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final latestBar = _bars.isNotEmpty ? _bars.last : null;
    final double currentPrice = latestBar != null
        ? double.tryParse(latestBar['close'].toString()) ?? 2500.0
        : 2500.0;
    final double openPrice = latestBar != null
        ? double.tryParse(latestBar['open'].toString()) ?? currentPrice
        : currentPrice;
    final double changeVal = currentPrice - openPrice;
    final double changePct = openPrice > 0 ? (changeVal / openPrice) * 100 : 0.0;
    final bool isPositive = changeVal >= 0;

    return Scaffold(
      backgroundColor: TerminalColors.canvas,
      appBar: AppBar(
        title: InkWell(
          onTap: _openStockSearchModal,
          borderRadius: BorderRadius.circular(6),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  _symbol,
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                    fontFamily: 'monospace',
                  ),
                ),
                const SizedBox(width: 4),
                const Icon(Icons.arrow_drop_down, color: TerminalColors.action, size: 20),
              ],
            ),
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.auto_awesome, color: TerminalColors.action),
            tooltip: "Ask Gemini Assistant",
            onPressed: _openAiAssistantSheet,
          ),
          IconButton(
            icon: const Icon(Icons.shopping_cart_outlined, color: TerminalColors.positive),
            tooltip: "Paper Order Ticket",
            onPressed: _openOrderSheet,
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Top Mini Header: Price & Feed Status
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              color: TerminalColors.surface,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        "${_modeInfo?['currency'] == 'USD' ? '\$' : '₹'}${currentPrice.toStringAsFixed(2)}",
                        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, fontFamily: 'monospace'),
                      ),
                      Text(
                        "${isPositive ? '+' : ''}${changeVal.toStringAsFixed(2)} (${isPositive ? '+' : ''}${changePct.toStringAsFixed(2)}%)",
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: isPositive ? TerminalColors.positive : TerminalColors.negative,
                        ),
                      ),
                    ],
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: TerminalColors.panel,
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(color: TerminalColors.borderSubtle),
                    ),
                    child: Text(
                      _modeInfo?['mode']?.contains('US') == true
                          ? "Live IEX (USD Paper)"
                          : "NSE Historical Replay (${_modeInfo?['lag_days'] ?? 30}D Lag)",
                      style: const TextStyle(fontSize: 10, color: TerminalColors.textMuted, fontWeight: FontWeight.w600),
                    ),
                  ),
                ],
              ),
            ),

            // Groww-style Range Bar
            Container(
              height: 34,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              color: const Color(0xFF14171F),
              child: Row(
                children: [
                  for (final rng in ['1D', '1W', '1M', '3M', '6M', '1Y', '5Y', 'ALL'])
                    Padding(
                      padding: const EdgeInsets.only(right: 4),
                      child: GestureDetector(
                        onTap: () {
                          setState(() {
                            _range = rng;
                            if (rng == '1D') {
                              _timeframe = '5m';
                            } else if (rng == '1W') {
                              _timeframe = '15m';
                            } else if (rng == '1M') {
                              _timeframe = '1h';
                            } else {
                              _timeframe = '1D';
                            }
                          });
                          _fetchChartData();
                        },
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: _range == rng ? TerminalColors.action.withValues(alpha: 0.2) : Colors.transparent,
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(
                              color: _range == rng ? TerminalColors.action : Colors.transparent,
                              width: 1,
                            ),
                          ),
                          child: Text(
                            rng,
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: _range == rng ? FontWeight.bold : FontWeight.w500,
                              color: _range == rng ? TerminalColors.action : TerminalColors.textMuted,
                            ),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),

            // Timeframe Selector & Indicators bar
            Container(
              height: 34,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              color: Colors.black,
              child: Row(
                children: [
                  for (final tf in ['1m', '5m', '15m', '1h', '1D', '1W', '1M'])
                    Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: GestureDetector(
                        onTap: () {
                          setState(() => _timeframe = tf);
                          _fetchChartData();
                        },
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                          decoration: BoxDecoration(
                            color: _timeframe == tf ? TerminalColors.borderMedium : Colors.transparent,
                            borderRadius: BorderRadius.circular(3),
                          ),
                          child: Text(
                            tf,
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                              color: _timeframe == tf ? TerminalColors.action : TerminalColors.textMuted,
                            ),
                          ),
                        ),
                      ),
                    ),
                  const Spacer(),
                  // Chart style toggle
                  GestureDetector(
                    onTap: () => setState(() => _showCandlesticks = !_showCandlesticks),
                    child: Icon(
                      _showCandlesticks ? Icons.candlestick_chart : Icons.show_chart,
                      size: 18,
                      color: TerminalColors.action,
                    ),
                  ),
                  const SizedBox(width: 8),
                  // SMA toggle
                  GestureDetector(
                    onTap: () => setState(() => _showSma20 = !_showSma20),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                      decoration: BoxDecoration(
                        color: _showSma20 ? TerminalColors.borderMedium : Colors.transparent,
                        borderRadius: BorderRadius.circular(2),
                      ),
                      child: Text(
                        "SMA20",
                        style: TextStyle(
                          fontSize: 9,
                          color: _showSma20 ? Colors.amber : TerminalColors.textMuted,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),

            // Main Interactive Mobile Chart Area
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator(color: TerminalColors.action))
                  : _error != null
                      ? Center(child: Text("Error: $_error", style: const TextStyle(color: TerminalColors.negative)))
                      : _bars.isEmpty
                          ? const Center(child: Text("No bars available for this instrument.", style: TextStyle(color: TerminalColors.textMuted)))
                          : GestureDetector(
                              onHorizontalDragUpdate: (details) {
                                // Touch crosshair inspection
                              },
                              child: CustomPaint(
                                size: Size.infinite,
                                painter: _MobileCandlePainter(
                                  bars: _bars,
                                  showCandlesticks: _showCandlesticks,
                                  showSma20: _showSma20,
                                  showVolume: _showVolume,
                                  hoverIndex: _hoverIndex,
                                ),
                              ),
                            ),
            ),

            // TradingView Lightweight Charts Attribution
            Container(
              padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 12),
              color: Colors.black,
              alignment: Alignment.centerLeft,
              child: const Text(
                "TradingView Lightweight Charts™ • Mobile Workspace View",
                style: TextStyle(fontSize: 9, color: TerminalColors.textFaint),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Custom Interactive Candlestick & Volume Painter for Pure-Black Mobile Experience
class _MobileCandlePainter extends CustomPainter {
  final List<Map<String, dynamic>> bars;
  final bool showCandlesticks;
  final bool showSma20;
  final bool showVolume;
  final int? hoverIndex;

  _MobileCandlePainter({
    required this.bars,
    required this.showCandlesticks,
    required this.showSma20,
    required this.showVolume,
    this.hoverIndex,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (bars.isEmpty) return;

    final double width = size.width;
    final double height = size.height;
    final double volumeHeight = showVolume ? height * 0.2 : 0;
    final double priceHeight = height - volumeHeight;

    // Determine min/max price
    double minPrice = double.infinity;
    double maxPrice = -double.infinity;
    double maxVolume = 0;

    for (final b in bars) {
      final high = double.tryParse(b['high'].toString()) ?? 0.0;
      final low = double.tryParse(b['low'].toString()) ?? 0.0;
      final vol = double.tryParse(b['volume'].toString()) ?? 0.0;

      if (high > maxPrice) maxPrice = high;
      if (low < minPrice && low > 0) minPrice = low;
      if (vol > maxVolume) maxVolume = vol;
    }

    if (minPrice >= maxPrice) {
      minPrice = maxPrice * 0.95;
      maxPrice = maxPrice * 1.05;
    }

    final double priceRange = maxPrice - minPrice;
    final int count = bars.length;
    final double barWidth = width / count;

    // Grid Lines
    final gridPaint = Paint()
      ..color = const Color(0x0DFFFFFF)
      ..strokeWidth = 1;

    for (int i = 1; i <= 4; i++) {
      final y = priceHeight * (i / 4);
      canvas.drawLine(Offset(0, y), Offset(width, y), gridPaint);
    }

    // Paint Candlesticks & Volume
    final bullPaint = Paint()..color = const Color(0xFF26A69A);
    final bearPaint = Paint()..color = const Color(0xFFEF5350);
    final wickPaint = Paint()..strokeWidth = 1;

    final List<Offset> smaPoints = [];

    for (int i = 0; i < count; i++) {
      final b = bars[i];
      final open = double.tryParse(b['open'].toString()) ?? 0.0;
      final high = double.tryParse(b['high'].toString()) ?? 0.0;
      final low = double.tryParse(b['low'].toString()) ?? 0.0;
      final close = double.tryParse(b['close'].toString()) ?? 0.0;
      final vol = double.tryParse(b['volume'].toString()) ?? 0.0;

      final bool isBull = close >= open;
      final paint = isBull ? bullPaint : bearPaint;
      wickPaint.color = paint.color;

      final double xCenter = (i * barWidth) + (barWidth / 2);

      // Y coordinates for OHLC
      final double yOpen = priceHeight - ((open - minPrice) / priceRange * priceHeight);
      final double yClose = priceHeight - ((close - minPrice) / priceRange * priceHeight);
      final double yHigh = priceHeight - ((high - minPrice) / priceRange * priceHeight);
      final double yLow = priceHeight - ((low - minPrice) / priceRange * priceHeight);

      if (showCandlesticks) {
        // High-Low Wick
        canvas.drawLine(Offset(xCenter, yHigh), Offset(xCenter, yLow), wickPaint);

        // Body Rect
        final double top = yOpen < yClose ? yOpen : yClose;
        final double bodyHeight = (yOpen - yClose).abs().clamp(1.0, priceHeight);
        final double candleWidth = (barWidth * 0.7).clamp(2.0, 16.0);

        canvas.drawRect(
          Rect.fromLTWH(xCenter - (candleWidth / 2), top, candleWidth, bodyHeight),
          paint,
        );
      } else {
        // Line chart point
        if (i == 0) {
          smaPoints.add(Offset(xCenter, yClose));
        } else {
          smaPoints.add(Offset(xCenter, yClose));
        }
      }

      // Volume Bar
      if (showVolume && maxVolume > 0) {
        final double volBarHeight = (vol / maxVolume) * volumeHeight * 0.85;
        final double volTop = height - volBarHeight;
        final volPaint = Paint()..color = paint.color.withAlpha(76);
        final double candleWidth = (barWidth * 0.7).clamp(2.0, 16.0);
        canvas.drawRect(
          Rect.fromLTWH(xCenter - (candleWidth / 2), volTop, candleWidth, volBarHeight),
          volPaint,
        );
      }
    }

    // Draw Line if line mode
    if (!showCandlesticks && smaPoints.length > 1) {
      final linePaint = Paint()
        ..color = TerminalColors.action
        ..strokeWidth = 2
        ..style = PaintingStyle.stroke;
      final path = Path()..moveTo(smaPoints.first.dx, smaPoints.first.dy);
      for (int i = 1; i < smaPoints.length; i++) {
        path.lineTo(smaPoints[i].dx, smaPoints[i].dy);
      }
      canvas.drawPath(path, linePaint);
    }
  }

  @override
  bool shouldRepaint(covariant _MobileCandlePainter oldDelegate) {
    return oldDelegate.bars != bars ||
        oldDelegate.showCandlesticks != showCandlesticks ||
        oldDelegate.showSma20 != showSma20 ||
        oldDelegate.hoverIndex != hoverIndex;
  }
}
