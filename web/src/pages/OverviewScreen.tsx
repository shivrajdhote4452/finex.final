import React from 'react';
import { NavigationTab } from '../components/layout/AppShell';

interface OverviewScreenProps {
  onNavigate: (tab: NavigationTab) => void;
}

export const OverviewScreen: React.FC<OverviewScreenProps> = ({ onNavigate }) => {
  return (
    <div style={{ maxWidth: '1240px', margin: '0 auto' }}>
      {/* Date & Greeting */}
      <div style={{ marginBottom: '40px' }}>
        <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-cobalt)', fontWeight: 600 }}>
          Friday, 16 October
        </span>
        <h1 style={{ fontSize: '44px', lineHeight: 1.15, marginTop: '8px', marginBottom: '8px' }}>
          Good morning, Shivraj.
        </h1>
        <p style={{ color: 'var(--color-ink-muted)', fontSize: '15px' }}>
          Here is your practice portfolio at a glance.
        </p>
      </div>

      {/* Primary Metrics Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1.4fr 1fr 1fr',
          gap: '32px',
          borderBottom: '1px solid var(--color-border)',
          paddingBottom: '32px',
          marginBottom: '40px',
        }}
      >
        {/* Virtual Account Value */}
        <div>
          <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>
            Virtual Account Value
          </span>
          <div style={{ fontFamily: 'var(--font-serif)', fontSize: '52px', fontWeight: 400, color: 'var(--color-ink)', margin: '8px 0 12px 0', letterSpacing: '-0.02em' }}>
            ₹1,24,500
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span className="badge-gain">+₹5,500 unrealized</span>
            <span style={{ fontSize: '12px', color: 'var(--color-ink-faint)' }}>Illustrative data</span>
          </div>
        </div>

        {/* Holdings Value */}
        <div>
          <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>
            Holdings
          </span>
          <div style={{ fontFamily: 'var(--font-serif)', fontSize: '38px', fontWeight: 400, color: 'var(--color-ink)', marginTop: '16px' }}>
            ₹99,500
          </div>
        </div>

        {/* Virtual Cash */}
        <div>
          <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>
            Virtual Cash
          </span>
          <div style={{ fontFamily: 'var(--font-serif)', fontSize: '38px', fontWeight: 400, color: 'var(--color-ink)', marginTop: '16px' }}>
            ₹25,000
          </div>
        </div>
      </div>

      {/* Chart & Beside Explanation Section */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.8fr 1fr', gap: '56px', alignItems: 'start', marginBottom: '32px' }}>
        {/* Left Chart Area */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px', fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>
            <span>Account Value / INR</span>
            <span>May – Oct 2026</span>
          </div>

          {/* SVG Line Chart */}
          <div style={{ width: '100%', height: '240px', position: 'relative' }}>
            <svg viewBox="0 0 600 200" style={{ width: '100%', height: '100%', overflow: 'visible' }}>
              {/* Horizontal Reference Grid Lines */}
              <line x1="0" y1="20" x2="600" y2="20" stroke="var(--color-border-subtle)" strokeWidth="1" strokeDasharray="3 3" />
              <line x1="0" y1="70" x2="600" y2="70" stroke="var(--color-border-subtle)" strokeWidth="1" strokeDasharray="3 3" />
              <line x1="0" y1="120" x2="600" y2="120" stroke="var(--color-border-subtle)" strokeWidth="1" strokeDasharray="3 3" />
              <line x1="0" y1="170" x2="600" y2="170" stroke="var(--color-border-subtle)" strokeWidth="1" strokeDasharray="3 3" />

              {/* Y Axis Labels */}
              <text x="-40" y="24" fill="var(--color-ink-faint)" fontSize="10" fontFamily="var(--font-mono)">127,000</text>
              <text x="-40" y="74" fill="var(--color-ink-faint)" fontSize="10" fontFamily="var(--font-mono)">124,000</text>
              <text x="-40" y="124" fill="var(--color-ink-faint)" fontSize="10" fontFamily="var(--font-mono)">121,000</text>
              <text x="-40" y="174" fill="var(--color-ink-faint)" fontSize="10" fontFamily="var(--font-mono)">118,000</text>

              {/* Blue Value Trend Line */}
              <polyline
                fill="none"
                stroke="var(--color-cobalt)"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                points="10,165 110,150 210,170 310,135 410,145 490,110 540,120 590,90"
              />

              {/* Terminal End Point */}
              <circle cx="590" cy="90" r="4" fill="var(--color-cobalt)" />
            </svg>

            {/* X Axis Months */}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '16px', fontSize: '11px', color: 'var(--color-ink-muted)' }}>
              <span>May</span>
              <span>Jun</span>
              <span>Jul</span>
              <span>Aug</span>
              <span>Sep</span>
              <span>Oct</span>
            </div>
          </div>
        </div>

        {/* Right Editorial Insight (Worth a Closer Look) */}
        <div style={{ borderLeft: '1px solid var(--color-border-subtle)', paddingLeft: '40px' }}>
          <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-cobalt)', fontWeight: 600 }}>
            Worth a Closer Look
          </span>
          <div style={{ fontFamily: 'var(--font-serif)', fontSize: '56px', color: 'var(--color-ink)', margin: '16px 0 12px 0', fontWeight: 400 }}>
            36.2%
          </div>
          <p style={{ fontSize: '15px', color: 'var(--color-ink-muted)', lineHeight: 1.5, marginBottom: '24px' }}>
            of invested holdings are in TCS. Cash is excluded from this comparison.
          </p>
          <span
            onClick={() => onNavigate('ask-finex')}
            style={{ fontSize: '14px', color: 'var(--color-cobalt)', fontWeight: 500, cursor: 'pointer', textDecoration: 'none' }}
          >
            Understand concentration →
          </span>
        </div>
      </div>

      <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '16px', fontSize: '12px', color: 'var(--color-ink-faint)' }}>
        All values are illustrative. Account value includes holdings and virtual cash.
      </div>
    </div>
  );
};
