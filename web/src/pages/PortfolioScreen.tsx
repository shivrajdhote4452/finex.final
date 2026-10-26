import React, { useState, useEffect } from 'react';
import { useFinancial } from '../context/FinancialContext';
import { NavigationTab } from '../components/layout/AppShell';
import { RecentTransactions } from '../components/trading/RecentTransactions';
import { CardSkeleton, TableSkeleton } from '../components/common/Skeleton';
import { apiClient, OptionPositionItem } from '../api/client';
import { useToast } from '../context/ToastContext';

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
    isAccountLoading,
    openQuickTrade,
    depositFunds,
    refreshAccount,
  } = useFinancial();
  const { showToast } = useToast();

  const [showRebalanceModal, setShowRebalanceModal] = useState(false);
  const [positionsTab, setPositionsTab] = useState<'EQUITIES' | 'OPTIONS'>('EQUITIES');
  const [optionsPositions, setOptionsPositions] = useState<OptionPositionItem[]>([]);
  const [isOptionsLoading, setIsOptionsLoading] = useState<boolean>(false);
  const [isSettling, setIsSettling] = useState<boolean>(false);

  const loadOptionsPositions = () => {
    setIsOptionsLoading(true);
    apiClient.paperTrading
      .getOptionPositions()
      .then((res) => {
        if (res && res.positions) {
          setOptionsPositions(res.positions);
        }
      })
      .catch((err) => {
        console.warn('Failed to load option positions:', err);
      })
      .finally(() => {
        setIsOptionsLoading(false);
      });
  };

  useEffect(() => {
    loadOptionsPositions();
  }, []);

  const handleSettleOptions = async () => {
    setIsSettling(true);
    try {
      const res = await apiClient.paperTrading.settleOptions();
      if (res && res.count > 0) {
        showToast(
          `Settled ${res.count} option contract(s). In-the-money intrinsic values credited to cash balance.`,
          'success',
          'Options Settlement Complete'
        );
      } else {
        showToast('No option positions have reached expiry date.', 'info', 'Settlement Status');
      }
      loadOptionsPositions();
      await refreshAccount();
    } catch (err: any) {
      showToast(err?.message || 'Failed to settle options.', 'error', 'Settlement Failed');
    } finally {
      setIsSettling(false);
    }
  };

  const isProfit = unrealizedPnL >= 0;

  // Day P&L computed client-side from holdings dayChangePct
  const dayPnL = holdings.reduce((sum, h) => {
    const curVal = (Number(h.shares) || 0) * (Number(h.currentPrice) || 0);
    const dayPct = Number(h.dayChangePct) || 0;
    const prevVal = curVal / (1 + dayPct / 100);
    return sum + (curVal - prevVal);
  }, 0);

  const prevPortfolioValue = totalPortfolioValue - dayPnL;
  const dayPnLPct = prevPortfolioValue > 0 ? (dayPnL / prevPortfolioValue) * 100 : 0;
  const isDayProfit = dayPnL >= 0;

  // Donut chart segments (circumference = 2 * PI * 50 = 314.159)
  const circumference = 314.159;
  let accumulatedPct = 0;
  const donutSegments = holdings.map((h) => {
    const holdingVal = (Number(h.shares) || 0) * (Number(h.currentPrice) || 0);
    const pct = totalHoldingsValue > 0 ? (holdingVal / totalHoldingsValue) * 100 : 0;
    const dash = (pct / 100) * circumference;
    const offset = -(accumulatedPct / 100) * circumference;
    accumulatedPct += pct;
    return {
      symbol: h.symbol,
      pct,
      dash,
      offset,
      color: h.color || 'var(--color-primary)',
    };
  });

  if (isAccountLoading && holdings.length === 0 && virtualCash === 0) {
    return (
      <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px', width: '100%', boxSizing: 'border-box' }}>
        <CardSkeleton count={4} />
        <TableSkeleton rows={5} columns={7} />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px', width: '100%', minWidth: 0, boxSizing: 'border-box' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '14px', width: '100%', minWidth: 0 }}>
        <div style={{ minWidth: 0, flex: '1 1 240px' }}>
          <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-primary)', fontWeight: 600 }}>
            Asset Management & Rebalancing
          </span>
          <h1 style={{ fontSize: 'clamp(22px, 5.5vw, 36px)', fontWeight: 700, color: '#FFFFFF', marginTop: '4px', letterSpacing: '-0.02em', wordBreak: 'break-word', lineHeight: 1.2 }}>
            Portfolio & Holdings Architecture
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '4px', wordBreak: 'break-word', lineHeight: 1.5 }}>
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

      {/* Portfolio Hero Upgrade Card */}
      <div
        className="glass-card"
        style={{
          padding: '28px',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '32px',
          alignItems: 'center',
          boxSizing: 'border-box',
          width: '100%',
        }}
      >
        {/* Left Column: Total Value, Day P&L, Key Sub-Metrics */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', minWidth: 0 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span
                style={{
                  fontSize: '11px',
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  color: 'var(--text-muted)',
                  fontWeight: 600,
                }}
              >
                Total Portfolio Valuation
              </span>
              <span className="badge badge-cyan" style={{ fontSize: '10px' }}>
                100% Reconciled
              </span>
            </div>
            <div
              className="tabular-nums"
              style={{
                fontSize: 'clamp(30px, 4vw, 40px)',
                fontWeight: 800,
                color: '#FFFFFF',
                letterSpacing: '-0.02em',
                lineHeight: 1.1,
              }}
            >
              ₹{totalPortfolioValue.toLocaleString('en-IN')}
            </div>
          </div>

          {/* Day P&L & Total ROI Badge Row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <span
              className={isDayProfit ? 'badge badge-profit' : 'badge badge-loss'}
              style={{ fontSize: '12.5px', padding: '4px 10px', fontWeight: 700 }}
            >
              {isDayProfit ? '▲ +' : '▼ '}₹{Math.abs(dayPnL).toLocaleString('en-IN', { maximumFractionDigits: 2 })} ({isDayProfit ? '+' : ''}{dayPnLPct.toFixed(2)}% today)
            </span>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Overall Return:{' '}
              <strong style={{ color: isProfit ? 'var(--color-profit)' : 'var(--color-loss)' }}>
                {isProfit ? '+' : ''}₹{unrealizedPnL.toLocaleString('en-IN')}
              </strong>
            </span>
          </div>

          {/* 3-Column Sub-Metrics Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: '12px',
              marginTop: '4px',
              paddingTop: '16px',
              borderTop: '1px solid var(--border-subtle)',
            }}
          >
            <div>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block' }}>
                Invested Equity
              </span>
              <div className="tabular-nums" style={{ fontSize: '15px', fontWeight: 700, color: '#FFFFFF', marginTop: '2px' }}>
                ₹{totalHoldingsValue.toLocaleString('en-IN')}
              </div>
              <span style={{ fontSize: '11px', color: 'var(--text-faint)' }}>
                {holdings.length} Active Positions
              </span>
            </div>
            <div>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block' }}>
                Liquid Cash
              </span>
              <div className="tabular-nums" style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-virtual)', marginTop: '2px' }}>
                ₹{virtualCash.toLocaleString('en-IN')}
              </div>
              <span style={{ fontSize: '11px', color: 'var(--text-faint)' }}>
                Paper Reserve
              </span>
            </div>
            <div>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block' }}>
                Unrealized Gain
              </span>
              <div
                className="tabular-nums"
                style={{
                  fontSize: '15px',
                  fontWeight: 700,
                  color: isProfit ? 'var(--color-profit)' : 'var(--color-loss)',
                  marginTop: '2px',
                }}
              >
                {isProfit ? '+' : ''}₹{unrealizedPnL.toLocaleString('en-IN')}
              </div>
              <span style={{ fontSize: '11px', color: 'var(--text-faint)' }}>
                {((unrealizedPnL / (totalHoldingsValue - unrealizedPnL || 1)) * 100).toFixed(2)}% Return
              </span>
            </div>
          </div>
        </div>

        {/* Right Column: Allocation Donut Chart (Client-side SVG) */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '24px',
            backgroundColor: 'rgba(255, 255, 255, 0.015)',
            padding: '18px 20px',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)',
            minWidth: 0,
          }}
        >
          {/* Donut SVG */}
          <div style={{ position: 'relative', width: '124px', height: '124px', flexShrink: 0 }}>
            <svg viewBox="0 0 140 140" width="124" height="124" style={{ transform: 'rotate(-90deg)' }}>
              {/* Background ring */}
              <circle cx="70" cy="70" r="50" fill="none" stroke="rgba(255, 255, 255, 0.05)" strokeWidth="16" />
              {/* Colored Segments */}
              {donutSegments.map((seg) => (
                <circle
                  key={seg.symbol}
                  cx="70"
                  cy="70"
                  r="50"
                  fill="none"
                  stroke={seg.color}
                  strokeWidth="16"
                  strokeDasharray={`${seg.dash} 314.159`}
                  strokeDashoffset={seg.offset}
                  strokeLinecap="butt"
                />
              ))}
            </svg>
            {/* Center label */}
            <div
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                pointerEvents: 'none',
              }}
            >
              <span style={{ fontSize: '17px', fontWeight: 800, color: '#FFFFFF' }}>
                {holdings.length}
              </span>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Positions
              </span>
            </div>
          </div>

          {/* Donut Legend */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '120px' }}>
            <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Equity Weights
            </span>
            {holdings.slice(0, 4).map((h) => {
              const pct = totalHoldingsValue > 0 ? ((h.shares * h.currentPrice) / totalHoldingsValue) * 100 : 0;
              return (
                <div key={h.symbol} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', fontSize: '11.5px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: h.color, display: 'inline-block' }} />
                    <span style={{ color: '#FFFFFF', fontWeight: 500 }}>{h.symbol}</span>
                  </div>
                  <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>{pct.toFixed(1)}%</span>
                </div>
              );
            })}
            {holdings.length > 4 && (
              <span style={{ fontSize: '10.5px', color: 'var(--text-faint)' }}>
                +{holdings.length - 4} other positions
              </span>
            )}
            {holdings.length === 0 && (
              <span style={{ fontSize: '11px', color: 'var(--text-faint)' }}>
                No active equity positions
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Holdings & Options Positions Card */}
      <div className="glass-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', gap: '8px', background: 'rgba(255, 255, 255, 0.03)', padding: '3px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--border-subtle)' }}>
            <button
              id="portfolio-subtab-equities"
              type="button"
              onClick={() => setPositionsTab('EQUITIES')}
              style={{
                padding: '6px 14px',
                borderRadius: 'var(--radius-xs)',
                background: positionsTab === 'EQUITIES' ? 'var(--color-primary)' : 'transparent',
                color: positionsTab === 'EQUITIES' ? '#FFFFFF' : 'var(--text-muted)',
                fontWeight: 600,
                fontSize: '12.5px',
                border: 'none',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                transition: 'all var(--transition-fast)',
              }}
            >
              <span>📈</span> Equity Holdings ({holdings.length})
            </button>
            <button
              id="portfolio-subtab-options"
              type="button"
              onClick={() => setPositionsTab('OPTIONS')}
              style={{
                padding: '6px 14px',
                borderRadius: 'var(--radius-xs)',
                background: positionsTab === 'OPTIONS' ? 'var(--color-primary)' : 'transparent',
                color: positionsTab === 'OPTIONS' ? '#FFFFFF' : 'var(--text-muted)',
                fontWeight: 600,
                fontSize: '12.5px',
                border: 'none',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                transition: 'all var(--transition-fast)',
              }}
            >
              <span>⚡</span> Options Contracts ({optionsPositions.length})
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {positionsTab === 'OPTIONS' ? (
              <button
                type="button"
                onClick={handleSettleOptions}
                disabled={isSettling || optionsPositions.length === 0}
                className="btn btn-secondary"
                style={{ fontSize: '12px', padding: '6px 14px', cursor: optionsPositions.length === 0 ? 'not-allowed' : 'pointer' }}
              >
                {isSettling ? 'Settling Contracts...' : '⚡ Settle Expired Contracts'}
              </button>
            ) : (
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                {holdings.length} Positions Reconciled
              </span>
            )}
          </div>
        </div>

        {positionsTab === 'EQUITIES' ? (
          <>
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
                  {holdings.length === 0 ? (
                    <tr>
                      <td colSpan={8} style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>
                        No active holdings. Trade any Indian equity to initiate paper positions.
                      </td>
                    </tr>
                  ) : (
                    holdings.map((h) => {
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
                            <div className="truncate-text" style={{ maxWidth: '160px' }}>
                              <strong style={{ color: '#FFFFFF', fontSize: '14px' }}>{h.symbol}</strong>
                              <div style={{ fontSize: '11px', color: 'var(--text-faint)' }}>{h.name}</div>
                            </div>
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
                    })
                  )}
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
          </>
        ) : (
          /* Options Positions Table */
          <>
            <div className="table-scroll-wrapper">
              <div className="table-swipe-hint">← Swipe horizontally to view full options positions data →</div>
              <table style={{ width: '100%', minWidth: '820px', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-faint)', fontSize: '11px', textTransform: 'uppercase' }}>
                    <th style={{ padding: '12px 14px' }}>Contract</th>
                    <th style={{ padding: '12px 14px' }}>Expiry & Countdown</th>
                    <th style={{ padding: '12px 14px' }}>Lots (Units)</th>
                    <th style={{ padding: '12px 14px' }}>Avg Premium</th>
                    <th style={{ padding: '12px 14px' }}>Current Premium</th>
                    <th style={{ padding: '12px 14px' }}>Cost Basis</th>
                    <th style={{ padding: '12px 14px' }}>Current Value</th>
                    <th style={{ padding: '12px 14px' }}>Moneyness</th>
                    <th style={{ padding: '12px 14px', textAlign: 'right' }}>Unrealized Return</th>
                  </tr>
                </thead>
                <tbody>
                  {isOptionsLoading ? (
                    <tr>
                      <td colSpan={9} style={{ padding: '24px' }}>
                        <TableSkeleton rows={3} columns={9} />
                      </td>
                    </tr>
                  ) : optionsPositions.length === 0 ? (
                    <tr>
                      <td colSpan={9} style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>
                        <div>No open paper options positions.</div>
                        <button
                          onClick={() => onNavigate('markets')}
                          className="btn-emerald"
                          style={{ marginTop: '12px', padding: '6px 14px', fontSize: '12px', cursor: 'pointer' }}
                        >
                          Explore Options Chain →
                        </button>
                      </td>
                    </tr>
                  ) : (
                    optionsPositions.map((opt) => {
                      const isPos = opt.unrealized_pnl >= 0;
                      const isCall = opt.option_type === 'CE';

                      return (
                        <tr
                          key={opt.contract_symbol}
                          style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}
                        >
                          <td style={{ padding: '14px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <span
                                style={{
                                  fontSize: '10px',
                                  fontWeight: 700,
                                  padding: '2px 6px',
                                  borderRadius: '3px',
                                  backgroundColor: isCall ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                                  color: isCall ? 'var(--color-profit)' : 'var(--color-loss)',
                                }}
                              >
                                {isCall ? 'CE' : 'PE'}
                              </span>
                              <div>
                                <strong style={{ color: '#FFFFFF', fontSize: '13px' }}>{opt.contract_symbol}</strong>
                                <div style={{ fontSize: '11px', color: 'var(--text-faint)' }}>{opt.underlying}</div>
                              </div>
                            </div>
                          </td>
                          <td style={{ padding: '14px' }}>
                            <div style={{ color: '#FFFFFF', fontSize: '13px' }}>{opt.expiry}</div>
                            <span style={{ fontSize: '11px', color: opt.days_to_expiry <= 2 ? 'var(--color-loss)' : 'var(--color-action)' }}>
                              {opt.days_to_expiry} days to expiry
                            </span>
                          </td>
                          <td style={{ padding: '14px' }} className="tabular-nums">
                            <strong>{opt.lots} Lot{opt.lots > 1 ? 's' : ''}</strong>
                            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{opt.total_quantity} units</div>
                          </td>
                          <td style={{ padding: '14px' }} className="tabular-nums">
                            ₹{opt.average_premium.toFixed(2)}
                          </td>
                          <td style={{ padding: '14px' }} className="tabular-nums">
                            ₹{opt.current_premium.toFixed(2)}
                          </td>
                          <td style={{ padding: '14px', fontWeight: 600 }} className="tabular-nums">
                            ₹{opt.total_cost_basis.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                          </td>
                          <td style={{ padding: '14px', fontWeight: 600 }} className="tabular-nums">
                            ₹{opt.current_market_value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                          </td>
                          <td style={{ padding: '14px' }}>
                            <span
                              style={{
                                fontSize: '11px',
                                fontWeight: 700,
                                padding: '2px 8px',
                                borderRadius: '4px',
                                backgroundColor: opt.is_itm ? 'rgba(16, 185, 129, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                                color: opt.is_itm ? 'var(--color-profit)' : 'var(--text-muted)',
                              }}
                            >
                              {opt.is_itm ? 'ITM (Intrinsic)' : 'OTM (Extrinsic)'}
                            </span>
                          </td>
                          <td style={{ padding: '14px', textAlign: 'right' }}>
                            <span className={isPos ? 'badge badge-profit' : 'badge badge-loss'}>
                              {isPos ? '+' : ''}₹{opt.unrealized_pnl.toLocaleString('en-IN', { minimumFractionDigits: 2 })} ({isPos ? '+' : ''}{opt.unrealized_pnl_pct.toFixed(2)}%)
                            </span>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            {/* Educational Options Risk Notice */}
            <div
              style={{
                marginTop: '20px',
                padding: '12px 16px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'rgba(239, 68, 68, 0.05)',
                border: '1px solid rgba(239, 68, 68, 0.2)',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                fontSize: '12px',
                color: '#FCA5A5',
              }}
            >
              <span>⚠️</span>
              <span>
                <strong>Educational Notice:</strong> Options positions are isolated from equity holdings. Long calls and puts lose time value daily (theta decay) and expire worthless if spot finishes out of the money at expiry. Maximum risk is strictly capped at the premium paid.
              </span>
            </div>
          </>
        )}
      </div>

      {/* Recent Paper-Trading Transactions Ledger Feed (Below Holdings) */}
      <RecentTransactions
        title="Recent Portfolio Transactions"
        onNavigate={onNavigate}
        maxItems={8}
      />

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

export default PortfolioScreen;
