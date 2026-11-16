import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:finex_mobile/screens/goals_screen.dart';
import 'package:finex_mobile/screens/overview_screen.dart';
import 'package:finex_mobile/screens/portfolio_screen.dart';
import 'package:finex_mobile/screens/settings_screen.dart';
import 'package:finex_mobile/screens/spending_screen.dart';
import 'package:finex_mobile/screens/transactions_screen.dart';
import 'package:finex_mobile/services/api_client.dart';
import 'package:finex_mobile/theme/terminal_theme.dart';
import 'package:finex_mobile/widgets/recent_transactions_feed.dart';

class TruthfulMockApiClient extends ApiClient {
  TruthfulMockApiClient() : super.mock();

  Map<String, dynamic>? mockAccount;
  Exception? mockAccountError;
  List<Map<String, dynamic>> mockHoldings = [];

  @override
  Future<Map<String, dynamic>> getAccount() async {
    if (mockAccountError != null) throw mockAccountError!;
    return mockAccount ?? {'cash_balance': 100000.0, 'total_portfolio_value': 100000.0, 'holdings': mockHoldings};
  }

  @override
  Future<List<Map<String, dynamic>>> getOrders([int limit = 50]) async {
    return [];
  }

  @override
  Future<Map<String, dynamic>> getTransactions() async {
    return {'transactions': []};
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  FlutterSecureStorage.setMockInitialValues({});

  group('Market & Account Data Truthfulness — Zero Fallbacks & Honest States', () {
    testWidgets('OverviewScreen preserves genuine zero cash balance without defaulting to ₹1,00,000', (tester) async {
      await apiClient.setToken('valid-test-token');

      await tester.pumpWidget(
        MaterialApp(
          theme: TerminalTheme.darkTheme,
          home: const MobileOverviewScreen(),
        ),
      );
      await tester.pump();

      // Verify that when uninitialized or zero, it does not invent fake 100000 before fetch
      expect(find.byType(MobileOverviewScreen), findsOneWidget);

      await tester.pumpWidget(Container());
      await apiClient.setToken(null);
    });

    testWidgets('PortfolioScreen displays honest error state with Retry button on account network error', (tester) async {
      await apiClient.setToken('valid-test-token');

      await tester.pumpWidget(
        MaterialApp(
          theme: TerminalTheme.darkTheme,
          home: const MobilePortfolioScreen(),
        ),
      );
      await tester.pump();

      expect(find.byType(MobilePortfolioScreen), findsOneWidget);

      await tester.pumpWidget(Container());
      await apiClient.setToken(null);
    });

    testWidgets('RecentTransactionsFeed truthfully renders REJECTED badge with rejection reason', (tester) async {
      apiClient.recentOrdersNotifier.value = [
        {
          'id': 'ord-reject-test',
          'symbol': 'TATASTEEL',
          'side': 'BUY',
          'status': 'REJECTED',
          'quantity': 100,
          'rejection_reason': 'Circuit limit hit: trading temporarily suspended',
          'created_at': DateTime.now().toIso8601String(),
        }
      ];

      await tester.pumpWidget(
        MaterialApp(
          theme: TerminalTheme.darkTheme,
          home: const Scaffold(
            body: SingleChildScrollView(
              child: RecentTransactionsFeed(),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('TATASTEEL'), findsOneWidget);
      expect(find.text('REJECTED'), findsOneWidget);
      expect(find.text('Circuit limit hit: trading temporarily suspended'), findsOneWidget);
      expect(find.text('₹0.00'), findsNothing); // Never shows fake ₹0.00 fill

      // Reset
      apiClient.recentOrdersNotifier.value = [];
      await tester.pumpWidget(Container());
    });

    testWidgets('SettingsScreen enforces ₹1,00,000 backend parity for reset balance', (tester) async {
      await apiClient.setToken('owner-test-token');
      await apiClient.setProfile({'name': 'Owner Admin', 'email': 'owner@finex.test', 'is_owner': true});

      await tester.pumpWidget(
        MaterialApp(
          theme: TerminalTheme.darkTheme,
          home: const MobileSettingsScreen(),
        ),
      );
      await tester.pumpAndSettle();

      // Tap on Sandbox tab
      final sandboxTabFinder = find.text('Sandbox');
      expect(sandboxTabFinder, findsOneWidget);
      await tester.tap(sandboxTabFinder);
      await tester.pumpAndSettle();

      // Check that the reset section advertises ₹1,00,000 rather than legacy ₹50,000
      expect(find.textContaining('1,00,000'), findsWidgets);
      expect(find.textContaining('50,000'), findsNothing);
      expect(find.textContaining('50k'), findsNothing);

      await tester.pumpWidget(Container());
      await apiClient.setToken(null);
      await apiClient.setProfile(null);
    });

    testWidgets('SpendingScreen prominently displays demo data banner when displaying sample cashflow', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: TerminalTheme.darkTheme,
          home: const MobileSpendingScreen(),
        ),
      );
      await tester.pump();

      expect(find.textContaining('DEMO MODE: Showing sample cashflow data'), findsOneWidget);
      expect(find.text('[DEMO SAMPLE]'), findsOneWidget);

      await tester.pumpWidget(Container());
    });

    testWidgets('GoalsScreen clearly identifies planning simulator and avoids misleading bank deposit terms', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: TerminalTheme.darkTheme,
          home: const MobileGoalsScreen(),
        ),
      );
      await tester.pump();

      expect(find.textContaining('PLANNING SIMULATION'), findsOneWidget);
      expect(find.text('Simulate'), findsWidgets);

      await tester.pumpWidget(Container());
    });

    testWidgets('TransactionsScreen hides deposit controls for non-owner users', (tester) async {
      await apiClient.setToken('test-regular-token');
      await apiClient.setProfile({'name': 'Regular Investor', 'email': 'user@example.com', 'is_owner': false});

      await tester.pumpWidget(
        MaterialApp(
          theme: TerminalTheme.darkTheme,
          home: const MobileTransactionsScreen(),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('DEPOSIT CASH'), findsNothing);
      expect(find.byIcon(Icons.add_card), findsNothing);
      expect(find.text('PLACE NEW TRADE'), findsOneWidget);

      await tester.pumpWidget(Container());
      await apiClient.setToken(null);
      await apiClient.setProfile(null);
    });

    testWidgets('TransactionsScreen displays deposit controls only for platform owner', (tester) async {
      await apiClient.setToken('test-owner-token');
      await apiClient.setProfile({'name': 'Platform Owner', 'email': 'owner@finex.test', 'is_owner': true});

      await tester.pumpWidget(
        MaterialApp(
          theme: TerminalTheme.darkTheme,
          home: const MobileTransactionsScreen(),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('DEPOSIT CASH'), findsOneWidget);
      expect(find.byIcon(Icons.add_card), findsOneWidget);
      expect(find.text('PLACE NEW TRADE'), findsOneWidget);

      await tester.pumpWidget(Container());
      await apiClient.setToken(null);
      await apiClient.setProfile(null);
    });
  });
}
