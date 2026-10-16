import 'package:flutter_test/flutter_test.dart';
import 'package:finex_mobile/main.dart';

void main() {
  testWidgets('FinEx mobile terminal app smoke test', (WidgetTester tester) async {
    // Build our FinEx application and trigger a frame.
    await tester.pumpWidget(const FinExMobileApp());

    // Verify brand and key terminal navigation items exist
    expect(find.text('FinEx.'), findsOneWidget);
    expect(find.text("Shivraj's workspace"), findsOneWidget);
    expect(find.text('Home'), findsOneWidget);
    expect(find.text('Markets'), findsOneWidget);
    expect(find.text('Ask'), findsOneWidget);
    expect(find.text('More'), findsOneWidget);
  });
}
