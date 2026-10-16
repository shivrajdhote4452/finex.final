import React, { useState } from 'react';

export const GoalsScreen: React.FC = () => {
  const [selectedGoal, setSelectedGoal] = useState<'emergency' | 'laptop' | 'education'>('laptop');
  const [monthlyContribution, setMonthlyContribution] = useState<number>(5000);
  const [expectedAnnualRate, setExpectedAnnualRate] = useState<number>(7.0);

  const goals = {
    emergency: { name: 'Emergency Liquid Reserve', current: 60000, target: 100000, horizonMonths: 8 },
    laptop: { name: 'Professional Workstation Laptop', current: 30000, target: 75000, horizonMonths: 9 },
    education: { name: 'Higher Education & Certification', current: 50000, target: 500000, horizonMonths: 36 },
  };

  const active = goals[selectedGoal];
  const remaining = Math.max(0, active.target - active.current);
  const progressPct = Math.min(100, Math.round((active.current / active.target) * 100));

  // Deterministic Goal Math: Monthly effective rate
  const monthlyRate = Math.pow(1 + expectedAnnualRate / 100, 1 / 12) - 1;
  const n = active.horizonMonths;
  const P = active.current;
  const C = monthlyContribution;

  const futureValue =
    monthlyRate > 0
      ? Math.round(P * Math.pow(1 + monthlyRate, n) + C * ((Math.pow(1 + monthlyRate, n) - 1) / monthlyRate))
      : Math.round(P + n * C);

  const monthsToTarget = Math.ceil(remaining / (monthlyContribution || 1));

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '32px' }}>
      {/* Header */}
      <div>
        <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-primary)', fontWeight: 600 }}>
          Deterministic Wealth Planning
        </span>
        <h1 style={{ fontSize: '36px', fontWeight: 700, color: '#FFFFFF', marginTop: '4px', letterSpacing: '-0.02em' }}>
          Financial Goals & Compounding Scenarios
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
          Simulates future value projections using mathematical compounding formulas without speculative AI guesswork.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1.6fr', gap: '32px', alignItems: 'start' }}>
        {/* Left Column: Active Goals */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {(['emergency', 'laptop', 'education'] as const).map((key) => {
            const g = goals[key];
            const isSelected = selectedGoal === key;
            const pct = Math.min(100, Math.round((g.current / g.target) * 100));

            return (
              <div
                key={key}
                onClick={() => setSelectedGoal(key)}
                className={`glass-card ${isSelected ? '' : 'glass-card-interactive'}`}
                style={{
                  padding: '24px',
                  border: isSelected ? '1px solid var(--border-active)' : '1px solid var(--border-subtle)',
                  background: isSelected ? 'rgba(59, 130, 246, 0.08)' : 'var(--bg-card)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <strong style={{ fontSize: '16px', color: '#FFFFFF' }}>{g.name}</strong>
                  <span className="badge badge-cyan">{pct}% Funded</span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', color: 'var(--text-muted)', marginBottom: '10px' }}>
                  <span>Current: ₹{g.current.toLocaleString('en-IN')}</span>
                  <span>Target: ₹{g.target.toLocaleString('en-IN')}</span>
                </div>

                {/* Progress bar */}
                <div style={{ width: '100%', height: '6px', borderRadius: '3px', backgroundColor: 'rgba(255, 255, 255, 0.08)', overflow: 'hidden' }}>
                  <div style={{ width: `${pct}%`, height: '100%', background: 'linear-gradient(90deg, #3B82F6, #06B6D4)' }} />
                </div>
              </div>
            );
          })}
        </div>

        {/* Right Column: Interactive Scenario Calculator */}
        <div className="glass-card" style={{ padding: '32px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
            <div>
              <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-primary)', fontWeight: 600 }}>
                Interactive Projection
              </span>
              <h2 style={{ fontSize: '24px', fontWeight: 700, color: '#FFFFFF', marginTop: '2px' }}>
                {active.name}
              </h2>
            </div>
            <div className="badge badge-virtual">Scenario Model v1</div>
          </div>

          {/* Target & Gap */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '28px' }}>
            <div style={{ padding: '16px', borderRadius: 'var(--radius-sm)', backgroundColor: 'rgba(0, 0, 0, 0.25)', border: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Funding Gap</span>
              <div className="tabular-nums" style={{ fontSize: '26px', fontWeight: 700, color: '#FFFFFF', marginTop: '4px' }}>
                ₹{remaining.toLocaleString('en-IN')}
              </div>
            </div>

            <div style={{ padding: '16px', borderRadius: 'var(--radius-sm)', backgroundColor: 'rgba(0, 0, 0, 0.25)', border: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Est. Completion</span>
              <div className="tabular-nums" style={{ fontSize: '26px', fontWeight: 700, color: 'var(--color-profit)', marginTop: '4px' }}>
                {monthsToTarget} Months
              </div>
            </div>
          </div>

          {/* Sliders */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', borderTop: '1px solid var(--border-subtle)', paddingTop: '24px', marginBottom: '28px' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <label style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Monthly Contribution (INR)</label>
                <strong className="tabular-nums" style={{ color: '#FFFFFF' }}>₹{monthlyContribution.toLocaleString('en-IN')}</strong>
              </div>
              <input
                type="range"
                min="1000"
                max="30000"
                step="500"
                value={monthlyContribution}
                onChange={(e) => setMonthlyContribution(parseInt(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--color-primary)' }}
              />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <label style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Expected Annual Return (%)</label>
                <strong className="tabular-nums" style={{ color: '#FFFFFF' }}>{expectedAnnualRate}%</strong>
              </div>
              <input
                type="range"
                min="0"
                max="15"
                step="0.5"
                value={expectedAnnualRate}
                onChange={(e) => setExpectedAnnualRate(parseFloat(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--color-accent-cyan)' }}
              />
            </div>
          </div>

          {/* Calculated Future Projection */}
          <div
            style={{
              padding: '20px',
              borderRadius: 'var(--radius-sm)',
              background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.12) 0%, rgba(6, 182, 212, 0.08) 100%)',
              border: '1px solid rgba(59, 130, 246, 0.3)',
              marginBottom: '20px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-accent-cyan)', fontWeight: 600 }}>
                  Projected Value in {n} Months
                </span>
                <div className="tabular-nums" style={{ fontSize: '32px', fontWeight: 800, color: '#FFFFFF', marginTop: '2px' }}>
                  ₹{futureValue.toLocaleString('en-IN')}
                </div>
              </div>
              {futureValue >= active.target && (
                <span className="badge badge-profit" style={{ fontSize: '12px' }}>
                  Target Achieved!
                </span>
              )}
            </div>
            <p style={{ fontSize: '11px', color: 'var(--text-faint)', marginTop: '8px' }}>
              Formula: P(1+i)ⁿ + C((1+i)ⁿ - 1)/i with monthly effective compounding.
            </p>
          </div>

          <button className="btn btn-primary" style={{ width: '100%', padding: '12px' }}>
            Record Virtual Contribution of ₹{monthlyContribution.toLocaleString('en-IN')} →
          </button>
        </div>
      </div>
    </div>
  );
};
