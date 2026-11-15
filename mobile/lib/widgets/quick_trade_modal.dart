import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../services/api_client.dart';
import '../services/order_execution_service.dart';
import '../theme/terminal_theme.dart';
import 'app_toast.dart';

class QuickTradeModal extends StatefulWidget {
  final String? initialSymbol;
  final double? initialPrice;
  final VoidCallback? onTradeExecuted;

  const QuickTradeModal({
    super.key,
    this.initialSymbol,
    this.initialPrice,
    this.onTradeExecuted,
  });

  static Future<void> show(
    BuildContext context, {
    String? initialSymbol,
    double? initialPrice,
    VoidCallback? onTradeExecuted,
    VoidCallback? onOrderPlaced,
  }) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => QuickTradeModal(
        initialSymbol: initialSymbol,
        initialPrice: initialPrice,
        onTradeExecuted: onTradeExecuted ?? onOrderPlaced,
      ),
    );
  }

  @override
  State<QuickTradeModal> createState() => _QuickTradeModalState();
}

class _QuickTradeModalState extends State<QuickTradeModal> {
  late String _symbol;
  String _side = 'BUY';
  final String _orderType = 'MARKET';
  int _quantity = 10;
  double? _currentPrice;
  double _availableCash = 100000.0;
  bool _isLoading = false;
  bool _isQuoteLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _symbol = widget.initialSymbol ?? 'RELIANCE';
    _currentPrice = widget.initialPrice;
    _fetchAccountAndQuote();
  }

  Future<void> _fetchAccountAndQuote() async {
    try {
      final acct = await apiClient.getAccount();
      final cash = (acct['cash_balance'] ?? acct['current_cash'] as num?)?.toDouble();
      if (cash != null && mounted) {
        setState(() => _availableCash = cash);
      }
    } catch (_) {}

    try {
      final quote = await apiClient.getQuote(_symbol);
      if (mounted && quote != null) {
        final p = quote['price'] ?? quote['ltp'] ?? quote['regular_market_price'];
        double? parsedPrice;
        if (p is num) {
          parsedPrice = p.toDouble();
        } else if (p is String) {
          parsedPrice = double.tryParse(p);
        }
        if (parsedPrice != null && parsedPrice > 0) {
          setState(() {
            _currentPrice = parsedPrice;
            _isQuoteLoading = false;
          });
          return;
        }
      }
    } catch (_) {}

    if (mounted) {
      setState(() => _isQuoteLoading = false);
    }
  }

  double? get _estimatedTotal => _currentPrice != null ? _quantity * _currentPrice! : null;

  Future<void> _executeTrade() async {
    if (_currentPrice == null || _currentPrice! <= 0) {
      setState(() => _errorMessage = 'Current market price is unavailable. Cannot execute order.');
      return;
    }

    final total = _estimatedTotal ?? 0.0;
    if (_side == 'BUY' && total > _availableCash) {
      setState(() => _errorMessage =
          'Insufficient virtual cash (Required: ₹${total.toStringAsFixed(2)}, Available: ₹${_availableCash.toStringAsFixed(2)})');
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final result = await orderExecutionService.executePaperOrder(
        symbol: _symbol,
        side: _side,
        orderType: _orderType,
        quantity: _quantity.toDouble(),
        limitPrice: _orderType == 'LIMIT' ? _currentPrice : null,
      );

      if (!mounted) return;

      if (result.isFilled) {
        Navigator.pop(context);
        final verb = _side.toUpperCase() == 'BUY' ? 'Bought' : 'Sold';
        final fillPrice = result.fillPrice ?? _currentPrice ?? 0.0;
        final priceFmt = NumberFormat.currency(symbol: '₹', locale: 'en_IN', decimalDigits: 2).format(fillPrice);
        AppToast.success(
          context,
          '$verb $_quantity $_symbol @ $priceFmt',
        );
        widget.onTradeExecuted?.call();
      } else if (result.isPending) {
        Navigator.pop(context);
        AppToast.info(
          context,
          'Limit order placed (Pending fill in order book)',
          title: 'Order Placed',
        );
        widget.onTradeExecuted?.call();
      } else if (result.isRejected) {
        final reason = result.rejectionReason ?? result.error ?? 'Order was rejected by execution engine';
        setState(() {
          _errorMessage = reason;
          _isLoading = false;
        });
        AppToast.error(
          context,
          reason,
          title: 'Trade Rejected',
        );
      } else if (result.isUncertain) {
        final msg = result.error ?? 'Order outcome is unconfirmed. Check Order History before retrying.';
        setState(() {
          _errorMessage = msg;
          _isLoading = false;
        });
        AppToast.error(
          context,
          msg,
          title: 'Order Outcome Uncertain',
        );
      }
    } catch (e) {
      if (mounted) {
        final err = e.toString().replaceFirst('Exception: ', '');
        setState(() {
          _errorMessage = err;
          _isLoading = false;
        });
        AppToast.error(
          context,
          err,
          title: 'Trade Failed',
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;
    return Container(
      padding: EdgeInsets.only(bottom: bottomInset),
      decoration: const BoxDecoration(
        color: TerminalColors.surface,
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
        border: Border(top: BorderSide(color: TerminalColors.borderSubtle)),
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header Drag Handle
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

              // Title Row
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: TerminalColors.actionBg,
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: const Text('⚡ INSTANT TRADE',
                            style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: TerminalColors.action)),
                      ),
                      const SizedBox(width: 10),
                      Text('$_symbol (NSE)',
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: TerminalColors.textMain)),
                    ],
                  ),
                  if (_currentPrice != null)
                    Text('₹${_currentPrice!.toStringAsFixed(2)}',
                        style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w800,
                            fontFamily: 'monospace',
                            color: TerminalColors.positive))
                  else if (_isQuoteLoading)
                    const Text('Fetching quote...',
                        style: TextStyle(fontSize: 12, color: TerminalColors.textMuted))
                  else
                    const Text('Price unavailable',
                        style: TextStyle(fontSize: 12, color: TerminalColors.textMuted)),
                ],
              ),
              const SizedBox(height: 16),

              // Buy / Sell Toggle
              Container(
                height: 38,
                decoration: BoxDecoration(
                  color: TerminalColors.input,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: TerminalColors.borderSubtle),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: GestureDetector(
                        onTap: () => setState(() => _side = 'BUY'),
                        child: Container(
                          decoration: BoxDecoration(
                            color: _side == 'BUY' ? TerminalColors.positiveBg : Colors.transparent,
                            borderRadius: BorderRadius.circular(5),
                            border: _side == 'BUY' ? Border.all(color: TerminalColors.positive) : null,
                          ),
                          alignment: Alignment.center,
                          child: Text(
                            'BUY',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w800,
                              color: _side == 'BUY' ? TerminalColors.positive : TerminalColors.textMuted,
                            ),
                          ),
                        ),
                      ),
                    ),
                    Expanded(
                      child: GestureDetector(
                        onTap: () => setState(() => _side = 'SELL'),
                        child: Container(
                          decoration: BoxDecoration(
                            color: _side == 'SELL' ? TerminalColors.negativeBg : Colors.transparent,
                            borderRadius: BorderRadius.circular(5),
                            border: _side == 'SELL' ? Border.all(color: TerminalColors.negative) : null,
                          ),
                          alignment: Alignment.center,
                          child: Text(
                            'SELL',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w800,
                              color: _side == 'SELL' ? TerminalColors.negative : TerminalColors.textMuted,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),

              // Quantity Selector
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('QUANTITY (SHARES)',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: TerminalColors.textMuted)),
                  Row(
                    children: [
                      _buildPresetBtn(1),
                      const SizedBox(width: 6),
                      _buildPresetBtn(5),
                      const SizedBox(width: 6),
                      _buildPresetBtn(10),
                      const SizedBox(width: 6),
                      _buildPresetBtn(50),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 8),

              // Quantity Stepper
              Container(
                height: 44,
                padding: const EdgeInsets.symmetric(horizontal: 8),
                decoration: BoxDecoration(
                  color: TerminalColors.input,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: TerminalColors.borderSubtle),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    IconButton(
                      icon: const Icon(Icons.remove, size: 18, color: TerminalColors.textMain),
                      onPressed: _quantity > 1 ? () => setState(() => _quantity--) : null,
                    ),
                    Text(
                      '$_quantity Shares',
                      style: const TextStyle(
                          fontSize: 15, fontWeight: FontWeight.w800, fontFamily: 'monospace', color: TerminalColors.textMain),
                    ),
                    IconButton(
                      icon: const Icon(Icons.add, size: 18, color: TerminalColors.textMain),
                      onPressed: () => setState(() => _quantity++),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),

              // Financial Summary Box
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: TerminalColors.panel,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: TerminalColors.borderSubtle),
                ),
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Estimated Outlay', style: TextStyle(fontSize: 12, color: TerminalColors.textMuted)),
                        if (_estimatedTotal != null)
                          Text('₹${_estimatedTotal!.toStringAsFixed(2)}',
                              style: const TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w800,
                                  fontFamily: 'monospace',
                                  color: TerminalColors.textMain))
                        else
                          const Text('—',
                              style: TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w800,
                                  fontFamily: 'monospace',
                                  color: TerminalColors.textMuted)),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Virtual Cash Available', style: TextStyle(fontSize: 11, color: TerminalColors.textFaint)),
                        Text('₹${_availableCash.toStringAsFixed(2)}',
                            style: const TextStyle(
                                fontSize: 11, fontFamily: 'monospace', color: TerminalColors.action)),
                      ],
                    ),
                  ],
                ),
              ),

              if (_errorMessage != null) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: TerminalColors.negativeBg,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(_errorMessage!, style: const TextStyle(fontSize: 11, color: TerminalColors.negative)),
                ),
              ],
              const SizedBox(height: 16),

              // Execute Button
              SizedBox(
                width: double.infinity,
                height: 46,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _currentPrice == null
                        ? TerminalColors.borderMedium
                        : (_side == 'BUY' ? TerminalColors.positive : TerminalColors.negative),
                    foregroundColor: Colors.black,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                    elevation: 0,
                  ),
                  onPressed: (_isLoading || _currentPrice == null) ? null : _executeTrade,
                  child: Text(
                    _isLoading
                        ? 'PROCESSING...'
                        : (_currentPrice == null
                            ? 'QUOTE UNAVAILABLE'
                            : '$_side $_quantity SHARES OF $_symbol'),
                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, letterSpacing: 0.5),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPresetBtn(int q) {
    final isSelected = _quantity == q;
    return InkWell(
      onTap: () => setState(() => _quantity = q),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: isSelected ? TerminalColors.actionBg : TerminalColors.panel,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: isSelected ? TerminalColors.action : TerminalColors.borderSubtle),
        ),
        child: Text('$q',
            style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: isSelected ? TerminalColors.action : TerminalColors.textMuted)),
      ),
    );
  }
}
