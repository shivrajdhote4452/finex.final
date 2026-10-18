import 'package:flutter/material.dart';
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

  Future<void> _handleDevLogin() async {
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
      // Check for Google OAuth ID token from native environment
      const nativeGoogleIdToken = String.fromEnvironment('GOOGLE_ID_TOKEN', defaultValue: '');
      if (nativeGoogleIdToken.isNotEmpty) {
        await apiClient.loginWithGoogle(nativeGoogleIdToken);
        if (mounted) {
          widget.onAuthenticated();
        }
        return;
      }

      // If native Google Play Services credentials are not configured, guide the user
      throw Exception(
        "Google Sign-In requires native platform credentials (google-services.json on Android / GoogleService-Info.plist on iOS). "
        "For simulated sandbox evaluation, please use 'DEVELOPER SANDBOX SIGN-IN'.",
      );
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString().replaceFirst("Exception: ", "");
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
                      onPressed: _isLoading ? null : _handleGoogleSignIn,
                      child: Text(
                        _isLoading ? "AUTHENTICATING..." : "CONTINUE WITH GOOGLE",
                        style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800, letterSpacing: 0.5),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    height: 44,
                    child: OutlinedButton(
                      style: OutlinedButton.styleFrom(
                        foregroundColor: TerminalColors.textMain,
                        side: const BorderSide(color: TerminalColors.borderSubtle),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                      ),
                      onPressed: _isLoading ? null : _handleDevLogin,
                      child: const Text(
                        "DEVELOPER SANDBOX SIGN-IN",
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, letterSpacing: 0.5),
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
  String _riskAppetite = "MODERATE";
  String _investmentHorizon = "3-5_YEARS";
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

      // 2. Submit risk assessment questionnaire with approved schema
      final horizonCategory = _investmentHorizon == "LESS_THAN_1_YEAR"
          ? "<1"
          : _investmentHorizon == "1-3_YEARS"
              ? "1-3"
              : _investmentHorizon == "3-5_YEARS"
                  ? "3-5"
                  : ">5";

      final qAnswers = [
        {
          "question_id": "Q1",
          "option_id": _riskAppetite == "CONSERVATIVE"
              ? "Q1_A"
              : _riskAppetite == "MODERATE"
                  ? "Q1_C"
                  : "Q1_D",
          "score": _riskAppetite == "CONSERVATIVE"
              ? 10
              : _riskAppetite == "MODERATE"
                  ? 70
                  : 100,
        },
        {
          "question_id": "Q2",
          "option_id": "Q2_C",
          "score": 75,
        },
        {
          "question_id": "Q3",
          "option_id": _riskAppetite == "CONSERVATIVE"
              ? "Q3_A"
              : _riskAppetite == "MODERATE"
                  ? "Q3_B"
                  : "Q3_C",
          "score": _riskAppetite == "CONSERVATIVE"
              ? 20
              : _riskAppetite == "MODERATE"
                  ? 60
                  : 95,
        },
        {
          "question_id": "Q4",
          "option_id": "Q4_C",
          "score": 70,
        },
      ];

      await apiClient.submitRiskAssessment(
        horizonCategory: horizonCategory,
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
        title: const Text("Investor Onboarding & Consent", style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
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

            // Step 1: Risk Assessment
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: TerminalColors.surface,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: TerminalColors.borderSubtle),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("1. RISK APPETITE QUESTIONNAIRE", style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: TerminalColors.action)),
                  const SizedBox(height: 8),
                  const Text("What is your virtual investment risk profile?", style: TextStyle(fontSize: 12, color: TerminalColors.textMuted)),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      _buildChoiceChip("CONSERVATIVE", "Conservative"),
                      const SizedBox(width: 8),
                      _buildChoiceChip("MODERATE", "Moderate"),
                      const SizedBox(width: 8),
                      _buildChoiceChip("AGGRESSIVE", "Aggressive"),
                    ],
                  ),
                  const SizedBox(height: 16),
                  const Text("Investment Horizon", style: TextStyle(fontSize: 12, color: TerminalColors.textMuted)),
                  const SizedBox(height: 8),
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
                      DropdownMenuItem(value: "LESS_THAN_1_YEAR", child: Text("< 1 Year")),
                      DropdownMenuItem(value: "1-3_YEARS", child: Text("1 to 3 Years")),
                      DropdownMenuItem(value: "3-5_YEARS", child: Text("3 to 5 Years")),
                      DropdownMenuItem(value: "5+_YEARS", child: Text("5+ Years")),
                    ],
                    onChanged: (val) {
                      if (val != null) setState(() => _investmentHorizon = val);
                    },
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Step 2: Educational Consent Agreement
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: TerminalColors.surface,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: TerminalColors.borderSubtle),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("2. SEBI SIMULATED TRADING CONSENT (v1.0)", style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: TerminalColors.action)),
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
            const SizedBox(height: 24),

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

  Widget _buildChoiceChip(String value, String label) {
    final isSelected = _riskAppetite == value;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _riskAppetite = value),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: isSelected ? TerminalColors.action : TerminalColors.panel,
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: isSelected ? TerminalColors.action : TerminalColors.borderSubtle),
          ),
          alignment: Alignment.center,
          child: Text(
            label,
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: isSelected ? Colors.black : TerminalColors.textMain,
            ),
          ),
        ),
      ),
    );
  }
}
