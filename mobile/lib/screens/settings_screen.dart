import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../services/api_client.dart';
import '../theme/terminal_theme.dart';

class MobileSettingsScreen extends StatefulWidget {
  final VoidCallback? onLogout;

  const MobileSettingsScreen({super.key, this.onLogout});

  @override
  State<MobileSettingsScreen> createState() => _MobileSettingsScreenState();
}

class _MobileSettingsScreenState extends State<MobileSettingsScreen> {
  String _activeTab = 'profile'; // 'profile' | 'sandbox' | 'compliance'
  double _virtualCash = 50000.0;
  bool _isLoading = false;
  bool _resetSuccess = false;
  bool _notificationsEnabled = true;

  final _currencyFmt = NumberFormat.currency(symbol: '₹', locale: 'en_IN', decimalDigits: 2);

  @override
  void initState() {
    super.initState();
    _loadAccount();
  }

  Future<void> _loadAccount() async {
    try {
      final acct = await apiClient.getAccount();
      if (mounted) {
        setState(() {
          _virtualCash = (acct['cash_balance'] ?? acct['current_cash'] as num?)?.toDouble() ?? 50000.0;
        });
      }
    } catch (_) {
      // Fallback to default
    }
  }

  Future<void> _handleReset() async {
    setState(() => _isLoading = true);
    try {
      final res = await apiClient.resetAccount(confirmReset: true);
      if (mounted) {
        setState(() {
          _virtualCash = (res['cash_balance'] ?? res['current_cash'] as num?)?.toDouble() ?? 50000.0;
          _resetSuccess = true;
          _isLoading = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text("Simulated sandbox account successfully reset to ₹50,000."),
            backgroundColor: TerminalColors.positive,
            behavior: SnackBarBehavior.floating,
          ),
        );
        Future.delayed(const Duration(seconds: 3), () {
          if (mounted) setState(() => _resetSuccess = false);
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text("Account reset failed: $e"),
            backgroundColor: TerminalColors.negative,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: TerminalColors.canvas,
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              "Settings & Governance",
              style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: TerminalColors.textMain),
            ),
            Text(
              "Investor Profile · Sandbox · Compliance",
              style: TextStyle(fontSize: 10, color: TerminalColors.textMuted),
            ),
          ],
        ),
        backgroundColor: TerminalColors.canvas,
        elevation: 0,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(color: TerminalColors.borderSubtle, height: 1),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // User Card
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: TerminalColors.surface,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: TerminalColors.borderSubtle),
            ),
            child: Row(
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    color: TerminalColors.action,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  alignment: Alignment.center,
                  child: const Text(
                    "SD",
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: Colors.black),
                  ),
                ),
                const SizedBox(width: 14),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text("Shivraj Dhote", style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
                          SizedBox(width: 8),
                          _MiniBadge(label: "ADMIN", color: TerminalColors.action),
                        ],
                      ),
                      SizedBox(height: 2),
                      Text("Sole Developer & Investor · Pure Black Terminal", style: TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Sub-Tab Switcher
          Container(
            padding: const EdgeInsets.all(3),
            decoration: BoxDecoration(
              color: TerminalColors.surface,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: TerminalColors.borderSubtle),
            ),
            child: Row(
              children: [
                _buildSubTabButton("profile", "Profile"),
                _buildSubTabButton("sandbox", "Sandbox Rules"),
                _buildSubTabButton("compliance", "Compliance"),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Tab Body
          if (_activeTab == 'profile') _buildProfileSection(),
          if (_activeTab == 'sandbox') _buildSandboxSection(),
          if (_activeTab == 'compliance') _buildComplianceSection(),

          const SizedBox(height: 24),

          // Sign Out Button
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
                const Text(
                  "SESSION GOVERNANCE",
                  style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.textMuted),
                ),
                const SizedBox(height: 6),
                const Text(
                  "Terminating session revokes local secure tokens and clears encrypted cache.",
                  style: TextStyle(fontSize: 11, color: TerminalColors.textMuted),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                      foregroundColor: TerminalColors.negative,
                      side: const BorderSide(color: Color(0x40F48C7B)),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                    ),
                    icon: const Icon(Icons.logout, size: 16),
                    label: const Text("Sign Out of Session", style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                    onPressed: () {
                      if (widget.onLogout != null) {
                        widget.onLogout!();
                      } else {
                        apiClient.logout();
                        Navigator.pop(context);
                      }
                    },
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSubTabButton(String tabId, String label) {
    final isSelected = _activeTab == tabId;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _activeTab = tabId),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: isSelected ? const Color(0x33F29A60) : Colors.transparent,
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: isSelected ? TerminalColors.action : Colors.transparent),
          ),
          alignment: Alignment.center,
          child: Text(
            label,
            style: TextStyle(
              fontSize: 11,
              fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
              color: isSelected ? TerminalColors.action : TerminalColors.textMuted,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildProfileSection() {
    return Column(
      children: [
        _buildInfoCard(
          title: "INVESTOR PROFILE & RISK PARAMETERS",
          items: [
            const _InfoRow(
              label: "Display Name",
              value: "Shivraj Dhote",
              trailing: _MiniBadge(label: "Primary Admin", color: TerminalColors.positive),
            ),
            const Divider(color: TerminalColors.borderSubtle, height: 20),
            const _InfoRow(
              label: "Assessed Risk Profile",
              value: "Deterministic Score: 68/100 (Balanced Equity-Debt)",
              trailing: _MiniBadge(label: "Moderate", color: Color(0xFF60A5FA)),
            ),
            const Divider(color: TerminalColors.borderSubtle, height: 20),
            const _InfoRow(
              label: "Investment Horizon",
              value: "3 to 5 Years Capital Target",
              trailing: _MiniBadge(label: "3–5 Years", color: TerminalColors.action),
            ),
            const Divider(color: TerminalColors.borderSubtle, height: 20),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text("In-App Market Alerts", style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: TerminalColors.textMain)),
                    SizedBox(height: 2),
                    Text("Push notifications for price thresholds & drift", style: TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
                  ],
                ),
                GestureDetector(
                  onTap: () => setState(() => _notificationsEnabled = !_notificationsEnabled),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: _notificationsEnabled ? TerminalColors.positiveBg : const Color(0x22FFFFFF),
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(color: _notificationsEnabled ? TerminalColors.positive : TerminalColors.borderSubtle),
                    ),
                    child: Text(
                      _notificationsEnabled ? "Enabled ✓" : "Disabled",
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: _notificationsEnabled ? TerminalColors.positive : TerminalColors.textMuted,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildSandboxSection() {
    return Column(
      children: [
        // Current Cash Card
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0x15F29A60),
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: const Color(0x40F29A60)),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text("CURRENT VIRTUAL CASH", style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.action)),
                  SizedBox(height: 4),
                  Text("Deployable paper capital", style: TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
                ],
              ),
              Text(
                _currencyFmt.format(_virtualCash),
                style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, fontFamily: 'monospace', color: TerminalColors.action),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),

        _buildInfoCard(
          title: "SANDBOX GOVERNANCE & RESET",
          items: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text("Reset Sandbox Account", style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: TerminalColors.textMain)),
                      SizedBox(height: 2),
                      Text("Restores virtual cash to ₹50,000 and clears positions", style: TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
                    ],
                  ),
                ),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0x22F29A60),
                    foregroundColor: TerminalColors.action,
                    elevation: 0,
                    side: const BorderSide(color: TerminalColors.action),
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                  ),
                  onPressed: _isLoading ? null : _handleReset,
                  child: Text(
                    _resetSuccess ? "Reset ✓" : "Reset ₹50k",
                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700),
                  ),
                ),
              ],
            ),
            const Divider(color: TerminalColors.borderSubtle, height: 20),
            const _InfoRow(
              label: "Matching Engine Reference",
              value: "NSE Real-time observation quotes with zero-slippage paper fills",
              trailing: _MiniBadge(label: "Active (Live)", color: TerminalColors.positive),
            ),
            const Divider(color: TerminalColors.borderSubtle, height: 20),
            const _InfoRow(
              label: "Ledger Consistency",
              value: "Deterministic double-entry atomic transactions",
              trailing: _MiniBadge(label: "ACID Guaranteed", color: Color(0xFF60A5FA)),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildComplianceSection() {
    return Column(
      children: [
        _buildInfoCard(
          title: "REGULATORY CONSENT & EDUCATIONAL GROUNDING",
          items: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0x08FFFFFF),
                borderRadius: BorderRadius.circular(4),
                border: Border.all(color: TerminalColors.borderSubtle),
              ),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text("SEBI Paper Trading Risk Disclosure", style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
                      _MiniBadge(label: "Accepted v1.0", color: TerminalColors.positive),
                    ],
                  ),
                  SizedBox(height: 6),
                  Text(
                    "FinEx is an educational platform designed for learning portfolio management, risk evaluation, and asset allocation. All transactions use simulated virtual currency with zero brokerage or financial liability.",
                    style: TextStyle(fontSize: 11, height: 1.4, color: TerminalColors.textMuted),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0x08FFFFFF),
                borderRadius: BorderRadius.circular(4),
                border: Border.all(color: TerminalColors.borderSubtle),
              ),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text("AI Answer Grounding Policy", style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: TerminalColors.textMain)),
                      _MiniBadge(label: "Active Enforcement", color: Color(0xFF60A5FA)),
                    ],
                  ),
                  SizedBox(height: 6),
                  Text(
                    "FinEx AI strictly cites authentic regulatory corpus documents (SEBI Master Circular, RBI Master Directions, NSE Guidelines). Hallucinated recommendations or speculative stock tips are deterministically rejected.",
                    style: TextStyle(fontSize: 11, height: 1.4, color: TerminalColors.textMuted),
                  ),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildInfoCard({required String title, required List<Widget> items}) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: TerminalColors.surface,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: TerminalColors.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: TerminalColors.textMuted),
          ),
          const SizedBox(height: 12),
          ...items,
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  final Widget? trailing;

  const _InfoRow({required this.label, required this.value, this.trailing});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: TerminalColors.textMain)),
              const SizedBox(height: 2),
              Text(value, style: const TextStyle(fontSize: 11, color: TerminalColors.textMuted)),
            ],
          ),
        ),
        if (trailing != null) ...[
          const SizedBox(width: 8),
          trailing!,
        ],
      ],
    );
  }
}

class _MiniBadge extends StatelessWidget {
  final String label;
  final Color color;

  const _MiniBadge({required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(3),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(
        label,
        style: TextStyle(fontSize: 9, fontWeight: FontWeight.w700, fontFamily: 'monospace', color: color),
      ),
    );
  }
}
