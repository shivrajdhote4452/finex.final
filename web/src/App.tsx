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

export const AppContent: React.FC = () => {
  const [authState, setAuthState] = useState<'checking' | 'welcome' | 'onboarding' | 'authenticated'>('checking');
  const [currentTab, setCurrentTab] = useState<NavigationTab>('overview');

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
      } catch {
        setAuthState('welcome');
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
            apiClient.setToken(null);
            setAuthState('welcome');
          }
        }}
      />
    );
  }

  if (authState === 'onboarding') {
    return <OnboardingScreen onComplete={() => setAuthState('authenticated')} />;
  }

  return (
    <AppShell currentTab={currentTab} onNavigate={(tab) => setCurrentTab(tab)}>
      {currentTab === 'overview' && <OverviewScreen onNavigate={(t) => setCurrentTab(t)} />}
      {currentTab === 'markets' && <MarketsScreen onNavigate={(t) => setCurrentTab(t)} />}
      {currentTab === 'charts' && <ChartWorkspaceScreen onNavigate={(t) => setCurrentTab(t)} />}
      {currentTab === 'portfolio' && <PortfolioScreen onNavigate={(t) => setCurrentTab(t)} />}
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
