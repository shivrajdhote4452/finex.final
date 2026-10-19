import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart' hide TextDirection;
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
  bool _showEma50 = true;
  final bool _showVolume = true;

  // Flexibility & Interactive Pan / Zoom state
  double _candleWidth = 9.0; // width per candle in px (zoom level)
  double _scrollOffset = 0.0; // pan offset in px (0.0 = pinned to latest live candle at right)
  double _baseCandleWidth = 9.0;
  Offset? _hoverPosition;
  int? _hoverIndex;

  bool _loading = true;
  String? _error;
  List<Map<String, dynamic>> _bars = [];
  Map<String, dynamic>? _modeInfo;

  // Order Ticket state
  String _orderSide = 'BUY';
  double _orderQty = 5;
  String _orderType = 'MARKET';
  double? _limitPrice;
  bool _orderSubmitting = false;
  String? _orderFeedback;

  final _currencyFmt = NumberFormat.currency(symbol: '₹', locale: 'en_IN', decimalDigits: 2);

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
      _scrollOffset = 0.0; // reset pan to latest edge
      _hoverIndex = null;
      _hoverPosition = null;
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

  void _zoomIn() {
    setState(() {
      _candleWidth = (_candleWidth * 1.3).clamp(3.0, 36.0);
    });
  }

  void _zoomOut() {
    setState(() {
      _candleWidth = (_candleWidth / 1.3).clamp(3.0, 36.0);
    });
  }

  void _resetZoom() {
    setState(() {
      _candleWidth = 9.0;
      _scrollOffset = 0.0;
      _hoverIndex = null;
      _hoverPosition = null;
    });
  }

  void _jumpToLive() {
    setState(() {
      _scrollOffset = 0.0;
      _hoverIndex = null;
      _hoverPosition = null;
    });
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
                      decoration: const InputDecoration(
                        hintText: "Search 40+ stocks (e.g. TATASTEEL, INFY)...",
                        hintStyle: TextStyle(fontSize: 13, color: TerminalColors.textMuted),
                        prefixIcon: Icon(Icons.search, color: TerminalColors.action, size: 20),
                        filled: true,
                        fillColor: TerminalColors.panel,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.all(Radius.circular(8)),
                          borderSide: BorderSide(color: TerminalColors.borderSubtle),
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
                          _currencyFmt.format(total),
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
                          child: Text(
                            aiReply ?? "Ask any question about $_symbol technical patterns, RSI levels, support & resistance, or simulated order planning.",
                            style: const TextStyle(fontSize: 12, height: 1.4, color: TerminalColors.textMain),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: textController,
                            style: const TextStyle(fontSize: 13, color: Colors.white),
                            decoration: const InputDecoration(
                              hintText: "Ask Gemini about technical indicators...",
                              hintStyle: TextStyle(fontSize: 12, color: TerminalColors.textMuted),
                              filled: true,
                              fillColor: TerminalColors.panel,
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.all(Radius.circular(6)),
                                borderSide: BorderSide(color: TerminalColors.borderSubtle),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        IconButton(
                          icon: aiThinking
                              ? const SizedBox(
                                  width: 20,
                                  height: 20,
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
                          : "NSE Real-Time / Replay",
                      style: const TextStyle(fontSize: 10, color: TerminalColors.textMuted, fontWeight: FontWeight.w600),
                    ),
                  ),
                ],
              ),
            ),

            // Timeframe / Range Bar
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

            // Interactive Controls Toolbar: Timeframes, Zoom (+ / - / Reset), Indicators & Style
            Container(
              height: 36,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              color: Colors.black,
              child: Row(
                children: [
                  // Timeframe chips
                  for (final tf in ['5m', '15m', '1h', '1D', '1W'])
                    Padding(
                      padding: const EdgeInsets.only(right: 4),
                      child: GestureDetector(
                        onTap: () {
                          setState(() => _timeframe = tf);
                          _fetchChartData();
                        },
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
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

                  // Quick Zoom Buttons
                  _buildToolbarButton(
                    icon: Icons.zoom_in,
                    tooltip: "Zoom In (Wider Candles)",
                    onTap: _zoomIn,
                  ),
                  const SizedBox(width: 4),
                  _buildToolbarButton(
                    icon: Icons.zoom_out,
                    tooltip: "Zoom Out (More History)",
                    onTap: _zoomOut,
                  ),
                  const SizedBox(width: 4),
                  _buildToolbarButton(
                    icon: Icons.fit_screen,
                    tooltip: "Reset Zoom & Live Edge",
                    onTap: _resetZoom,
                  ),
                  const SizedBox(width: 8),

                  // Chart style toggle (Candles vs Area/Line)
                  GestureDetector(
                    onTap: () => setState(() => _showCandlesticks = !_showCandlesticks),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                      decoration: BoxDecoration(
                        color: _showCandlesticks ? const Color(0x33F29A60) : Colors.transparent,
                        borderRadius: BorderRadius.circular(3),
                      ),
                      child: Icon(
                        _showCandlesticks ? Icons.candlestick_chart : Icons.show_chart,
                        size: 16,
                        color: TerminalColors.action,
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),

                  // SMA20 toggle
                  GestureDetector(
                    onTap: () => setState(() => _showSma20 = !_showSma20),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                      decoration: BoxDecoration(
                        color: _showSma20 ? const Color(0x33F59E0B) : Colors.transparent,
                        borderRadius: BorderRadius.circular(2),
                        border: Border.all(color: _showSma20 ? Colors.amber : TerminalColors.borderSubtle),
                      ),
                      child: Text(
                        "SMA",
                        style: TextStyle(
                          fontSize: 9,
                          color: _showSma20 ? Colors.amber : TerminalColors.textMuted,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 4),

                  // EMA50 toggle
                  GestureDetector(
                    onTap: () => setState(() => _showEma50 = !_showEma50),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                      decoration: BoxDecoration(
                        color: _showEma50 ? const Color(0x333B82F6) : Colors.transparent,
                        borderRadius: BorderRadius.circular(2),
                        border: Border.all(color: _showEma50 ? const Color(0xFF60A5FA) : TerminalColors.borderSubtle),
                      ),
                      child: Text(
                        "EMA",
                        style: TextStyle(
                          fontSize: 9,
                          color: _showEma50 ? const Color(0xFF60A5FA) : TerminalColors.textMuted,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),

            // Main Interactive Mobile Chart Area with Pan, Zoom & Crosshairs
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator(color: TerminalColors.action))
                  : _error != null
                      ? Center(child: Text("Error: $_error", style: const TextStyle(color: TerminalColors.negative)))
                      : _bars.isEmpty
                          ? const Center(child: Text("No bars available for this instrument.", style: TextStyle(color: TerminalColors.textMuted)))
                          : LayoutBuilder(
                              builder: (context, constraints) {
                                return Stack(
                                  children: [
                                    // Interactive Pan, Pinch Zoom, Mouse Wheel Listener
                                    Listener(
                                      onPointerSignal: (pointerSignal) {
                                        if (pointerSignal is PointerScrollEvent) {
                                          final dy = pointerSignal.scrollDelta.dy;
                                          setState(() {
                                            if (dy < 0) {
                                              _candleWidth = (_candleWidth * 1.15).clamp(3.0, 36.0);
                                            } else {
                                              _candleWidth = (_candleWidth / 1.15).clamp(3.0, 36.0);
                                            }
                                          });
                                        }
                                      },
                                      child: GestureDetector(
                                        behavior: HitTestBehavior.opaque,
                                        onScaleStart: (details) {
                                          _baseCandleWidth = _candleWidth;
                                        },
                                        onScaleUpdate: (details) {
                                          if (details.pointerCount > 1 || details.scale != 1.0) {
                                            // Pinch Zoom
                                            setState(() {
                                              _candleWidth = (_baseCandleWidth * details.scale).clamp(3.0, 36.0);
                                            });
                                          } else {
                                            // 1-finger horizontal pan drag
                                            final dx = details.focalPointDelta.dx;
                                            final step = _candleWidth + 2.0;
                                            final maxScroll = (_bars.length * step) - (constraints.maxWidth * 0.4);
                                            setState(() {
                                              _scrollOffset = (_scrollOffset + dx).clamp(-40.0, maxScroll > 0 ? maxScroll : 0.0);
                                              _hoverPosition = details.localFocalPoint;
                                            });
                                          }
                                        },
                                        onTapDown: (details) {
                                          setState(() {
                                            _hoverPosition = details.localPosition;
                                          });
                                        },
                                        onDoubleTap: _resetZoom,
                                        child: CustomPaint(
                                          size: Size(constraints.maxWidth, constraints.maxHeight),
                                          painter: _MobileCandlePainter(
                                            bars: _bars,
                                            showCandlesticks: _showCandlesticks,
                                            showSma20: _showSma20,
                                            showEma50: _showEma50,
                                            showVolume: _showVolume,
                                            candleWidth: _candleWidth,
                                            scrollOffset: _scrollOffset,
                                            hoverPosition: _hoverPosition,
                                            onHoverUpdated: (idx) {
                                              if (_hoverIndex != idx) {
                                                WidgetsBinding.instance.addPostFrameCallback((_) {
                                                  if (mounted) setState(() => _hoverIndex = idx);
                                                });
                                              }
                                            },
                                          ),
                                        ),
                                      ),
                                    ),

                                    // Top Hover Inspection HUD Overlay Box
                                    if (_hoverIndex != null && _hoverIndex! >= 0 && _hoverIndex! < _bars.length)
                                      Positioned(
                                        top: 8,
                                        left: 10,
                                        right: 64,
                                        child: _buildHoverHud(_bars[_hoverIndex!]),
                                      ),

                                    // Jump To Live Floating Button (Appears when scrolled back into past)
                                    if (_scrollOffset > 50)
                                      Positioned(
                                        bottom: 30,
                                        right: 64,
                                        child: GestureDetector(
                                          onTap: _jumpToLive,
                                          child: Container(
                                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                                            decoration: BoxDecoration(
                                              color: TerminalColors.action,
                                              borderRadius: BorderRadius.circular(16),
                                              boxShadow: const [
                                                BoxShadow(color: Colors.black54, blurRadius: 4, offset: Offset(0, 2)),
                                              ],
                                            ),
                                            child: const Row(
                                              mainAxisSize: MainAxisSize.min,
                                              children: [
                                                Icon(Icons.skip_next, size: 14, color: Colors.black),
                                                SizedBox(width: 4),
                                                Text(
                                                  "Jump to Latest",
                                                  style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: Colors.black),
                                                ),
                                              ],
                                            ),
                                          ),
                                        ),
                                      ),
                                  ],
                                );
                              },
                            ),
            ),

            // TradingView Lightweight Charts Status Footer
            Container(
              padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 12),
              color: Colors.black,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    "FinEx Interactive Canvas • Pan & Pinch to Zoom",
                    style: TextStyle(fontSize: 9, color: TerminalColors.textFaint),
                  ),
                  Text(
                    "Zoom: ${(_candleWidth * 10).round()}% · ${_bars.length} Bars",
                    style: const TextStyle(fontSize: 9, fontFamily: 'monospace', color: TerminalColors.textMuted),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildToolbarButton({required IconData icon, required String tooltip, required VoidCallback onTap}) {
    return GestureDetector(
      onTap: onTap,
      child: Tooltip(
        message: tooltip,
        child: Container(
          padding: const EdgeInsets.all(4),
          decoration: BoxDecoration(
            color: const Color(0x1AFFFFFF),
            borderRadius: BorderRadius.circular(3),
          ),
          child: Icon(icon, size: 15, color: TerminalColors.textMain),
        ),
      ),
    );
  }

  Widget _buildHoverHud(Map<String, dynamic> bar) {
    final date = (bar['date'] ?? '').toString();
    final open = double.tryParse(bar['open'].toString()) ?? 0.0;
    final high = double.tryParse(bar['high'].toString()) ?? 0.0;
    final low = double.tryParse(bar['low'].toString()) ?? 0.0;
    final close = double.tryParse(bar['close'].toString()) ?? 0.0;
    final vol = double.tryParse(bar['volume'].toString()) ?? 0.0;
    final chg = close - open;
    final chgPct = open > 0 ? (chg / open) * 100 : 0.0;
    final isBull = chg >= 0;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xEE111111),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: TerminalColors.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(date, style: const TextStyle(fontSize: 10, fontFamily: 'monospace', fontWeight: FontWeight.bold, color: Colors.white)),
              Text(
                "${isBull ? '+' : ''}${chg.toStringAsFixed(2)} (${isBull ? '+' : ''}${chgPct.toStringAsFixed(2)}%)",
                style: TextStyle(
                  fontSize: 10,
                  fontFamily: 'monospace',
                  fontWeight: FontWeight.bold,
                  color: isBull ? const Color(0xFF26A69A) : const Color(0xFFEF5350),
                ),
              ),
            ],
          ),
          const SizedBox(height: 2),
          Text(
            "O: ${open.toStringAsFixed(2)}  H: ${high.toStringAsFixed(2)}  L: ${low.toStringAsFixed(2)}  C: ${close.toStringAsFixed(2)}  V: ${vol > 1000 ? '${(vol / 1000).toStringAsFixed(1)}k' : vol.toStringAsFixed(0)}",
            style: const TextStyle(fontSize: 9, fontFamily: 'monospace', color: TerminalColors.textMuted),
          ),
        ],
      ),
    );
  }
}

/// Fully Flexible Interactive Candlestick, Volume & Multi-Indicator Canvas Painter
class _MobileCandlePainter extends CustomPainter {
  final List<Map<String, dynamic>> bars;
  final bool showCandlesticks;
  final bool showSma20;
  final bool showEma50;
  final bool showVolume;
  final double candleWidth;
  final double scrollOffset;
  final Offset? hoverPosition;
  final ValueChanged<int?> onHoverUpdated;

  _MobileCandlePainter({
    required this.bars,
    required this.showCandlesticks,
    required this.showSma20,
    required this.showEma50,
    required this.showVolume,
    required this.candleWidth,
    required this.scrollOffset,
    this.hoverPosition,
    required this.onHoverUpdated,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (bars.isEmpty) return;

    final double width = size.width;
    final double height = size.height;
    const double rightScaleWidth = 54.0;
    const double bottomDateHeight = 22.0;

    final double chartWidth = width - rightScaleWidth;
    final double chartHeight = height - bottomDateHeight;
    final double volumeHeight = showVolume ? chartHeight * 0.18 : 0.0;
    final double priceHeight = chartHeight - volumeHeight;

    final double step = candleWidth + 2.0;
    final int totalBars = bars.length;

    // Determine which bars fall within visible canvas area
    int? firstVisibleIdx;
    int? lastVisibleIdx;
    double minPrice = double.infinity;
    double maxPrice = -double.infinity;
    double maxVolume = 0.0;

    // Calculate x positions for all bars and gather min/max from visible window
    final List<double> xCenters = List.filled(totalBars, 0.0);
    for (int i = 0; i < totalBars; i++) {
      final double x = chartWidth - (step / 2) - ((totalBars - 1 - i) * step) + scrollOffset;
      xCenters[i] = x;

      if (x >= -step && x <= chartWidth + step) {
        firstVisibleIdx ??= i;
        lastVisibleIdx = i;

        final high = double.tryParse(bars[i]['high'].toString()) ?? 0.0;
        final low = double.tryParse(bars[i]['low'].toString()) ?? 0.0;
        final vol = double.tryParse(bars[i]['volume'].toString()) ?? 0.0;

        if (high > maxPrice) maxPrice = high;
        if (low < minPrice && low > 0) minPrice = low;
        if (vol > maxVolume) maxVolume = vol;
      }
    }

    if (minPrice == double.infinity || maxPrice == -double.infinity || minPrice >= maxPrice) {
      minPrice = 1000.0;
      maxPrice = 1100.0;
    }

    // Add 4% vertical padding to top and bottom
    final double rawRange = maxPrice - minPrice;
    final double padding = rawRange * 0.05;
    minPrice -= padding;
    maxPrice += padding;
    final double priceRange = maxPrice - minPrice;

    // Detect hover index
    int? detectedHoverIdx;
    if (hoverPosition != null && hoverPosition!.dx >= 0 && hoverPosition!.dx < chartWidth) {
      final hx = hoverPosition!.dx;
      double closestDist = double.infinity;
      for (int i = (firstVisibleIdx ?? 0); i <= (lastVisibleIdx ?? totalBars - 1); i++) {
        final dist = (xCenters[i] - hx).abs();
        if (dist < closestDist) {
          closestDist = dist;
          detectedHoverIdx = i;
        }
      }
    }
    onHoverUpdated(detectedHoverIdx);

    // 1. Draw Background Gridlines & Right Y-Axis Scale
    final gridPaint = Paint()
      ..color = const Color(0x10FFFFFF)
      ..strokeWidth = 1;

    final axisTextPainter = TextPainter(textDirection: TextDirection.ltr);

    for (int i = 0; i <= 4; i++) {
      final double ratio = i / 4.0;
      final double y = priceHeight * ratio;
      final double priceAtY = maxPrice - (priceRange * ratio);

      // Horizontal dashed line
      canvas.drawLine(Offset(0, y), Offset(chartWidth, y), gridPaint);

      // Right axis label
      axisTextPainter.text = TextSpan(
        text: priceAtY.toStringAsFixed(priceAtY >= 500 ? 0 : 2),
        style: const TextStyle(fontSize: 9, fontFamily: 'monospace', color: TerminalColors.textMuted),
      );
      axisTextPainter.layout();
      axisTextPainter.paint(canvas, Offset(chartWidth + 5, y - 5));
    }

    // Vertical Right-Axis Border
    canvas.drawLine(Offset(chartWidth, 0), Offset(chartWidth, height), Paint()..color = TerminalColors.borderSubtle);
    // Horizontal Bottom-Axis Border
    canvas.drawLine(Offset(0, chartHeight), Offset(width, chartHeight), Paint()..color = TerminalColors.borderSubtle);

    // 2. Render Candlesticks and Volume Bars
    final bullPaint = Paint()..color = const Color(0xFF26A69A);
    final bearPaint = Paint()..color = const Color(0xFFEF5350);
    final wickPaint = Paint()..strokeWidth = 1.0;

    final List<Offset> linePoints = [];

    final startIdx = firstVisibleIdx ?? 0;
    final endIdx = lastVisibleIdx ?? (totalBars - 1);

    for (int i = startIdx; i <= endIdx; i++) {
      final b = bars[i];
      final open = double.tryParse(b['open'].toString()) ?? 0.0;
      final high = double.tryParse(b['high'].toString()) ?? 0.0;
      final low = double.tryParse(b['low'].toString()) ?? 0.0;
      final close = double.tryParse(b['close'].toString()) ?? 0.0;
      final vol = double.tryParse(b['volume'].toString()) ?? 0.0;

      final bool isBull = close >= open;
      final paint = isBull ? bullPaint : bearPaint;
      wickPaint.color = paint.color;

      final double xc = xCenters[i];

      final double yOpen = priceHeight - ((open - minPrice) / priceRange * priceHeight);
      final double yClose = priceHeight - ((close - minPrice) / priceRange * priceHeight);
      final double yHigh = priceHeight - ((high - minPrice) / priceRange * priceHeight);
      final double yLow = priceHeight - ((low - minPrice) / priceRange * priceHeight);

      if (showCandlesticks) {
        // High-low wick
        canvas.drawLine(Offset(xc, yHigh), Offset(xc, yLow), wickPaint);

        // Body rectangle
        final double top = yOpen < yClose ? yOpen : yClose;
        final double bodyH = (yOpen - yClose).abs().clamp(1.5, priceHeight);
        final double cWidth = (candleWidth * 0.75).clamp(2.0, 32.0);

        canvas.drawRect(
          Rect.fromLTWH(xc - (cWidth / 2), top, cWidth, bodyH),
          paint,
        );
      } else {
        linePoints.add(Offset(xc, yClose));
      }

      // Volume histogram bar
      if (showVolume && maxVolume > 0) {
        final double volBarHeight = (vol / maxVolume) * volumeHeight * 0.9;
        final double volTop = chartHeight - volBarHeight;
        final volPaint = Paint()..color = paint.color.withValues(alpha: 0.35);
        final double cWidth = (candleWidth * 0.75).clamp(2.0, 32.0);

        canvas.drawRect(
          Rect.fromLTWH(xc - (cWidth / 2), volTop, cWidth, volBarHeight),
          volPaint,
        );
      }
    }

    // 3. Render Mountain / Line if in line mode
    if (!showCandlesticks && linePoints.length > 1) {
      final linePath = Path()..moveTo(linePoints.first.dx, linePoints.first.dy);
      final areaPath = Path()..moveTo(linePoints.first.dx, chartHeight);
      areaPath.lineTo(linePoints.first.dx, linePoints.first.dy);

      for (int k = 1; k < linePoints.length; k++) {
        linePath.lineTo(linePoints[k].dx, linePoints[k].dy);
        areaPath.lineTo(linePoints[k].dx, linePoints[k].dy);
      }

      areaPath.lineTo(linePoints.last.dx, chartHeight);
      areaPath.close();

      final areaPaint = Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            TerminalColors.action.withValues(alpha: 0.25),
            TerminalColors.action.withValues(alpha: 0.0),
          ],
        ).createShader(Rect.fromLTWH(0, 0, chartWidth, chartHeight));

      canvas.drawPath(areaPath, areaPaint);

      final linePaint = Paint()
        ..color = TerminalColors.action
        ..strokeWidth = 2.0
        ..style = PaintingStyle.stroke;
      canvas.drawPath(linePath, linePaint);
    }

    // 4. Moving Average Overlays (SMA20 & EMA50)
    if (showSma20 && bars.length >= 20) {
      final smaPaint = Paint()
        ..color = Colors.amber
        ..strokeWidth = 1.5
        ..style = PaintingStyle.stroke;

      final Path smaPath = Path();
      bool firstSma = true;

      for (int i = 19; i < totalBars; i++) {
        final xc = xCenters[i];
        if (xc < -step || xc > chartWidth + step) continue;

        double sum = 0.0;
        for (int k = i - 19; k <= i; k++) {
          sum += double.tryParse(bars[k]['close'].toString()) ?? 0.0;
        }
        final avg = sum / 20.0;
        final yAvg = priceHeight - ((avg - minPrice) / priceRange * priceHeight);

        if (firstSma) {
          smaPath.moveTo(xc, yAvg);
          firstSma = false;
        } else {
          smaPath.lineTo(xc, yAvg);
        }
      }
      canvas.drawPath(smaPath, smaPaint);
    }

    if (showEma50 && bars.length >= 50) {
      final emaPaint = Paint()
        ..color = const Color(0xFF60A5FA)
        ..strokeWidth = 1.5
        ..style = PaintingStyle.stroke;

      final Path emaPath = Path();
      bool firstEma = true;
      double multiplier = 2.0 / (50 + 1);
      double currentEma = double.tryParse(bars[0]['close'].toString()) ?? 0.0;

      for (int i = 1; i < totalBars; i++) {
        final close = double.tryParse(bars[i]['close'].toString()) ?? 0.0;
        currentEma = ((close - currentEma) * multiplier) + currentEma;

        if (i >= 49) {
          final xc = xCenters[i];
          if (xc < -step || xc > chartWidth + step) continue;
          final yEma = priceHeight - ((currentEma - minPrice) / priceRange * priceHeight);

          if (firstEma) {
            emaPath.moveTo(xc, yEma);
            firstEma = false;
          } else {
            emaPath.lineTo(xc, yEma);
          }
        }
      }
      canvas.drawPath(emaPath, emaPaint);
    }

    // 5. Render Date Axis along bottom
    final dateStep = ((chartWidth / 70).floor()).clamp(3, 15);
    for (int i = startIdx; i <= endIdx; i += dateStep) {
      final xc = xCenters[i];
      if (xc >= 10 && xc <= chartWidth - 30) {
        final rawDate = (bars[i]['date'] ?? '').toString();
        // Extract DD/MM or MM-DD
        final displayDate = rawDate.length >= 10 ? rawDate.substring(5, 10) : rawDate;
        axisTextPainter.text = TextSpan(
          text: displayDate,
          style: const TextStyle(fontSize: 9, fontFamily: 'monospace', color: TerminalColors.textMuted),
        );
        axisTextPainter.layout();
        axisTextPainter.paint(canvas, Offset(xc - 12, chartHeight + 4));
      }
    }

    // 6. Draw Current Latest Price Pill on Right Axis
    final latestClose = double.tryParse(bars.last['close'].toString()) ?? 0.0;
    final double yLatest = (priceHeight - ((latestClose - minPrice) / priceRange * priceHeight)).clamp(8.0, priceHeight - 8.0);

    final ltpBgPaint = Paint()..color = TerminalColors.action;
    canvas.drawRRect(
      RRect.fromRectAndRadius(Rect.fromLTWH(chartWidth + 2, yLatest - 8, rightScaleWidth - 4, 16), const Radius.circular(3)),
      ltpBgPaint,
    );
    axisTextPainter.text = TextSpan(
      text: latestClose.toStringAsFixed(latestClose >= 500 ? 0 : 2),
      style: const TextStyle(fontSize: 9, fontFamily: 'monospace', fontWeight: FontWeight.bold, color: Colors.black),
    );
    axisTextPainter.layout();
    axisTextPainter.paint(canvas, Offset(chartWidth + 6, yLatest - 5));

    // 7. Interactive Crosshair Lines (when hovering / tapping)
    if (detectedHoverIdx != null && detectedHoverIdx >= 0 && detectedHoverIdx < totalBars) {
      final hxc = xCenters[detectedHoverIdx];
      final hy = (hoverPosition?.dy ?? 0.0).clamp(0.0, chartHeight);

      final crosshairPaint = Paint()
        ..color = const Color(0x66FFFFFF)
        ..strokeWidth = 1.0;

      // Vertical crosshair
      canvas.drawLine(Offset(hxc, 0), Offset(hxc, chartHeight), crosshairPaint);
      // Horizontal crosshair
      canvas.drawLine(Offset(0, hy), Offset(chartWidth, hy), crosshairPaint);

      // Price badge on right axis for hovered level
      final hoveredPrice = maxPrice - (hy / priceHeight * priceRange);
      final hoverPriceBg = Paint()..color = const Color(0xFF333333);
      canvas.drawRRect(
        RRect.fromRectAndRadius(Rect.fromLTWH(chartWidth + 2, hy - 7, rightScaleWidth - 4, 14), const Radius.circular(2)),
        hoverPriceBg,
      );
      axisTextPainter.text = TextSpan(
        text: hoveredPrice.toStringAsFixed(hoveredPrice >= 500 ? 0 : 2),
        style: const TextStyle(fontSize: 8, fontFamily: 'monospace', fontWeight: FontWeight.bold, color: Colors.white),
      );
      axisTextPainter.layout();
      axisTextPainter.paint(canvas, Offset(chartWidth + 5, hy - 5));
    }
  }

  @override
  bool shouldRepaint(covariant _MobileCandlePainter oldDelegate) {
    return oldDelegate.bars != bars ||
        oldDelegate.showCandlesticks != showCandlesticks ||
        oldDelegate.showSma20 != showSma20 ||
        oldDelegate.showEma50 != showEma50 ||
        oldDelegate.showVolume != showVolume ||
        oldDelegate.candleWidth != candleWidth ||
        oldDelegate.scrollOffset != scrollOffset ||
        oldDelegate.hoverPosition != hoverPosition;
  }
}
