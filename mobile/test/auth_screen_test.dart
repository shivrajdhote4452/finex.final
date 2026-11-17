import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:finex_mobile/screens/auth_screen.dart';
import 'package:finex_mobile/services/api_client.dart';
import 'package:finex_mobile/theme/terminal_theme.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  FlutterSecureStorage.setMockInitialValues({});

  setUp(() async {
    await apiClient.setToken(null);
    await apiClient.setProfile(null);
    apiClient.mockLoginWithEmailHandler = null;
    apiClient.mockSignupWithEmailHandler = null;
    apiClient.mockForgotPasswordHandler = null;
    apiClient.mockResendVerificationHandler = null;
    apiClient.mockLoginWithGoogleHandler = null;
  });

  tearDown(() async {
    await apiClient.setToken(null);
    await apiClient.setProfile(null);
    apiClient.mockLoginWithEmailHandler = null;
    apiClient.mockSignupWithEmailHandler = null;
    apiClient.mockForgotPasswordHandler = null;
    apiClient.mockResendVerificationHandler = null;
    apiClient.mockLoginWithGoogleHandler = null;
  });

  Widget buildTestableAuthScreen({VoidCallback? onAuthenticated}) {
    return MaterialApp(
      theme: TerminalTheme.darkTheme,
      home: Scaffold(
        body: MobileAuthScreen(
          onAuthenticated: onAuthenticated ?? () {},
        ),
      ),
    );
  }

  group('FinEx Mobile Authentication Screen — Visuals & Parity', () {
    testWidgets('Renders pure black theme, brand title, and platform pillars', (tester) async {
      await tester.pumpWidget(buildTestableAuthScreen());
      await tester.pumpAndSettle();

      // Brand mark and terminal pill
      expect(find.text('FinEx.'), findsOneWidget);
      expect(find.text('TERMINAL'), findsOneWidget);
      expect(
        find.text('High-Precision Educational Trading Terminal & Wealth Planning (Pure Black Edition)'),
        findsOneWidget,
      );

      // Clean Continue with Google button without implementation text
      expect(find.byKey(const Key('btn_google')), findsOneWidget);
      expect(find.text('Continue with Google'), findsOneWidget);
      expect(find.textContaining('REQUIRES OAUTH'), findsNothing);

      // Mode header
      expect(find.text('Sign In to FinEx'), findsOneWidget);
      expect(find.text('Your personal market workspace awaits.'), findsOneWidget);

      // Tabs
      expect(find.byKey(const Key('tab_signin')), findsOneWidget);
      expect(find.byKey(const Key('tab_signup')), findsOneWidget);

      // Input fields
      expect(find.byKey(const Key('input_email')), findsOneWidget);
      expect(find.byKey(const Key('input_password')), findsOneWidget);
      expect(find.byKey(const Key('link_forgot_password')), findsOneWidget);

      // Action button
      expect(find.byKey(const Key('btn_submit')), findsOneWidget);
      expect(find.text('Sign In to Workspace →'), findsOneWidget);

      // Bottom educational recap pillars
      expect(find.text('₹1,00,000'), findsOneWidget);
      expect(find.text('Virtual Funds'), findsOneWidget);
      expect(find.text('AI Guided'), findsOneWidget);
      expect(find.text('Educational Insights'), findsOneWidget);
      expect(
        find.text('FinEx is an educational platform. Paper trading uses virtual funds.'),
        findsOneWidget,
      );
    });

    testWidgets('Switches smoothly between Sign In, Create Account, and Forgot Password', (tester) async {
      await tester.pumpWidget(buildTestableAuthScreen());
      await tester.pumpAndSettle();

      // Switch to Create Account via tab
      await tester.tap(find.byKey(const Key('tab_signup')));
      await tester.pumpAndSettle();

      expect(find.text('Create Your FinEx Account'), findsOneWidget);
      expect(find.text('Start with ₹1,00,000 in virtual funds today.'), findsOneWidget);
      expect(find.byKey(const Key('input_name')), findsOneWidget);
      expect(find.text('Create Account & Verify Email →'), findsOneWidget);

      // Switch back to Sign In via tab
      await tester.tap(find.byKey(const Key('tab_signin')));
      await tester.pumpAndSettle();

      expect(find.text('Sign In to FinEx'), findsOneWidget);
      expect(find.text('Sign In to Workspace →'), findsOneWidget);

      // Open Forgot Password
      await tester.tap(find.byKey(const Key('link_forgot_password')));
      await tester.pumpAndSettle();

      expect(find.text('Reset Your Password'), findsOneWidget);
      expect(find.byKey(const Key('input_email')), findsOneWidget);
      expect(find.text('Send Password Reset Link →'), findsOneWidget);
      expect(find.byKey(const Key('btn_back_to_signin')), findsOneWidget);
      expect(
        find.textContaining('Note: The password reset link will open in your web browser.'),
        findsOneWidget,
      );

      // Return to Sign In
      await tester.ensureVisible(find.byKey(const Key('btn_back_to_signin')));
      await tester.tap(find.byKey(const Key('btn_back_to_signin')));
      await tester.pumpAndSettle();

      expect(find.text('Sign In to FinEx'), findsOneWidget);
    });

    testWidgets('Toggles password visibility between obscure and plain text', (tester) async {
      await tester.pumpWidget(buildTestableAuthScreen());
      await tester.pumpAndSettle();

      expect(find.text('Show'), findsOneWidget);

      await tester.tap(find.text('Show'));
      await tester.pumpAndSettle();

      expect(find.text('Hide'), findsOneWidget);

      await tester.tap(find.text('Hide'));
      await tester.pumpAndSettle();

      expect(find.text('Show'), findsOneWidget);
    });
  });

  group('FinEx Mobile Authentication Screen — Validation & Error States', () {
    testWidgets('Validates empty and malformed email inputs', (tester) async {
      await tester.pumpWidget(buildTestableAuthScreen());
      await tester.pumpAndSettle();

      // Empty submission
      await tester.ensureVisible(find.byKey(const Key('btn_submit')));
      await tester.tap(find.byKey(const Key('btn_submit')));
      await tester.pumpAndSettle();

      expect(find.text('Please enter both your email address and password.'), findsOneWidget);

      // Malformed email
      await tester.enterText(find.byKey(const Key('input_email')), 'invalid-email');
      await tester.enterText(find.byKey(const Key('input_password')), 'Password123!');
      await tester.ensureVisible(find.byKey(const Key('btn_submit')));
      await tester.tap(find.byKey(const Key('btn_submit')));
      await tester.pumpAndSettle();

      expect(find.text('Please enter a valid email address.'), findsOneWidget);
    });

    testWidgets('Enforces minimum 8-character password requirement on Create Account', (tester) async {
      await tester.pumpWidget(buildTestableAuthScreen());
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('tab_signup')));
      await tester.pumpAndSettle();

      await tester.enterText(find.byKey(const Key('input_email')), 'investor@example.com');
      await tester.enterText(find.byKey(const Key('input_password')), 'short');
      await tester.ensureVisible(find.byKey(const Key('btn_submit')));
      await tester.tap(find.byKey(const Key('btn_submit')));
      await tester.pumpAndSettle();

      expect(find.text('Password must be at least 8 characters long.'), findsOneWidget);
    });

    testWidgets('Requires consent acceptance to proceed', (tester) async {
      await tester.pumpWidget(buildTestableAuthScreen());
      await tester.pumpAndSettle();

      // Uncheck consent checkbox
      await tester.ensureVisible(find.byKey(const Key('checkbox_consent')));
      await tester.tap(find.byKey(const Key('checkbox_consent')));
      await tester.pumpAndSettle();

      await tester.enterText(find.byKey(const Key('input_email')), 'investor@example.com');
      await tester.enterText(find.byKey(const Key('input_password')), 'SecurePassword123!');
      await tester.ensureVisible(find.byKey(const Key('btn_submit')));
      await tester.tap(find.byKey(const Key('btn_submit')));
      await tester.pumpAndSettle();

      expect(find.text('You must accept the Terms of Service and Privacy Policy to proceed.'), findsOneWidget);
    });
  });

  group('FinEx Mobile Authentication Screen — Flows & Backend Parity', () {
    testWidgets('Successful email/password sign-in calls API and triggers onAuthenticated', (tester) async {
      bool authenticated = false;
      apiClient.mockLoginWithEmailHandler = (email, password) async {
        await apiClient.setToken('test-access-token');
        await apiClient.setProfile({
          'id': 'usr-123',
          'email': email,
          'name': 'Aditi Sharma',
          'onboarding_completed': true,
          'risk_band': 'MODERATE',
        });
        return {
          'access_token': 'test-access-token',
          'user_id': 'usr-123',
          'email': email,
          'name': 'Aditi Sharma',
        };
      };

      await tester.pumpWidget(buildTestableAuthScreen(onAuthenticated: () {
        authenticated = true;
      }));
      await tester.pumpAndSettle();

      await tester.enterText(find.byKey(const Key('input_email')), 'aditi@example.com');
      await tester.enterText(find.byKey(const Key('input_password')), 'ValidPass123!');
      await tester.ensureVisible(find.byKey(const Key('btn_submit')));
      await tester.tap(find.byKey(const Key('btn_submit')));
      await tester.pumpAndSettle();

      expect(authenticated, isTrue);
      expect(apiClient.isAuthenticated, isTrue);
    });

    testWidgets('Unverified account sign-in displays error and provides resend verification CTA', (tester) async {
      apiClient.mockLoginWithEmailHandler = (email, password) async {
        throw ApiException(
          'Email address is not verified. Please check your inbox or request a new verification link.',
          statusCode: 403,
        );
      };

      bool resendCalled = false;
      apiClient.mockResendVerificationHandler = (email, {password}) async {
        resendCalled = true;
        return {
          'sent': true,
          'message': 'Verification link sent! Please open the link in your email browser to verify your address.',
        };
      };

      await tester.pumpWidget(buildTestableAuthScreen());
      await tester.pumpAndSettle();

      await tester.enterText(find.byKey(const Key('input_email')), 'unverified@example.com');
      await tester.enterText(find.byKey(const Key('input_password')), 'ValidPass123!');
      await tester.ensureVisible(find.byKey(const Key('btn_submit')));
      await tester.tap(find.byKey(const Key('btn_submit')));
      await tester.pumpAndSettle();

      expect(find.textContaining('Your email address is not verified yet.'), findsOneWidget);
      expect(find.byKey(const Key('btn_resend_verification')), findsOneWidget);

      // Tap Resend
      await tester.ensureVisible(find.byKey(const Key('btn_resend_verification')));
      await tester.tap(find.byKey(const Key('btn_resend_verification')));
      await tester.pumpAndSettle();

      expect(resendCalled, isTrue);
      expect(find.textContaining('Verification link sent!'), findsOneWidget);
    });

    testWidgets('Create account successfully dispatches verification and shows browser instructions', (tester) async {
      bool signupCalled = false;
      apiClient.mockSignupWithEmailHandler = (email, password, {name}) async {
        signupCalled = true;
        return {
          'sent': true,
          'email': email,
          'delivery_status': 'delivered',
          'message': 'If this email address is not already registered, a verification link has been sent. Please check your inbox.',
        };
      };

      await tester.pumpWidget(buildTestableAuthScreen());
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('tab_signup')));
      await tester.pumpAndSettle();

      await tester.enterText(find.byKey(const Key('input_name')), 'Aditi Sharma');
      await tester.enterText(find.byKey(const Key('input_email')), 'aditi@example.com');
      await tester.enterText(find.byKey(const Key('input_password')), 'StrongPass123!');
      await tester.ensureVisible(find.byKey(const Key('btn_submit')));
      await tester.tap(find.byKey(const Key('btn_submit')));
      await tester.pumpAndSettle();

      expect(signupCalled, isTrue);
      expect(find.textContaining('verification link has been sent'), findsOneWidget);
      // Automatically switched back to Sign In mode for seamless login after email verification
      expect(find.text('Sign In to FinEx'), findsOneWidget);
    });

    testWidgets('Forgot password successfully dispatches recovery instructions', (tester) async {
      bool forgotCalled = false;
      apiClient.mockForgotPasswordHandler = (email) async {
        forgotCalled = true;
        return {
          'sent': true,
          'delivery_status': 'delivered',
          'message': 'If an account exists for this email, password reset instructions have been sent.',
        };
      };

      await tester.pumpWidget(buildTestableAuthScreen());
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('link_forgot_password')));
      await tester.pumpAndSettle();

      await tester.enterText(find.byKey(const Key('input_email')), 'aditi@example.com');
      await tester.ensureVisible(find.byKey(const Key('btn_submit')));
      await tester.tap(find.byKey(const Key('btn_submit')));
      await tester.pumpAndSettle();

      expect(forgotCalled, isTrue);
      expect(find.textContaining('password reset instructions have been sent'), findsOneWidget);
    });

    testWidgets('Terms of Service and Privacy Policy open in-app modal sheet', (tester) async {
      await tester.pumpWidget(buildTestableAuthScreen());
      await tester.pumpAndSettle();

      // Tap Terms of Service link in footer
      await tester.ensureVisible(find.byKey(const Key('footer_terms')));
      await tester.tap(find.byKey(const Key('footer_terms')));
      await tester.pumpAndSettle();

      expect(find.text('FinEx Terms of Service (v1.0)'), findsOneWidget);
      expect(find.textContaining('EDUCATIONAL SIMULATION PLATFORM'), findsOneWidget);

      // Close modal
      await tester.tap(find.byIcon(Icons.close));
      await tester.pumpAndSettle();

      expect(find.text('FinEx Terms of Service (v1.0)'), findsNothing);

      // Tap Privacy Policy link in footer
      await tester.ensureVisible(find.byKey(const Key('footer_privacy')));
      await tester.tap(find.byKey(const Key('footer_privacy')));
      await tester.pumpAndSettle();

      expect(find.text('FinEx Privacy Policy (v1.0)'), findsOneWidget);
      expect(find.textContaining('PRIVACY-PRESERVING DESIGN'), findsOneWidget);

      await tester.tap(find.byIcon(Icons.close));
      await tester.pumpAndSettle();

      expect(find.text('FinEx Privacy Policy (v1.0)'), findsNothing);
    });

    testWidgets('Renders properly without clipping on narrow viewport (320x568)', (tester) async {
      tester.view.physicalSize = const Size(320, 568);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(buildTestableAuthScreen());
      await tester.pumpAndSettle();

      expect(find.text('FinEx.'), findsOneWidget);
      expect(find.byKey(const Key('btn_google')), findsOneWidget);
      expect(find.byKey(const Key('btn_submit')), findsOneWidget);
    });
  });
}
