import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../services/api_client.dart';
import '../theme/terminal_theme.dart';
import '../widgets/quick_trade_modal.dart';

class RecentTransactionsFeed extends StatefulWidget {
  final String title;
  final int? maxItems;
  final bool showFilters;
  final VoidCallback? onNavigateToPractice;
  final VoidCallback? onNavigateToAudit;

  const RecentTransactionsFeed({
    super.key,
    this.title = 'Recent Transactions & Execution Activity',
    this.maxItems,
    this.showFilters = true,
    this.onNavigateToPractice,
    this.onNavigateToAudit,
  });

  @override
  State<RecentTransactionsFeed> createState() => _RecentTransactionsFeedState();
}

class _RecentTransactionsFeedState extends State<RecentTransactionsFeed> {
  String _sideFilter = 'ALL'; // 'ALL' | 'BUY' | 'SELL'
  String _searchQuery = '';
  bool _isLoading = false;

  final _currencyFmt = NumberFormat.currency(symbol: '₹', locale: 'en_IN', decimalDigits: 2);

  @override
  void initState() {
    super.initState();
    if (apiClient.recentOrdersNotifier.value.isEmpty) {
      _loadOrders();
    }
  }

  Future<void> _loadOrders() async {
    setState(() => _isLoading = true);
    try {
      await apiClient.getOrders(50);
    } catch (_) {}
    if (mounted) {
      setState(() => _isLoading = false);
    }
  }

  String _formatTime(dynamic ts) {
    if (ts == null) return 'Recent';
    try {
      final dt = DateTime.parse(ts.toString()).toLocal();
      final now = DateTime.now();
      final diff = now.difference(dt);
      if (diff.inSeconds < 60) return 'Just now';
      if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
      if (diff.inHours < 24) return DateFormat('HH:mm').format(dt);
      return DateFormat('dd MMM, HH:mm').format(dt);
    } catch (_) {
      return ts.toString();
    }
  }

