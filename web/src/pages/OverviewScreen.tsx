import React, { useState } from 'react';
import { useFinancial } from '../context/FinancialContext';
import { NavigationTab } from '../components/layout/AppShell';
import { RecentTransactions } from '../components/trading/RecentTransactions';
import { CardSkeleton, TableSkeleton } from '../components/common/Skeleton';

interface OverviewScreenProps {
  onNavigate: (tab: NavigationTab) => void;
}

export function getTimeOfDayGreeting(name: string = 'Shivraj'): string {
  const hour = new Date().getHours();
  if (hour >= 5 && hour < 12) {
    return `Good morning, ${name}`;
  } else if (hour >= 12 && hour < 17) {
    return `Good afternoon, ${name}`;
  } else {
    return `Good evening, ${name}`;
  }
}

export const OverviewScreen: React.FC<OverviewScreenProps> = ({ onNavigate }) => {
  const {
    virtualCash,
    holdings,
    totalHoldingsValue,
    totalPortfolioValue,
    unrealizedPnL,
    marketQuotes,
    openQuickTrade,
    depositFunds,
    isAccountLoading,
  } = useFinancial();

  const [hoveredPoint, setHoveredPoint] = useState<{ month: string; value: number } | null>(null);
  const [chartView, setChartView] = useState<'line' | 'candle'>('line');

  const pnlPct = ((unrealizedPnL / (totalHoldingsValue - unrealizedPnL || 1)) * 100).toFixed(2);
  const isProfit = unrealizedPnL >= 0;

  const chartData = [
    { month: 'May', value: 118500, o: 117000, h: 119200, l: 116500, c: 118500 },
    { month: 'Jun', value: 120400, o: 118500, h: 121000, l: 118000, c: 120400 },
    { month: 'Jul', value: 119800, o: 120400, h: 121500, l: 119000, c: 119800 },
    { month: 'Aug', value: 122600, o: 119800, h: 123200, l: 119500, c: 122600 },
    { month: 'Sep', value: 123800, o: 122600, h: 124500, l: 122000, c: 123800 },
    { month: 'Oct', value: totalPortfolioValue, o: 123800, h: Math.max(125000, totalPortfolioValue), l: 123000, c: totalPortfolioValue },
  ];

  const equityPct = Math.round((totalHoldingsValue / (totalPortfolioValue || 1)) * 100);
  const cashPct = 100 - equityPct;
  const greeting = getTimeOfDayGreeting('Shivraj');

  if (isAccountLoading && holdings.length === 0 && virtualCash === 0) {
    return (
      <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px', width: '100%', boxSizing: 'border-box' }}>
        <CardSkeleton count={4} />
        <TableSkeleton rows={4} columns={5} />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px', width: '100%', minWidth: 0, boxSizing: 'border-box' }}>
      {/* Top Welcome & Quick Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '14px', width: '100%', minWidth: 0 }}>
        <div style={{ minWidth: 0, flex: '1 1 240px' }}>
          <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-primary)', fontWeight: 600 }}>
            Executive Workspace
          </span>
          <h1 style={{ fontSize: 'clamp(22px, 5.5vw, 36px)', fontWeight: 700, color: '#FFFFFF', marginTop: '4px', letterSpacing: '-0.02em', wordBreak: 'break-word', lineHeight: 1.2 }}>
            {greeting}
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '4px', wordBreak: 'break-word', lineHeight: 1.5 }}>
            Simulated portfolio synchronized with authentic ledger.
          </p>
        </div>

        <div className="overview-actions-row">
          <button onClick={() => openQuickTrade()} className="btn-emerald" style={{ padding: '9px 16px', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }}>
            ⚡ Instant Trade
          </button>
          <button onClick={() => onNavigate('transactions')} className="btn btn-secondary">
            📑 View Ledger
          </button>
          <button onClick={() => onNavigate('ask-finex')} className="btn btn-secondary">
            🤖 AI Diagnosis
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

      {/* KPI Metrics Ribbon */}
      <div className="overview-kpi-grid">
        {/* Total Value */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>
              Total Portfolio Value
            </span>
            <span className="badge badge-cyan">Reconciled</span>
          </div>
          <div className="tabular-nums" style={{ fontSize: '38px', fontWeight: 700, color: '#FFFFFF', lineHeight: 1.1 }}>
            ₹{totalPortfolioValue.toLocaleString('en-IN')}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '12px' }}>
            <span className={isProfit ? 'badge badge-profit' : 'badge badge-loss'}>
              {isProfit ? '+' : ''}₹{Math.abs(unrealizedPnL).toLocaleString('en-IN')} ({pnlPct}%)
            </span>
            <span style={{ fontSize: '12px', color: 'var(--text-faint)' }}>Unrealized Gain</span>
          </div>
        </div>

        {/* Invested Holdings */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, display: 'block', marginBottom: '8px' }}>
            Invested Holdings
          </span>
          <div className="tabular-nums" style={{ fontSize: '32px', fontWeight: 700, color: '#FFFFFF', lineHeight: 1.1 }}>
            ₹{totalHoldingsValue.toLocaleString('en-IN')}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '14px' }}>
            {holdings.length} Active Positions • {equityPct}% Allocation
          </div>
        </div>

        {/* Liquid Virtual Cash */}
        <div
          onClick={() => openQuickTrade()}
          className="glass-card glass-card-interactive"
          style={{ padding: '24px', border: '1px solid var(--color-virtual-border)' }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-virtual)', fontWeight: 600 }}>
              Virtual Cash
            </span>
            <span className="badge-virtual">Trade Ready</span>
          </div>
          <div className="tabular-nums" style={{ fontSize: '32px', fontWeight: 700, color: '#FFFFFF', lineHeight: 1.1 }}>
            ₹{virtualCash.toLocaleString('en-IN')}
          </div>
          <div
            role="button"
            tabIndex={0}
            onClick={(e) => {
              e.stopPropagation();
              openQuickTrade();
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                openQuickTrade();
              }
            }}
            style={{ fontSize: '12px', color: 'var(--color-primary)', marginTop: '14px', cursor: 'pointer', fontWeight: 500 }}
          >
            {cashPct}% Liquid • Deploy now →
          </div>
        </div>

        {/* Risk Profile */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-muted)', fontWeight: 600, display: 'block', marginBottom: '8px' }}>
            Deterministic Risk
          </span>
          <div style={{ fontSize: '28px', fontWeight: 700, color: 'var(--color-primary)', lineHeight: 1.1 }}>
            Moderate
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '18px' }}>
            Horizon: 3–5 Years
          </div>
        </div>
      </div>

      {/* Allocation Strip Bar */}
      <div className="glass-card" style={{ padding: '18px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '8px' }}>
          <span style={{ color: 'var(--text-muted)' }}>Capital Deployment Split:</span>
          <span style={{ color: '#FFFFFF' }}>Equities: <strong>{equityPct}%</strong> • Liquid Paper Cash: <strong>{cashPct}%</strong></span>
        </div>
        <div style={{ display: 'flex', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
          <div style={{ width: `${equityPct}%`, backgroundColor: 'var(--color-primary)' }} title={`Equities ${equityPct}%`} />
          <div style={{ width: `${cashPct}%`, backgroundColor: 'var(--color-virtual)' }} title={`Cash ${cashPct}%`} />
        </div>
      </div>

      {/* Live Market Active Instruments Carousel / 1-Click Trade Row */}
      <div className="glass-card" style={{ padding: '20px 24px', width: '100%', minWidth: 0, boxSizing: 'border-box' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '10px', width: '100%', minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, flex: '1 1 200px' }}>
            <span className="pulse-dot" style={{ flexShrink: 0 }} />
            <h3 style={{ fontSize: '15px', fontWeight: 600, color: '#FFFFFF', margin: 0, wordBreak: 'break-word', lineHeight: 1.3 }}>
              Live NSE Market Quotes & Instant 1-Click Order Execution
            </h3>
          </div>
          <button onClick={() => onNavigate('markets')} className="btn btn-secondary" style={{ padding: '5px 12px', fontSize: '11px', flexShrink: 0 }}>
            Explore All 8 Equities →
          </button>
        </div>

        <div className="overview-quotes-grid">
          {Object.values(marketQuotes).slice(0, 4).map((q) => (
            <div
              key={q.symbol}
              style={{
                backgroundColor: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '14px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                minWidth: 0,
                boxSizing: 'border-box',
                width: '100%',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', minWidth: 0 }}>
                <strong style={{ color: '#FFFFFF', fontSize: '14px' }}>{q.symbol}</strong>
                <span className={q.isPositive ? 'badge badge-profit' : 'badge badge-loss'} style={{ fontSize: '10px' }}>
                  {q.isPositive ? '+' : ''}{q.changePct}%
                </span>
              </div>
              <div className="tabular-nums" style={{ fontSize: '18px', fontWeight: 700, color: '#FFFFFF' }}>
                ₹{q.price.toLocaleString('en-IN')}
              </div>
              <div className="quote-card-btn-row">
                <button
                  onClick={() => openQuickTrade(q.symbol)}
                  className="btn-emerald"
                  style={{ flex: 1, minWidth: 0, padding: '7px 4px', fontSize: '11px', borderRadius: 'var(--radius-xs)', cursor: 'pointer', textAlign: 'center' }}
                >
                  Buy
                </button>
                <button
                  onClick={() => openQuickTrade(q.symbol)}
                  className="btn btn-secondary"
                  style={{ flex: 1, minWidth: 0, padding: '7px 4px', fontSize: '11px', borderRadius: 'var(--radius-xs)', color: 'var(--color-loss)', borderColor: 'var(--color-loss-border)', textAlign: 'center' }}
                >
                  Sell
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Chart Section & Concentration Insight */}
      <div className="overview-chart-insight-grid">
        {/* Interactive Account Value Chart with Line / Candlestick toggle */}
        <div className="glass-card" style={{ padding: '24px', minWidth: 0, overflow: 'hidden', width: '100%', boxSizing: 'border-box' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px', flexWrap: 'wrap', gap: '10px', width: '100%', minWidth: 0 }}>
            <div style={{ minWidth: 0, flex: '1 1 220px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#FFFFFF', margin: 0, wordBreak: 'break-word' }}>Portfolio Performance Curve</h2>
                {/* Line / Candle Switch */}
                <div style={{ display: 'inline-flex', background: 'rgba(0,0,0,0.3)', padding: '2px', borderRadius: '4px', flexShrink: 0 }}>
                  <button
                    onClick={() => setChartView('line')}
                    style={{
                      background: chartView === 'line' ? 'var(--color-primary)' : 'transparent',
                      color: chartView === 'line' ? '#FFFFFF' : 'var(--text-muted)',
                      border: 'none',
                      borderRadius: '3px',
                      padding: '2px 8px',
                      fontSize: '11px',
                      cursor: 'pointer',
                    }}
                  >
                    Area
                  </button>
                  <button
                    onClick={() => setChartView('candle')}
                    style={{
                      background: chartView === 'candle' ? 'var(--color-primary)' : 'transparent',
                      color: chartView === 'candle' ? '#FFFFFF' : 'var(--text-muted)',
                      border: 'none',
                      borderRadius: '3px',
                      padding: '2px 8px',
                      fontSize: '11px',
                      cursor: 'pointer',
                    }}
                  >
                    Candles
                  </button>
                </div>
              </div>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginTop: '2px' }}>Historical simulated valuation (May – Oct 2026)</span>
            </div>

            {hoveredPoint ? (
              <div className="badge badge-cyan" style={{ fontSize: '12px', flexShrink: 0 }}>
                {hoveredPoint.month}: ₹{hoveredPoint.value.toLocaleString('en-IN')}
              </div>
            ) : (
              <span className="badge badge-neutral" style={{ fontSize: '11px', flexShrink: 0 }}>Hover nodes for exact valuation</span>
            )}
          </div>

          {/* SVG Interactive Chart */}
          <div style={{ width: '100%', minWidth: 0, height: '200px', position: 'relative', overflow: 'hidden' }}>
            <svg viewBox="0 0 600 180" style={{ width: '100%', height: '100%', display: 'block' }} preserveAspectRatio="none">
              <defs>
                <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#F29A60" stopOpacity="0.3" />
                  <stop offset="100%" stopColor="#F29A60" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              {/* Grid Lines */}
              <line x1="0" y1="30" x2="600" y2="30" stroke="rgba(255, 255, 255, 0.05)" strokeDasharray="3 3" />
              <line x1="0" y1="75" x2="600" y2="75" stroke="rgba(255, 255, 255, 0.05)" strokeDasharray="3 3" />
              <line x1="0" y1="120" x2="600" y2="120" stroke="rgba(255, 255, 255, 0.05)" strokeDasharray="3 3" />
              <line x1="0" y1="165" x2="600" y2="165" stroke="rgba(255, 255, 255, 0.05)" strokeDasharray="3 3" />

              {chartView === 'line' ? (
                <>
                  {/* Shaded Area under Curve */}
                  <polygon
                    points="20,165 20,140 130,120 250,130 370,95 490,75 580,45 580,165"
                    fill="url(#chartGradient)"
                  />
                  {/* Main Curve */}
                  <polyline
                    fill="none"
                    stroke="#F29A60"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    points="20,140 130,120 250,130 370,95 490,75 580,45"
                  />
                  {/* Interactive Data Nodes */}
                  {chartData.map((d, i) => {
                    const xs = [20, 130, 250, 370, 490, 580];
                    const ys = [140, 120, 130, 95, 75, 45];
                    return (
                      <circle
                        key={d.month}
                        cx={xs[i]}
                        cy={ys[i]}
                        r="4.5"
                        fill="#F29A60"
                        stroke="#111111"
                        strokeWidth="2"
                        style={{ cursor: 'pointer', transition: 'r 0.15s ease' }}
                        onMouseEnter={() => setHoveredPoint(d)}
                        onMouseLeave={() => setHoveredPoint(null)}
                      />
                    );
                  })}
                </>
              ) : (
                /* Candlestick Visualization */
                chartData.map((d, i) => {
                  const xs = [50, 150, 250, 350, 450, 550];
                  const x = xs[i];
                  const isGreen = d.c >= d.o;
                  const bodyTop = isGreen ? 75 - i * 6 : 95 + i * 4;
                  const bodyHeight = 24;
                  const color = isGreen ? 'var(--color-profit)' : 'var(--color-loss)';

                  return (
                    <g key={d.month} onMouseEnter={() => setHoveredPoint(d)} onMouseLeave={() => setHoveredPoint(null)} style={{ cursor: 'pointer' }}>
                      {/* High-Low Wick */}
                      <line x1={x} y1={bodyTop - 14} x2={x} y2={bodyTop + bodyHeight + 14} stroke={color} strokeWidth="1.5" />
                      {/* Candle Body */}
                      <rect x={x - 12} y={bodyTop} width="24" height={bodyHeight} fill={color} rx="2" />
                    </g>
                  );
                })
              )}
            </svg>

            {/* X Labels */}
            <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', marginTop: '12px', fontSize: '11px', color: 'var(--text-faint)', padding: '0 4px', boxSizing: 'border-box' }}>
              {chartData.map((d) => (
                <span key={d.month}>{d.month}</span>
              ))}
            </div>
          </div>
        </div>

        {/* Right AI Research Insight Card */}
        <div className="glass-card" style={{ padding: '24px', border: '1px solid rgba(6, 182, 212, 0.3)', minWidth: 0, overflow: 'hidden', width: '100%', boxSizing: 'border-box' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px', flexWrap: 'wrap' }}>
            <span className="badge badge-cyan">AI Research Insight</span>
            <span style={{ fontSize: '11px', color: 'var(--text-faint)' }}>Grounded in Holdings</span>
          </div>

          <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#FFFFFF', marginBottom: '8px', wordBreak: 'break-word', lineHeight: 1.3 }}>
            High IT Concentration
          </h3>
          <p style={{ fontSize: '13px', lineHeight: 1.6, color: 'var(--text-muted)', marginBottom: '18px', wordBreak: 'break-word', whiteSpace: 'normal', overflowWrap: 'break-word' }}>
            TCS and Infosys represent <strong>50.8%</strong> of your invested equity holdings. While both are market leaders, SEBI diversification guidelines recommend capping single-sector exposure under 30% to mitigate industry downturns.
          </p>

          <div
            style={{
              padding: '12px 14px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'rgba(6, 182, 212, 0.08)',
              border: '1px solid rgba(6, 182, 212, 0.2)',
              marginBottom: '18px',
              fontSize: '11.5px',
              color: 'var(--color-accent-cyan)',
              wordBreak: 'break-word',
              whiteSpace: 'normal',
              lineHeight: 1.45,
            }}
          >
            Citation: SEBI Investor Education Guide (Chapter 3: Asset Allocation Principles).
          </div>

          <button onClick={() => onNavigate('ask-finex')} className="btn btn-secondary" style={{ width: '100%' }}>
            Ask FinEx about rebalancing →
          </button>
        </div>
      </div>

      {/* Bottom Grid: Holdings Table & Recent Execution Activity */}
      <div className="overview-bottom-grid">
        {/* Holdings Table */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#FFFFFF' }}>Portfolio Holdings</h3>
            <button onClick={() => onNavigate('portfolio')} className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '11px' }}>
              View Full Portfolio →
            </button>
          </div>

          <div className="table-scroll-wrapper" style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-faint)', fontSize: '11px', textTransform: 'uppercase' }}>
                  <th style={{ padding: '8px 12px' }}>Instrument</th>
                  <th style={{ padding: '8px 12px' }}>Shares</th>
                  <th style={{ padding: '8px 12px' }}>Market Value</th>
                  <th style={{ padding: '8px 12px', textAlign: 'right' }}>Day Change</th>
                  <th style={{ padding: '8px 12px', textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {holdings.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
                      No active holdings. Trade any Indian equity to initiate paper positions.
                    </td>
                  </tr>
                ) : (
                  holdings.map((h) => {
                  const val = h.shares * h.currentPrice;
                  const isPos = h.dayChangePct >= 0;
                  return (
                    <tr key={h.symbol} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                      <td style={{ padding: '12px' }}>
                        <strong style={{ color: '#FFFFFF' }}>{h.symbol}</strong>
                        <div style={{ fontSize: '11px', color: 'var(--text-faint)' }}>{h.assetClass}</div>
                      </td>
                      <td style={{ padding: '12px' }} className="tabular-nums">{h.shares}</td>
                      <td style={{ padding: '12px', fontWeight: 600 }} className="tabular-nums">₹{val.toLocaleString('en-IN')}</td>
                      <td style={{ padding: '12px', textAlign: 'right' }}>
                        <span className={isPos ? 'badge badge-profit' : 'badge badge-loss'}>
                          {isPos ? '+' : ''}{h.dayChangePct}%
                        </span>
                      </td>
                      <td style={{ padding: '12px', textAlign: 'right' }}>
                        <button
                          onClick={() => openQuickTrade(h.symbol)}
                          className="btn-emerald"
                          style={{ padding: '4px 10px', fontSize: '11px', borderRadius: 'var(--radius-xs)', cursor: 'pointer' }}
                        >
                          Trade
                        </button>
                      </td>
                    </tr>
                  );
                }))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recent Execution Activity Feed via Shared Component */}
        <RecentTransactions
          title="Recent Order Activity"
          maxItems={5}
          onNavigate={onNavigate}
        />
      </div>
    </div>
  );
};
