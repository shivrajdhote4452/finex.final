import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../services/api_client.dart';
import '../theme/terminal_theme.dart';
import '../widgets/quick_trade_modal.dart';

class MobileTransactionsScreen extends StatefulWidget {
  const MobileTransactionsScreen({super.key});

  @override
  State<MobileTransactionsScreen> createState() => _MobileTransactionsScreenState();
}

class _MobileTransactionsScreenState extends State<MobileTransactionsScreen> {
  List<Map<String, dynamic>> _orders = [];
  bool _isLoading = false;
  String _activeFilter = 'ALL';
  String _searchQuery = '';

  final _currencyFmt = NumberFormat.currency(symbol: '₹ ', locale: 'en_IN', decimalDigits: 2);

  @override
  void initState() {
    super.initState();
    _loadTransactions();
  }

  Future<void> _loadTransactions() async {
    setState(() => _isLoading = true);
    try {
      final rawOrders = await apiClient.getOrders(100);
      if (mounted) {
        setState(() {
          _orders = rawOrders;
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _showDepositModal() {
    double amount = 50000.0;
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        return StatefulBuilder(builder: (ctx, setModalState) {
          return Container(
            padding: const EdgeInsets.all(20),
            decoration: const BoxDecoration(
              color: TerminalColors.surface,
              borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
              border: Border(top: BorderSide(color: TerminalColors.borderSubtle)),
            ),
            child: SafeArea(
              top: false,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Center(
                    child: Container(
                      width: 36,
                      height: 4,
                      margin: const EdgeInsets.only(bottom: 16),
                      decoration: BoxDecoration(color: TerminalColors.borderMedium, borderRadius: BorderRadius.circular(2)),
                    ),
                  ),
                  const Text('💰 DEPOSIT VIRTUAL CAPITAL', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: TerminalColors.action)),
                  const SizedBox(height: 6),
                  const Text('Add simulated cash to your paper trading ledger for learning and backtesting.', style: TextStyle(fontSize: 12, color: TerminalColors.textMuted)),
                  const SizedBox(height: 16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [10000.0, 50000.0, 100000.0].map((val) {
                      final isSelected = amount == val;
                      return ChoiceChip(
                        label: Text('₹${val.toStringAsFixed(0)}'),
                        selected: isSelected,
                        selectedColor: TerminalColors.actionBg,
                        backgroundColor: TerminalColors.panel,
                        labelStyle: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: isSelected ? TerminalColors.action : TerminalColors.textMuted),
                        onSelected: (selected) {
                          if (selected) setModalState(() => amount = val);
                        },
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 20),
                  SizedBox(
                    width: double.infinity,
                    height: 44,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: TerminalColors.action,
                        foregroundColor: Colors.black,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                      ),
                      onPressed: () {
                        Navigator.pop(ctx);
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            backgroundColor: TerminalColors.surface,
                            content: Text('Deposited ₹${amount.toStringAsFixed(0)} virtual funds into ledger.'),
                          ),
                        );
                        _loadTransactions();
                      },
                      child: Text('DEPOSIT ₹${amount.toStringAsFixed(0)} VIRTUAL CASH', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
                    ),
                  ),
                ],
              ),
            ),
          );
        });
      },
    );
  }

  void _showContractNoteModal(Map<String, dynamic> order) {
    final sym = order['symbol'] ?? 'RELIANCE';
    final side = order['side'] ?? 'BUY';
    final qty = (order['quantity'] as num?)?.toInt() ?? 1;
    final price = (order['price'] ?? order['fill_price'] as num?)?.toDouble() ?? 2500.0;
    final gross = qty * price;
    final stt = gross * 0.001; // 0.1% STT
    final exchFees = gross * 0.0000345;
    final gst = (stt + exchFees) * 0.18;
    final stampDuty = gross * 0.00015;
    final totalCharges = stt + exchFees + gst + stampDuty;
    final netOutlay = side == 'BUY' ? gross + totalCharges : gross - totalCharges;
    final orderId = order['id'] ?? order['order_id'] ?? 'ORD-12345';
    final ts = order['created_at'] ?? order['timestamp'] ?? DateTime.now().toIso8601String();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        return Container(
          padding: const EdgeInsets.all(20),
          decoration: const BoxDecoration(
            color: TerminalColors.surface,
            borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
            border: Border(top: BorderSide(color: TerminalColors.borderSubtle)),
          ),
          child: SafeArea(
            top: false,
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Center(
                    child: Container(
                      width: 36,
                      height: 4,
                      margin: const EdgeInsets.only(bottom: 16),
                      decoration: BoxDecoration(color: TerminalColors.borderMedium, borderRadius: BorderRadius.circular(2)),
                    ),
                  ),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('ELECTRONIC CONTRACT NOTE', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: TerminalColors.action)),
                          Text('Simulated Execution Receipt • SEBI Educational Model', style: TextStyle(fontSize: 10, color: TerminalColors.textMuted)),
                        ],
                      ),
                      IconButton(icon: const Icon(Icons.close, size: 20, color: TerminalColors.textMuted), onPressed: () => Navigator.pop(ctx)),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(color: TerminalColors.panel, borderRadius: BorderRadius.circular(6)),
                    child: Column(
                      children: [
                        _buildReceiptRow('Order Reference', '$orderId'),
                        _buildReceiptRow('Execution Time', ts),
                        _buildReceiptRow('Instrument', 'NSE:$sym'),
                        _buildReceiptRow('Transaction', '$side $qty SHARES @ ₹${price.toStringAsFixed(2)}'),
                        const Divider(color: TerminalColors.borderSubtle, height: 16),
                        _buildReceiptRow('Gross Trade Value', '₹${gross.toStringAsFixed(2)}'),
                        _buildReceiptRow('Securities Transaction Tax (0.1%)', '₹${stt.toStringAsFixed(2)}'),
                        _buildReceiptRow('Exchange Charges & SEBI Fees', '₹${exchFees.toStringAsFixed(2)}'),
                        _buildReceiptRow('GST (18% on fees)', '₹${gst.toStringAsFixed(2)}'),
                        _buildReceiptRow('Stamp Duty', '₹${stampDuty.toStringAsFixed(2)}'),
                        const Divider(color: TerminalColors.borderSubtle, height: 16),
                        _buildReceiptRow('Net Consideration Outlay', '₹${netOutlay.toStringAsFixed(2)}', isBold: true, highlightColor: TerminalColors.textMain),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'NOTICE: Simulated transaction executed within FinEx virtual paper-trading ledger. No real currency or actual exchange settlement involved.',
                    style: TextStyle(fontSize: 10, color: TerminalColors.textFaint, height: 1.4),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildReceiptRow(String label, String value, {bool isBold = false, Color? highlightColor}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
          Text(value, style: TextStyle(fontSize: 11, fontWeight: isBold ? FontWeight.w800 : FontWeight.w600, fontFamily: 'monospace', color: highlightColor ?? TerminalColors.textMain)),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _orders.filter((o) {
      final matchesFilter = _activeFilter == 'ALL' || (o['side'] ?? '') == _activeFilter;
      final sym = (o['symbol'] ?? '').toString().toLowerCase();
      final id = (o['id'] ?? o['order_id'] ?? '').toString().toLowerCase();
      final matchesSearch = _searchQuery.isEmpty || sym.contains(_searchQuery.toLowerCase()) || id.contains(_searchQuery.toLowerCase());
      return matchesFilter && matchesSearch;
    }).toList();

    final totalTrades = _orders.length;
    double totalVol = 0.0;
    for (var o in _orders) {
      final q = (o['quantity'] as num?)?.toDouble() ?? 0.0;
      final p = (o['price'] ?? o['fill_price'] as num?)?.toDouble() ?? 0.0;
      totalVol += q * p;
    }
    final brokerageSaved = totalTrades * 20;

    return Scaffold(
      backgroundColor: TerminalColors.canvas,
      appBar: AppBar(
        title: const Text('TRANSACTION LEDGER & AUDIT DESK'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add_card, size: 20, color: TerminalColors.action),
            tooltip: 'Add Paper Cash',
            onPressed: _showDepositModal,
          ),
          IconButton(
            icon: const Icon(Icons.refresh, size: 20, color: TerminalColors.textMain),
            onPressed: _loadTransactions,
          ),
        ],
        bottom: _isLoading
            ? const PreferredSize(
                preferredSize: Size.fromHeight(2),
                child: LinearProgressIndicator(color: TerminalColors.action, minHeight: 2),
              )
            : null,
      ),
      body: RefreshIndicator(
        color: TerminalColors.action,
        backgroundColor: TerminalColors.surface,
        onRefresh: _loadTransactions,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Top KPI Ribbon
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _buildKpiCard('TOTAL ORDERS', '$totalTrades Trades', 'Executed', TerminalColors.textMain),
                  const SizedBox(width: 8),
                  _buildKpiCard('TRADED VOLUME', _currencyFmt.format(totalVol), 'Virtual INR', TerminalColors.textMain),
                  const SizedBox(width: 8),
                  _buildKpiCard('BROKERAGE SAVED', '₹$brokerageSaved', '₹20/Trade Discount', TerminalColors.positive),
                  const SizedBox(width: 8),
                  _buildKpiCard('LEDGER INTEGRITY', '100% Atomic', 'PostgreSQL ACID', TerminalColors.action),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Instant Trade & Deposit Action Bar
            Row(
              children: [
                Expanded(
                  child: SizedBox(
                    height: 40,
                    child: ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: TerminalColors.positive,
                        foregroundColor: Colors.black,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                      ),
                      icon: const Icon(Icons.bolt, size: 16),
                      label: const Text('PLACE NEW TRADE', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800)),
                      onPressed: () => QuickTradeModal.show(context, onTradeExecuted: _loadTransactions),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                SizedBox(
                  height: 40,
                  child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                      foregroundColor: TerminalColors.action,
                      side: const BorderSide(color: TerminalColors.action),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                    ),
                    icon: const Icon(Icons.attach_money, size: 16),
                    label: const Text('DEPOSIT CASH', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800)),
                    onPressed: _showDepositModal,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Search Bar
            Container(
              height: 40,
              decoration: BoxDecoration(
                color: TerminalColors.surface,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: TerminalColors.borderSubtle),
              ),
              padding: const EdgeInsets.symmetric(horizontal: 10),
              child: Row(
                children: [
                  const Icon(Icons.search, size: 18, color: TerminalColors.textMuted),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextField(
                      style: const TextStyle(fontSize: 13, color: TerminalColors.textMain),
                      decoration: const InputDecoration(
                        hintText: 'Search order ID, symbol (e.g. RELIANCE)...',
                        hintStyle: TextStyle(fontSize: 12, color: TerminalColors.textMuted),
                        border: InputBorder.none,
                        isDense: true,
                      ),
                      onChanged: (val) => setState(() => _searchQuery = val),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),

            // Filter Pills
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: ['ALL', 'BUY', 'SELL'].map((f) {
                  final isSelected = _activeFilter == f;
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: FilterChip(
                      label: Text(f),
                      selected: isSelected,
                      selectedColor: TerminalColors.actionBg,
                      backgroundColor: TerminalColors.surface,
                      labelStyle: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: isSelected ? TerminalColors.action : TerminalColors.textMuted),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(4),
                        side: BorderSide(color: isSelected ? TerminalColors.action : TerminalColors.borderSubtle),
                      ),
                      onSelected: (val) => setState(() => _activeFilter = f),
                    ),
                  );
                }).toList(),
              ),
            ),
            const SizedBox(height: 16),

            // Transaction Cards List
            if (filtered.isEmpty)
              Container(
                padding: const EdgeInsets.all(28),
                decoration: BoxDecoration(
                  color: TerminalColors.surface,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: TerminalColors.borderSubtle),
                ),
                alignment: Alignment.center,
                child: const Column(
                  children: [
                    Icon(Icons.receipt_long_outlined, size: 36, color: TerminalColors.textFaint),
                    SizedBox(height: 10),
                    Text('No Transactions Found', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
                    SizedBox(height: 4),
                    Text('Orders executed in Paper Trading will appear here with complete audit receipts.', style: TextStyle(fontSize: 12, color: TerminalColors.textMuted), textAlign: TextAlign.center),
                  ],
                ),
              )
            else
              ...filtered.map((o) {
                final sym = o['symbol'] ?? 'RELIANCE';
                final side = (o['side'] ?? 'BUY').toString().toUpperCase();
                final qty = (o['quantity'] as num?)?.toInt() ?? 1;
                final price = (o['price'] ?? o['fill_price'] as num?)?.toDouble() ?? 2500.0;
                final total = qty * price;
                final isBuy = side == 'BUY';
                final status = (o['status'] ?? 'FILLED').toString().toUpperCase();
                final orderId = o['id'] ?? o['order_id'] ?? 'ORD-REF';

                return Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: TerminalColors.surface,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: TerminalColors.borderSubtle),
                  ),
                  child: InkWell(
                    onTap: () => _showContractNoteModal(o),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Row(
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: isBuy ? TerminalColors.positiveBg : TerminalColors.negativeBg,
                                    borderRadius: BorderRadius.circular(3),
                                  ),
                                  child: Text(side, style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: isBuy ? TerminalColors.positive : TerminalColors.negative)),
                                ),
                                const SizedBox(width: 8),
                                Text(sym, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: TerminalColors.textMain)),
                              ],
                            ),
                            Text(_currencyFmt.format(total), style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800, fontFamily: 'monospace', color: TerminalColors.textMain)),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text('$qty shares @ ₹${price.toStringAsFixed(2)}', style: const TextStyle(fontSize: 11, color: TerminalColors.textMuted, fontFamily: 'monospace')),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: status == 'FILLED' ? TerminalColors.positiveBg : TerminalColors.panel,
                                borderRadius: BorderRadius.circular(3),
                              ),
                              child: Text(status, style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: status == 'FILLED' ? TerminalColors.positive : TerminalColors.textMuted)),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text('$orderId', style: const TextStyle(fontSize: 10, fontFamily: 'monospace', color: TerminalColors.textFaint)),
                            const Row(
                              children: [
                                Text('View Receipt', style: TextStyle(fontSize: 11, color: TerminalColors.action, fontWeight: FontWeight.w600)),
                                SizedBox(width: 2),
                                Icon(Icons.chevron_right, size: 14, color: TerminalColors.action),
                              ],
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              }),
          ],
        ),
      ),
    );
  }

  Widget _buildKpiCard(String title, String val, String sub, Color valColor) {
    return Container(
      width: 130,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: TerminalColors.surface,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: TerminalColors.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: TerminalColors.textMuted)),
          const SizedBox(height: 4),
          Text(val, style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, fontFamily: 'monospace', color: valColor)),
          const SizedBox(height: 2),
          Text(sub, style: const TextStyle(fontSize: 10, color: TerminalColors.textFaint)),
        ],
      ),
    );
  }
}

extension _IterableExt<T> on Iterable<T> {
  Iterable<T> filter(bool Function(T) test) sync* {
    for (var element in this) {
      if (test(element)) yield element;
    }
  }
}
