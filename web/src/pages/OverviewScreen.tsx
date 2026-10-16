import React, { useState } from 'react';
import { useFinancial, LedgerEntry } from '../context/FinancialContext';
import { NavigationTab } from '../components/layout/AppShell';

interface OverviewScreenProps {
  onNavigate: (tab: NavigationTab) => void;
}

export const OverviewScreen: React.FC<OverviewScreenProps> = ({ onNavigate }) => {
  const {
    virtualCash,
    holdings,
    ledger,
    totalHoldingsValue,
    totalPortfolioValue,
    unrealizedPnL,
    marketQuotes,
    openQuickTrade,
  } = useFinancial();

  const [hoveredPoint, setHoveredPoint] = useState<{ month: string; value: number } | null>(null);
  const [chartView, setChartView] = useState<'line' | 'candle'>('line');
  const [selectedSlip, setSelectedSlip] = useState<LedgerEntry | null>(null);

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

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '32px' }}>
      {/* Top Welcome & Quick Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-primary)', fontWeight: 600 }}>
            Executive Workspace
          </span>
          <h1 style={{ fontSize: '36px', fontWeight: 700, color: '#FFFFFF', marginTop: '4px', letterSpacing: '-0.02em' }}>
            Good afternoon, Shivraj
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
            Live simulated portfolio synchronized with authentic NSE observations and atomic virtual ledger.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button onClick={() => openQuickTrade()} className="btn-emerald" style={{ padding: '10px 20px', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }}>
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

      {/* KPI Metrics Ribbon */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr 1fr 1fr', gap: '20px' }}>
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
          <div style={{ fontSize: '12px', color: 'var(--color-primary)', marginTop: '14px' }}>
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
      <div className="glass-card" style={{ padding: '20px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="pulse-dot" />
            <h3 style={{ fontSize: '15px', fontWeight: 600, color: '#FFFFFF', margin: 0 }}>
              Live NSE Market Quotes & Instant 1-Click Order Execution
            </h3>
          </div>
          <button onClick={() => onNavigate('markets')} className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '11px' }}>
            Explore All 8 Equities →
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '14px' }}>
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
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong style={{ color: '#FFFFFF', fontSize: '14px' }}>{q.symbol}</strong>
                <span className={q.isPositive ? 'badge badge-profit' : 'badge badge-loss'} style={{ fontSize: '10px' }}>
                  {q.isPositive ? '+' : ''}{q.changePct}%
                </span>
              </div>
              <div className="tabular-nums" style={{ fontSize: '18px', fontWeight: 700, color: '#FFFFFF' }}>
                ₹{q.price.toLocaleString('en-IN')}
              </div>
              <div style={{ display: 'flex', gap: '6px', marginTop: '4px' }}>
                <button
                  onClick={() => openQuickTrade(q.symbol)}
                  className="btn-emerald"
                  style={{ flex: 1, padding: '6px', fontSize: '11px', borderRadius: 'var(--radius-xs)', cursor: 'pointer' }}
                >
                  Buy
                </button>
                <button
                  onClick={() => openQuickTrade(q.symbol)}
                  className="btn btn-secondary"
                  style={{ flex: 1, padding: '6px', fontSize: '11px', borderRadius: 'var(--radius-xs)', color: 'var(--color-loss)', borderColor: 'var(--color-loss-border)' }}
                >
                  Sell
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Chart Section & Concentration Insight */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '28px', alignItems: 'start' }}>
        {/* Interactive Account Value Chart with Line / Candlestick toggle */}
        <div className="glass-card" style={{ padding: '28px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#FFFFFF' }}>Portfolio Performance Curve</h2>
                {/* Line / Candle Switch */}
                <div style={{ display: 'inline-flex', background: 'rgba(0,0,0,0.3)', padding: '2px', borderRadius: '4px' }}>
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
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Historical simulated valuation (May – Oct 2026)</span>
            </div>

            {hoveredPoint ? (
              <div className="badge badge-cyan" style={{ fontSize: '13px' }}>
                {hoveredPoint.month}: ₹{hoveredPoint.value.toLocaleString('en-IN')}
              </div>
            ) : (
              <span className="badge badge-neutral">Hover nodes for exact valuation</span>
            )}
          </div>

          {/* SVG Interactive Chart */}
          <div style={{ width: '100%', height: '220px', position: 'relative' }}>
            <svg viewBox="0 0 600 180" style={{ width: '100%', height: '100%', overflow: 'visible' }}>
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
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '16px', fontSize: '11px', color: 'var(--text-faint)' }}>
              {chartData.map((d) => (
                <span key={d.month}>{d.month}</span>
              ))}
            </div>
          </div>
        </div>

        {/* Right AI Research Insight Card */}
        <div className="glass-card" style={{ padding: '28px', border: '1px solid rgba(6, 182, 212, 0.3)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <span className="badge badge-cyan">AI Research Insight</span>
            <span style={{ fontSize: '11px', color: 'var(--text-faint)' }}>Grounded in Holdings</span>
          </div>

          <h3 style={{ fontSize: '20px', fontWeight: 600, color: '#FFFFFF', marginBottom: '8px' }}>
            High IT Concentration
          </h3>
          <p style={{ fontSize: '13px', lineHeight: 1.6, color: 'var(--text-muted)', marginBottom: '20px' }}>
            TCS and Infosys represent <strong>50.8%</strong> of your invested equity holdings. While both are market leaders, SEBI diversification guidelines recommend capping single-sector exposure under 30% to mitigate industry downturns.
          </p>

          <div
            style={{
              padding: '14px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'rgba(6, 182, 212, 0.08)',
              border: '1px solid rgba(6, 182, 212, 0.2)',
              marginBottom: '20px',
              fontSize: '12px',
              color: 'var(--color-accent-cyan)',
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
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '28px' }}>
        {/* Holdings Table */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#FFFFFF' }}>Portfolio Holdings</h3>
            <button onClick={() => onNavigate('portfolio')} className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '11px' }}>
              View Full Portfolio →
            </button>
          </div>

          <div style={{ overflowX: 'auto' }}>
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
                {holdings.map((h) => {
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
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recent Execution Activity with Contract Note triggers */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#FFFFFF' }}>Recent Order Activity</h3>
            <button onClick={() => onNavigate('transactions')} className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '11px' }}>
              Full Ledger ({ledger.length}) →
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {ledger.slice(0, 4).map((entry) => (
              <div
                key={entry.id}
                onClick={() => setSelectedSlip(entry)}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '12px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-subtle)',
                  cursor: 'pointer',
                  transition: 'background 0.15s ease',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.05)')}
                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.02)')}
                title="Click to view electronic contract note"
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className={entry.type === 'BUY' ? 'badge badge-profit' : entry.type === 'SELL' ? 'badge badge-loss' : 'badge badge-virtual'} style={{ fontSize: '10px' }}>
                      {entry.type}
                    </span>
                    <strong style={{ fontSize: '13px', color: '#FFFFFF' }}>{entry.symbol}</strong>
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>({entry.shares} sh)</span>
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-faint)', marginTop: '2px' }}>
                    {entry.timestamp}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className="tabular-nums" style={{ fontSize: '13px', fontWeight: 600, color: '#FFFFFF' }}>
                    ₹{entry.total.toLocaleString('en-IN')}
                  </div>
                  <span className="badge badge-profit" style={{ fontSize: '10px', marginTop: '2px' }}>
                    {entry.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Slip Modal */}
      {selectedSlip && (
        <div className="modal-overlay" onClick={() => setSelectedSlip(null)}>
          <div className="modal-content contract-note" style={{ maxWidth: '520px', padding: '32px' }} onClick={(e) => e.stopPropagation()}>
            <div className="compliance-watermark">FINEX</div>
            <h3 style={{ fontSize: '20px', fontWeight: 700, color: '#FFFFFF', marginBottom: '8px' }}>
              Contract Note Slip • {selectedSlip.id}
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '20px' }}>
              Execution confirmed on FinEx simulated matching engine.
            </p>

            <div style={{ backgroundColor: 'rgba(0,0,0,0.4)', padding: '16px', borderRadius: 'var(--radius-sm)', marginBottom: '20px', fontSize: '13px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Security:</span>
                <strong style={{ color: '#FFFFFF' }}>{selectedSlip.symbol}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Order Type:</span>
                <span style={{ color: '#FFFFFF' }}>{selectedSlip.type} ({selectedSlip.orderType})</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Quantity:</span>
                <span style={{ color: '#FFFFFF' }}>{selectedSlip.shares} shares</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Gross Amount:</span>
                <span style={{ color: '#FFFFFF', fontWeight: 700 }}>₹{selectedSlip.total.toLocaleString('en-IN')}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '8px', marginTop: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Virtual Cash After:</span>
                <span style={{ color: 'var(--color-virtual)', fontWeight: 700 }}>₹{selectedSlip.cashAfter.toLocaleString('en-IN')}</span>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button onClick={() => setSelectedSlip(null)} className="btn btn-primary">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
