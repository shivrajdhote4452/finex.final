import React, { useState } from 'react';
import { NavigationTab } from '../components/layout/AppShell';

interface MarketsScreenProps {
  onNavigate: (tab: NavigationTab) => void;
}

export const MarketsScreen: React.FC<MarketsScreenProps> = ({ onNavigate }) => {
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'watchlist' | 'all'>('watchlist');
  const [searchQuery, setSearchQuery] = useState('');

  const instruments = [
    {
      symbol: 'RELIANCE',
      name: 'Reliance Industries',
      avatar: 'R',
      price: '2,500.00',
      change: '+1.21%',
      isPositive: true,
      sparkline: 'M0,15 L15,10 L30,16 L45,8 L60,11 L75,4',
    },
    {
      symbol: 'TCS',
      name: 'Tata Consultancy Services',
      avatar: 'T',
      price: '3,600.00',
      change: '-0.80%',
      isPositive: false,
      sparkline: 'M0,5 L15,8 L30,6 L45,14 L60,12 L75,18',
    },
    {
      symbol: 'INFY',
      name: 'Infosys',
      avatar: 'I',
      price: '1,450.00',
      change: '+0.55%',
      isPositive: true,
      sparkline: 'M0,12 L15,14 L30,9 L45,11 L60,7 L75,5',
    },
    {
      symbol: 'HDFCBANK',
      name: 'HDFC Bank',
      avatar: 'H',
      price: '1,600.00',
      change: '+0.32%',
      isPositive: true,
      sparkline: 'M0,14 L15,12 L30,10 L45,6 L60,8 L75,4',
    },
  ];

  // Screen 06 / 08: Instrument in context (Detail view)
  if (selectedSymbol) {
    const inst = instruments.find((i) => i.symbol === selectedSymbol) || instruments[0];
    return (
      <div style={{ maxWidth: '1240px', margin: '0 auto' }}>
        {/* Breadcrumb */}
        <div style={{ marginBottom: '16px' }}>
          <span
            onClick={() => setSelectedSymbol(null)}
            style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-cobalt)', fontWeight: 600, cursor: 'pointer' }}
          >
            Markets
          </span>
          <span style={{ fontSize: '11px', color: 'var(--color-ink-faint)', margin: '0 8px' }}>/</span>
          <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>
            {inst.symbol}
          </span>
        </div>

        {/* Title & Add to Watchlist */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
          <div>
            <h1 style={{ fontSize: '38px', lineHeight: 1.2, margin: 0 }}>{inst.name}</h1>
            <p style={{ fontSize: '13px', color: 'var(--color-ink-muted)', marginTop: '4px' }}>
              NSE / Equity / INR
            </p>
          </div>
          <button className="button-secondary" style={{ padding: '8px 16px', fontSize: '13px' }}>
            Add to watchlist →
          </button>
        </div>

        {/* Price & Period Ribbon */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', borderBottom: '1px solid var(--color-border)', paddingBottom: '20px', marginBottom: '32px' }}>
          <div>
            <div style={{ fontFamily: 'var(--font-serif)', fontSize: '48px', color: 'var(--color-ink)', lineHeight: 1, letterSpacing: '-0.02em' }}>
              ₹{inst.price}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '10px' }}>
              <span className={inst.isPositive ? 'badge-gain' : 'badge-loss'}>
                +₹30.00 ({inst.change})
              </span>
              <span style={{ fontSize: '12px', color: 'var(--color-ink-faint)' }}>Illustrative daily change</span>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '8px', fontSize: '12px' }}>
            {['1D', '1W', '1M', '6M', '1Y'].map((p) => (
              <button
                key={p}
                style={{
                  background: p === '1M' ? 'var(--color-cobalt-subtle)' : 'transparent',
                  color: p === '1M' ? 'var(--color-cobalt)' : 'var(--color-ink-muted)',
                  fontWeight: p === '1M' ? 600 : 400,
                  border: 'none',
                  padding: '4px 10px',
                  borderRadius: 'var(--radius-sm)',
                  cursor: 'pointer',
                }}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        {/* Chart & Quote Details Column */}
        <div style={{ display: 'grid', gridTemplateColumns: '1.8fr 1fr', gap: '56px', alignItems: 'start' }}>
          {/* Main Chart */}
          <div>
            <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>
              Price / INR
            </span>
            <div style={{ width: '100%', height: '260px', marginTop: '16px' }}>
              <svg viewBox="0 0 600 200" style={{ width: '100%', height: '100%', overflow: 'visible' }}>
                <line x1="0" y1="30" x2="600" y2="30" stroke="var(--color-border-subtle)" strokeWidth="1" strokeDasharray="3 3" />
                <line x1="0" y1="80" x2="600" y2="80" stroke="var(--color-border-subtle)" strokeWidth="1" strokeDasharray="3 3" />
                <line x1="0" y1="130" x2="600" y2="130" stroke="var(--color-border-subtle)" strokeWidth="1" strokeDasharray="3 3" />
                <line x1="0" y1="180" x2="600" y2="180" stroke="var(--color-border-subtle)" strokeWidth="1" strokeDasharray="3 3" />

                <text x="-40" y="34" fill="var(--color-ink-faint)" fontSize="10" fontFamily="var(--font-mono)">2,530</text>
                <text x="-40" y="84" fill="var(--color-ink-faint)" fontSize="10" fontFamily="var(--font-mono)">2,470</text>
                <text x="-40" y="134" fill="var(--color-ink-faint)" fontSize="10" fontFamily="var(--font-mono)">2,410</text>
                <text x="-40" y="184" fill="var(--color-ink-faint)" fontSize="10" fontFamily="var(--font-mono)">2,350</text>

                <polyline
                  fill="none"
                  stroke="var(--color-cobalt)"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  points="10,170 80,140 160,155 240,120 300,145 380,105 460,95 530,110 590,75"
                />
                <circle cx="590" cy="75" r="4" fill="var(--color-cobalt)" />
              </svg>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '16px', fontSize: '11px', color: 'var(--color-ink-muted)' }}>
                <span>16 Sep</span>
                <span>23 Sep</span>
                <span>30 Sep</span>
                <span>07 Oct</span>
                <span>16 Oct</span>
              </div>
            </div>
          </div>

          {/* Right Quote Details & Action Desk */}
          <div style={{ borderLeft: '1px solid var(--color-border-subtle)', paddingLeft: '40px' }}>
            <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-cobalt)', fontWeight: 600 }}>
              Quote Details
            </span>

            <div style={{ marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '20px', borderBottom: '1px solid var(--color-border)', paddingBottom: '24px', marginBottom: '28px' }}>
              <div>
                <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-ink-faint)', letterSpacing: '0.06em' }}>Provider</span>
                <div style={{ fontSize: '14px', fontWeight: 500, marginTop: '2px' }}>yfinance / NSE Adapter</div>
              </div>
              <div>
                <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-ink-faint)', letterSpacing: '0.06em' }}>Observed At</span>
                <div style={{ fontSize: '14px', fontWeight: 500, marginTop: '2px' }}>16 Oct 2026, 15:30 IST</div>
              </div>
              <div>
                <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-ink-faint)', letterSpacing: '0.06em' }}>History Basis</span>
                <div style={{ fontSize: '14px', fontWeight: 500, marginTop: '2px' }}>Daily closing observation</div>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <button onClick={() => onNavigate('alerts')} className="button-secondary" style={{ width: '100%', justifyContent: 'space-between' }}>
                <span>Set price alert</span>
                <span>→</span>
              </button>
              <button onClick={() => onNavigate('practice')} className="button-primary" style={{ width: '100%', justifyContent: 'space-between' }}>
                <span>Practice a trade</span>
                <span>→</span>
              </button>
              <span style={{ fontSize: '11px', color: 'var(--color-ink-faint)', textAlign: 'center', marginTop: '4px' }}>
                Virtual funds only.
              </span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Screen 05 / 07: Watchlist Overview Table
  return (
    <div style={{ maxWidth: '1240px', margin: '0 auto' }}>
      <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-cobalt)', fontWeight: 600 }}>
        Markets
      </span>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginTop: '8px', marginBottom: '28px' }}>
        <div>
          <h1 style={{ fontSize: '40px', lineHeight: 1.15, margin: 0 }}>
            Keep an eye on what matters.
          </h1>
          <p style={{ color: 'var(--color-ink-muted)', fontSize: '14px', marginTop: '4px' }}>
            Illustrative NSE equity watchlist. Prices below are genuine daily observations.
          </p>
        </div>

        {/* Search Input */}
        <div style={{ position: 'relative', width: '280px' }}>
          <input
            type="text"
            placeholder="Search name or symbol ↗"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '9px 14px',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'transparent',
              fontFamily: 'var(--font-sans)',
              fontSize: '13px',
              color: 'var(--color-ink)',
            }}
          />
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '28px', borderBottom: '1px solid var(--color-border)', marginBottom: '24px' }}>
        <button
          onClick={() => setActiveTab('watchlist')}
          style={{
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'watchlist' ? '2px solid var(--color-cobalt)' : '2px solid transparent',
            color: activeTab === 'watchlist' ? 'var(--color-ink)' : 'var(--color-ink-muted)',
            fontWeight: activeTab === 'watchlist' ? 600 : 400,
            fontSize: '14px',
            paddingBottom: '12px',
            cursor: 'pointer',
          }}
        >
          Your watchlist
        </button>
        <button
          onClick={() => setActiveTab('all')}
          style={{
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'all' ? '2px solid var(--color-cobalt)' : '2px solid transparent',
            color: activeTab === 'all' ? 'var(--color-ink)' : 'var(--color-ink-muted)',
            fontWeight: activeTab === 'all' ? 600 : 400,
            fontSize: '14px',
            paddingBottom: '12px',
            cursor: 'pointer',
          }}
        >
          All instruments
        </button>
      </div>

      {/* Watchlist Table */}
      <div style={{ width: '100%', overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--color-border)', fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>
              <th style={{ padding: '12px 16px', fontWeight: 500 }}>Instrument</th>
              <th style={{ padding: '12px 16px', fontWeight: 500 }}>Price / INR</th>
              <th style={{ padding: '12px 16px', fontWeight: 500 }}>Day Change</th>
              <th style={{ padding: '12px 16px', fontWeight: 500 }}>Illustrative Trend</th>
              <th style={{ padding: '12px 16px', fontWeight: 500, textAlign: 'right' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {instruments.map((inst) => (
              <tr
                key={inst.symbol}
                onClick={() => setSelectedSymbol(inst.symbol)}
                style={{
                  borderBottom: '1px solid var(--color-border-subtle)',
                  cursor: 'pointer',
                  transition: 'background-color var(--transition-fast)',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--color-paper-subtle)')}
                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
              >
                <td style={{ padding: '18px 16px', display: 'flex', alignItems: 'center', gap: '14px' }}>
                  <div
                    style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: 'var(--radius-sm)',
                      backgroundColor: 'var(--color-paper-subtle)',
                      border: '1px solid var(--color-border)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontFamily: 'var(--font-serif)',
                      fontSize: '15px',
                      color: 'var(--color-cobalt)',
                      fontWeight: 600,
                    }}
                  >
                    {inst.avatar}
                  </div>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '15px' }}>{inst.symbol}</div>
                    <div style={{ fontSize: '12px', color: 'var(--color-ink-muted)' }}>{inst.name}</div>
                  </div>
                </td>
                <td style={{ padding: '18px 16px', fontFamily: 'var(--font-mono)', fontSize: '15px' }}>
                  ₹{inst.price}
                </td>
                <td style={{ padding: '18px 16px' }}>
                  <span className={inst.isPositive ? 'badge-gain' : 'badge-loss'}>
                    {inst.change}
                  </span>
                </td>
                <td style={{ padding: '18px 16px' }}>
                  <svg width="75" height="20" style={{ overflow: 'visible' }}>
                    <path
                      d={inst.sparkline}
                      fill="none"
                      stroke={inst.isPositive ? 'var(--color-gain)' : 'var(--color-loss)'}
                      strokeWidth="1.5"
                    />
                  </svg>
                </td>
                <td style={{ padding: '18px 16px', textAlign: 'right', fontSize: '13px', color: 'var(--color-ink-muted)' }}>
                  <span>EOD 16 Oct →</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: '24px', fontSize: '12px', color: 'var(--color-ink-faint)' }}>
        Source + observation time + retrieved time are shown when real provider data is connected.
      </div>
    </div>
  );
};
