import React, { useState } from 'react';

export const GoalsScreen: React.FC = () => {
  const [selectedGoalId, setSelectedGoalId] = useState('02');

  const goals = [
    { id: '01', name: 'Emergency fund', saved: '60,000', target: '1,00,000', pct: 60, color: 'var(--color-cobalt)' },
    { id: '02', name: 'New laptop', saved: '30,000', target: '75,000', pct: 40, color: '#162032' },
    { id: '03', name: 'Higher education', saved: '50,000', target: '5,00,000', pct: 10, color: 'var(--color-loss)' },
  ];

  return (
    <div style={{ maxWidth: '1240px', margin: '0 auto' }}>
      <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-cobalt)', fontWeight: 600 }}>
        Goals
      </span>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginTop: '8px', marginBottom: '32px' }}>
        <div>
          <h1 style={{ fontSize: '40px', lineHeight: 1.15, margin: 0 }}>Give your plans a place to grow.</h1>
          <p style={{ color: 'var(--color-ink-muted)', fontSize: '14px', marginTop: '4px' }}>
            Track actual contributions and label every future scenario.
          </p>
        </div>
        <button className="button-primary" style={{ padding: '10px 20px', fontSize: '13px' }}>
          New goal →
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1.2fr', gap: '56px', alignItems: 'start' }}>
        {/* Left Goal List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
          {goals.map((g) => {
            const isSelected = selectedGoalId === g.id;
            return (
              <div
                key={g.id}
                onClick={() => setSelectedGoalId(g.id)}
                style={{
                  border: isSelected ? '1px solid var(--color-cobalt)' : '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '24px',
                  backgroundColor: isSelected ? 'var(--color-paper-elevated)' : 'transparent',
                  cursor: 'pointer',
                  transition: 'border-color var(--transition-fast)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px' }}>
                    <span style={{ fontFamily: 'var(--font-serif)', fontSize: '20px', color: 'var(--color-cobalt)' }}>
                      {g.id}
                    </span>
                    <strong style={{ fontSize: '18px', fontWeight: 600 }}>{g.name}</strong>
                  </div>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 600 }}>
                    {g.pct}%
                  </span>
                </div>

                <div style={{ fontSize: '13px', color: 'var(--color-ink-muted)', marginBottom: '12px' }}>
                  ₹{g.saved} / ₹{g.target}
                </div>

                {/* Progress bar */}
                <div style={{ width: '100%', height: '4px', backgroundColor: 'var(--color-border)', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{ width: `${g.pct}%`, height: '100%', backgroundColor: g.color }} />
                </div>
              </div>
            );
          })}
        </div>

        {/* Right Selected Goal Scenario Card */}
        <div style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '36px', backgroundColor: 'var(--color-paper-subtle)' }}>
          <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>
            Selected Goal
          </span>

          <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '38px', margin: '12px 0 24px 0' }}>
            Your next laptop.
          </h2>

          {/* Simple object outline drawing (Screen 12 of PDF) */}
          <div style={{ display: 'flex', justifyContent: 'center', margin: '20px 0' }}>
            <svg width="180" height="110" viewBox="0 0 180 110" fill="none" stroke="var(--color-ink)" strokeWidth="1.5">
              <rect x="25" y="10" width="130" height="80" rx="4" fill="#FFFFFF" />
              <line x1="5" y1="95" x2="175" y2="95" strokeWidth="2.5" strokeLinecap="round" />
            </svg>
          </div>

          <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '20px', marginBottom: '24px' }}>
            <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-faint)' }}>Remaining</span>
            <div style={{ fontFamily: 'var(--font-serif)', fontSize: '42px', color: 'var(--color-ink)', margin: '6px 0 12px 0' }}>
              ₹45,000
            </div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-ink)' }}>
              If you set aside ₹5,000 each month…
            </div>
            <p style={{ fontSize: '13px', color: 'var(--color-ink-muted)', marginTop: '4px', lineHeight: 1.5 }}>
              9 contributions would close the gap. This simple scenario assumes no interest, fees or withdrawals.
            </p>
          </div>

          <button className="button-primary" style={{ width: '100%', padding: '12px 20px', fontSize: '14px' }}>
            Add contribution →
          </button>
        </div>
      </div>
    </div>
  );
};
