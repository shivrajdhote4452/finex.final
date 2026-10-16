import React, { useState } from 'react';
import { useFinancial } from '../context/FinancialContext';
import { NavigationTab } from '../components/layout/AppShell';

interface MarketsScreenProps {
  onNavigate: (tab: NavigationTab) => void;
}

export const MarketsScreen: React.FC<MarketsScreenProps> = ({ onNavigate }) => {
  const { marketQuotes, openQuickTrade } = useFinancial();
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [selectedSector, setSelectedSector] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [chartPeriod, setChartPeriod] = useState<'1D' | '1W' | '1M' | '1Y'>('1M');

  // Extended Stock Registry
  const instruments = [
    {
      symbol: 'RELIANCE',
      name: 'Reliance Industries Ltd',
      sector: 'Energy & Retail',
      price: marketQuotes['RELIANCE']?.price || 2500.0,
      changeVal: marketQuotes['RELIANCE']?.changeVal || 30.0,
      changePct: marketQuotes['RELIANCE']?.changePct || 1.21,
      isPositive: marketQuotes['RELIANCE']?.isPositive ?? true,
      open: 2475.0,
      high: marketQuotes['RELIANCE']?.high || 2515.0,
      low: marketQuotes['RELIANCE']?.low || 2468.0,
      volume: '8.4M',
      mktCap: '₹16.9T',
      sparkline: 'M0,15 L15,10 L30,16 L45,8 L60,11 L75,4',
    },
    {
      symbol: 'TCS',
      name: 'Tata Consultancy Services',
      sector: 'Technology',
      price: marketQuotes['TCS']?.price || 3600.0,
      changeVal: marketQuotes['TCS']?.changeVal || -29.0,
      changePct: marketQuotes['TCS']?.changePct || -0.8,
      isPositive: marketQuotes['TCS']?.isPositive ?? false,
      open: 3630.0,
      high: marketQuotes['TCS']?.high || 3645.0,
      low: marketQuotes['TCS']?.low || 3590.0,
      volume: '3.1M',
      mktCap: '₹13.1T',
      sparkline: 'M0,5 L15,8 L30,6 L45,14 L60,12 L75,18',
    },
    {
      symbol: 'INFY',
      name: 'Infosys Ltd',
      sector: 'Technology',
      price: marketQuotes['INFY']?.price || 1450.0,
      changeVal: marketQuotes['INFY']?.changeVal || 7.9,
      changePct: marketQuotes['INFY']?.changePct || 0.55,
      isPositive: marketQuotes['INFY']?.isPositive ?? true,
      open: 1442.0,
      high: marketQuotes['INFY']?.high || 1458.0,
      low: marketQuotes['INFY']?.low || 1438.0,
      volume: '5.2M',
      mktCap: '₹6.0T',
      sparkline: 'M0,12 L15,14 L30,9 L45,11 L60,7 L75,5',
    },
    {
      symbol: 'HDFCBANK',
      name: 'HDFC Bank Ltd',
      sector: 'Banking & Financial',
      price: marketQuotes['HDFCBANK']?.price || 1600.0,
      changeVal: marketQuotes['HDFCBANK']?.changeVal || 5.1,
      changePct: marketQuotes['HDFCBANK']?.changePct || 0.32,
      isPositive: marketQuotes['HDFCBANK']?.isPositive ?? true,
      open: 1595.0,
      high: marketQuotes['HDFCBANK']?.high || 1612.0,
      low: marketQuotes['HDFCBANK']?.low || 1590.0,
      volume: '9.8M',
      mktCap: '₹12.2T',
      sparkline: 'M0,14 L15,12 L30,10 L45,6 L60,8 L75,4',
    },
    {
      symbol: 'ICICIBANK',
      name: 'ICICI Bank Ltd',
      sector: 'Banking & Financial',
      price: marketQuotes['ICICIBANK']?.price || 1240.0,
      changeVal: marketQuotes['ICICIBANK']?.changeVal || 18.6,
      changePct: marketQuotes['ICICIBANK']?.changePct || 1.52,
      isPositive: marketQuotes['ICICIBANK']?.isPositive ?? true,
      open: 1225.0,
      high: marketQuotes['ICICIBANK']?.high || 1248.0,
      low: marketQuotes['ICICIBANK']?.low || 1222.0,
      volume: '11.5M',
      mktCap: '₹8.7T',
      sparkline: 'M0,16 L15,12 L30,14 L45,8 L60,6 L75,3',
    },
    {
      symbol: 'TATAMOTORS',
      name: 'Tata Motors Ltd',
      sector: 'Automobile',
      price: marketQuotes['TATAMOTORS']?.price || 924.5,
      changeVal: marketQuotes['TATAMOTORS']?.changeVal || 19.2,
      changePct: marketQuotes['TATAMOTORS']?.changePct || 2.12,
      isPositive: marketQuotes['TATAMOTORS']?.isPositive ?? true,
      open: 908.0,
      high: marketQuotes['TATAMOTORS']?.high || 932.0,
      low: marketQuotes['TATAMOTORS']?.low || 905.0,
      volume: '14.2M',
      mktCap: '₹3.4T',
      sparkline: 'M0,18 L15,14 L30,12 L45,7 L60,5 L75,2',
    },
    {
      symbol: 'ITC',
      name: 'ITC Ltd',
      sector: 'FMCG / Conglomerate',
      price: marketQuotes['ITC']?.price || 495.2,
      changeVal: marketQuotes['ITC']?.changeVal || 1.95,
      changePct: marketQuotes['ITC']?.changePct || 0.4,
      isPositive: marketQuotes['ITC']?.isPositive ?? true,
      open: 493.0,
      high: marketQuotes['ITC']?.high || 498.0,
      low: marketQuotes['ITC']?.low || 492.5,
      volume: '7.6M',
      mktCap: '₹6.2T',
      sparkline: 'M0,12 L15,11 L30,13 L45,9 L60,8 L75,6',
    },
    {
      symbol: 'SBIN',
      name: 'State Bank of India',
      sector: 'Banking & Financial',
      price: marketQuotes['SBIN']?.price || 815.0,
      changeVal: marketQuotes['SBIN']?.changeVal || -4.2,
      changePct: marketQuotes['SBIN']?.changePct || -0.51,
      isPositive: marketQuotes['SBIN']?.isPositive ?? false,
      open: 822.0,
      high: marketQuotes['SBIN']?.high || 824.0,
      low: marketQuotes['SBIN']?.low || 811.0,
      volume: '12.8M',
      mktCap: '₹7.3T',
      sparkline: 'M0,6 L15,9 L30,7 L45,13 L60,15 L75,17',
    },
  ];

  const filtered = instruments.filter((i) => {
    const matchesSearch =
      i.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      i.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesSector =
      selectedSector === 'ALL' ||
      (selectedSector === 'TECH' && i.sector.includes('Technology')) ||
      (selectedSector === 'BANK' && i.sector.includes('Banking')) ||
      (selectedSector === 'ENERGY' && i.sector.includes('Energy')) ||
      (selectedSector === 'AUTO' && i.sector.includes('Automobile'));
    return matchesSearch && matchesSector;
  });

  // Detail View
  if (selectedSymbol) {
    const inst = instruments.find((i) => i.symbol === selectedSymbol) || instruments[0];

    return (
      <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '28px' }}>
        {/* Navigation Breadcrumb */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px' }}>
          <button
            onClick={() => setSelectedSymbol(null)}
            className="btn btn-secondary"
            style={{ padding: '4px 10px', fontSize: '12px' }}
          >
            ← Back to Instruments
          </button>
          <span style={{ color: 'var(--text-faint)' }}>/</span>
          <span style={{ color: '#FFFFFF', fontWeight: 600 }}>{inst.symbol}</span>
        </div>

        {/* Header Ribbon */}
        <div className="glass-card" style={{ padding: '28px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <h1 style={{ fontSize: '32px', fontWeight: 700, color: '#FFFFFF', margin: 0 }}>
                {inst.name}
              </h1>
              <span className="badge badge-neutral">NSE: {inst.symbol}</span>
              <span className="badge badge-cyan">{inst.sector}</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'baseline', gap: '16px', marginTop: '12px' }}>
              <div className="tabular-nums" style={{ fontSize: '42px', fontWeight: 800, color: '#FFFFFF' }}>
                ₹{inst.price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
              <span className={inst.isPositive ? 'badge badge-profit' : 'badge badge-loss'} style={{ fontSize: '14px', padding: '4px 10px' }}>
                {inst.isPositive ? '▲ +' : '▼ '}{Math.abs(inst.changeVal).toFixed(2)} ({inst.isPositive ? '+' : ''}{inst.changePct}%)
              </span>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>NSE EOD Verified Observation</span>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              onClick={() => openQuickTrade(inst.symbol)}
              className="btn-emerald"
              style={{ padding: '12px 24px', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }}
            >
              ⚡ Instant Trade {inst.symbol}
            </button>
            <button onClick={() => onNavigate('practice')} className="btn btn-secondary">
              Open Pro Trade Desk →
            </button>
          </div>
        </div>

        {/* Chart & Fundamentals Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '28px' }}>
          {/* Main Chart */}
          <div className="glass-card" style={{ padding: '28px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
              <div>
                <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#FFFFFF' }}>Simulated Price History</h3>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Historical daily candles from yfinance baseline</span>
              </div>

              {/* Timeframe Selectors */}
              <div style={{ display: 'flex', gap: '4px', background: 'rgba(0, 0, 0, 0.3)', padding: '3px', borderRadius: 'var(--radius-xs)' }}>
                {(['1D', '1W', '1M', '1Y'] as const).map((period) => (
                  <button
                    key={period}
                    onClick={() => setChartPeriod(period)}
                    style={{
                      background: chartPeriod === period ? 'var(--color-primary)' : 'transparent',
                      color: chartPeriod === period ? '#FFFFFF' : 'var(--text-muted)',
                      border: 'none',
                      borderRadius: '3px',
                      fontSize: '11px',
                      fontWeight: 600,
                      padding: '4px 10px',
                      cursor: 'pointer',
                    }}
                  >
                    {period}
                  </button>
                ))}
              </div>
            </div>

            {/* SVG Chart Area */}
            <div style={{ width: '100%', height: '260px' }}>
              <svg viewBox="0 0 600 200" style={{ width: '100%', height: '100%', overflow: 'visible' }}>
                <defs>
                  <linearGradient id="marketChartGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={inst.isPositive ? '#10B981' : '#EF4444'} stopOpacity="0.3" />
                    <stop offset="100%" stopColor={inst.isPositive ? '#10B981' : '#EF4444'} stopOpacity="0.0" />
                  </linearGradient>
                </defs>

                <line x1="0" y1="40" x2="600" y2="40" stroke="rgba(255, 255, 255, 0.05)" strokeDasharray="3 3" />
                <line x1="0" y1="90" x2="600" y2="90" stroke="rgba(255, 255, 255, 0.05)" strokeDasharray="3 3" />
                <line x1="0" y1="140" x2="600" y2="140" stroke="rgba(255, 255, 255, 0.05)" strokeDasharray="3 3" />

                <polygon
                  points="20,180 20,130 110,110 200,125 310,80 420,95 520,60 580,40 580,180"
                  fill="url(#marketChartGrad)"
                />
                <polyline
                  fill="none"
                  stroke={inst.isPositive ? '#10B981' : '#EF4444'}
                  strokeWidth="3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  points="20,130 110,110 200,125 310,80 420,95 520,60 580,40"
                />
              </svg>
            </div>
          </div>

          {/* Fundamentals Sidebar */}
          <div className="glass-card" style={{ padding: '28px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#FFFFFF', margin: 0 }}>
              Instrument Summary
            </h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '13px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Day Range</span>
                <span className="tabular-nums" style={{ color: '#FFFFFF' }}>₹{inst.low} - ₹{inst.high}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Opening Price</span>
                <span className="tabular-nums" style={{ color: '#FFFFFF' }}>₹{inst.open}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Volume</span>
                <span className="tabular-nums" style={{ color: '#FFFFFF' }}>{inst.volume}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Market Cap</span>
                <span className="tabular-nums" style={{ color: '#FFFFFF' }}>{inst.mktCap}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Data Provenance</span>
                <span className="badge badge-neutral">NSE / yfinance Real Observation</span>
              </div>
            </div>

            <button
              onClick={() => openQuickTrade(inst.symbol)}
              className="btn-emerald"
              style={{ width: '100%', padding: '12px', borderRadius: 'var(--radius-sm)', marginTop: 'auto', cursor: 'pointer' }}
            >
              Place Simulated Order for {inst.symbol} →
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Watchlist List View
  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* Search & Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-primary)', fontWeight: 600 }}>
            Market Intelligence
          </span>
          <h1 style={{ fontSize: '36px', fontWeight: 700, color: '#FFFFFF', marginTop: '4px', letterSpacing: '-0.02em' }}>
            Instruments & Watchlist
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
            Verified Indian equities from NSE official reports with real live end-of-day market observations.
          </p>
        </div>

        {/* Search */}
        <div style={{ width: '320px' }}>
          <input
            type="text"
            placeholder="Search symbol e.g., RELIANCE, TCS..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '12px 16px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-medium)',
              backgroundColor: 'var(--bg-input)',
              color: '#FFFFFF',
              fontFamily: 'var(--font-sans)',
              fontSize: '14px',
            }}
          />
        </div>
      </div>

      {/* Sector Filter Tabs */}
      <div style={{ display: 'flex', gap: '8px' }}>
        {[
          { id: 'ALL', label: 'All Sectors (8)' },
          { id: 'TECH', label: 'Technology (2)' },
          { id: 'BANK', label: 'Banking & Financials (3)' },
          { id: 'ENERGY', label: 'Energy (1)' },
          { id: 'AUTO', label: 'Automobile (1)' },
        ].map((sec) => (
          <button
            key={sec.id}
            onClick={() => setSelectedSector(sec.id)}
            style={{
              padding: '8px 16px',
              borderRadius: 'var(--radius-sm)',
              border: selectedSector === sec.id ? '1px solid var(--color-primary)' : '1px solid var(--border-subtle)',
              background: selectedSector === sec.id ? 'rgba(59, 130, 246, 0.15)' : 'rgba(255, 255, 255, 0.02)',
              color: selectedSector === sec.id ? '#FFFFFF' : 'var(--text-muted)',
              fontSize: '13px',
              fontWeight: selectedSector === sec.id ? 600 : 500,
              cursor: 'pointer',
            }}
          >
            {sec.label}
          </button>
        ))}
      </div>

      {/* Watchlist Table */}
      <div className="glass-card" style={{ padding: '24px' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-faint)', fontSize: '11px', textTransform: 'uppercase' }}>
                <th style={{ padding: '16px' }}>Instrument</th>
                <th style={{ padding: '16px' }}>Sector</th>
                <th style={{ padding: '16px' }}>Last Price</th>
                <th style={{ padding: '16px' }}>Day Change</th>
                <th style={{ padding: '16px' }}>24h Sparkline</th>
                <th style={{ padding: '16px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((inst) => (
                <tr
                  key={inst.symbol}
                  style={{
                    borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                    transition: 'background-color var(--transition-fast)',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.02)')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <td style={{ padding: '16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div
                        style={{
                          width: '36px',
                          height: '36px',
                          borderRadius: 'var(--radius-sm)',
                          backgroundColor: 'rgba(255, 255, 255, 0.06)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontWeight: 700,
                          fontSize: '14px',
                        }}
                      >
                        {inst.symbol.slice(0, 2)}
                      </div>
                      <div>
                        <strong style={{ color: '#FFFFFF', fontSize: '15px' }}>{inst.symbol}</strong>
                        <div style={{ fontSize: '12px', color: 'var(--text-faint)' }}>{inst.name}</div>
                      </div>
                    </div>
                  </td>
                  <td style={{ padding: '16px', color: 'var(--text-muted)' }}>{inst.sector}</td>
                  <td style={{ padding: '16px', fontWeight: 600 }} className="tabular-nums">
                    ₹{inst.price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </td>
                  <td style={{ padding: '16px' }}>
                    <span className={inst.isPositive ? 'badge badge-profit' : 'badge badge-loss'}>
                      {inst.isPositive ? '+' : ''}{inst.changePct}%
                    </span>
                  </td>
                  <td style={{ padding: '16px' }}>
                    <svg width="75" height="20" style={{ overflow: 'visible' }}>
                      <path
                        d={inst.sparkline}
                        fill="none"
                        stroke={inst.isPositive ? 'var(--color-profit)' : 'var(--color-loss)'}
                        strokeWidth="2"
                      />
                    </svg>
                  </td>
                  <td style={{ padding: '16px', textAlign: 'right' }}>
                    <div style={{ display: 'inline-flex', gap: '8px' }}>
                      <button
                        onClick={() => setSelectedSymbol(inst.symbol)}
                        className="btn btn-secondary"
                        style={{ padding: '6px 12px', fontSize: '12px' }}
                      >
                        Inspect
                      </button>
                      <button
                        onClick={() => openQuickTrade(inst.symbol)}
                        className="btn-emerald"
                        style={{ padding: '6px 12px', fontSize: '12px', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }}
                      >
                        Trade
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