  void _showTransactionDetails(Map<String, dynamic> entry) {
    final sym = entry['symbol'] ?? 'UNKNOWN';
    final side = (entry['side'] ?? 'BUY').toString().toUpperCase();
    final qty = (entry['quantity'] as num?)?.toDouble() ?? 1.0;
    final price = (entry['fill_price'] ?? entry['price'] as num?)?.toDouble() ?? 0.0;
    final total = qty * price;
    final isBuy = side == 'BUY';
    final status = (entry['status'] ?? 'FILLED').toString().toUpperCase();
    final orderId = entry['order_id'] ?? entry['id'] ?? 'ORD-REF';
    final isReplay = entry['is_replay'] == true ||
        (entry['notes'] != null && entry['notes'].toString().contains('REPLAY'));
    final realizedPnl = (entry['realized_pnl'] as num?)?.toDouble();
    final timestamp = entry['created_at'] ?? entry['timestamp'] ?? 'N/A';

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
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Center(
                  child: Container(
                    width: 36,
                    height: 4,
                    margin: const EdgeInsets.only(bottom: 16),
                    decoration: BoxDecoration(
                      color: TerminalColors.borderMedium,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: isBuy ? TerminalColors.positiveBg : TerminalColors.negativeBg,
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            side,
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w800,
                              color: isBuy ? TerminalColors.positive : TerminalColors.negative,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          sym,
                          style: const TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.w800,
                            color: TerminalColors.textMain,
                          ),
                        ),
                        if (isReplay) ...[
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                            decoration: BoxDecoration(
                              color: const Color(0x33F59E0B),
                              borderRadius: BorderRadius.circular(3),
                              border: Border.all(color: const Color(0x66F59E0B)),
                            ),
                            child: const Text(
                              'REPLAY',
                              style: TextStyle(
                                fontSize: 9,
                                fontWeight: FontWeight.w800,
                                color: Color(0xFFFBBF24),
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                    IconButton(
                      icon: const Icon(Icons.close, size: 20, color: TerminalColors.textMuted),
                      onPressed: () => Navigator.pop(ctx),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                _buildDetailRow('Execution Status', status, valueColor: TerminalColors.positive),
                const Divider(color: TerminalColors.borderSubtle, height: 16),
                _buildDetailRow('Order ID', orderId, isMono: true),
                const Divider(color: TerminalColors.borderSubtle, height: 16),
                _buildDetailRow('Timestamp', timestamp.toString(), isMono: true),
                const Divider(color: TerminalColors.borderSubtle, height: 16),
                _buildDetailRow(
                  'Quantity',
                  qty % 1 == 0 ? '${qty.toInt()} Shares' : '$qty Shares',
                  isMono: true,
                ),
                const Divider(color: TerminalColors.borderSubtle, height: 16),
                _buildDetailRow('Executed Price', _currencyFmt.format(price), isMono: true),
                const Divider(color: TerminalColors.borderSubtle, height: 16),
                _buildDetailRow('Total Settlement', _currencyFmt.format(total), isMono: true, isBold: true),
                if (!isBuy && realizedPnl != null) ...[
                  const Divider(color: TerminalColors.borderSubtle, height: 16),
                  _buildDetailRow(
                    'Realized P&L',
                    '${realizedPnl >= 0 ? '+' : ''}${_currencyFmt.format(realizedPnl)}',
                    isMono: true,
                    valueColor: realizedPnl >= 0 ? TerminalColors.positive : TerminalColors.negative,
                    isBold: true,
                  ),
                ],
                const SizedBox(height: 20),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildDetailRow(String label, String value, {bool isMono = false, Color? valueColor, bool isBold = false}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: const TextStyle(fontSize: 12, color: TerminalColors.textMuted),
        ),
        Text(
          value,
          style: TextStyle(
            fontSize: 12.5,
            fontFamily: isMono ? 'monospace' : null,
            fontWeight: isBold ? FontWeight.w800 : FontWeight.w600,
            color: valueColor ?? TerminalColors.textMain,
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<List<Map<String, dynamic>>>(
      valueListenable: apiClient.recentOrdersNotifier,
      builder: (context, rawOrders, _) {
        // Filter orders
        final filtered = rawOrders.where((entry) {
          final side = (entry['side'] ?? 'BUY').toString().toUpperCase();
          final sym = (entry['symbol'] ?? '').toString().toLowerCase();
          final orderId = (entry['order_id'] ?? entry['id'] ?? '').toString().toLowerCase();

          final matchesSide = _sideFilter == 'ALL' || side == _sideFilter;
          final query = _searchQuery.trim().toLowerCase();
          final matchesSearch = query.isEmpty || sym.contains(query) || orderId.contains(query);

          return matchesSide && matchesSearch;
        }).toList();

        final displayed = widget.maxItems != null ? filtered.take(widget.maxItems!).toList() : filtered;

        return Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: TerminalColors.surface,
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: TerminalColors.borderSubtle),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header Row
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Row(
                      children: [
                        Flexible(
                          child: Text(
                            widget.title,
                            style: const TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                              color: TerminalColors.textMain,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: TerminalColors.panel,
                            borderRadius: BorderRadius.circular(3),
                          ),
                          child: Text(
                            '${rawOrders.length} ${rawOrders.length == 1 ? 'Trade' : 'Trades'}',
                            style: const TextStyle(fontSize: 10, fontFamily: 'monospace', color: TerminalColors.textMuted),
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (widget.onNavigateToAudit != null)
                    GestureDetector(
                      onTap: widget.onNavigateToAudit,
                      child: const Text(
                        'Audit Ledger →',
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: TerminalColors.action),
                      ),
                    ),
                ],
              ),

              // Filter Controls
              if (widget.showFilters) ...[
                const SizedBox(height: 12),
                Row(
                  children: [
                    // Side Filter Pills
                    Row(
                      children: ['ALL', 'BUY', 'SELL'].map((f) {
                        final isSel = _sideFilter == f;
                        return GestureDetector(
                          onTap: () => setState(() => _sideFilter = f),
                          child: Container(
                            margin: const EdgeInsets.only(right: 6),
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(
                              color: isSel ? const Color(0x33F29A60) : Colors.transparent,
                              borderRadius: BorderRadius.circular(3),
                              border: Border.all(color: isSel ? TerminalColors.action : TerminalColors.borderSubtle),
                            ),
                            child: Text(
                              f == 'ALL' ? 'All' : f == 'BUY' ? 'Buys' : 'Sells',
                              style: TextStyle(
                                fontSize: 10.5,
                                fontWeight: isSel ? FontWeight.w700 : FontWeight.w500,
                                color: isSel ? TerminalColors.action : TerminalColors.textMuted,
                              ),
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                    const SizedBox(width: 6),
                    // Search Field
                    Expanded(
                      child: Container(
                        height: 28,
                        decoration: BoxDecoration(
                          color: TerminalColors.input,
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: TerminalColors.borderSubtle),
                        ),
                        child: TextField(
                          onChanged: (v) => setState(() => _searchQuery = v),
                          style: const TextStyle(fontSize: 11, color: TerminalColors.textMain),
                          decoration: const InputDecoration(
                            hintText: 'Search symbol or order...',
                            hintStyle: TextStyle(fontSize: 10.5, color: TerminalColors.textMuted),
                            prefixIcon: Icon(Icons.search, size: 14, color: TerminalColors.textMuted),
                            prefixIconConstraints: BoxConstraints(minWidth: 26, minHeight: 26),
                            border: InputBorder.none,
                            contentPadding: EdgeInsets.symmetric(vertical: 6),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ],

              const SizedBox(height: 12),

              // Loading or Empty State
              if (_isLoading && rawOrders.isEmpty) ...[
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 24),
                  child: Center(
                    child: SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2, color: TerminalColors.action),
                    ),
                  ),
                ),
              ] else if (displayed.isEmpty) ...[
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    color: TerminalColors.panel.withValues(alpha: 0.5),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: TerminalColors.borderSubtle),
                  ),
                  child: Column(
                    children: [
                      const Icon(Icons.receipt_long_outlined, size: 32, color: TerminalColors.textMuted),
                      const SizedBox(height: 8),
                      Text(
                        rawOrders.isEmpty
                            ? 'No trades yet — your paper trades will appear here'
                            : 'No transactions match the selected filter',
                        style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: TerminalColors.textMain),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        rawOrders.isEmpty
                            ? 'Simulate your first buy or sell order on the Practice desk or test historical strategies.'
                            : 'Try adjusting your side filter or search query.',
                        style: const TextStyle(fontSize: 11, color: TerminalColors.textMuted),
                        textAlign: TextAlign.center,
                      ),
                      if (rawOrders.isEmpty) ...[
                        const SizedBox(height: 14),
                        ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: TerminalColors.action,
                            foregroundColor: Colors.black,
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                            elevation: 0,
                          ),
                          icon: const Icon(Icons.bolt, size: 16),
                          label: const Text('Open Practice Desk →', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800)),
                          onPressed: () {
                            if (widget.onNavigateToPractice != null) {
                              widget.onNavigateToPractice!();
                            } else {
                              QuickTradeModal.show(context);
                            }
                          },
                        ),
                      ],
                    ],
                  ),
                ),
              ] else ...[
                // List of Orders
                ListView.separated(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: displayed.length,
                  separatorBuilder: (_, __) => const Divider(color: TerminalColors.borderSubtle, height: 12),
                  itemBuilder: (context, idx) {
                    final item = displayed[idx];
                    final sym = item['symbol'] ?? 'UNKNOWN';
                    final side = (item['side'] ?? 'BUY').toString().toUpperCase();
                    final qty = (item['quantity'] as num?)?.toDouble() ?? 1.0;
                    final price = (item['fill_price'] ?? item['price'] as num?)?.toDouble() ?? 0.0;
                    final total = qty * price;
                    final isBuy = side == 'BUY';
                    final isReplay = item['is_replay'] == true ||
                        (item['notes'] != null && item['notes'].toString().contains('REPLAY'));
                    final realizedPnl = (item['realized_pnl'] as num?)?.toDouble();
                    final timeStr = _formatTime(item['created_at'] ?? item['timestamp']);

                    return InkWell(
                      onTap: () => _showTransactionDetails(item),
                      borderRadius: BorderRadius.circular(4),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            // Left: Badge + Symbol + Qty & Time
                            Row(
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: isBuy ? TerminalColors.positiveBg : TerminalColors.negativeBg,
                                    borderRadius: BorderRadius.circular(3),
                                  ),
                                  child: Text(
                                    side,
                                    style: TextStyle(
                                      fontSize: 9.5,
                                      fontWeight: FontWeight.w800,
                                      color: isBuy ? TerminalColors.positive : TerminalColors.negative,
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Text(
                                          sym,
                                          style: const TextStyle(
                                            fontSize: 13,
                                            fontWeight: FontWeight.w800,
                                            color: TerminalColors.textMain,
                                          ),
                                        ),
                                        if (isReplay) ...[
                                          const SizedBox(width: 6),
                                          Container(
                                            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                                            decoration: BoxDecoration(
                                              color: const Color(0x33F59E0B),
                                              borderRadius: BorderRadius.circular(2),
                                            ),
                                            child: const Text(
                                              'REPLAY',
                                              style: TextStyle(
                                                fontSize: 8.5,
                                                fontWeight: FontWeight.w800,
                                                color: Color(0xFFFBBF24),
                                              ),
                                            ),
                                          ),
                                        ],
                                      ],
                                    ),
                                    Text(
                                      '${qty % 1 == 0 ? qty.toInt() : qty} sh · $timeStr',
                                      style: const TextStyle(fontSize: 10.5, color: TerminalColors.textMuted),
                                    ),
                                  ],
                                ),
                              ],
                            ),

                            // Right: Price & Total & Realized P&L
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.end,
                              children: [
                                Text(
                                  _currencyFmt.format(total),
                                  style: const TextStyle(
                                    fontSize: 13,
                                    fontFamily: 'monospace',
                                    fontWeight: FontWeight.w700,
                                    color: TerminalColors.textMain,
                                  ),
                                ),
                                if (!isBuy && realizedPnl != null)
                                  Text(
                                    '${realizedPnl >= 0 ? '+' : ''}${_currencyFmt.format(realizedPnl)}',
                                    style: TextStyle(
                                      fontSize: 10.5,
                                      fontFamily: 'monospace',
                                      fontWeight: FontWeight.w700,
                                      color: realizedPnl >= 0 ? TerminalColors.positive : TerminalColors.negative,
                                    ),
                                  )
                                else
                                  Text(
                                    '@ ₹${price.toStringAsFixed(2)}',
                                    style: const TextStyle(
                                      fontSize: 10.5,
                                      fontFamily: 'monospace',
                                      color: TerminalColors.textMuted,
                                    ),
                                  ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ],
            ],
          ),
        );
      },
    );
  }
}
