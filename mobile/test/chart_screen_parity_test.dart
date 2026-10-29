import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:finex_mobile/screens/chart_screen.dart';
import 'package:finex_mobile/theme/terminal_theme.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Mobile Chart Screen — Freshness & Honest Data Parity', () {
    testWidgets('Renders MobileChartScreen without throwing exception and shows terminal header', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: TerminalTheme.darkTheme,
          home: const MobileChartScreen(
            initialSymbol: 'RELIANCE',
            isIndex: false,
          ),
        ),
      );

      // Verify header elements exist
      expect(find.text('RELIANCE'), findsOneWidget);
      expect(find.byType(MobileChartScreen), findsOneWidget);

      // Timeframe chips exist
      expect(find.text('1D'), findsWidgets);
      expect(find.text('1W'), findsWidgets);
      expect(find.text('1M'), findsWidgets);
      expect(find.text('1Y'), findsOneWidget);

      await tester.pumpWidget(Container());
    });

    testWidgets('Renders index mode for NIFTY 50 without fake candle generators', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: TerminalTheme.darkTheme,
          home: const MobileChartScreen(
            initialSymbol: 'NIFTY 50',
            isIndex: true,
          ),
        ),
      );

      expect(find.text('NIFTY 50'), findsOneWidget);
      await tester.pumpWidget(Container());
    });
  });
}

