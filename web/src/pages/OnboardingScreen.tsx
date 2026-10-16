import React, { useState } from 'react';

interface OnboardingScreenProps {
  onComplete: () => void;
}

export const OnboardingScreen: React.FC<OnboardingScreenProps> = ({ onComplete }) => {
  const [step, setStep] = useState<2 | 3>(2);
  const [selectedHorizon, setSelectedHorizon] = useState('3-5');

  const horizonOptions = [
    { id: '<1', title: 'Less than 1 year', desc: 'Liquid, immediate capital requirements' },
    { id: '1-3', title: '1 – 3 years', desc: 'Short-term horizon with minimal drawdown tolerance' },
    { id: '3-5', title: '3 – 5 years', desc: 'Medium-term horizon; time to navigate market cycles' },
    { id: '>5', title: 'More than 5 years', desc: 'Long-term wealth building with compounding focus' },
  ];

  if (step === 3) {
    // Risk Profile Result Explained
    return (
      <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '32px 0' }}>
        <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-primary)', fontWeight: 600 }}>
          Deterministic Evaluation • Step 04 / 04
        </span>
        <h1 style={{ fontSize: '36px', fontWeight: 700, color: '#FFFFFF', margin: '8px 0' }}>
          Your Risk Profile, Grounded & Explained
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginBottom: '32px' }}>
          Derived strictly by the deterministic scoring engine. AI explains the outcome without altering calculations.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: '32px', alignItems: 'start' }}>
          {/* Left Result Card */}
          <div className="glass-card" style={{ padding: '36px', border: '1px solid var(--border-active)' }}>
            <span className="badge badge-cyan">Assessed Band</span>
            <h2 style={{ fontSize: '42px', fontWeight: 800, color: '#FFFFFF', margin: '16px 0 12px 0' }}>
              Moderate
            </h2>
            <p style={{ fontSize: '14px', lineHeight: 1.6, color: 'var(--text-muted)', marginBottom: '24px' }}>
              Your willingness to accept equity volatility is balanced with a disciplined capacity to absorb downside over a 3–5 year investment window.
            </p>
            <button onClick={() => setStep(2)} className="btn btn-secondary" style={{ width: '100%' }}>
              ← Review Answers
            </button>
          </div>

          {/* Right Breakdown */}
          <div className="glass-card" style={{ padding: '32px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#FFFFFF', marginBottom: '20px' }}>
              Influencing Factors Breakdown
            </h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <strong style={{ color: '#FFFFFF', fontSize: '14px' }}>01. Investment Horizon</strong>
                  <span className="badge badge-profit">3–5 Years</span>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  A medium horizon allows temporary market drawdowns to recover through equity cycles.
                </p>
              </div>

              <div style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <strong style={{ color: '#FFFFFF', fontSize: '14px' }}>02. Willingness to Take Risk</strong>
                  <span className="badge badge-cyan">Balanced (Score: 68/100)</span>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Psychological tolerance evaluated via questionnaire weighting version v1.0.
                </p>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <strong style={{ color: '#FFFFFF', fontSize: '14px' }}>03. Capacity to Absorb Loss</strong>
                  <span className="badge badge-virtual">Medium Buffer</span>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Assessed based on liquidity buffers and absence of high near-term debt liabilities.
                </p>
              </div>
            </div>

            <div style={{ marginTop: '28px', display: 'flex', justifyContent: 'flex-end' }}>
              <button onClick={onComplete} className="btn btn-primary" style={{ padding: '12px 28px', fontSize: '14px' }}>
                Confirm Profile & Enter Workspace →
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Question 02 View
  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '32px 0' }}>
      <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-primary)', fontWeight: 600 }}>
        Risk Assessment • Question 02 / 04
      </span>
      <h1 style={{ fontSize: '36px', fontWeight: 700, color: '#FFFFFF', margin: '8px 0' }}>
        What is your expected investment horizon?
      </h1>
      <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginBottom: '32px' }}>
        Select the timeframe when you anticipate needing to liquidate or access these funds.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '32px', alignItems: 'start' }}>
        {/* Options */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {horizonOptions.map((opt) => {
            const isSelected = selectedHorizon === opt.id;
            return (
              <div
                key={opt.id}
                onClick={() => setSelectedHorizon(opt.id)}
                className="glass-card glass-card-interactive"
                style={{
                  padding: '20px',
                  border: isSelected ? '1px solid var(--color-primary)' : '1px solid var(--border-subtle)',
                  background: isSelected ? 'rgba(59, 130, 246, 0.12)' : 'var(--bg-card)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                }}
              >
                <div
                  style={{
                    width: '20px',
                    height: '20px',
                    borderRadius: '50%',
                    border: isSelected ? '6px solid var(--color-primary)' : '2px solid var(--border-medium)',
                    backgroundColor: '#111827',
                  }}
                />
                <div>
                  <div style={{ fontWeight: 600, fontSize: '15px', color: '#FFFFFF' }}>{opt.title}</div>
                  <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>{opt.desc}</div>
                </div>
              </div>
            );
          })}

          <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
            <button onClick={() => setStep(3)} className="btn btn-primary" style={{ padding: '12px 28px' }}>
              Continue to Evaluation →
            </button>
          </div>
        </div>

        {/* Right Info Box */}
        <div className="glass-card" style={{ padding: '28px' }}>
          <span className="badge badge-cyan" style={{ marginBottom: '12px' }}>
            Why Horizon Matters
          </span>
          <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#FFFFFF', marginBottom: '8px' }}>
            Time Diversifies Volatility
          </h3>
          <p style={{ fontSize: '13px', lineHeight: 1.6, color: 'var(--text-muted)' }}>
            According to the Securities and Exchange Board of India (SEBI), short-term investments in equity carry high timing risk. Longer horizons afford portfolios the resilience to absorb downturns without forcing premature liquidations.
          </p>
        </div>
      </div>
    </div>
  );
};
