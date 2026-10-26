import 'package:flutter/material.dart';
import 'services/api_client.dart';
import 'theme/terminal_theme.dart';
import 'theme/theme_controller.dart';
import 'screens/auth_screen.dart';
import 'screens/overview_screen.dart';
import 'screens/markets_screen.dart';
import 'screens/chart_screen.dart';
import 'screens/ask_finex_screen.dart';
import 'screens/more_screen.dart';
import 'widgets/error_boundary.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  ErrorWidget.builder = (FlutterErrorDetails details) {
    return ErrorFallbackView(
      onTryAgain: () {},
      onRefresh: () {},
      error: details.exception,
    );
  };
  await themeController.init();
  runApp(const FinExMobileApp());
}

class FinExMobileApp extends StatelessWidget {
  const FinExMobileApp({super.key});

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: themeController,
      builder: (context, _) {
        return MaterialApp(
          title: 'FinEx Terminal',
          debugShowCheckedModeBanner: false,
          theme: TerminalTheme.lightTheme,
          darkTheme: TerminalTheme.darkTheme,
          themeMode: themeController.themeMode,
          home: const AppRoot(),
        );
      },
    );
  }
}

enum AppState { auth, onboarding, terminal }

class AppRoot extends StatefulWidget {
  const AppRoot({super.key});

  @override
  State<AppRoot> createState() => _AppRootState();
}

class _AppRootState extends State<AppRoot> {
  AppState _state = AppState.auth;
  bool _isChecking = true;

  @override
  void initState() {
    super.initState();
    _checkInitialSession();
  }

  Future<void> _checkInitialSession() async {
    await apiClient.initSession();
    // If not authenticated, require login immediately
    if (!apiClient.isAuthenticated) {
      if (mounted) {
        setState(() {
          _state = AppState.auth;
          _isChecking = false;
        });
      }
      return;
    }

    try {
      final profile = await apiClient.getProfile();
      final user = profile['user'] ?? profile;
      final onboardingCompleted = user['onboarding_completed'] == true;
      final riskBand = user['risk_band'];

      if (!onboardingCompleted || riskBand == null) {
        if (mounted) setState(() => _state = AppState.onboarding);
      } else {
        if (mounted) setState(() => _state = AppState.terminal);
      }
    } catch (_) {
      // Session expired or failed - never fallback to terminal
      await apiClient.logout();
      if (mounted) setState(() => _state = AppState.auth);
    } finally {
      if (mounted) setState(() => _isChecking = false);
    }
  }

  Future<void> _onAuthenticated() async {
    try {
      final profile = await apiClient.getProfile();
      final user = profile['user'] ?? profile;
      final onboardingCompleted = user['onboarding_completed'] == true;
      final riskBand = user['risk_band'];

      if (!onboardingCompleted || riskBand == null) {
        if (mounted) setState(() => _state = AppState.onboarding);
      } else {
        if (mounted) setState(() => _state = AppState.terminal);
      }
    } catch (_) {
      // Authentication or profile failure must never open terminal as fallback
      if (mounted) setState(() => _state = AppState.auth);
    }
  }

  Future<void> _onLogout() async {
    await apiClient.logout();
    if (mounted) setState(() => _state = AppState.auth);
  }

  @override
  Widget build(BuildContext context) {
    if (_isChecking) {
      return const Scaffold(
        backgroundColor: Colors.black,
        body: Center(
          child: CircularProgressIndicator(color: TerminalColors.action),
        ),
      );
    }

    switch (_state) {
      case AppState.auth:
        return MobileAuthScreen(onAuthenticated: _onAuthenticated);
      case AppState.onboarding:
        return MobileOnboardingScreen(
          onOnboardingComplete: () => setState(() => _state = AppState.terminal),
        );
      case AppState.terminal:
        return MainMobileNavigationShell(onLogout: _onLogout);
    }
  }
}

class MainMobileNavigationShell extends StatefulWidget {
  final VoidCallback? onLogout;

  const MainMobileNavigationShell({super.key, this.onLogout});

  @override
  State<MainMobileNavigationShell> createState() => _MainMobileNavigationShellState();
}

