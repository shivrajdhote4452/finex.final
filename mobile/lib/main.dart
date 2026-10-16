import 'package:flutter/material.dart';
import 'theme/terminal_theme.dart';
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
      home: const MainMobileNavigationShell(),
    );
  }
}

class MainMobileNavigationShell extends StatefulWidget {
  const MainMobileNavigationShell({super.key});

  @override
  State<MainMobileNavigationShell> createState() => _MainMobileNavigationShellState();
}

class _MainMobileNavigationShellState extends State<MainMobileNavigationShell> {
  int _currentIndex = 0;

  final List<Widget> _screens = const [
    MobileOverviewScreen(),
    MobileMarketsScreen(),
    MobileAskFinExScreen(),
    MobileMoreScreen(),
  ];

  @override
  Widget build(BuildContext context) {
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
            Expanded(child: _screens[_currentIndex]),
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
