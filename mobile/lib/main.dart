import 'package:flutter/material.dart';
import 'services/api_client.dart';
import 'theme/terminal_theme.dart';
import 'screens/auth_screen.dart';
import 'screens/overview_screen.dart';
import 'screens/markets_screen.dart';
import 'screens/ask_finex_screen.dart';
import 'screens/more_screen.dart';

void main() {
  runApp(const FinExMobileApp());
}

class FinExMobileApp extends StatelessWidget {
  const FinExMobileApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FinEx Terminal',
      debugShowCheckedModeBanner: false,
      theme: TerminalTheme.darkTheme,
      home: const AppRoot(),
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
              height: 32,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              decoration: const BoxDecoration(
                color: TerminalColors.canvas,
                border: Border(bottom: BorderSide(color: TerminalColors.borderSubtle)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
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
                      const Text(
                        "Shivraj's workspace",
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: TerminalColors.textMain),
                      ),
                    ],
                  ),
                  const Row(
                    children: [
                      Text("NIFTY 25,480", style: TextStyle(fontSize: 10, fontFamily: 'monospace', color: TerminalColors.textMuted)),
                      SizedBox(width: 4),
                      Text("+0.45%", style: TextStyle(fontSize: 10, fontFamily: 'monospace', color: TerminalColors.positive, fontWeight: FontWeight.w700)),
                    ],
                  ),
                ],
              ),
            ),
            // Active Tab View
            Expanded(child: screens[_currentIndex]),
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
}
