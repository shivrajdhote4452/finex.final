import React, { useState } from 'react';
import { AppShell, NavigationTab } from './components/layout/AppShell';
import { WelcomeScreen } from './pages/WelcomeScreen';
import { OnboardingScreen } from './pages/OnboardingScreen';
import { OverviewScreen } from './pages/OverviewScreen';
import { MarketsScreen } from './pages/MarketsScreen';
import { PortfolioScreen } from './pages/PortfolioScreen';
import { AskFinExScreen } from './pages/AskFinExScreen';
import { PracticeScreen } from './pages/PracticeScreen';
import { AlertsScreen } from './pages/AlertsScreen';
import { GoalsScreen } from './pages/GoalsScreen';
import { SpendingScreen } from './pages/SpendingScreen';
import { SettingsScreen } from './pages/SettingsScreen';

export const App: React.FC = () => {
  const [authState, setAuthState] = useState<'welcome' | 'onboarding' | 'authenticated'>('authenticated');
  const [currentTab, setCurrentTab] = useState<NavigationTab>('overview');

  // Handle flow transitions
  if (authState === 'welcome') {
    return <WelcomeScreen onLoginSuccess={() => setAuthState('onboarding')} />;
  }

  if (authState === 'onboarding') {
    return <OnboardingScreen onComplete={() => setAuthState('authenticated')} />;
  }

  return (
    <AppShell currentTab={currentTab} onNavigate={(tab) => setCurrentTab(tab)}>
      {currentTab === 'overview' && <OverviewScreen onNavigate={(t) => setCurrentTab(t)} />}
      {currentTab === 'markets' && <MarketsScreen onNavigate={(t) => setCurrentTab(t)} />}
      {currentTab === 'portfolio' && <PortfolioScreen onNavigate={(t) => setCurrentTab(t)} />}
      {currentTab === 'ask-finex' && <AskFinExScreen />}
      {currentTab === 'practice' && <PracticeScreen />}
      {currentTab === 'alerts' && <AlertsScreen />}
      {currentTab === 'goals' && <GoalsScreen />}
      {currentTab === 'spending' && <SpendingScreen />}
      {currentTab === 'settings' && <SettingsScreen onSignOut={() => setAuthState('welcome')} />}
    </AppShell>
  );
};

export default App;
