import React from 'react';
import { useFinancial } from '../../context/FinancialContext';
import { QuickTradeModal } from '../trading/QuickTradeModal';

export type NavigationTab =
  | 'overview'
  | 'markets'
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
  const { virtualCash, notifications, totalTradesCount, marketQuotes, openQuickTrade } = useFinancial();
  const unreadAlerts = notifications.filter((n) => !n.read).length;

  const navItems: { id: NavigationTab; label: string; badge?: string | number; isHot?: boolean }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'markets', label: 'Markets' },
    { id: 'portfolio', label: 'Portfolio' },
    { id: 'transactions', label: 'Transactions', badge: totalTradesCount },
    { id: 'practice', label: 'Trade Desk', isHot: true },
    { id: 'ask-finex', label: 'Ask FinEx AI' },
    { id: 'alerts', label: 'Alerts', badge: unreadAlerts > 0 ? unreadAlerts : undefined },
    { id: 'goals', label: 'Goals' },
    { id: 'spending', label: 'Spending' },
  ];

  // Ticker items
  const tickerStocks = Object.values(marketQuotes);

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-app)' }}>
      {/* Live Market Ticker Tape Marquee */}
      <div className="ticker-tape-container">
        <div className="ticker-tape-track">
          {/* Broad Market Indices */}
          <div className="ticker-pill">
            <span style={{ color: '#9CA3AF', fontWeight: 600 }}>NIFTY 50</span>
            <span style={{ color: '#FFFFFF' }}>25,480.30</span>
            <span style={{ color: 'var(--color-profit)' }}>▲ +0.45%</span>
          </div>
          <div className="ticker-pill">
            <span style={{ color: '#9CA3AF', fontWeight: 600 }}>SENSEX</span>
            <span style={{ color: '#FFFFFF' }}>83,120.15</span>
            <span style={{ color: 'var(--color-profit)' }}>▲ +0.38%</span>
          </div>
          <div className="ticker-pill">
            <span style={{ color: '#9CA3AF', fontWeight: 600 }}>BANK NIFTY</span>
            <span style={{ color: '#FFFFFF' }}>52,190.40</span>
            <span style={{ color: 'var(--color-loss)' }}>▼ -0.12%</span>
          </div>
          <div className="ticker-pill">
            <span style={{ color: '#9CA3AF', fontWeight: 600 }}>INDIA VIX</span>
            <span style={{ color: '#FFFFFF' }}>12.85</span>
            <span style={{ color: 'var(--color-loss)' }}>▼ -2.40%</span>
          </div>

          {/* Dynamic Stock Quotes from Context */}
          {tickerStocks.map((s) => (
            <div
              key={s.symbol}
              className={`ticker-pill ${s.lastTick === 'up' ? 'flash-green' : s.lastTick === 'down' ? 'flash-red' : ''}`}
              onClick={() => openQuickTrade(s.symbol)}
              title={`Click to trade ${s.symbol}`}
            >
              <span style={{ color: '#FFFFFF', fontWeight: 700 }}>{s.symbol}</span>
              <span style={{ color: '#E5E7EB' }}>₹{s.price.toLocaleString('en-IN')}</span>
              <span style={{ color: s.isPositive ? 'var(--color-profit)' : 'var(--color-loss)' }}>
                {s.isPositive ? '▲' : '▼'} {s.isPositive ? '+' : ''}{s.changePct}%
              </span>
            </div>
          ))}

          {/* Repeat for continuous marquee illusion */}
          <div className="ticker-pill">
            <span style={{ color: '#9CA3AF', fontWeight: 600 }}>NIFTY 50</span>
            <span style={{ color: '#FFFFFF' }}>25,480.30</span>
            <span style={{ color: 'var(--color-profit)' }}>▲ +0.45%</span>
          </div>
          <div className="ticker-pill">
            <span style={{ color: '#9CA3AF', fontWeight: 600 }}>SENSEX</span>
            <span style={{ color: '#FFFFFF' }}>83,120.15</span>
            <span style={{ color: 'var(--color-profit)' }}>▲ +0.38%</span>
          </div>
          {tickerStocks.map((s) => (
            <div
              key={`${s.symbol}-repeat`}
              className="ticker-pill"
              onClick={() => openQuickTrade(s.symbol)}
              title={`Click to trade ${s.symbol}`}
            >
              <span style={{ color: '#FFFFFF', fontWeight: 700 }}>{s.symbol}</span>
              <span style={{ color: '#E5E7EB' }}>₹{s.price.toLocaleString('en-IN')}</span>
              <span style={{ color: s.isPositive ? 'var(--color-profit)' : 'var(--color-loss)' }}>
                {s.isPositive ? '▲' : '▼'} {s.isPositive ? '+' : ''}{s.changePct}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Top Glassmorphic Navigation Header */}
      <header
        style={{
          borderBottom: '1px solid var(--border-subtle)',
          backgroundColor: 'rgba(11, 15, 25, 0.88)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          position: 'sticky',
          top: 0,
          zIndex: 50,
        }}
      >
        <div
          style={{
            maxWidth: '1440px',
            margin: '0 auto',
            padding: '0 32px',
            height: '66px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          {/* Brand & Tabs */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '36px' }}>
            {/* Logo */}
            <div
              onClick={() => onNavigate('overview')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                cursor: 'pointer',
              }}
            >
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: 'var(--radius-sm)',
                  background: 'linear-gradient(135deg, #3B82F6 0%, #06B6D4 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 800,
                  fontSize: '17px',
                  color: '#FFFFFF',
                  boxShadow: '0 0 16px rgba(59, 130, 246, 0.4)',
                }}
              >
                F
              </div>
              <span
                style={{
                  fontFamily: 'var(--font-sans)',
                  fontSize: '22px',
                  fontWeight: 700,
                  letterSpacing: '-0.03em',
                  color: '#FFFFFF',
                }}
              >
                finex<span style={{ color: 'var(--color-primary)' }}>.</span>
              </span>
            </div>

            {/* Navigation Tabs */}
            <nav style={{ display: 'flex', gap: '4px', height: '66px', alignItems: 'center' }}>
              {navItems.map((item) => {
                const isActive = currentTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onNavigate(item.id)}
                    style={{
                      background: isActive ? 'rgba(59, 130, 246, 0.12)' : 'transparent',
                      border: 'none',
                      borderRadius: 'var(--radius-sm)',
                      color: isActive ? '#FFFFFF' : 'var(--text-muted)',
                      fontFamily: 'var(--font-sans)',
                      fontSize: '13px',
                      fontWeight: isActive ? 600 : 500,
                      cursor: 'pointer',
                      padding: '8px 12px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      transition: 'all var(--transition-fast)',
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) e.currentTarget.style.color = '#FFFFFF';
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) e.currentTarget.style.color = 'var(--text-muted)';
                    }}
                  >
                    <span>{item.label}</span>
                    {item.badge !== undefined && (
                      <span
                        style={{
                          backgroundColor: item.id === 'alerts' ? 'var(--color-loss)' : 'rgba(59, 130, 246, 0.25)',
                          color: '#FFFFFF',
                          fontSize: '10px',
                          fontWeight: 700,
                          borderRadius: '10px',
                          padding: '1px 6px',
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

          {/* Right Header Status, Quick Trade, Cash Pill, and Avatar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            {/* Live Indicator */}
            <div
              className="glass-card"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '6px 12px',
                borderRadius: 'var(--radius-full)',
                fontSize: '11px',
                color: 'var(--text-muted)',
              }}
            >
              <div className="pulse-dot" />
              <span>NSE Live Paper Route</span>
            </div>

            {/* Quick Trade Button */}
            <button
              onClick={() => openQuickTrade()}
              className="btn-emerald"
              style={{
                padding: '7px 14px',
                borderRadius: 'var(--radius-full)',
                fontSize: '12px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <span>⚡</span>
              <span>Quick Trade</span>
            </button>

            {/* Virtual Cash Pill */}
            <div
              onClick={() => onNavigate('practice')}
              className="glass-card glass-card-interactive"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '6px 14px',
                borderRadius: 'var(--radius-full)',
                border: '1px solid var(--color-virtual-border)',
                background: 'rgba(245, 158, 11, 0.08)',
              }}
              title="Click to trade with virtual balance"
            >
              <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-virtual)', fontWeight: 700 }}>
                Virtual Cash
              </span>
              <span className="tabular-nums" style={{ fontSize: '13px', fontWeight: 600, color: '#FFFFFF' }}>
                ₹{virtualCash.toLocaleString('en-IN')}
              </span>
            </div>

            {/* User Profile Avatar */}
            <button
              onClick={() => onNavigate('settings')}
              title="Shivraj Dhote (Profile & Settings)"
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #1E293B 0%, #0F172A 100%)',
                color: '#FFFFFF',
                border: '1.5px solid var(--border-medium)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.3)',
              }}
            >
              SD
            </button>
          </div>
        </div>
      </header>

      {/* Main Viewport */}
      <main style={{ flex: 1, maxWidth: '1440px', width: '100%', margin: '0 auto', padding: '36px 32px' }}>
        {children}
      </main>

      {/* Global Quick Trade Drawer Modal */}
      <QuickTradeModal />

      {/* Footer */}
      <footer
        style={{
          borderTop: '1px solid var(--border-subtle)',
          padding: '20px 32px',
          maxWidth: '1440px',
          width: '100%',
          margin: '0 auto',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '12px',
          color: 'var(--text-faint)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <span>FinEx Financial Excellence</span>
          <span>•</span>
          <span style={{ color: 'var(--color-accent-cyan)' }}>Live Paper Trading Ledger Engine</span>
          <span>•</span>
          <span>NSE End-Of-Day Observation Reconciled</span>
        </div>
        <span>Developer: Shivraj Dhote</span>
      </footer>
    </div>
  );
};
