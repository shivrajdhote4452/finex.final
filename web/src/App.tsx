import React, { useState, useEffect } from 'react';
import { ThemeProvider } from './context/ThemeContext';
import { FinancialProvider } from './context/FinancialContext';
import { ToastProvider } from './context/ToastContext';
import { AppShell, NavigationTab } from './components/layout/AppShell';
import { ErrorBoundary } from './components/common/ErrorBoundary';
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
import { PrivacyPolicyScreen } from './pages/PrivacyPolicyScreen';
import { TermsOfServiceScreen } from './pages/TermsOfServiceScreen';
import { apiClient } from './api/client';

const VALID_TABS: NavigationTab[] = [
  'overview',
  'markets',
  'indices',
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

type PublicPage = 'privacy' | 'terms' | null;

const detectPublicPage = (): PublicPage => {
  if (typeof window === 'undefined') return null;
  const path = window.location.pathname.toLowerCase().replace(/\/$/, '');
  const hash = window.location.hash.toLowerCase().replace('#', '').trim();
  if (
    path === '/privacy' ||
    path === '/privacy-policy' ||
    path === '/privacy.html' ||
    hash === 'privacy' ||
    hash === '/privacy'
  ) {
    return 'privacy';
  }
  if (
    path === '/terms' ||
    path === '/terms-of-service' ||
    path === '/terms.html' ||
    hash === 'terms' ||
    hash === '/terms'
  ) {
    return 'terms';
  }
  return null;
};

export const AppContent: React.FC = () => {
  const [authState, setAuthState] = useState<'checking' | 'welcome' | 'onboarding' | 'authenticated'>('checking');
  const [currentTab, setCurrentTab] = useState<NavigationTab>(getSavedTab);
  const [publicPage, setPublicPage] = useState<PublicPage>(detectPublicPage);

  const openPrivacy = () => {
    window.history.pushState(null, '', '/privacy');
    setPublicPage('privacy');
  };

  const openTerms = () => {
    window.history.pushState(null, '', '/terms');
    setPublicPage('terms');
  };

  const closePublicPage = () => {
    const currentPath = window.location.pathname.toLowerCase().replace(/\/$/, '');
    if (
      currentPath === '/privacy' ||
      currentPath === '/terms' ||
      currentPath === '/privacy-policy' ||
      currentPath === '/terms-of-service' ||
      currentPath === '/privacy.html' ||
      currentPath === '/terms.html'
    ) {
      window.history.pushState(null, '', '/');
    }
    const currentHash = window.location.hash.toLowerCase().replace('#', '').trim();
    if (currentHash === 'privacy' || currentHash === 'terms' || currentHash === '/privacy' || currentHash === '/terms') {
      window.location.hash = '';
    }
    setPublicPage(null);
  };

  // Listen to browser navigation (back/forward) and hash changes for public pages
  useEffect(() => {
    const handleLocationChange = () => {
      setPublicPage(detectPublicPage());
    };

    window.addEventListener('popstate', handleLocationChange);
    window.addEventListener('hashchange', handleLocationChange);
    return () => {
      window.removeEventListener('popstate', handleLocationChange);
      window.removeEventListener('hashchange', handleLocationChange);
    };
  }, []);

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
    let isMounted = true;
    const checkSession = async () => {
      const token = apiClient.getToken();
      if (!token || apiClient.isTokenExpired(token)) {
        if (typeof window !== 'undefined') {
          const hash = window.location.hash.toLowerCase();
          if (hash.includes('onboarding') || hash.includes('step=')) {
            if (isMounted) setAuthState('onboarding');
            return;
          }
        }
        if (isMounted) setAuthState('welcome');
        return;
      }

      try {
        const user = await apiClient.auth.getMe();
        if (!isMounted) return;
        if (user && user.onboarding_completed) {
          setAuthState('authenticated');
        } else {
          setAuthState('onboarding');
        }
      } catch (err: any) {
        if (!isMounted) return;
        // If 401 Unauthorized, session has been revoked or invalidated by server
        if (err?.status === 401) {
          apiClient.setToken(null);
          setAuthState('welcome');
          return;
        }

        // If backend is sleeping/temporarily unreachable (network or cold start), preserve session
        if (apiClient.isAuthenticated()) {
          setAuthState('authenticated');
        } else {
          setAuthState('welcome');
        }
      }
    };

    checkSession();
    return () => {
      isMounted = false;
    };
  }, []);

  // Priority: If viewing a public legal page, render immediately without requiring auth
  if (publicPage === 'privacy') {
    return <PrivacyPolicyScreen onBack={closePublicPage} />;
  }
  if (publicPage === 'terms') {
    return <TermsOfServiceScreen onBack={closePublicPage} />;
  }

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
        onOpenPrivacy={openPrivacy}
        onOpenTerms={openTerms}
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
      <ErrorBoundary>
        {currentTab === 'overview' && <OverviewScreen onNavigate={handleNavigate} />}
        {currentTab === 'markets' && <MarketsScreen onNavigate={handleNavigate} initialView="equities" />}
        {currentTab === 'indices' && <MarketsScreen onNavigate={handleNavigate} initialView="indices" />}
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
      </ErrorBoundary>
    </AppShell>
  );
};

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <FinancialProvider>
        <ToastProvider>
          <AppContent />
        </ToastProvider>
      </FinancialProvider>
    </ThemeProvider>
  );
};

export default App;
