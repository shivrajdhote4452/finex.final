import React, { useState } from 'react';
import { useFinancial } from '../../context/FinancialContext';
import { QuickTradeModal } from '../trading/QuickTradeModal';

export type NavigationTab =
  | 'overview'
  | 'markets'
  | 'charts'
  | 'portfolio'
  | 'transactions'
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
  const {
    virtualCash,
    totalHoldingsValue,

    totalPortfolioValue,
    notifications,
    totalTradesCount,
    openQuickTrade,
  } = useFinancial();

  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchFocused, setIsSearchFocused] = useState(false);

  const unreadAlerts = notifications.filter((n) => !n.read).length;

  const navItems: { id: NavigationTab; label: string; badge?: string | number }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'markets', label: 'Markets' },
    { id: 'charts', label: 'Charts' },
    { id: 'portfolio', label: 'Portfolio' },
    { id: 'ask-finex', label: 'Ask FinEx' },
    { id: 'practice', label: 'Paper trading' },
    { id: 'transactions', label: 'Order activity', badge: totalTradesCount },
    { id: 'alerts', label: 'Alerts', badge: unreadAlerts > 0 ? unreadAlerts : undefined },
    { id: 'goals', label: 'Goals' },
    { id: 'spending', label: 'Spending' },
  ];

  return (
    <div style={{ height: '100vh', width: '100vw', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-app)', overflow: 'hidden' }}>
      {/* 2. Main Two-Column Terminal Container (Sidebar + Central Workspace) */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0, height: '100%', overflow: 'hidden' }}>
        {/* Left Navigation Rail (Per Graphite Terminal Full Frontend Guide) */}
        <aside
          style={{
            width: '240px',
            backgroundColor: 'var(--bg-sidebar)',
            borderRight: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            padding: '24px 16px',
            flexShrink: 0,
            height: '100%',
            overflowY: 'auto',
          }}
        >
          {/* Rail Header / Brand */}
          <div>
            <div
              onClick={() => onNavigate('overview')}
              style={{
                cursor: 'pointer',
                marginBottom: '28px',
                paddingLeft: '8px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '3px' }}>
                <span style={{ fontSize: '24px', fontWeight: 900, color: '#FFFFFF', letterSpacing: '-0.03em' }}>Fin</span>
                <span style={{ fontSize: '24px', fontWeight: 900, color: 'var(--color-action)', letterSpacing: '-0.03em' }}>Ex</span>
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 500, letterSpacing: '0.04em', marginTop: '2px' }}>
                Learn &nbsp;·&nbsp; Practice &nbsp;·&nbsp; Plan
              </div>
            </div>

            {/* Navigation Menu Links */}
            <nav style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              {navItems.map((item) => {
                const isActive = currentTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onNavigate(item.id)}
                    style={{
                      background: isActive ? '#141414' : 'transparent',
                      border: 'none',
                      borderLeft: isActive ? '2px solid var(--color-action)' : '2px solid transparent',
                      borderRadius: 'var(--radius-xs)',
                      color: isActive ? '#FFFFFF' : 'var(--text-muted)',
                      fontFamily: 'var(--font-sans)',
                      fontSize: '13px',
                      fontWeight: isActive ? 600 : 500,
                      cursor: 'pointer',
                      padding: '8px 12px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      textAlign: 'left',
                      transition: 'all var(--transition-fast)',
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.color = '#FFFFFF';
                        e.currentTarget.style.backgroundColor = '#101010';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.color = 'var(--text-muted)';
                        e.currentTarget.style.backgroundColor = 'transparent';
                      }
                    }}
                  >
                    <span>{item.label}</span>
                    {item.badge !== undefined && (
                      <span
                        style={{
                          backgroundColor: item.id === 'alerts' ? 'var(--color-loss)' : '#242424',
                          color: '#FFFFFF',
                          fontSize: '10px',
                          fontWeight: 700,
                          borderRadius: '10px',
                          padding: '1px 6px',
                          fontFamily: 'var(--font-mono)',
                        }}
                      >
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Bottom Rail Disclaimer & Settings Link */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', paddingTop: '16px', borderTop: '1px solid var(--border-subtle)' }}>
            {/* Legal Educational Badge */}
            <div
              style={{
                backgroundColor: '#101010',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-xs)',
                padding: '10px 12px',
                fontSize: '11px',
                lineHeight: 1.4,
                color: 'var(--text-muted)',
              }}
            >
              <div style={{ color: 'var(--color-action)', fontWeight: 600, marginBottom: '2px' }}>
                Virtual trading.
              </div>
              <div>Educational use only. No real-money orders.</div>
            </div>

            {/* Settings Link */}
            <button
              onClick={() => onNavigate('settings')}
              style={{
                background: currentTab === 'settings' ? '#141414' : 'transparent',
                border: 'none',
                borderLeft: currentTab === 'settings' ? '2px solid var(--color-action)' : '2px solid transparent',
                borderRadius: 'var(--radius-xs)',
                color: currentTab === 'settings' ? '#FFFFFF' : 'var(--text-muted)',
                fontSize: '13px',
                fontWeight: 500,
                cursor: 'pointer',
                padding: '8px 12px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                textAlign: 'left',
              }}
            >
              <span>⚙</span>
              <span>Settings</span>
            </button>
          </div>
        </aside>

        {/* Central Workspace + Top Workspace Bar */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, minHeight: 0, height: '100%', overflow: 'hidden', backgroundColor: 'var(--bg-app)' }}>
          {/* Top Workspace Header Bar */}
          <header
            style={{
              height: '56px',
              borderBottom: '1px solid var(--border-subtle)',
              backgroundColor: 'var(--bg-app)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '0 28px',
              flexShrink: 0,
              zIndex: 40,
            }}
          >
            {/* Left: Workspace Identifier */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div className="pulse-dot" style={{ backgroundColor: 'var(--color-action)', boxShadow: '0 0 6px var(--color-action)' }} />
              <span style={{ fontSize: '13px', fontWeight: 600, color: '#FFFFFF', letterSpacing: '-0.01em' }}>
                Shivraj’s workspace
              </span>
            </div>

            {/* Center: Global Search Bar (with Ctrl K) */}
            <div style={{ position: 'relative', width: '380px' }}>
              <input
                type="text"
                placeholder="Search for an instrument, topic or command…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => setIsSearchFocused(true)}
                onBlur={() => setIsSearchFocused(false)}
                style={{
                  width: '100%',
                  backgroundColor: 'var(--bg-input)',
                  border: isSearchFocused ? '1px solid var(--color-action)' : '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-xs)',
                  padding: '7px 64px 7px 12px',
                  color: '#FFFFFF',
                  fontSize: '12px',
                  fontFamily: 'var(--font-sans)',
                  outline: 'none',
                  transition: 'border-color var(--transition-fast)',
                }}
              />
              <span
                style={{
                  position: 'absolute',
                  right: '8px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  backgroundColor: '#1C1C1C',
                  border: '1px solid #2C2C2C',
                  borderRadius: '3px',
                  padding: '1px 5px',
                  fontSize: '10px',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-muted)',
                }}
              >
                Ctrl K
              </span>
            </div>

            {/* Right: Currency, Account Stats Ribbon, and Profile Avatar */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
              {/* Account Quick Metrics Summary (From PDF Page 3 & Page 1) */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '14px',
                  fontSize: '11px',
                  fontFamily: 'var(--font-mono)',
                  borderRight: '1px solid var(--border-subtle)',
                  paddingRight: '18px',
                }}
              >
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Virtual account: </span>
                  <span style={{ color: 'var(--color-action)', fontWeight: 600 }}>Illustrative</span>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Holdings: </span>
                  <span style={{ color: '#FFFFFF', fontWeight: 600 }}>₹{(totalHoldingsValue ?? 0).toLocaleString('en-IN')}</span>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Virtual cash: </span>
                  <span style={{ color: '#FFFFFF', fontWeight: 600 }}>₹{(virtualCash ?? 0).toLocaleString('en-IN')}</span>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Total: </span>
                  <span style={{ color: 'var(--color-positive)', fontWeight: 700 }}>₹{(totalPortfolioValue ?? 0).toLocaleString('en-IN')}</span>
                </div>
              </div>

              {/* Currency Tag */}
              <span
                style={{
                  fontSize: '11px',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-muted)',
                  border: '1px solid var(--border-subtle)',
                  padding: '3px 6px',
                  borderRadius: 'var(--radius-xs)',
                }}
              >
                INR
              </span>

              {/* Quick Trade Button */}
              <button
                onClick={() => openQuickTrade()}
                className="btn btn-action"
                style={{
                  padding: '5px 12px',
                  fontSize: '12px',
                  borderRadius: 'var(--radius-xs)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                }}
              >
                <span>+</span>
                <span>Trade</span>
              </button>

              {/* Profile Avatar */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '7px',
                  cursor: 'pointer',
                  padding: '3px 6px',
                  borderRadius: 'var(--radius-xs)',
                  backgroundColor: '#121212',
                  border: '1px solid var(--border-subtle)',
                }}
                onClick={() => onNavigate('settings')}
              >
                <div
                  style={{
                    width: '20px',
                    height: '20px',
                    borderRadius: 'var(--radius-xs)',
                    backgroundColor: 'var(--color-action)',
                    color: '#000000',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 800,
                    fontSize: '11px',
                  }}
                >
                  S
                </div>
                <span style={{ fontSize: '12px', fontWeight: 600, color: '#FFFFFF' }}>Shivraj</span>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>↓</span>
              </div>
            </div>
          </header>

          {/* Main Content Pane */}
          <main
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              minHeight: 0,
              minWidth: 0,
              padding: currentTab === 'charts' || currentTab === 'ask-finex' ? 0 : '24px 28px',
              overflowY: currentTab === 'charts' || currentTab === 'ask-finex' ? 'hidden' : 'auto',
            }}
          >
            {children}
          </main>
        </div>
      </div>

      {/* Global Quick Trade Modal Drawer */}
      <QuickTradeModal />
    </div>
  );
};
