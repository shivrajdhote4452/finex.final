import React from 'react';
import { NavigationTab } from '../components/layout/AppShell';

interface PortfolioScreenProps {
  onNavigate: (tab: NavigationTab) => void;
}

export const PortfolioScreen: React.FC<PortfolioScreenProps> = ({ onNavigate }) => {
  const holdings = [
    { symbol: 'RELIANCE', name: 'Reliance Industries', qty: 10, value: '25,000', costBasis: '23,000', pnl: '+₹2,000', weight: '25.1%', color: '#234BC0' },
    { symbol: 'TCS', name: 'Tata Consultancy Services', qty: 10, value: '36,000', costBasis: '34,500', pnl: '+₹1,500', weight: '36.2%', color: '#162032' },
    { symbol: 'INFY', name: 'Infosys', qty: 10, value: '14,500', costBasis: '13,500', pnl: '+₹1,000', weight: '14.6%', color: '#966336' },
    { symbol: 'HDFCBANK', name: 'HDFC Bank', qty: 15, value: '24,000', costBasis: '23,000', pnl: '+₹1,000', weight: '24.1%', color: '#56667A' },
  ];

  return (
    <div style={{ maxWidth: '1240px', margin: '0 auto' }}>
      <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-cobalt)', fontWeight: 600 }}>
        Portfolio
      </span>

      <div style={{ marginTop: '8px', marginBottom: '32px' }}>
        <h1 style={{ fontSize: '40px', lineHeight: 1.15, margin: 0 }}>Know what you hold.</h1>
        <p style={{ color: 'var(--color-ink-muted)', fontSize: '14px', marginTop: '4px' }}>
          Paper portfolio • Figures reconcile across holdings, cash and account value.
        </p>
      </div>

      {/* Summary Metrics Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '32px',
          borderBottom: '1px solid var(--color-border)',
          paddingBottom: '28px',
          marginBottom: '36px',
        }}
      >
        <div>
          <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>
            Holdings Value
          </span>
          <div style={{ fontFamily: 'var(--font-serif)', fontSize: '38px', color: 'var(--color-ink)', marginTop: '8px' }}>
            ₹99,500
          </div>
        </div>

        <div>
          <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>
            Cost Basis
          </span>
          <div style={{ fontFamily: 'var(--font-serif)', fontSize: '38px', color: 'var(--color-ink)', marginTop: '8px' }}>
            ₹94,000
          </div>
        </div>

        <div>
          <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>
            Unrealized P&L
          </span>
          <div style={{ fontFamily: 'var(--font-serif)', fontSize: '38px', color: 'var(--color-gain)', marginTop: '8px' }}>
            +₹5,500
          </div>
        </div>

        <div>
          <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>
            Virtual Cash
          </span>
          <div style={{ fontFamily: 'var(--font-serif)', fontSize: '38px', color: 'var(--color-ink)', marginTop: '8px' }}>
            ₹25,000
          </div>
        </div>
      </div>

      {/* Invested Allocation Strip (Screen 07 of PDF) */}
      <div style={{ marginBottom: '40px' }}>
        <div style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-ink-muted)', marginBottom: '12px' }}>
          Invested Allocation / Excludes Cash
        </div>

        {/* Multi-segment thin strip */}
        <div style={{ display: 'flex', width: '100%', height: '14px', borderRadius: '2px', overflow: 'hidden', marginBottom: '12px' }}>
          <div style={{ width: '36.2%', backgroundColor: '#162032' }} title="TCS 36.2%" />
          <div style={{ width: '25.1%', backgroundColor: '#234BC0' }} title="RELIANCE 25.1%" />
          <div style={{ width: '24.1%', backgroundColor: '#56667A' }} title="HDFCBANK 24.1%" />
          <div style={{ width: '14.6%', backgroundColor: '#966336' }} title="INFY 14.6%" />
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', gap: '32px', fontSize: '12px', color: 'var(--color-ink-muted)' }}>
          <span><strong style={{ color: '#162032' }}>■</strong> TCS 36.2%</span>
          <span><strong style={{ color: '#234BC0' }}>■</strong> RELIANCE 25.1%</span>
          <span><strong style={{ color: '#56667A' }}>■</strong> HDFCBANK 24.1%</span>
          <span><strong style={{ color: '#966336' }}>■</strong> INFY 14.6%</span>
        </div>
      </div>

      {/* Holdings Table */}
      <div style={{ width: '100%', overflowX: 'auto', marginBottom: '24px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--color-border)', fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>
              <th style={{ padding: '12px 16px', fontWeight: 500 }}>Holding</th>
              <th style={{ padding: '12px 16px', fontWeight: 500 }}>Qty</th>
              <th style={{ padding: '12px 16px', fontWeight: 500 }}>Value</th>
              <th style={{ padding: '12px 16px', fontWeight: 500 }}>Cost Basis</th>
              <th style={{ padding: '12px 16px', fontWeight: 500, textAlign: 'right' }}>P&L</th>
            </tr>
          </thead>
          <tbody>
            {holdings.map((h) => (
              <tr
                key={h.symbol}
                onClick={() => onNavigate('markets')}
                style={{
                  borderBottom: '1px solid var(--color-border-subtle)',
                  cursor: 'pointer',
                  transition: 'background-color var(--transition-fast)',
                }}
              >
                <td style={{ padding: '16px 16px' }}>
                  <div style={{ fontWeight: 600, fontSize: '15px' }}>{h.symbol}</div>
                  <div style={{ fontSize: '12px', color: 'var(--color-ink-muted)' }}>{h.name}</div>
                </td>
                <td style={{ padding: '16px 16px', fontFamily: 'var(--font-mono)' }}>{h.qty}</td>
                <td style={{ padding: '16px 16px', fontFamily: 'var(--font-mono)' }}>₹{h.value}</td>
                <td style={{ padding: '16px 16px', fontFamily: 'var(--font-mono)' }}>₹{h.costBasis}</td>
                <td style={{ padding: '16px 16px', fontFamily: 'var(--font-mono)', textAlign: 'right', color: 'var(--color-gain)' }}>
                  {h.pnl}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Deterministic Reconciliation Footer */}
      <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '16px', fontSize: '13px', color: 'var(--color-ink-muted)' }}>
        Virtual account value: <strong>₹99,500</strong> holdings + <strong>₹25,000</strong> cash = <strong>₹1,24,500</strong>
      </div>
    </div>
  );
};
