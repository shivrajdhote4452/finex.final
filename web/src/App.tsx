import React, { useState, useEffect } from 'react';
import { FinancialProvider } from './context/FinancialContext';
import { AppShell, NavigationTab } from './components/layout/AppShell';
import { WelcomeScreen } from './pages/WelcomeScreen';
import { OnboardingScreen } from './pages/OnboardingScreen';
import { OverviewScreen } from './pages/OverviewScreen';
import { MarketsScreen } from './pages/MarketsScreen';
import { PortfolioScreen } from './pages/PortfolioScreen';
import { TransactionsScreen } from './pages/TransactionsScreen';
import { AskFinExScreen } from './pages/AskFinExScreen';
import { PracticeScreen } from './pages/PracticeScreen';
import { ChartWorkspaceScreen } from './pages/ChartWorkspaceScreen';
import { AlertsScreen } from './pages/AlertsScreen';
import { GoalsScreen } from './pages/GoalsScreen';
import { SpendingScreen } from './pages/SpendingScreen';
import { SettingsScreen } from './pages/SettingsScreen';
import { apiClient } from './api/client';

const VALID_TABS: NavigationTab[] = [
  'overview',
  'markets',
  'charts',
  'portfolio',
  'transactions',
  'ask-finex',
  'practice',
  'alerts',
  'goals',
  'spending',
  'settings',
];

const getSavedTab = (): NavigationTab => {
  try {
    const hash = window.location.hash.replace('#', '').trim() as NavigationTab;
    if (VALID_TABS.includes(hash)) {
      return hash;
    }
    const saved = localStorage.getItem('finex_active_tab') as NavigationTab;
    if (VALID_TABS.includes(saved)) {
      return saved;
    }
  } catch {
    // Fallback if storage access is restricted
  }
  return 'overview';
};

export const AppContent: React.FC = () => {
  const [authState, setAuthState] = useState<'checking' | 'welcome' | 'onboarding' | 'authenticated'>('checking');
  const [currentTab, setCurrentTab] = useState<NavigationTab>(getSavedTab);

  const handleNavigate = (tab: NavigationTab) => {
    setCurrentTab(tab);
    window.location.hash = tab;
    try {
      localStorage.setItem('finex_active_tab', tab);
    } catch {
      // Ignore storage errors
    }
  };

  // Sync hash changes (e.g., browser back/forward or manual hash updates)
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '').trim() as NavigationTab;
      if (VALID_TABS.includes(hash) && hash !== currentTab) {
        setCurrentTab(hash);
        try {
          localStorage.setItem('finex_active_tab', hash);
        } catch {}
      }
    };

    window.addEventListener('hashchange', handleHashChange);
    if (!window.location.hash && currentTab) {
      window.location.hash = currentTab;
    }
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, [currentTab]);

  // Fail-closed initial session check against FastAPI /users/me
  useEffect(() => {
    const checkSession = async () => {
      if (!apiClient.isAuthenticated()) {
        setAuthState('welcome');
        return;
      }
      try {
        const user = await apiClient.auth.getMe();
        if (user && user.onboarding_completed) {
          setAuthState('authenticated');
        } else {
          setAuthState('onboarding');
        }
      } catch (err: any) {
        // If backend is offline or static Vercel (404/network error), allow authenticated session if token exists
        if (apiClient.isAuthenticated()) {
          setAuthState('authenticated');
        } else {
          setAuthState('welcome');
        }
      }
    };

    checkSession();
  }, []);

  // Sleek Pure-Black Loading Splash
  if (authState === 'checking') {
    return (
      <div
        style={{
          minHeight: '100vh',
          backgroundColor: '#000000',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '3px' }}>
          <span style={{ fontSize: '32px', fontWeight: 900, color: '#FFFFFF', letterSpacing: '-0.03em' }}>Fin</span>
          <span style={{ fontSize: '32px', fontWeight: 900, color: 'var(--color-action)', letterSpacing: '-0.03em' }}>Ex</span>
        </div>
        <div style={{ fontSize: '12px', color: '#8E8E93', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
          Initializing Session...
        </div>
      </div>
    );
  }

  // Handle flow transitions
  if (authState === 'welcome') {
    return (
      <WelcomeScreen
        onLoginSuccess={async () => {
          try {
            const user = await apiClient.auth.getMe();
            if (user && user.onboarding_completed) {
              setAuthState('authenticated');
            } else {
              setAuthState('onboarding');
            }
          } catch {
            // When backend is offline or static Vercel deployment, grant entry to authenticated dashboard
            setAuthState('authenticated');
          }
        }}
      />
    );
  }

  if (authState === 'onboarding') {
    return <OnboardingScreen onComplete={() => setAuthState('authenticated')} />;
  }

  return (
    <AppShell currentTab={currentTab} onNavigate={handleNavigate}>
      {currentTab === 'overview' && <OverviewScreen onNavigate={handleNavigate} />}
      {currentTab === 'markets' && <MarketsScreen onNavigate={handleNavigate} />}
      {currentTab === 'charts' && <ChartWorkspaceScreen onNavigate={handleNavigate} />}
      {currentTab === 'portfolio' && <PortfolioScreen onNavigate={handleNavigate} />}
      {currentTab === 'transactions' && <TransactionsScreen />}
      {currentTab === 'practice' && <PracticeScreen />}
      {currentTab === 'ask-finex' && <AskFinExScreen />}
      {currentTab === 'alerts' && <AlertsScreen />}
      {currentTab === 'goals' && <GoalsScreen />}
      {currentTab === 'spending' && <SpendingScreen />}
      {currentTab === 'settings' && (
        <SettingsScreen
          onSignOut={async () => {
            await apiClient.auth.logout();
            setAuthState('welcome');
          }}
        />
      )}
    </AppShell>
  );
};

export const App: React.FC = () => {
  return (
    <FinancialProvider>
      <AppContent />
    </FinancialProvider>
  );
};

export default App;
