import 'dart:math' as math;
import 'package:flutter/foundation.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';
import '../services/api_client.dart';
import '../theme/terminal_theme.dart';

enum AuthScreenMode { signIn, createAccount, forgotPassword }

class MobileAuthScreen extends StatefulWidget {
  final VoidCallback onAuthenticated;
  final GoogleSignIn? googleSignIn;

  const MobileAuthScreen({
    super.key,
    required this.onAuthenticated,
    this.googleSignIn,
  });

  @override
  State<MobileAuthScreen> createState() => _MobileAuthScreenState();
}

class _MobileAuthScreenState extends State<MobileAuthScreen> {
  AuthScreenMode _mode = AuthScreenMode.signIn;
  bool _isLoading = false;
  String? _errorMessage;
  String? _successMessage;
  bool _isUnverified = false;
  bool _showPassword = false;
  bool _consentAccepted = true;

  late final TextEditingController _nameController;
  late final TextEditingController _emailController;
  late final TextEditingController _passwordController;
  late final GoogleSignIn _googleSignIn;
  late final TapGestureRecognizer _termsRecognizer;
  late final TapGestureRecognizer _privacyRecognizer;

  static const String _googleServerClientId = String.fromEnvironment(
    'GOOGLE_SERVER_CLIENT_ID',
    defaultValue: '71626572471-2333p55kgim64b3738oabca9l9ss9th0.apps.googleusercontent.com',
  );

  @override
  void initState() {
    super.initState();
    _googleSignIn = widget.googleSignIn ??
        GoogleSignIn(
          scopes: ['email', 'openid'],
          clientId: kIsWeb ? _googleServerClientId : null,
          serverClientId: _googleServerClientId.isNotEmpty ? _googleServerClientId : null,
        );
    _nameController = TextEditingController();
    _emailController = TextEditingController();
    _passwordController = TextEditingController();
    _termsRecognizer = TapGestureRecognizer()..onTap = () => _showLegalSheet(context, isTerms: true);
    _privacyRecognizer = TapGestureRecognizer()..onTap = () => _showLegalSheet(context, isTerms: false);
  }

