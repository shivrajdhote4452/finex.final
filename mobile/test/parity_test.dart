import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:finex_mobile/services/api_client.dart';
import 'package:finex_mobile/widgets/error_boundary.dart';
import 'package:finex_mobile/widgets/recent_transactions_feed.dart';
import 'package:finex_mobile/theme/terminal_theme.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  FlutterSecureStorage.setMockInitialValues({});

  group('Task 1 — Identity & Dynamic Greetings', () {
    test('getTimeOfDayGreeting with name includes greeting and name', () {
      final greeting = ApiClient.getTimeOfDayGreeting('Priya');
      expect(greeting, anyOf(
        startsWith('Good morning, Priya'),
        startsWith('Good afternoon, Priya'),
        startsWith('Good evening, Priya'),
      ));
    });

    test('getTimeOfDayGreeting with null or empty name renders generic greeting with no name and no comma', () {
      final greetingNull = ApiClient.getTimeOfDayGreeting(null);
      expect(greetingNull, anyOf(
        equals('Good morning'),
        equals('Good afternoon'),
        equals('Good evening'),
      ));
      expect(greetingNull.contains(','), isFalse);

      final greetingEmpty = ApiClient.getTimeOfDayGreeting('');
      expect(greetingEmpty, anyOf(
        equals('Good morning'),
        equals('Good afternoon'),
        equals('Good evening'),
      ));
      expect(greetingEmpty.contains(','), isFalse);

      final greetingWhitespace = ApiClient.getTimeOfDayGreeting('   ');
      expect(greetingWhitespace, anyOf(
        equals('Good morning'),
        equals('Good afternoon'),
        equals('Good evening'),
      ));
      expect(greetingWhitespace.contains(','), isFalse);
    });

    test('Owner sandbox gate fails closed when unauthenticated or non-owner', () async {
      await apiClient.setToken(null);
      await apiClient.setProfile(null);
      expect(apiClient.isOwner, isFalse);

      // Authenticated with non-owner email fails closed
      await apiClient.setToken('test-token');
      await apiClient.setProfile({'name': 'Regular User', 'email': 'regular@example.com'});
      expect(apiClient.isOwner, isFalse);

      // Authenticated with null/empty email fails closed
      await apiClient.setProfile({'name': 'Anonymous', 'email': ''});
      expect(apiClient.isOwner, isFalse);

      // Authenticated with owner email succeeds
      await apiClient.setProfile({'name': 'Owner User', 'email': 'shivrajdhote4452@gmail.com'});
      expect(apiClient.isOwner, isTrue);

      // Reset
      await apiClient.setToken(null);
      await apiClient.setProfile(null);
    });
  });

  group('Task 2 — Transactions Ledger & Feed', () {
    testWidgets('Empty ledger renders honest empty state with CTA', (WidgetTester tester) async {
      apiClient.recentOrdersNotifier.value = [];

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

      expect(find.text('No trades yet — your paper trades will appear here'), findsOneWidget);
      expect(find.textContaining('Open Practice Desk'), findsOneWidget);
    });

    testWidgets('Populated ledger renders orders with side badges and immediate update', (WidgetTester tester) async {
      apiClient.recentOrdersNotifier.value = [
        {
          'id': 'test-ord-1',
          'symbol': 'TCS',
          'side': 'BUY',
          'quantity': 10,
          'price': 3500.0,
          'total_amount': 35000.0,
          'status': 'FILLED',
          'created_at': DateTime.now().toIso8601String(),
          'is_replay': false,
        },
        {
          'id': 'test-ord-2',
          'symbol': 'INFY',
          'side': 'SELL',
          'quantity': 5,
          'price': 1600.0,
          'total_amount': 8000.0,
          'realized_pnl': 250.0,
          'status': 'FILLED',
          'created_at': DateTime.now().toIso8601String(),
          'is_replay': true,
        },
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

      expect(find.text('TCS'), findsOneWidget);
      expect(find.text('INFY'), findsOneWidget);
      expect(find.text('BUY'), findsOneWidget);
      expect(find.text('SELL'), findsOneWidget);
      expect(find.text('REPLAY'), findsOneWidget);
      expect(find.textContaining('+₹250.00'), findsOneWidget);
    });
  });

  group('Task 5 — Error Boundary & Fallback View', () {
    testWidgets('ErrorFallbackView displays error details and action buttons', (WidgetTester tester) async {
      bool tryAgainCalled = false;
      bool refreshCalled = false;

      await tester.pumpWidget(
        MaterialApp(
          theme: TerminalTheme.darkTheme,
          home: Scaffold(
            body: ErrorFallbackView(
              onTryAgain: () => tryAgainCalled = true,
              onRefresh: () => refreshCalled = true,
              error: 'Test error explosion',
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Something went wrong'), findsOneWidget);
      expect(find.text('Try again'), findsOneWidget);
      expect(find.text('Refresh'), findsOneWidget);
      expect(find.textContaining('Test error explosion'), findsOneWidget);

      await tester.tap(find.text('Try again'));
      expect(tryAgainCalled, isTrue);

      await tester.tap(find.text('Refresh'));
      expect(refreshCalled, isTrue);
    });

    testWidgets('FinExErrorBoundary captures reported error and resets on try again', (WidgetTester tester) async {
      final key = GlobalKey();

      await tester.pumpWidget(
        MaterialApp(
          theme: TerminalTheme.darkTheme,
          home: Scaffold(
            body: FinExErrorBoundary(
              key: key,
              child: const Text('Healthy Screen Content'),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Healthy Screen Content'), findsOneWidget);
      expect(find.text('Something went wrong'), findsNothing);

      // Report error to boundary
      final dynamic state = key.currentState;
      state.reportError('Simulated runtime error', null);
      await tester.pumpAndSettle();

      // Error view active
      expect(find.text('Healthy Screen Content'), findsNothing);
      expect(find.text('Something went wrong'), findsOneWidget);

      // Tap Try Again to reset
      await tester.tap(find.text('Try again'));
      await tester.pumpAndSettle();

      // Healthy screen restored
      expect(find.text('Healthy Screen Content'), findsOneWidget);
      expect(find.text('Something went wrong'), findsNothing);
    });
  });
}
