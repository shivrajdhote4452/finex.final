import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:finex_mobile/main.dart';
import 'package:finex_mobile/services/api_client.dart';
import 'package:finex_mobile/theme/terminal_theme.dart';

void main() {
  testWidgets('FinEx mobile unauthenticated launches auth screen', (WidgetTester tester) async {
    apiClient.setToken(null);
    await tester.pumpWidget(const FinExMobileApp());
    await tester.pumpAndSettle();

    // Verify brand and key auth buttons exist in pure black terminal auth
    expect(find.text('FinEx.'), findsOneWidget);
    expect(find.text('CONTINUE WITH GOOGLE'), findsOneWidget);
    expect(find.text('DEVELOPER SANDBOX SIGN-IN'), findsOneWidget);
  });

  testWidgets('FinEx mobile navigation shell displays workspace tabs', (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: TerminalTheme.darkTheme,
        home: const MainMobileNavigationShell(),
      ),
    );
    await tester.pumpAndSettle();

    // Verify workspace brand and key terminal navigation items exist
    expect(find.text("Shivraj's workspace"), findsOneWidget);
    expect(find.text('Home'), findsOneWidget);
    expect(find.text('Markets'), findsOneWidget);
    expect(find.text('Ask'), findsOneWidget);
    expect(find.text('More'), findsOneWidget);
  });
}
