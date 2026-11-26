import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:finex_mobile/services/api_client.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  FlutterSecureStorage.setMockInitialValues({});

  setUp(() async {
    await apiClient.setToken(null);
    await apiClient.setProfile(null);
    apiClient.recentOrdersNotifier.value = [];
    apiClient.setHttpClient(null);
  });

  tearDown(() async {
    await apiClient.setToken(null);
    await apiClient.setProfile(null);
    apiClient.recentOrdersNotifier.value = [];
    apiClient.setHttpClient(null);
  });

  group('Mobile ApiClient Auth & Revocation Resilience', () {
    test('HTTP 401 on protected endpoints clears local session across profile, orders, and AI', () async {
      apiClient.setHttpClient(
        MockClient((request) async {
          return http.Response(
            jsonEncode({'detail': 'Access token has been revoked'}),
            401,
            headers: {'content-type': 'application/json'},
          );
        }),
      );

      for (final call in <Future<void> Function()>[
        () => apiClient.getProfile(),
        () => apiClient.getOrders(),
        () => apiClient.submitOrder(
              symbol: 'RELIANCE',
              side: 'BUY',
              orderType: 'MARKET',
              quantity: 1,
            ),
        () => apiClient.sendAiAssistantMessage('Hello'),
      ]) {
        await apiClient.setToken('active-jwt-token');
        await apiClient.setProfile({'email': 'investor@example.com'});
        apiClient.recentOrdersNotifier.value = [
          {'id': 'ord-1', 'symbol': 'RELIANCE'},
        ];

        await expectLater(call(), throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', 401)));
        expect(apiClient.isAuthenticated, isFalse);
        expect(apiClient.currentUserProfile, isNull);
        expect(apiClient.recentOrdersNotifier.value, isEmpty);
      }
    });

    test('Disabled account 403 clears session whereas owner-only 403 preserves valid investor session', () async {
      await apiClient.setToken('valid-investor-jwt');
      await apiClient.setProfile({'email': 'investor@example.com'});

      apiClient.setHttpClient(
        MockClient((request) async {
          if (request.url.path.endsWith('/paper-trading/reset')) {
            return http.Response(
              jsonEncode({'detail': 'Forbidden: Sandbox controls and accounts are restricted to the platform owner.'}),
              403,
            );
          }
          return http.Response(
            jsonEncode({'detail': 'Account is disabled or inactive'}),
            403,
          );
        }),
      );

      await expectLater(
        apiClient.resetAccount(),
        throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', 403)),
      );
      expect(apiClient.isAuthenticated, isTrue);

      await expectLater(
        apiClient.getProfile(),
        throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', 403)),
      );
      expect(apiClient.isAuthenticated, isFalse);
    });

    test('Non-JSON 502 error body throws controlled ApiException instead of FormatException', () async {
      await apiClient.setToken('valid-investor-jwt');
      apiClient.setHttpClient(
        MockClient((request) async => http.Response('<html>Bad Gateway</html>', 502)),
      );

      await expectLater(
        apiClient.getProfile(),
        throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', 502)),
      );
      expect(apiClient.isAuthenticated, isTrue);
    });

    test('logout revokes token on backend and clears local credentials even when server rejects with 401', () async {
      String? capturedAuthHeader;
      String? capturedBody;
      await apiClient.setToken('tok-to-revoke');
      await apiClient.setProfile({'email': 'investor@example.com'});

      apiClient.setHttpClient(
        MockClient((request) async {
          capturedAuthHeader = request.headers['Authorization'];
          capturedBody = request.body;
          return http.Response(jsonEncode({'detail': 'Expired'}), 401);
        }),
      );

      await apiClient.logout();
      expect(capturedAuthHeader, 'Bearer tok-to-revoke');
      expect(jsonDecode(capturedBody!), {'token': 'tok-to-revoke'});
      expect(apiClient.isAuthenticated, isFalse);
      expect(apiClient.currentUserProfile, isNull);
    });
  });
}
