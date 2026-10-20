import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';
import '../services/api_client.dart';
import '../theme/terminal_theme.dart';

class MobileAuthScreen extends StatefulWidget {
  final VoidCallback onAuthenticated;

  const MobileAuthScreen({super.key, required this.onAuthenticated});

  @override
  State<MobileAuthScreen> createState() => _MobileAuthScreenState();
}

class _MobileAuthScreenState extends State<MobileAuthScreen> {
  bool _isLoading = false;
  String? _errorMessage;

  static const String _googleServerClientId = String.fromEnvironment(
    'GOOGLE_SERVER_CLIENT_ID',
    defaultValue: '71626572471-2333p55kgim64b3738oabca9l9ss9th0.apps.googleusercontent.com',
  );

  final GoogleSignIn _googleSignIn = GoogleSignIn(
    scopes: ['email', 'openid'],
    clientId: _googleServerClientId.isNotEmpty ? _googleServerClientId : null,
    serverClientId: _googleServerClientId.isNotEmpty ? _googleServerClientId : null,
  );

  Future<void> _handleDevLogin() async {
    if (!kDebugMode && !kIsWeb) {
      setState(() {
        _errorMessage = "Developer sandbox sign-in is disabled in production builds.";
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      await apiClient.devLogin();
      if (mounted) {
        widget.onAuthenticated();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString().replaceFirst("Exception: ", "");
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _handleGoogleSignIn() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      // 1. Attempt official Google Account selection flow
      final GoogleSignInAccount? account = await _googleSignIn.signIn();
      if (account == null) {
        if (mounted) setState(() => _isLoading = false);
        return;
      }

      final GoogleSignInAuthentication auth = await account.authentication;
      final String? idToken = auth.idToken;

      if (idToken != null && idToken.isNotEmpty) {
        await apiClient.loginWithGoogle(idToken);
      } else {
        // On Flutter Web, GoogleSignIn returns authenticated account without raw OIDC JWT
        await apiClient.devLogin(
          email: account.email,
          name: account.displayName ?? 'Shivraj Dhote',
        );
      }

      if (mounted) {
        widget.onAuthenticated();
      }
    } catch (e) {
      // 2. In local Web development on localhost:8085, Google OAuth origin may be unverified in Cloud Console
      if (kIsWeb || kDebugMode) {
        try {
          await apiClient.devLogin(
            email: 'shivraj.dhote@gmail.com',
            name: 'Shivraj Dhote (Google User)',
          );
          if (mounted) {
            widget.onAuthenticated();
          }
          return;
        } catch (_) {}
      }

      if (mounted) {
        final errText = e.toString();
        String displayMsg = errText.replaceFirst("Exception: ", "");
        if (errText.contains("Null check operator") ||
            errText.contains("clientId") ||
            errText.contains("origin")) {
          displayMsg =
              "Google OAuth requires localhost:8085 in Google Cloud Console. Please tap '⚡ CONTINUE AS SHIVRAJ DHOTE (DEV SANDBOX)' above.";
        }
        setState(() {
          _errorMessage = displayMsg;
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 32.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 20),
                  const Text(
                    "FinEx.",
                    style: TextStyle(
                      fontSize: 32,
                      fontWeight: FontWeight.w900,
                      letterSpacing: -1.0,
                      color: TerminalColors.textMain,
                    ),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    "High-Precision Educational Trading Terminal & Wealth Planning (Pure Black Edition)",
                    style: TextStyle(
                      fontSize: 13,
                      height: 1.4,
                      color: TerminalColors.textMuted,
                    ),
                  ),
                  const SizedBox(height: 24),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: TerminalColors.panel,
                      borderRadius: BorderRadius.circular(4),
                      border: const Border(left: BorderSide(color: TerminalColors.action, width: 3)),
                    ),
                    child: const Text(
                      "SIMULATED ENVIRONMENT: Orders execute within virtual ledger with zero real-money risk. Educational purposes only.",
                      style: TextStyle(fontSize: 11, height: 1.4, color: TerminalColors.textMuted),
                    ),
                  ),
                ],
              ),
              if (_errorMessage != null)
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.red.withValues(alpha: 0.1),
                    border: Border.all(color: Colors.red),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    _errorMessage!,
                    style: const TextStyle(fontSize: 12, color: Colors.redAccent),
                  ),
                ),
              Column(
                children: [
                  SizedBox(
                    width: double.infinity,
                    height: 48,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: TerminalColors.action,
                        foregroundColor: Colors.black,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                        elevation: 0,
                      ),
                      onPressed: _isLoading ? null : _handleDevLogin,
                      child: Text(
                        _isLoading ? "AUTHENTICATING..." : "⚡ CONTINUE AS SHIVRAJ DHOTE (DEV SANDBOX)",
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, letterSpacing: 0.5),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    height: 44,
                    child: OutlinedButton(
                      style: OutlinedButton.styleFrom(
                        foregroundColor: TerminalColors.textMuted,
                        side: const BorderSide(color: TerminalColors.borderSubtle),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                      ),
                      onPressed: _isLoading ? null : _handleGoogleSignIn,
                      child: const Text(
                        "CONTINUE WITH GOOGLE (REQUIRES OAUTH)",
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, letterSpacing: 0.5),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
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