  @override
  void dispose() {
    _termsRecognizer.dispose();
    _privacyRecognizer.dispose();
    _nameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  bool _isValidEmail(String email) {
    return RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$').hasMatch(email.trim());
  }

  Future<void> _handleGoogleSignIn() async {
    if (!_consentAccepted) {
      setState(() {
        _errorMessage = "You must accept the Terms of Service and Privacy Policy to proceed.";
        _successMessage = null;
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _successMessage = null;
      _isUnverified = false;
    });

    try {
      final GoogleSignInAccount? account = await _googleSignIn.signIn();
      if (account == null) {
        if (mounted) setState(() => _isLoading = false);
        return;
      }

      final GoogleSignInAuthentication auth = await account.authentication;
      final String? idToken = auth.idToken;

      if (idToken != null && idToken.isNotEmpty) {
        await apiClient.loginWithGoogle(
          idToken,
          email: account.email,
          name: account.displayName,
        );
      } else {
        throw Exception(
          "Google sign-in did not return a valid OIDC ID token. Verified Google OAuth is required.",
        );
      }

      if (mounted) {
        setState(() => _isLoading = false);
        widget.onAuthenticated();
      }
    } catch (e) {
      if (mounted) {
        final errText = e.toString().replaceFirst("Exception: ", "");
        setState(() {
          _errorMessage = errText;
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _handleEmailSignIn() async {
    if (!_consentAccepted) {
      setState(() {
        _errorMessage = "You must accept the Terms of Service and Privacy Policy to proceed.";
        _successMessage = null;
      });
      return;
    }

    final email = _emailController.text.trim();
    final password = _passwordController.text;

    if (email.isEmpty || password.isEmpty) {
      setState(() {
        _errorMessage = "Please enter both your email address and password.";
        _successMessage = null;
      });
      return;
    }

    if (!_isValidEmail(email)) {
      setState(() {
        _errorMessage = "Please enter a valid email address.";
        _successMessage = null;
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _successMessage = null;
      _isUnverified = false;
    });

    try {
      await apiClient.loginWithEmail(email, password);
      if (mounted) {
        setState(() => _isLoading = false);
        widget.onAuthenticated();
      }
    } catch (e) {
      if (mounted) {
        final errText = e.toString().replaceFirst("Exception: ", "");
        final isUnverified = errText.toLowerCase().contains("not verified") ||
            errText.toLowerCase().contains("check your inbox");
        setState(() {
          _isLoading = false;
          _isUnverified = isUnverified;
          if (isUnverified) {
            _errorMessage =
                "Your email address is not verified yet. Please check your inbox and verify in your browser, or tap resend below.";
          } else {
            _errorMessage = errText;
          }
        });
      }
    }
  }

  Future<void> _handleEmailSignUp() async {
    if (!_consentAccepted) {
      setState(() {
        _errorMessage = "You must accept the Terms of Service and Privacy Policy to proceed.";
        _successMessage = null;
      });
      return;
    }

    final email = _emailController.text.trim();
    final password = _passwordController.text;
    final name = _nameController.text.trim();

    if (email.isEmpty || password.isEmpty) {
      setState(() {
        _errorMessage = "Please enter an email address and password.";
        _successMessage = null;
      });
      return;
    }

    if (!_isValidEmail(email)) {
      setState(() {
        _errorMessage = "Please enter a valid email address.";
        _successMessage = null;
      });
      return;
    }

    if (password.length < 8) {
      setState(() {
        _errorMessage = "Password must be at least 8 characters long.";
        _successMessage = null;
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _successMessage = null;
      _isUnverified = false;
    });

    try {
      final res = await apiClient.signupWithEmail(
        email,
        password,
        name: name.isNotEmpty ? name : null,
      );

      if (mounted) {
        setState(() {
          _isLoading = false;
          if (res['sent'] == false) {
            _errorMessage = res['message'] ??
                "Account registration via email is currently unavailable. Please sign in with Google.";
          } else {
            _successMessage = res['message'] ??
                "If this email address is not already registered, a verification link has been sent. Please open the link in your email browser to activate your account, then sign in.";
            _mode = AuthScreenMode.signIn;
            _passwordController.clear();
          }
        });
      }
    } catch (e) {
      if (mounted) {
        final errText = e.toString().replaceFirst("Exception: ", "");
        setState(() {
          _isLoading = false;
          _errorMessage = errText;
        });
      }
    }
  }

  Future<void> _handleForgotPassword() async {
    final email = _emailController.text.trim();

    if (email.isEmpty) {
      setState(() {
        _errorMessage = "Please enter your email address to receive password reset instructions.";
        _successMessage = null;
      });
      return;
    }

    if (!_isValidEmail(email)) {
      setState(() {
        _errorMessage = "Please enter a valid email address.";
        _successMessage = null;
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _successMessage = null;
      _isUnverified = false;
    });

    try {
      final res = await apiClient.forgotPassword(email);
      if (mounted) {
        setState(() {
          _isLoading = false;
          if (res['sent'] == false) {
            _errorMessage = res['message'] ??
                "Password reset via email is currently unavailable. Please contact support.";
          } else {
            _successMessage = res['message'] ??
                "If an account exists for this email, password reset instructions have been sent. Please open the link in your email browser to choose a new password, then return here to sign in.";
          }
        });
      }
    } catch (e) {
      if (mounted) {
        final errText = e.toString().replaceFirst("Exception: ", "");
        setState(() {
          _isLoading = false;
          _errorMessage = errText;
        });
      }
    }
  }

  Future<void> _handleResendVerification() async {
    final email = _emailController.text.trim();
    final password = _passwordController.text;

    if (email.isEmpty) {
      setState(() {
        _errorMessage = "Please enter your email address to resend the verification link.";
        _successMessage = null;
      });
      return;
    }

    if (!_isValidEmail(email)) {
      setState(() {
        _errorMessage = "Please enter a valid email address.";
        _successMessage = null;
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _successMessage = null;
    });

    try {
      final res = await apiClient.resendVerification(
        email,
        password: password.isNotEmpty ? password : null,
      );

      if (mounted) {
        setState(() {
          _isLoading = false;
          if (res['sent'] == false) {
            _errorMessage = res['message'] ?? "Could not resend verification email.";
          } else {
            _successMessage = res['message'] ??
                "Verification link sent! Please open the link in your email browser to verify your address, then sign in.";
            _isUnverified = false;
          }
        });
      }
    } catch (e) {
      if (mounted) {
        final errText = e.toString().replaceFirst("Exception: ", "");
        setState(() {
          _isLoading = false;
          _errorMessage = errText;
        });
      }
    }
  }

  void _showLegalSheet(BuildContext context, {required bool isTerms}) {
    final title = isTerms ? "FinEx Terms of Service (v1.0)" : "FinEx Privacy Policy (v1.0)";
    final content = isTerms
        ? "1. EDUCATIONAL SIMULATION PLATFORM\n"
          "FinEx is purely an educational financial intelligence and paper-trading terminal. All cash balances (initial ₹1,00,000 virtual funds), transactions, order fills, and holdings operate strictly within a simulated ledger.\n\n"
          "2. ZERO FINANCIAL RISK & NO BROKERAGE CONNECTION\n"
          "No real funds are ever deposited, transferred, routed, or placed at risk. FinEx does not connect to bank accounts, demat accounts, or real exchange matching engines for live trading.\n\n"
          "3. NO REGISTERED INVESTMENT ADVICE\n"
          "FinEx provides educational tools, algorithmic simulations, and grounded regulatory reference material. FinEx is not a SEBI-registered investment advisor or research analyst. No content on this platform constitutes personalized financial recommendations.\n\n"
          "4. REPRODUCIBLE RISK MANAGEMENT\n"
          "Simulated trades follow double-entry ledger bookkeeping. Users are encouraged to practice position sizing, risk mitigation, and disciplined portfolio tracking."
        : "1. PRIVACY-PRESERVING DESIGN\n"
          "FinEx respects your privacy. We collect only the minimum personal data required to maintain your educational workspace: email address, display name, and securely hashed credentials.\n\n"
          "2. INDUSTRY-STANDARD ENCRYPTION\n"
          "Passwords are salted and hashed using bcrypt. Access tokens use HS256 JWTs with fail-closed server-side verification and revocation blacklists.\n\n"
          "3. ZERO SALE OF PERSONAL DATA\n"
          "FinEx never sells, rents, monetizes, or shares user email addresses or activity data with third-party advertisers.\n\n"
          "4. UNIFIED SECURE IDENTITIES\n"
          "When signing in via Google OAuth or verified email/password with the same verified email address, both identities link securely to your same workspace, portfolio holdings, orders, and virtual cash balance.";

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: TerminalColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(12)),
        side: BorderSide(color: TerminalColors.borderSubtle),
      ),
      builder: (ctx) {
        return DraggableScrollableSheet(
          initialChildSize: 0.7,
          minChildSize: 0.4,
          maxChildSize: 0.9,
          expand: false,
          builder: (context, scrollController) {
            return Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Center(
                    child: Container(
                      width: 36,
                      height: 4,
                      margin: const EdgeInsets.only(bottom: 14),
                      decoration: BoxDecoration(
                        color: TerminalColors.borderMedium,
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                  ),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Text(
                          title,
                          style: const TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                            color: TerminalColors.textMain,
                          ),
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close, color: TerminalColors.textMuted, size: 20),
                        onPressed: () => Navigator.pop(ctx),
                      ),
                    ],
                  ),
                  const Divider(color: TerminalColors.borderSubtle, height: 16),
                  Expanded(
                    child: ListView(
                      controller: scrollController,
                      children: [
                        Text(
                          content,
                          style: const TextStyle(
                            fontSize: 12,
                            height: 1.5,
                            color: TerminalColors.textPrimary,
                          ),
                        ),
                        const SizedBox(height: 20),
                      ],
                    ),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            return SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              child: ConstrainedBox(
                constraints: BoxConstraints(minHeight: constraints.maxHeight),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 22.0, vertical: 24.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _buildBrandHeader(),
                          const SizedBox(height: 24),
                          _buildAuthTitle(),
                          const SizedBox(height: 18),
                          if (_mode != AuthScreenMode.forgotPassword) ...[
                            _buildTabSwitcher(),
                            const SizedBox(height: 16),
                          ],
                          if (_errorMessage != null) ...[
                            _buildErrorBanner(),
                            const SizedBox(height: 14),
                          ],
                          if (_successMessage != null) ...[
                            _buildSuccessBanner(),
                            const SizedBox(height: 14),
                          ],
                          if (_mode != AuthScreenMode.forgotPassword) ...[
                            _buildGoogleButton(),
                            _buildDivider(),
                          ],
                          _buildFormFields(),
                        ],
                      ),
                      const SizedBox(height: 28),
                      _buildEducationalPillars(),
                    ],
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildBrandHeader() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Text(
              "FinEx.",
              style: TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.w900,
                letterSpacing: -1.0,
                color: TerminalColors.textMain,
              ),
            ),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: TerminalColors.panel,
                borderRadius: BorderRadius.circular(3),
                border: Border.all(color: TerminalColors.borderSubtle),
              ),
              child: const Text(
                "TERMINAL",
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.8,
                  fontFamily: 'monospace',
                  color: TerminalColors.action,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        const Text(
          "High-Precision Educational Trading Terminal & Wealth Planning (Pure Black Edition)",
          style: TextStyle(fontSize: 12, height: 1.4, color: TerminalColors.textMuted),
        ),
      ],
    );
  }

  Widget _buildAuthTitle() {
    String title;
    String subtitle;

    switch (_mode) {
      case AuthScreenMode.signIn:
        title = "Sign In to FinEx";
        subtitle = "Your personal market workspace awaits.";
        break;
      case AuthScreenMode.createAccount:
        title = "Create Your FinEx Account";
        subtitle = "Start with ₹1,00,000 in virtual funds today.";
        break;
      case AuthScreenMode.forgotPassword:
        title = "Reset Your Password";
        subtitle = "Enter your email to receive recovery instructions.";
        break;
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.w800,
            color: TerminalColors.textMain,
            letterSpacing: -0.3,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          subtitle,
          style: const TextStyle(fontSize: 12, color: TerminalColors.textMuted),
        ),
      ],
    );
  }

  Widget _buildTabSwitcher() {
    final isSignIn = _mode == AuthScreenMode.signIn;
    return Container(
      height: 40,
      decoration: BoxDecoration(
        color: TerminalColors.surface,
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: TerminalColors.borderSubtle),
      ),
      child: Row(
        children: [
          Expanded(
            child: GestureDetector(
              key: const Key('tab_signin'),
              onTap: () {
                setState(() {
                  _mode = AuthScreenMode.signIn;
                  _errorMessage = null;
                  _successMessage = null;
                  _isUnverified = false;
                });
              },
              child: Container(
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: isSignIn ? TerminalColors.action.withValues(alpha: 0.12) : Colors.transparent,
                  borderRadius: BorderRadius.circular(3),
                  border: isSignIn ? Border.all(color: TerminalColors.action, width: 1.2) : null,
                ),
                child: Text(
                  "Sign In",
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: isSignIn ? FontWeight.w700 : FontWeight.w500,
                    color: isSignIn ? TerminalColors.action : TerminalColors.textMuted,
                  ),
                ),
              ),
            ),
          ),
          Expanded(
            child: GestureDetector(
              key: const Key('tab_signup'),
              onTap: () {
                setState(() {
                  _mode = AuthScreenMode.createAccount;
                  _errorMessage = null;
                  _successMessage = null;
                  _isUnverified = false;
                });
              },
              child: Container(
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: !isSignIn ? TerminalColors.action.withValues(alpha: 0.12) : Colors.transparent,
                  borderRadius: BorderRadius.circular(3),
                  border: !isSignIn ? Border.all(color: TerminalColors.action, width: 1.2) : null,
                ),
                child: Text(
                  "Create Account",
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: !isSignIn ? FontWeight.w700 : FontWeight.w500,
                    color: !isSignIn ? TerminalColors.action : TerminalColors.textMuted,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorBanner() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: TerminalColors.negative.withValues(alpha: 0.12),
        border: Border.all(color: TerminalColors.negative.withValues(alpha: 0.8)),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _errorMessage!,
            style: const TextStyle(fontSize: 12, height: 1.4, color: Color(0xFFFFA292)),
          ),
          if (_isUnverified ||
              _errorMessage!.toLowerCase().contains("not verified") ||
              _errorMessage!.toLowerCase().contains("resend")) ...[
            const SizedBox(height: 8),
            GestureDetector(
              key: const Key('btn_resend_verification'),
              onTap: _isLoading ? null : _handleResendVerification,
              child: const Text(
                "Resend verification link →",
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: TerminalColors.action,
                  decoration: TextDecoration.underline,
                ),
              ),
            ),
          ],
          if (_mode == AuthScreenMode.signIn &&
              _errorMessage!.toLowerCase().contains("invalid email or password")) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 14,
              runSpacing: 6,
              children: [
                GestureDetector(
                  key: const Key('link_forgot_from_error'),
                  onTap: () {
                    setState(() {
                      _mode = AuthScreenMode.forgotPassword;
                      _errorMessage = null;
                    });
                  },
                  child: const Text(
                    "Forgot password?",
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: TerminalColors.action,
                    ),
                  ),
                ),
                GestureDetector(
                  key: const Key('link_signup_from_error'),
                  onTap: () {
                    setState(() {
                      _mode = AuthScreenMode.createAccount;
                      _errorMessage = null;
                    });
                  },
                  child: const Text(
                    "Create account →",
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: TerminalColors.textMain,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildSuccessBanner() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: TerminalColors.positive.withValues(alpha: 0.12),
        border: Border.all(color: TerminalColors.positive.withValues(alpha: 0.8)),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        _successMessage!,
        style: const TextStyle(fontSize: 12, height: 1.4, color: Color(0xFF7AE8C4)),
      ),
    );
  }

  Widget _buildGoogleButton() {
    return SizedBox(
      width: double.infinity,
      height: 48,
      child: OutlinedButton(
        key: const Key('btn_google'),
        style: OutlinedButton.styleFrom(
          backgroundColor: const Color(0xFF161616),
          foregroundColor: TerminalColors.textMain,
          side: const BorderSide(color: TerminalColors.borderMedium),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
          elevation: 0,
        ),
        onPressed: _isLoading ? null : _handleGoogleSignIn,
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: [
            const GoogleLogo(size: 18),
            const SizedBox(width: 12),
            Flexible(
              child: Text(
                _isLoading ? "CONNECTING..." : "Continue with Google",
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.2,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDivider() {
    return const Padding(
      padding: EdgeInsets.symmetric(vertical: 16.0),
      child: Row(
        children: [
          Expanded(child: Divider(color: TerminalColors.borderSubtle)),
          Padding(
            padding: EdgeInsets.symmetric(horizontal: 10.0),
            child: Text(
              "or with email",
              style: TextStyle(fontSize: 11, color: TerminalColors.textMuted),
            ),
          ),
          Expanded(child: Divider(color: TerminalColors.borderSubtle)),
        ],
      ),
    );
  }

  Widget _buildFormFields() {
    switch (_mode) {
      case AuthScreenMode.signIn:
        return _buildSignInForm();
      case AuthScreenMode.createAccount:
        return _buildSignUpForm();
      case AuthScreenMode.forgotPassword:
        return _buildForgotPasswordForm();
    }
  }

  Widget _buildSignInForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildTextField(
          fieldKey: const Key('input_email'),
          controller: _emailController,
          label: "Email Address",
          hint: "name@example.com",
          keyboardType: TextInputType.emailAddress,
        ),
        const SizedBox(height: 14),
        _buildPasswordField(fieldKey: const Key('input_password'), isSignUp: false),
        const SizedBox(height: 8),
        _buildConsentCheckbox(),
        const SizedBox(height: 12),
        _buildPrimaryButton(
          buttonKey: const Key('btn_submit'),
          label: _isLoading ? "SIGNING IN..." : "Sign In to Workspace →",
          onPressed: _handleEmailSignIn,
        ),
        const SizedBox(height: 14),
        Center(
          child: Wrap(
            alignment: WrapAlignment.center,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              const Text("Don't have an account? ", style: TextStyle(fontSize: 12, color: TerminalColors.textMuted)),
              GestureDetector(
                key: const Key('link_switch_to_signup'),
                onTap: () {
                  setState(() {
                    _mode = AuthScreenMode.createAccount;
                    _errorMessage = null;
                    _successMessage = null;
                  });
                },
                child: const Text(
                  "Create Account",
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: TerminalColors.action,
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildSignUpForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildTextField(
          fieldKey: const Key('input_name'),
          controller: _nameController,
          label: "Your Full Name",
          hint: "e.g. Aditi Sharma",
          keyboardType: TextInputType.name,
        ),
        const SizedBox(height: 14),
        _buildTextField(
          fieldKey: const Key('input_email'),
          controller: _emailController,
          label: "Email Address",
          hint: "name@example.com",
          keyboardType: TextInputType.emailAddress,
        ),
        const SizedBox(height: 14),
        _buildPasswordField(fieldKey: const Key('input_password'), isSignUp: true),
        const SizedBox(height: 8),
        _buildConsentCheckbox(),
        const SizedBox(height: 12),
        _buildPrimaryButton(
          buttonKey: const Key('btn_submit'),
          label: _isLoading ? "CREATING ACCOUNT..." : "Create Account & Verify Email →",
          onPressed: _handleEmailSignUp,
        ),
        const SizedBox(height: 14),
        Center(
          child: Wrap(
            alignment: WrapAlignment.center,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              const Text("Already have an account? ", style: TextStyle(fontSize: 12, color: TerminalColors.textMuted)),
              GestureDetector(
                key: const Key('link_switch_to_signin'),
                onTap: () {
                  setState(() {
                    _mode = AuthScreenMode.signIn;
                    _errorMessage = null;
                    _successMessage = null;
                  });
                },
                child: const Text(
                  "Sign In",
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: TerminalColors.action,
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildForgotPasswordForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(12),
          margin: const EdgeInsets.only(bottom: 16),
          decoration: BoxDecoration(
            color: TerminalColors.panel,
            borderRadius: BorderRadius.circular(4),
            border: const Border(left: BorderSide(color: TerminalColors.action, width: 3)),
          ),
          child: const Text(
            "Note: The password reset link will open in your web browser. Once updated, return here to sign in with your new password.",
            style: TextStyle(fontSize: 11, height: 1.4, color: TerminalColors.textMuted),
          ),
        ),
        _buildTextField(
          fieldKey: const Key('input_email'),
          controller: _emailController,
          label: "Account Email Address",
          hint: "name@example.com",
          keyboardType: TextInputType.emailAddress,
        ),
        const SizedBox(height: 16),
        _buildPrimaryButton(
          buttonKey: const Key('btn_submit'),
          label: _isLoading ? "SENDING INSTRUCTIONS..." : "Send Password Reset Link →",
          onPressed: _handleForgotPassword,
        ),
        const SizedBox(height: 12),
        SizedBox(
          width: double.infinity,
          height: 44,
          child: OutlinedButton(
            key: const Key('btn_back_to_signin'),
            style: OutlinedButton.styleFrom(
              foregroundColor: TerminalColors.textMuted,
              side: const BorderSide(color: TerminalColors.borderSubtle),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
            ),
            onPressed: () {
              setState(() {
                _mode = AuthScreenMode.signIn;
                _errorMessage = null;
                _successMessage = null;
              });
            },
            child: const Text(
              "← Back to Sign In",
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildTextField({
    Key? fieldKey,
    required TextEditingController controller,
    required String label,
    required String hint,
    required TextInputType keyboardType,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: TerminalColors.textMuted),
        ),
        const SizedBox(height: 6),
        TextFormField(
          key: fieldKey,
          controller: controller,
          keyboardType: keyboardType,
          style: const TextStyle(fontSize: 13, color: TerminalColors.textMain),
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: const TextStyle(fontSize: 12, color: TerminalColors.textFaint),
            filled: true,
            fillColor: TerminalColors.input,
            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(4),
              borderSide: const BorderSide(color: TerminalColors.borderSubtle),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(4),
              borderSide: const BorderSide(color: TerminalColors.borderSubtle),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(4),
              borderSide: const BorderSide(color: TerminalColors.action, width: 1.5),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildPasswordField({Key? fieldKey, required bool isSignUp}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Flexible(
              child: Text(
                isSignUp ? "Password (min. 8 characters)" : "Password",
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: TerminalColors.textMuted),
              ),
            ),
            if (!isSignUp)
              GestureDetector(
                key: const Key('link_forgot_password'),
                onTap: () {
                  setState(() {
                    _mode = AuthScreenMode.forgotPassword;
                    _errorMessage = null;
                    _successMessage = null;
                  });
                },
                child: const Text(
                  "Forgot password?",
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: TerminalColors.action,
                  ),
                ),
              ),
          ],
        ),
        const SizedBox(height: 6),
        TextFormField(
          key: fieldKey,
          controller: _passwordController,
          obscureText: !_showPassword,
          style: const TextStyle(fontSize: 13, color: TerminalColors.textMain),
          decoration: InputDecoration(
            hintText: isSignUp ? "At least 8 characters" : "••••••••",
            hintStyle: const TextStyle(fontSize: 12, color: TerminalColors.textFaint),
            filled: true,
            fillColor: TerminalColors.input,
            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(4),
              borderSide: const BorderSide(color: TerminalColors.borderSubtle),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(4),
              borderSide: const BorderSide(color: TerminalColors.borderSubtle),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(4),
              borderSide: const BorderSide(color: TerminalColors.action, width: 1.5),
            ),
            suffixIcon: IconButton(
              icon: Text(
                _showPassword ? "Hide" : "Show",
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: TerminalColors.textMuted),
              ),
              onPressed: () => setState(() => _showPassword = !_showPassword),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildConsentCheckbox() {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 20,
            height: 20,
            child: Checkbox(
              key: const Key('checkbox_consent'),
              value: _consentAccepted,
              activeColor: TerminalColors.action,
              checkColor: Colors.black,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(3)),
              side: const BorderSide(color: TerminalColors.borderMedium, width: 1.5),
              onChanged: (val) => setState(() => _consentAccepted = val ?? false),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: RichText(
              text: TextSpan(
                style: const TextStyle(fontSize: 11, height: 1.4, color: TerminalColors.textMuted),
                children: [
                  const TextSpan(text: "I accept the "),
                  TextSpan(
                    text: "Terms of Service",
                    style: const TextStyle(
                      fontSize: 11,
                      color: TerminalColors.action,
                      fontWeight: FontWeight.w600,
                      decoration: TextDecoration.underline,
                    ),
                    recognizer: _termsRecognizer,
                  ),
                  const TextSpan(text: " and "),
                  TextSpan(
                    text: "Privacy Policy",
                    style: const TextStyle(
                      fontSize: 11,
                      color: TerminalColors.action,
                      fontWeight: FontWeight.w600,
                      decoration: TextDecoration.underline,
                    ),
                    recognizer: _privacyRecognizer,
                  ),
                  const TextSpan(
                    text: ", and understand FinEx is an educational platform.",
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPrimaryButton({
    Key? buttonKey,
    required String label,
    required VoidCallback? onPressed,
  }) {
    return SizedBox(
      width: double.infinity,
      height: 48,
      child: ElevatedButton(
        key: buttonKey,
        style: ElevatedButton.styleFrom(
          backgroundColor: TerminalColors.action,
          foregroundColor: Colors.black,
          disabledBackgroundColor: TerminalColors.action.withValues(alpha: 0.3),
          disabledForegroundColor: Colors.black45,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
          elevation: 0,
        ),
        onPressed: _isLoading ? null : onPressed,
        child: _isLoading
            ? const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black),
              )
            : Text(
                label,
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800, letterSpacing: 0.4),
              ),
      ),
    );
  }

  Widget _buildEducationalPillars() {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                decoration: BoxDecoration(
                  color: TerminalColors.surface,
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: TerminalColors.borderSubtle),
                ),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      "₹1,00,000",
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w800,
                        color: TerminalColors.positive,
                        fontFamily: 'monospace',
                      ),
                    ),
                    SizedBox(height: 2),
                    Text(
                      "Virtual Funds",
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 10, color: TerminalColors.textMuted),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                decoration: BoxDecoration(
                  color: TerminalColors.surface,
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: TerminalColors.borderSubtle),
                ),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      "AI Guided",
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFFA5B4FC),
                      ),
                    ),
                    SizedBox(height: 2),
                    Text(
                      "Educational Insights",
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 10, color: TerminalColors.textMuted),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 14),
        const Text(
          "FinEx is an educational platform. Paper trading uses virtual funds.",
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 11, color: TerminalColors.textMuted),
        ),
        const SizedBox(height: 8),
        Wrap(
          alignment: WrapAlignment.center,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            GestureDetector(
              key: const Key('footer_privacy'),
              onTap: () => _showLegalSheet(context, isTerms: false),
              child: const Text(
                "Privacy Policy",
                style: TextStyle(fontSize: 11, color: TerminalColors.textFaint),
              ),
            ),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 8.0),
              child: Text("•", style: TextStyle(color: TerminalColors.textFaint)),
            ),
            GestureDetector(
              key: const Key('footer_terms'),
              onTap: () => _showLegalSheet(context, isTerms: true),
              child: const Text(
                "Terms of Service",
                style: TextStyle(fontSize: 11, color: TerminalColors.textFaint),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class GoogleLogo extends StatelessWidget {
  final double size;
  const GoogleLogo({super.key, this.size = 18});

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      size: Size(size, size),
      painter: _GoogleLogoPainter(),
    );
  }
}

class _GoogleLogoPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final double w = size.width;
    final double h = size.height;
    final center = Offset(w / 2, h / 2);
    final radius = w / 2;

    const blue = Color(0xFF4285F4);
    const red = Color(0xFFEA4335);
    const yellow = Color(0xFFFBBC05);
    const green = Color(0xFF34A853);

    final strokeWidth = w * 0.22;
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth;

    final arcRect = Rect.fromCircle(center: center, radius: radius - strokeWidth / 2);

    paint.color = red;
    canvas.drawArc(arcRect, -math.pi * 0.75, math.pi * 0.55, false, paint);

    paint.color = blue;
    canvas.drawArc(arcRect, -math.pi * 0.2, math.pi * 0.45, false, paint);

    paint.color = green;
    canvas.drawArc(arcRect, math.pi * 0.25, math.pi * 0.5, false, paint);

    paint.color = yellow;
    canvas.drawArc(arcRect, math.pi * 0.75, math.pi * 0.5, false, paint);

    final barPaint = Paint()
      ..color = blue
      ..style = PaintingStyle.fill;
    final barRect = Rect.fromLTWH(
      center.dx - strokeWidth * 0.1,
      center.dy - strokeWidth / 2,
      radius - strokeWidth * 0.4,
      strokeWidth,
    );
    canvas.drawRect(barRect, barPaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class MobileOnboardingScreen extends StatefulWidget {
  final VoidCallback onOnboardingComplete;

  const MobileOnboardingScreen({super.key, required this.onOnboardingComplete});

  @override
  State<MobileOnboardingScreen> createState() => _MobileOnboardingScreenState();
}

class _MobileOnboardingScreenState extends State<MobileOnboardingScreen> {
  bool _consentAccepted = false;
  String _investmentHorizon = "3-5";

  // Server-authoritative questionnaire selections (Q1-Q4)
  String _q1Option = "Q1_C";
  String _q2Option = "Q2_C";
  String _q3Option = "Q3_B";
  String _q4Option = "Q4_D";

  bool _isSubmitting = false;
  String? _errorMessage;

  Future<void> _submitOnboarding() async {
    if (!_consentAccepted) {
      setState(() => _errorMessage = "You must accept the FinEx simulation consent to proceed.");
      return;
    }

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    try {
      // 1. Record consent v1.0
      await apiClient.recordConsent(
        consentVersion: "v1.0",
        termsAccepted: true,
        privacyAccepted: true,
        educationalDisclaimerAccepted: true,
      );

      // 2. Submit server-authoritative risk answers (no fabricated client scores)
      final qAnswers = [
        {"question_id": "Q1", "option_id": _q1Option},
        {"question_id": "Q2", "option_id": _q2Option},
        {"question_id": "Q3", "option_id": _q3Option},
        {"question_id": "Q4", "option_id": _q4Option},
      ];

      await apiClient.submitRiskAssessment(
        horizonCategory: _investmentHorizon,
        answers: qAnswers,
        questionnaireVersion: "v1.0",
      );

      if (mounted) {
        widget.onOnboardingComplete();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString().replaceFirst("Exception: ", "");
          _isSubmitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        title: const Text(
          "Investor Onboarding & Consent",
          style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: TerminalColors.textMain),
        ),
        elevation: 0,
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            const Text(
              "MANDATORY ONBOARDING COMPLIANCE",
              style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: TerminalColors.action, letterSpacing: 0.8),
            ),
            const SizedBox(height: 6),
            const Text(
              "Risk Assessment & Regulatory Terms",
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: TerminalColors.textMain),
            ),
            const SizedBox(height: 16),
            if (_errorMessage != null)
              Container(
                padding: const EdgeInsets.all(10),
                margin: const EdgeInsets.only(bottom: 14),
                decoration: BoxDecoration(
                  color: Colors.red.withValues(alpha: 0.1),
                  border: Border.all(color: Colors.red),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(_errorMessage!, style: const TextStyle(fontSize: 11, color: Colors.redAccent)),
              ),

            // Step 1: Investment Horizon
            Container(
              padding: const EdgeInsets.all(16),
              margin: const EdgeInsets.only(bottom: 16),
              decoration: BoxDecoration(
                color: TerminalColors.surface,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: TerminalColors.borderSubtle),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("INVESTMENT HORIZON", style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: TerminalColors.action)),
                  const SizedBox(height: 8),
                  const Text("What is your expected investment timeframe?", style: TextStyle(fontSize: 12, color: TerminalColors.textMuted)),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    initialValue: _investmentHorizon,
                    dropdownColor: TerminalColors.panel,
                    style: const TextStyle(fontSize: 12, color: TerminalColors.textMain),
                    decoration: const InputDecoration(
                      filled: true,
                      fillColor: TerminalColors.panel,
                      border: OutlineInputBorder(borderSide: BorderSide(color: TerminalColors.borderSubtle)),
                    ),
                    items: const [
                      DropdownMenuItem(value: "<1", child: Text("< 1 Year (Constrained capacity)")),
                      DropdownMenuItem(value: "1-3", child: Text("1 to 3 Years (Near-term capital protection)")),
                      DropdownMenuItem(value: "3-5", child: Text("3 to 5 Years (Balanced market cycle window)")),
                      DropdownMenuItem(value: ">5", child: Text("> 5 Years (Long-term compounding timeframe)")),
                    ],
                    onChanged: (val) {
                      if (val != null) setState(() => _investmentHorizon = val);
                    },
                  ),
                ],
              ),
            ),

            // Question 1: Willingness
            _buildQuestionCard(
              number: "1",
              title: "MARKET CORRECTION BEHAVIOR",
              prompt: "If your portfolio dropped by 15% in a broad market correction over 3 months, what would you do?",
              options: const [
                {"id": "Q1_A", "label": "Panic & sell all holdings"},
                {"id": "Q1_B", "label": "Sell a portion to hold cash"},
                {"id": "Q1_C", "label": "Do nothing & wait for recovery"},
                {"id": "Q1_D", "label": "Buy more shares at discount"},
              ],
              selectedId: _q1Option,
              onSelected: (id) => setState(() => _q1Option = id),
            ),

            // Question 2: Capacity (Emergency Reserves)
            _buildQuestionCard(
              number: "2",
              title: "EMERGENCY RESERVES",
              prompt: "How many months of basic living expenses do you hold in liquid cash/emergency reserves?",
              options: const [
                {"id": "Q2_A", "label": "Less than 1 month"},
                {"id": "Q2_B", "label": "1 to 3 months"},
                {"id": "Q2_C", "label": "3 to 6 months reserves"},
                {"id": "Q2_D", "label": "Over 6 months secure reserves"},
              ],
              selectedId: _q2Option,
              onSelected: (id) => setState(() => _q2Option = id),
            ),

            // Question 3: Willingness (Return Profile)
            _buildQuestionCard(
              number: "3",
              title: "TARGET RETURN PROFILE",
              prompt: "Which asset return profile best aligns with your primary investment goal?",
              options: const [
                {"id": "Q3_A", "label": "Capital preservation (5-7%)"},
                {"id": "Q3_B", "label": "Balanced growth (9-11%)"},
                {"id": "Q3_C", "label": "Wealth maximization (13-16%)"},
              ],
              selectedId: _q3Option,
              onSelected: (id) => setState(() => _q3Option = id),
            ),

            // Question 4: Capacity (Fixed Debt Payments)
            _buildQuestionCard(
              number: "4",
              title: "DEBT OBLIGATIONS (EMIs)",
              prompt: "What proportion of your monthly take-home income is committed to fixed debt payments?",
              options: const [
                {"id": "Q4_A", "label": "Over 50% committed to EMIs"},
                {"id": "Q4_B", "label": "30% to 50% committed"},
                {"id": "Q4_C", "label": "10% to 30% committed"},
                {"id": "Q4_D", "label": "Zero / negligible loan debt"},
              ],
              selectedId: _q4Option,
              onSelected: (id) => setState(() => _q4Option = id),
            ),

            // Step 2: Educational Consent Agreement
            Container(
              padding: const EdgeInsets.all(16),
              margin: const EdgeInsets.only(bottom: 20),
              decoration: BoxDecoration(
                color: TerminalColors.surface,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: TerminalColors.borderSubtle),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    "SEBI SIMULATED TRADING CONSENT (v1.0)",
                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: TerminalColors.action),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    "FinEx is purely an educational paper-trading terminal. All cash and trades are simulated in an isolated virtual ledger without real financial routing or exchange connectivity. PII descriptions are masked server-side.",
                    style: TextStyle(fontSize: 11, height: 1.4, color: TerminalColors.textMuted),
                  ),
                  const SizedBox(height: 12),
                  CheckboxListTile(
                    value: _consentAccepted,
                    activeColor: TerminalColors.action,
                    checkColor: Colors.black,
                    contentPadding: EdgeInsets.zero,
                    title: const Text(
                      "I accept the educational terms, privacy policy, and simulated paper execution rules.",
                      style: TextStyle(fontSize: 11, color: TerminalColors.textMain, fontWeight: FontWeight.w600),
                    ),
                    onChanged: (val) => setState(() => _consentAccepted = val ?? false),
                  ),
                ],
              ),
            ),

            // Submit Button
            SizedBox(
              width: double.infinity,
              height: 48,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: TerminalColors.action,
                  foregroundColor: Colors.black,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                ),
                onPressed: _isSubmitting ? null : _submitOnboarding,
                child: Text(
                  _isSubmitting ? "COMPLETING ONBOARDING..." : "ENTER FINEX TERMINAL",
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800, letterSpacing: 0.5),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQuestionCard({
    required String number,
    required String title,
    required String prompt,
    required List<Map<String, String>> options,
    required String selectedId,
    required ValueChanged<String> onSelected,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: TerminalColors.surface,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: TerminalColors.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: TerminalColors.panel,
                  borderRadius: BorderRadius.circular(2),
                ),
                child: Text(
                  "Q$number",
                  style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: TerminalColors.action),
                ),
              ),
              const SizedBox(width: 8),
              Text(
                title,
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: TerminalColors.textMain),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            prompt,
            style: const TextStyle(fontSize: 12, color: TerminalColors.textMuted, height: 1.3),
          ),
          const SizedBox(height: 12),
          Column(
            children: options.map((opt) {
              final isSelected = selectedId == opt["id"];
              return GestureDetector(
                onTap: () => onSelected(opt["id"]!),
                child: Container(
                  width: double.infinity,
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(
                    color: isSelected ? TerminalColors.action.withValues(alpha: 0.15) : TerminalColors.panel,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(
                      color: isSelected ? TerminalColors.action : TerminalColors.borderSubtle,
                      width: isSelected ? 1.5 : 1.0,
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        isSelected ? Icons.radio_button_checked : Icons.radio_button_off,
                        size: 16,
                        color: isSelected ? TerminalColors.action : TerminalColors.textMuted,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          opt["label"]!,
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                            color: isSelected ? TerminalColors.action : TerminalColors.textMain,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}
