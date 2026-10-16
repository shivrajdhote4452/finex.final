import React from 'react';

export type NavigationTab =
  | 'overview'
  | 'markets'
  | 'portfolio'
  | 'ask-finex'
  | 'practice'
  | 'alerts'
  | 'goals'
  | 'spending'
  | 'settings';

interface AppShellProps {
  currentTab: NavigationTab;
  onNavigate: (tab: NavigationTab) => void;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({ currentTab, onNavigate, children }) => {
  const navItems: { id: NavigationTab; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'markets', label: 'Markets' },
    { id: 'portfolio', label: 'Portfolio' },
    { id: 'ask-finex', label: 'Ask FinEx' },
    { id: 'practice', label: 'Practice' },
    { id: 'alerts', label: 'Alerts' },
    { id: 'goals', label: 'Goals' },
    { id: 'spending', label: 'Spending' },
  ];

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--color-paper)' }}>
      {/* Top Editorial Navigation */}
      <header
        style={{
          borderBottom: '1px solid var(--color-border)',
          backgroundColor: 'var(--color-paper)',
          position: 'sticky',
          top: 0,
          zIndex: 40,
        }}
      >
        <div
          style={{
            maxWidth: '1360px',
            margin: '0 auto',
            padding: '0 32px',
            height: '64px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          {/* Logo & Navigation Tabs */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '48px' }}>
            <span
              onClick={() => onNavigate('overview')}
              style={{
                fontFamily: 'var(--font-serif)',
                fontSize: '26px',
                fontWeight: 600,
                color: 'var(--color-ink)',
                cursor: 'pointer',
                letterSpacing: '-0.02em',
              }}
            >
              finex.
            </span>

            <nav style={{ display: 'flex', gap: '28px', height: '64px' }}>
              {navItems.map((item) => {
                const isActive = currentTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onNavigate(item.id)}
                    style={{
                      background: 'none',
                      border: 'none',
                      borderBottom: isActive ? '2px solid var(--color-cobalt)' : '2px solid transparent',
                      color: isActive ? 'var(--color-ink)' : 'var(--color-ink-muted)',
                      fontFamily: 'var(--font-sans)',
                      fontSize: '14px',
                      fontWeight: isActive ? 600 : 400,
                      cursor: 'pointer',
                      padding: '0 4px',
                      height: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      transition: 'color var(--transition-fast)',
                    }}
                  >
                    {item.label}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Right Workspace Context & User Avatar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <span style={{ fontSize: '13px', color: 'var(--color-ink-faint)' }}>
              Demo workspace
            </span>
            <button
              onClick={() => onNavigate('settings')}
              title="Shivraj Dhote (Profile & Settings)"
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                backgroundColor: 'var(--color-ink)',
                color: '#FFFFFF',
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                fontFamily: 'var(--font-sans)',
              }}
            >
              SD
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Viewport */}
      <main style={{ flex: 1, maxWidth: '1360px', width: '100%', margin: '0 auto', padding: '40px 32px' }}>
        {children}
      </main>

      {/* Subtle Editorial Footer Note */}
      <footer
        style={{
          borderTop: '1px solid var(--color-border-subtle)',
          padding: '20px 32px',
          maxWidth: '1360px',
          width: '100%',
          margin: '0 auto',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '12px',
          color: 'var(--color-ink-faint)',
        }}
      >
        <span>FinEx Editorial Edition • Genuine Market Observations & Educational Document Research</span>
        <span>Shivraj Dhote (Sole Developer)</span>
      </footer>
    </div>
  );
};
