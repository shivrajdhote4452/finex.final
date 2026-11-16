import 'dart:async';
import 'dart:math' as math;
import 'api_client.dart';

class OrderExecutionResult {
  final bool success;
  final String status; // 'FILLED', 'PENDING', 'REJECTED', 'UNCERTAIN'
  final String? rejectionReason;
  final double? fillPrice;
  final Map<String, dynamic>? orderData;
  final String? error;
  final bool isUncertain;
  final String idempotencyKey;

  const OrderExecutionResult({
    required this.success,
    required this.status,
    this.rejectionReason,
    this.fillPrice,
    this.orderData,
    this.error,
    this.isUncertain = false,
    required this.idempotencyKey,
  });

  bool get isFilled => status == 'FILLED';
  bool get isPending => status == 'PENDING' || status == 'ACCEPTED';
  bool get isRejected => status == 'REJECTED';
}

class OrderExecutionService {
  final ApiClient _client;
  static final OrderExecutionService _instance = OrderExecutionService._internal(apiClient);
  factory OrderExecutionService([ApiClient? client]) =>
      client != null ? OrderExecutionService._internal(client) : _instance;
  OrderExecutionService._internal(this._client);

  static String generateIdempotencyKey() {
    final rand = math.Random().nextInt(900000) + 100000;
    return 'mob-ord-${DateTime.now().millisecondsSinceEpoch}-$rand';
  }

  static bool isNetworkOrTimeoutError(dynamic err) {
    if (err == null) return false;
    final str = err.toString().toLowerCase();
    return str.contains('timeout') ||
        str.contains('timed out') ||
        str.contains('time out') ||
        str.contains('socketexception') ||
        str.contains('network') ||
        str.contains('connection refused') ||
        str.contains('connection closed') ||
        str.contains('clientexception') ||
        str.contains('handshake');
  }

  /// Authoritative paper order execution matching web & backend contract.
  Future<OrderExecutionResult> executePaperOrder({
    required String symbol,
    required String side,
    required String orderType,
    required double quantity,
    double? limitPrice,
    String? idempotencyKey,
  }) async {
    final key = idempotencyKey ?? generateIdempotencyKey();

    if (quantity <= 0) {
      return OrderExecutionResult(
        success: false,
        status: 'REJECTED',
        rejectionReason: 'Quantity must be strictly positive',
        error: 'Quantity must be strictly positive',
        idempotencyKey: key,
      );
    }

    final cleanSide = side.toUpperCase();
    if (cleanSide != 'BUY' && cleanSide != 'SELL') {
      return OrderExecutionResult(
        success: false,
        status: 'REJECTED',
        rejectionReason: 'Invalid order side: $side',
        error: 'Invalid order side: $side',
        idempotencyKey: key,
      );
    }

    final cleanOrderType = orderType.toUpperCase();
    if (cleanOrderType == 'LIMIT' && (limitPrice == null || limitPrice <= 0)) {
      return OrderExecutionResult(
        success: false,
        status: 'REJECTED',
        rejectionReason: 'Limit price must be greater than zero for LIMIT orders',
        error: 'Limit price must be greater than zero for LIMIT orders',
        idempotencyKey: key,
      );
    }

    try {
      final res = await _client.submitOrder(
        symbol: symbol,
        side: cleanSide,
        orderType: cleanOrderType,
        quantity: quantity,
        limitPrice: cleanOrderType == 'LIMIT' ? limitPrice : null,
        idempotencyKey: key,
      );

      final status = (res['status'] ?? 'FILLED').toString().toUpperCase();
      final reason = res['rejection_reason'] as String?;

      double? toNum(dynamic v) {
        if (v == null) return null;
        if (v is num) return v.toDouble();
        if (v is String) return double.tryParse(v);
        return null;
      }

      final fillPrice = toNum(res['fill_price']) ?? toNum(res['price']);

      if (status == 'FILLED') {
        return OrderExecutionResult(
          success: true,
          status: 'FILLED',
          fillPrice: fillPrice,
          orderData: res,
          idempotencyKey: key,
        );
      } else if (status == 'ACCEPTED' || status == 'PENDING') {
        return OrderExecutionResult(
          success: true,
          status: 'PENDING',
          fillPrice: 0.0,
          orderData: res,
          idempotencyKey: key,
        );
      } else {
        // Explicit backend rejection (insufficient funds, risk check, stale quote, etc.)
        final rejectionMsg = reason ?? 'Order was rejected by the paper execution engine';
        return OrderExecutionResult(
          success: false,
          status: 'REJECTED',
          rejectionReason: rejectionMsg,
          error: rejectionMsg,
          orderData: res,
          idempotencyKey: key,
        );
      }
    } catch (err) {
      if (isNetworkOrTimeoutError(err)) {
        // Attempt reconciliation against recent orders before reporting outcome
        try {
          final recentOrders = await _client.getOrders(10);
          final matched = recentOrders.firstWhere(
            (o) => o['idempotency_key'] == key || o['id'] == key || o['order_id'] == key,
            orElse: () => <String, dynamic>{},
          );

          if (matched.isNotEmpty) {
            final matchedStatus = (matched['status'] ?? 'FILLED').toString().toUpperCase();
            double? toNum(dynamic v) {
              if (v == null) return null;
              if (v is num) return v.toDouble();
              if (v is String) return double.tryParse(v);
              return null;
            }
            final reconciledFill = toNum(matched['fill_price']) ?? toNum(matched['price']);

            if (matchedStatus == 'FILLED') {
              return OrderExecutionResult(
                success: true,
                status: 'FILLED',
                fillPrice: reconciledFill,
                orderData: matched,
                idempotencyKey: key,
              );
            } else if (matchedStatus == 'ACCEPTED' || matchedStatus == 'PENDING') {
              return OrderExecutionResult(
                success: true,
                status: 'PENDING',
                fillPrice: 0.0,
                orderData: matched,
                idempotencyKey: key,
              );
            } else {
              return OrderExecutionResult(
                success: false,
                status: 'REJECTED',
                rejectionReason: matched['rejection_reason'] ?? 'Order was rejected',
                error: matched['rejection_reason'] ?? 'Order was rejected',
                orderData: matched,
                idempotencyKey: key,
              );
            }
          }
        } catch (_) {
          // Reconciliation attempt failed due to persistent network partition
        }

        // Unconfirmed outcome: DO NOT report failure as false rejection, and DO NOT fabricate fill
        return OrderExecutionResult(
          success: false,
          status: 'UNCERTAIN',
          isUncertain: true,
          error: 'Network connection timed out. Order outcome is unconfirmed. Check Order History before retrying to prevent duplicate trades.',
          idempotencyKey: key,
        );
      }

      // Definite HTTP or client error
      final errorMsg = err.toString().replaceFirst('Exception: ', '');
      return OrderExecutionResult(
        success: false,
        status: 'REJECTED',
        rejectionReason: errorMsg,
        error: errorMsg,
        idempotencyKey: key,
      );
    }
  }
}

final orderExecutionService = OrderExecutionService();
