import 'package:flutter_test/flutter_test.dart';
import 'package:finex_mobile/services/api_client.dart';
import 'package:finex_mobile/services/order_execution_service.dart';

class MockApiClient extends ApiClient {
  MockApiClient() : super.mock();

  Map<String, dynamic>? mockSubmitResponse;
  Exception? mockSubmitException;
  List<Map<String, dynamic>> mockOrdersResponse = [];
  Map<String, dynamic>? lastSubmittedPayload;

  @override
  Future<Map<String, dynamic>> submitOrder({
    required String symbol,
    required String side,
    required String orderType,
    required double quantity,
    double? limitPrice,
    String? idempotencyKey,
  }) async {
    lastSubmittedPayload = {
      'symbol': symbol,
      'side': side,
      'order_type': orderType,
      'quantity': quantity,
      'limit_price': limitPrice,
      'idempotency_key': idempotencyKey,
    };
    if (mockSubmitException != null) {
      throw mockSubmitException!;
    }
    return mockSubmitResponse ?? {'status': 'FILLED', 'fill_price': 100.0};
  }

  @override
  Future<List<Map<String, dynamic>>> getOrders([int limit = 20]) async {
    return mockOrdersResponse;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late MockApiClient mockClient;
  late OrderExecutionService service;

  setUp(() {
    mockClient = MockApiClient();
    service = OrderExecutionService(mockClient);
  });

  group('OrderExecutionService — Authoritative Parity & Error Handling', () {
    test('Client-side input validations fail closed without network call', () async {
      // Non-positive quantity
      final resQtyZero = await service.executePaperOrder(
        symbol: 'RELIANCE',
        side: 'BUY',
        orderType: 'MARKET',
        quantity: 0,
      );
      expect(resQtyZero.isRejected, isTrue);
      expect(resQtyZero.rejectionReason, contains('strictly positive'));
      expect(mockClient.lastSubmittedPayload, isNull);

      final resQtyNegative = await service.executePaperOrder(
        symbol: 'RELIANCE',
        side: 'BUY',
        orderType: 'MARKET',
        quantity: -5,
      );
      expect(resQtyNegative.isRejected, isTrue);

      // Invalid side
      final resInvalidSide = await service.executePaperOrder(
        symbol: 'RELIANCE',
        side: 'HOLD',
        orderType: 'MARKET',
        quantity: 10,
      );
      expect(resInvalidSide.isRejected, isTrue);
      expect(resInvalidSide.rejectionReason, contains('Invalid order side'));

      // Limit order without limit price
      final resLimitNoPrice = await service.executePaperOrder(
        symbol: 'RELIANCE',
        side: 'BUY',
        orderType: 'LIMIT',
        quantity: 10,
        limitPrice: null,
      );
      expect(resLimitNoPrice.isRejected, isTrue);
      expect(resLimitNoPrice.rejectionReason, contains('greater than zero'));

      // Limit order with negative limit price
      final resLimitNegativePrice = await service.executePaperOrder(
        symbol: 'RELIANCE',
        side: 'BUY',
        orderType: 'LIMIT',
        quantity: 10,
        limitPrice: -100.0,
      );
      expect(resLimitNegativePrice.isRejected, isTrue);
    });

    test('Backend REJECTED envelope is reported honestly without fake fills', () async {
      mockClient.mockSubmitResponse = {
        'id': 'ord-reject-1',
        'status': 'REJECTED',
        'rejection_reason': 'Insufficient virtual cash balance for this order (Required: ₹25,000.00, Available: ₹10,000.00)',
      };

      final res = await service.executePaperOrder(
        symbol: 'RELIANCE',
        side: 'BUY',
        orderType: 'MARKET',
        quantity: 10,
      );

      expect(res.success, isFalse);
      expect(res.isFilled, isFalse);
      expect(res.isRejected, isTrue);
      expect(res.rejectionReason, contains('Insufficient virtual cash balance'));
      expect(res.fillPrice, isNull);
    });

    test('Pending limit order is reported as PENDING without fabricated fill price', () async {
      mockClient.mockSubmitResponse = {
        'id': 'ord-pend-1',
        'status': 'PENDING',
        'symbol': 'TCS',
        'side': 'BUY',
        'quantity': 5,
        'limit_price': 3200.0,
      };

      final res = await service.executePaperOrder(
        symbol: 'TCS',
        side: 'BUY',
        orderType: 'LIMIT',
        quantity: 5,
        limitPrice: 3200.0,
      );

      expect(res.success, isTrue);
      expect(res.isPending, isTrue);
      expect(res.isFilled, isFalse);
      expect(res.fillPrice, equals(0.0));
    });

    test('Filled market order truthfully reports execution and fill price', () async {
      mockClient.mockSubmitResponse = {
        'id': 'ord-fill-1',
        'status': 'FILLED',
        'symbol': 'INFY',
        'side': 'BUY',
        'quantity': 2,
        'fill_price': 1520.45,
      };

      final res = await service.executePaperOrder(
        symbol: 'INFY',
        side: 'BUY',
        orderType: 'MARKET',
        quantity: 2,
      );

      expect(res.success, isTrue);
      expect(res.isFilled, isTrue);
      expect(res.isPending, isFalse);
      expect(res.isRejected, isFalse);
      expect(res.fillPrice, equals(1520.45));
    });

    test('Timeout with successful backend reconciliation adopts backend order', () async {
      const fixedKey = 'mob-ord-test-reconcile-12345';
      mockClient.mockSubmitException = Exception('Connection timed out');
      mockClient.mockOrdersResponse = [
        {
          'id': 'backend-ord-999',
          'idempotency_key': fixedKey,
          'status': 'FILLED',
          'symbol': 'RELIANCE',
          'side': 'BUY',
          'quantity': 10,
          'fill_price': 2510.0,
        }
      ];

      final res = await service.executePaperOrder(
        symbol: 'RELIANCE',
        side: 'BUY',
        orderType: 'MARKET',
        quantity: 10,
        idempotencyKey: fixedKey,
      );

      expect(res.success, isTrue);
      expect(res.isFilled, isTrue);
      expect(res.isUncertain, isFalse);
      expect(res.fillPrice, equals(2510.0));
      expect(res.idempotencyKey, equals(fixedKey));
    });

    test('Timeout without reconciliation match returns UNCERTAIN with safe guidance', () async {
      const fixedKey = 'mob-ord-test-uncertain-67890';
      mockClient.mockSubmitException = Exception('SocketException: Connection refused');
      mockClient.mockOrdersResponse = []; // Reconciliation returns empty list

      final res = await service.executePaperOrder(
        symbol: 'RELIANCE',
        side: 'BUY',
        orderType: 'MARKET',
        quantity: 10,
        idempotencyKey: fixedKey,
      );

      expect(res.success, isFalse);
      expect(res.isFilled, isFalse);
      expect(res.isUncertain, isTrue);
      expect(res.status, equals('UNCERTAIN'));
      expect(res.error, contains('timed out'));
      expect(res.error, contains('Check Order History'));
    });

    test('Idempotency keys are unique and conform to expected format', () {
      final key1 = OrderExecutionService.generateIdempotencyKey();
      final key2 = OrderExecutionService.generateIdempotencyKey();

      expect(key1, isNot(equals(key2)));
      expect(key1, startsWith('mob-ord-'));
      expect(key2, startsWith('mob-ord-'));
    });
  });
}
