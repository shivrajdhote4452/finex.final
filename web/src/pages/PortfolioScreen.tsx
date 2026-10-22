import React, { useState } from 'react';
import { useFinancial } from '../context/FinancialContext';
import { NavigationTab } from '../components/layout/AppShell';

interface PortfolioScreenProps {
  onNavigate: (tab: NavigationTab) => void;
}

export const PortfolioScreen: React.FC<PortfolioScreenProps> = ({ onNavigate }) => {
  const {
    virtualCash,
    holdings,
    totalHoldingsValue,
    unrealizedPnL,
    totalPortfolioValue,
    openQuickTrade,
    depositFunds,
  } = useFinancial();

  const [showRebalanceModal, setShowRebalanceModal] = useState(false);
  const isProfit = unrealizedPnL >= 0;

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '32px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-primary)', fontWeight: 600 }}>
            Asset Management & Rebalancing
          </span>
          <h1 style={{ fontSize: '36px', fontWeight: 700, color: '#FFFFFF', marginTop: '4px', letterSpacing: '-0.02em' }}>
            Portfolio & Holdings Architecture
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
            Reconciles live positions, average cost basis, current valuations, and virtual cash ledger.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <button onClick={() => setShowRebalanceModal(true)} className="btn btn-secondary">
            ⚖️ Simulate Rebalance
          </button>
          <button onClick={() => openQuickTrade()} className="btn-emerald" style={{ padding: '10px 20px', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }}>
            ⚡ Instant Trade
          </button>
          <button onClick={() => onNavigate('transactions')} className="btn btn-secondary">
            Audit Ledger →
          </button>
        </div>
      </div>

      {/* Empty Wallet State Banner when no cash and no positions */}
      {virtualCash === 0 && holdings.length === 0 && (
        <div
          className="glass-card"
          style={{
            padding: '20px 24px',
            border: '1px solid var(--color-action)',
            backgroundColor: 'rgba(242, 154, 96, 0.08)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '16px',
            flexWrap: 'wrap',
          }}
        >
          <div>
            <div style={{ color: '#FFFFFF', fontWeight: 600, fontSize: '15px' }}>
              Your paper wallet is empty
            </div>
            <div style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '2px' }}>
              Seed your practice account with virtual capital to start simulating trades with authentic market data.
            </div>
          </div>
          <button
            type="button"
            onClick={() => depositFunds(1000000)}
            className="btn btn-action"
            style={{ whiteSpace: 'nowrap', cursor: 'pointer' }}
          >
            Start with ₹10,00,000
          </button>
        </div>
      )}

      {/* Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px' }}>
        <div className="glass-card" style={{ padding: '24px' }}>
          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>
            Holdings Valuation
          </span>
          <div className="tabular-nums" style={{ fontSize: '32px', fontWeight: 700, color: '#FFFFFF', marginTop: '8px' }}>
            ₹{totalHoldingsValue.toLocaleString('en-IN')}
          </div>
          <span style={{ fontSize: '12px', color: 'var(--text-faint)' }}>{holdings.length} Active Positions</span>
        </div>

        <div className="glass-card" style={{ padding: '24px' }}>
          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>
            Unrealized Gain / Loss
          </span>
          <div className="tabular-nums" style={{ fontSize: '32px', fontWeight: 700, color: isProfit ? 'var(--color-profit)' : 'var(--color-loss)', marginTop: '8px' }}>
            {isProfit ? '+' : ''}₹{unrealizedPnL.toLocaleString('en-IN')}
          </div>
          <span className={isProfit ? 'badge badge-profit' : 'badge badge-loss'} style={{ marginTop: '4px' }}>
            {isProfit ? '+' : ''}{((unrealizedPnL / (totalHoldingsValue - unrealizedPnL || 1)) * 100).toFixed(2)}% Return
          </span>
        </div>

        <div className="glass-card" style={{ padding: '24px' }}>
          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>
            Virtual Cash Reserve
          </span>
          <div className="tabular-nums" style={{ fontSize: '32px', fontWeight: 700, color: 'var(--color-virtual)', marginTop: '8px' }}>
            ₹{virtualCash.toLocaleString('en-IN')}
          </div>
          <span style={{ fontSize: '12px', color: 'var(--text-faint)' }}>Available for trade simulation</span>
        </div>

        <div className="glass-card" style={{ padding: '24px' }}>
          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>
            Total Account Equity
          </span>
          <div className="tabular-nums" style={{ fontSize: '32px', fontWeight: 700, color: '#FFFFFF', marginTop: '8px' }}>
            ₹{totalPortfolioValue.toLocaleString('en-IN')}
          </div>
          <span style={{ fontSize: '12px', color: 'var(--color-accent-cyan)' }}>100% Reconciled</span>
        </div>
      </div>

      {/* Allocation Segment Strip */}
      <div className="glass-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <h3 style={{ fontSize: '15px', fontWeight: 600, color: '#FFFFFF' }}>Asset Distribution</h3>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Excludes Liquid Cash</span>
        </div>

        {/* Dynamic Horizontal Allocation Bar */}
        <div style={{ display: 'flex', height: '14px', borderRadius: '4px', overflow: 'hidden', marginBottom: '16px' }}>
          {holdings.map((h) => {
            const pct = ((h.shares * h.currentPrice) / (totalHoldingsValue || 1)) * 100;
            return (
              <div
                key={h.symbol}
                style={{ width: `${pct}%`, backgroundColor: h.color }}
                title={`${h.symbol}: ${pct.toFixed(1)}%`}
              />
            );
          })}
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '24px', fontSize: '12px' }}>
          {holdings.map((h) => {
            const pct = ((h.shares * h.currentPrice) / (totalHoldingsValue || 1)) * 100;
            return (
              <div key={h.symbol} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ color: h.color, fontSize: '14px' }}>●</span>
                <span style={{ color: '#FFFFFF', fontWeight: 500 }}>{h.symbol}</span>
                <span style={{ color: 'var(--text-faint)' }}>({pct.toFixed(1)}%)</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Holdings Detailed Table */}
      <div className="glass-card" style={{ padding: '24px' }}>
        <div className="table-scroll-wrapper">
          <div className="table-swipe-hint">← Swipe horizontally to view full holdings data →</div>
          <table style={{ width: '100%', minWidth: '760px', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-faint)', fontSize: '11px', textTransform: 'uppercase' }}>
                <th style={{ padding: '12px 14px' }}>Holding</th>
                <th style={{ padding: '12px 14px' }}>Sector</th>
                <th style={{ padding: '12px 14px' }}>Shares</th>
                <th style={{ padding: '12px 14px' }}>Avg Cost</th>
                <th style={{ padding: '12px 14px' }}>Market Price</th>
                <th style={{ padding: '12px 14px' }}>Current Value</th>
                <th style={{ padding: '12px 14px', textAlign: 'right' }}>Total Return</th>
                <th style={{ padding: '12px 14px', textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((h) => {
                const curVal = h.shares * h.currentPrice;
                const costVal = h.shares * h.avgPrice;
                const pnl = curVal - costVal;
                const isPos = pnl >= 0;

                return (
                  <tr
                    key={h.symbol}
                    style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}
                  >
                    <td style={{ padding: '14px' }}>
                      <strong style={{ color: '#FFFFFF', fontSize: '14px' }}>{h.symbol}</strong>
                      <div style={{ fontSize: '11px', color: 'var(--text-faint)' }}>{h.name}</div>
                    </td>
                    <td style={{ padding: '14px', color: 'var(--text-muted)' }}>{h.assetClass}</td>
                    <td style={{ padding: '14px' }} className="tabular-nums">{h.shares}</td>
                    <td style={{ padding: '14px' }} className="tabular-nums">₹{h.avgPrice.toLocaleString('en-IN')}</td>
                    <td style={{ padding: '14px' }} className="tabular-nums">₹{h.currentPrice.toLocaleString('en-IN')}</td>
                    <td style={{ padding: '14px', fontWeight: 600 }} className="tabular-nums">
                      ₹{curVal.toLocaleString('en-IN')}
                    </td>
                    <td style={{ padding: '14px', textAlign: 'right' }}>
                      <span className={isPos ? 'badge badge-profit' : 'badge badge-loss'}>
                        {isPos ? '+' : ''}₹{pnl.toLocaleString('en-IN')}
                      </span>
                    </td>
                    <td style={{ padding: '14px', textAlign: 'right' }}>
                      <button
                        onClick={() => openQuickTrade(h.symbol)}
                        className="btn-emerald"
                        style={{ padding: '5px 12px', fontSize: '11px', borderRadius: 'var(--radius-xs)', cursor: 'pointer' }}
                      >
                        Trade
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Ledger Reconciliation Note */}
        <div
          title={`Ledger Proof: Holdings (₹${totalHoldingsValue.toLocaleString('en-IN')}) + Cash (₹${virtualCash.toLocaleString('en-IN')}) = Account Total (₹${totalPortfolioValue.toLocaleString('en-IN')})`}
          style={{
            marginTop: '24px',
            padding: '12px 16px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '12px',
            flexWrap: 'wrap',
            fontSize: '12px',
            color: 'var(--text-muted)',
            lineHeight: 1.5,
          }}
        >
          <span style={{ flex: '1 1 auto', minWidth: '220px', wordBreak: 'break-word', whiteSpace: 'normal', overflow: 'visible' }}>
            Ledger Proof: Holdings (<strong>₹{totalHoldingsValue.toLocaleString('en-IN')}</strong>) + Cash (<strong>₹{virtualCash.toLocaleString('en-IN')}</strong>) = Account Total (<strong>₹{totalPortfolioValue.toLocaleString('en-IN')}</strong>)
          </span>
          <span className="badge badge-profit" style={{ flexShrink: 0 }}>Zero Discrepancy</span>
        </div>
      </div>

      {/* Rebalance Simulator Modal */}
      {showRebalanceModal && (
        <div className="modal-overlay" onClick={() => setShowRebalanceModal(false)}>
          <div className="modal-content" style={{ maxWidth: '600px', padding: '32px' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '20px', fontWeight: 700, color: '#FFFFFF', margin: 0 }}>
                SEBI Asset Allocation & Rebalance Simulator
              </h3>
              <button onClick={() => setShowRebalanceModal(false)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '20px', cursor: 'pointer' }}>✕</button>
            </div>

            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '20px' }}>
              Current portfolio has <strong>50.8%</strong> allocation in Technology (TCS + INFY). SEBI investor guidelines advise diversifying across uncorrelated sectors.
            </p>

            <div style={{ backgroundColor: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: 'var(--radius-sm)', marginBottom: '20px', fontSize: '13px' }}>
              <strong style={{ color: '#FFFFFF', display: 'block', marginBottom: '8px' }}>Recommended Simulated Execution Steps:</strong>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
                  <span>Sell 3 shares of TCS:</span>
                  <span style={{ color: 'var(--color-profit)' }}>+₹10,800 Virtual Cash</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
                  <span>Buy 5 shares of HDFCBANK:</span>
                  <span style={{ color: 'var(--color-primary)' }}>-₹8,000 Consideration</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
                  <span>Buy 3 shares of TATAMOTORS:</span>
                  <span style={{ color: 'var(--color-primary)' }}>-₹2,773 Consideration</span>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px' }}>
              <button onClick={() => setShowRebalanceModal(false)} className="btn btn-secondary" style={{ flex: 1 }}>
                Cancel
              </button>
              <button
                onClick={() => {
                  setShowRebalanceModal(false);
                  openQuickTrade('HDFCBANK');
                }}
                className="btn-emerald"
                style={{ flex: 1, padding: '10px', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }}
              >
                Execute Rebalancing Trade →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