class _MainMobileNavigationShellState extends State<MainMobileNavigationShell> {
  int _currentIndex = 0;

  @override
  Widget build(BuildContext context) {
    final screens = [
      const MobileOverviewScreen(),
      const MobileMarketsScreen(),
      const MobileChartScreen(),
      const MobileAskFinExScreen(),
      MobileMoreScreen(onLogout: widget.onLogout),
    ];
    return Scaffold(
      backgroundColor: TerminalColors.canvas,
      body: SafeArea(
        child: Column(
          children: [
            // Top Terminal Mini Ticker & Workspace Status
            Container(
              height: 34,
              decoration: const BoxDecoration(
                color: TerminalColors.canvas,
                border: Border(bottom: BorderSide(color: TerminalColors.borderSubtle)),
              ),
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Row(
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 6,
                          height: 6,
                          decoration: const BoxDecoration(
                            color: TerminalColors.action,
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Text(
                          apiClient.displayName.isNotEmpty
                              ? "${apiClient.displayName}'s workspace"
                              : "Trading workspace",
                          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: TerminalColors.textMain),
                        ),
                      ],
                    ),
                    const SizedBox(width: 14),
                    Container(height: 14, width: 1, color: TerminalColors.borderSubtle),
                    const SizedBox(width: 14),
                    _buildTopTickerPill("NIFTY 50", "25,480.30", "+0.45%", true),
                    const SizedBox(width: 12),
                    _buildTopTickerPill("SENSEX", "83,120.15", "+0.38%", true),
                    const SizedBox(width: 12),
                    _buildTopTickerPill("BANK NIFTY", "52,190.40", "-0.12%", false),
                    const SizedBox(width: 12),
                    _buildTopTickerPill("INDIA VIX", "12.85", "-2.40%", false),
                    const SizedBox(width: 12),
                    _buildTopTickerPill("RELIANCE", "₹2,984.50", "+1.25%", true),
                    const SizedBox(width: 12),
                    _buildTopTickerPill("TCS", "₹4,125.00", "+0.85%", true),
                    const SizedBox(width: 12),
                    _buildTopTickerPill("INFY", "₹1,892.40", "-0.42%", false),
                  ],
                ),
              ),
            ),
            // Active Tab View wrapped with Error Boundary (Web PR #27 Parity)
            Expanded(
              child: FinExErrorBoundary(
                screenName: ['Home', 'Markets', 'Charts', 'Ask', 'More'][_currentIndex],
                child: screens[_currentIndex],
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) => setState(() => _currentIndex = index),
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.dashboard_outlined),
            activeIcon: Icon(Icons.dashboard),
            label: 'Home',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.trending_up_outlined),
            activeIcon: Icon(Icons.trending_up),
            label: 'Markets',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.show_chart_outlined),
            activeIcon: Icon(Icons.show_chart),
            label: 'Charts',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.smart_toy_outlined),
            activeIcon: Icon(Icons.smart_toy),
            label: 'Ask',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.menu_outlined),
            activeIcon: Icon(Icons.menu),
            label: 'More',
          ),
        ],
      ),
    );
  }

  Widget _buildTopTickerPill(String symbol, String price, String change, bool isPositive) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
      decoration: BoxDecoration(
        color: const Color(0x10FFFFFF),
        borderRadius: BorderRadius.circular(3),
        border: Border.all(color: TerminalColors.borderSubtle),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            symbol,
            style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: TerminalColors.textMuted),
          ),
          const SizedBox(width: 5),
          Text(
            price,
            style: const TextStyle(fontSize: 10, fontFamily: 'monospace', fontWeight: FontWeight.w600, color: TerminalColors.textMain),
          ),
          const SizedBox(width: 4),
          Text(
            "${isPositive ? '▲ ' : '▼ '}$change",
            style: TextStyle(
              fontSize: 9,
              fontFamily: 'monospace',
              fontWeight: FontWeight.w700,
              color: isPositive ? TerminalColors.positive : TerminalColors.negative,
            ),
          ),
        ],
      ),
    );
  }
}

