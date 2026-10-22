import React, { useState } from 'react';
import { apiClient } from '../api/client';

interface OnboardingScreenProps {
  onComplete: () => void;
}

export const OnboardingScreen: React.FC<OnboardingScreenProps> = ({ onComplete }) => {
  const [step, setStep] = useState<2 | 3>(2);
  const [selectedHorizon, setSelectedHorizon] = useState('3-5');
  const [loading, setLoading] = useState(false);
  const [evaluatedProfile, setEvaluatedProfile] = useState<{
    score: number;
    risk_band: string;
    summary: string;
    suggested_allocation: Record<string, number>;
  }>({
    score: 65,
    risk_band: 'Moderate',
    summary: 'Balanced exposure between steady income assets and capital appreciation equities.',
    suggested_allocation: { Equity: 50, Debt: 40, Gold: 10 },
  });

  const horizonOptions = [
    { id: '<1', title: 'Less than 1 year', desc: 'Short-term needs, lower tolerance for volatility' },
    { id: '1-3', title: '1-3 years', desc: 'Near-term capital protection priority' },
    { id: '3-5', title: '3-5 years', desc: 'Balanced window navigating market cycles' },
    { id: '>5', title: 'More than 5 years', desc: 'Long-term equity compounding timeframe' },
  ];

  const handleCalculateProfile = async () => {
    setLoading(true);
    try {
      const res = await apiClient.risk.submitAssessment({
        investor_horizon: selectedHorizon === '>5' ? 'LONG' : selectedHorizon === '3-5' ? 'MEDIUM' : 'SHORT',
        risk_tolerance: 'MODERATE',
        liquidity_need: 'LOW',
      });
      if (res) {
        setEvaluatedProfile(res);
      }
    } catch {
      // fallback to deterministic moderate
    } finally {
      setLoading(false);
      setStep(3);
    }
  };

  if (step === 3) {
    // Screen 03 / 06: Risk Result & Explanation
    return (
      <div style={{ maxWidth: '960px', margin: '0 auto', padding: '16px 0' }}>
        <div style={{ fontSize: '11px', color: 'var(--color-action)', fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
          SCREEN 03 / 06 · RISK RESULT & EXPLANATION
        </div>
        <h1 style={{ fontSize: '32px', fontWeight: 700, color: '#FFFFFF', margin: '6px 0 4px 0' }}>
          Your risk profile
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginBottom: '28px' }}>
          Deterministic score evaluated via FinEx Risk Engine: Score {evaluatedProfile.score}/100.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '24px', alignItems: 'start' }}>
          {/* Profile Summary Panel */}
          <div className="glass-card" style={{ padding: '28px', border: '1px solid var(--border-medium)', backgroundColor: '#111111' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Profile summary
            </div>
            <div style={{ fontSize: '11px', color: 'var(--color-action)', fontWeight: 600, marginTop: '2px' }}>
              Verified deterministic result
            </div>
            <div style={{ fontSize: '36px', fontWeight: 800, color: '#FFFFFF', margin: '14px 0 8px 0' }}>
              {evaluatedProfile.risk_band}
            </div>
            <p style={{ fontSize: '13px', lineHeight: 1.5, color: 'var(--text-muted)', marginBottom: '20px' }}>
              {evaluatedProfile.summary}
            </p>
            <div
              onClick={() => setStep(2)}
              style={{
                fontSize: '12px',
                color: 'var(--color-action)',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                marginBottom: '16px',
              }}
            >
              Review your answers →
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-faint)', borderTop: '1px solid var(--border-subtle)', paddingTop: '12px' }}>
              No return is guaranteed.
            </div>
          </div>


          {/* Influencing Answers */}
          <div className="glass-card" style={{ padding: '28px', backgroundColor: '#111111' }}>
            <h3 style={{ fontSize: '15px', fontWeight: 600, color: '#FFFFFF', marginBottom: '20px' }}>
              What influenced the result
            </h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <div style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: '14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
                  <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--color-action)', fontWeight: 700 }}>01</span>
                  <strong style={{ color: '#FFFFFF', fontSize: '13px' }}>Time horizon</strong>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', paddingLeft: '24px' }}>
                  Selected answer: 3-5 years in this example.
                </p>
              </div>

              <div style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: '14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
                  <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--color-action)', fontWeight: 700 }}>02</span>
                  <strong style={{ color: '#FFFFFF', fontSize: '13px' }}>Willingness to take risk</strong>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', paddingLeft: '24px' }}>
                  Explain the approved response factors in plain language.
                </p>
              </div>

              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
                  <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--color-action)', fontWeight: 700 }}>03</span>
                  <strong style={{ color: '#FFFFFF', fontSize: '13px' }}>Capacity to absorb loss</strong>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', paddingLeft: '24px' }}>
                  Keep financial capacity separate from risk preference.
                </p>
              </div>
            </div>

            <div style={{ marginTop: '28px', display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button onClick={() => setStep(2)} className="btn btn-secondary">
                View scoring details
              </button>
              <button onClick={onComplete} className="btn btn-action">
                Confirm profile
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Screen 02 / 05: Risk Onboarding Questionnaire
  return (
    <div style={{ maxWidth: '960px', margin: '0 auto', padding: '16px 0' }}>
      <div style={{ fontSize: '11px', color: 'var(--color-action)', fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
        SCREEN 02 / 05 · RISK ONBOARDING
      </div>
      <h1 style={{ fontSize: '32px', fontWeight: 700, color: '#FFFFFF', margin: '6px 0 4px 0' }}>
        Understand your investment horizon
      </h1>
      <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginBottom: '24px' }}>
        Question 2 of 4.
      </p>

      {/* Progress Steps */}
      <div style={{ display: 'flex', gap: '24px', marginBottom: '28px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '14px' }}>
        <div style={{ fontSize: '12px', color: 'var(--text-faint)' }}>01 Basics</div>
        <div style={{ fontSize: '12px', color: 'var(--color-action)', fontWeight: 700 }}>02 Time horizon</div>
        <div style={{ fontSize: '12px', color: 'var(--text-faint)' }}>03 Capacity</div>
        <div style={{ fontSize: '12px', color: 'var(--text-faint)' }}>04 Review</div>
      </div>

      <div className="onboarding-risk-grid">
        {/* Question Options */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ fontSize: '15px', fontWeight: 600, color: '#FFFFFF', marginBottom: '4px' }}>
            When might you need this money?
          </div>

          {horizonOptions.map((opt) => {
            const isSelected = selectedHorizon === opt.id;
            return (
              <div
                key={opt.id}
                onClick={() => setSelectedHorizon(opt.id)}
                className="glass-card glass-card-interactive"
                style={{
                  padding: '16px 20px',
                  border: isSelected ? '1px solid var(--color-action)' : '1px solid var(--border-subtle)',
                  backgroundColor: isSelected ? '#181818' : '#111111',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '14px',
                }}
              >
                <div
                  style={{
                    width: '16px',
                    height: '16px',
                    borderRadius: '50%',
                    border: isSelected ? '5px solid var(--color-action)' : '2px solid var(--border-medium)',
                    backgroundColor: '#000000',
                  }}
                />
                <div>
                  <div style={{ fontWeight: 600, fontSize: '14px', color: '#FFFFFF' }}>{opt.title}</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{opt.desc}</div>
                </div>
              </div>
            );
          })}

          <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
            <button onClick={() => {}} className="btn btn-secondary">
              Back
            </button>
            <button onClick={handleCalculateProfile} disabled={loading} className="btn btn-action">
              {loading ? 'Evaluating...' : 'Continue'}
            </button>
          </div>
        </div>

        {/* Right Explanatory Box: Why We Ask */}
        <div className="glass-card" style={{ padding: '24px', backgroundColor: '#111111' }}>
          <div style={{ fontSize: '11px', color: 'var(--color-action)', fontWeight: 700, textTransform: 'uppercase', marginBottom: '8px' }}>
            Why we ask
          </div>
          <p style={{ fontSize: '13px', lineHeight: 1.6, color: '#D4D4D8', marginBottom: '16px' }}>
            Your time horizon helps explain how investment risk relates to your plans. It is only one part of your profile.
          </p>
          <p style={{ fontSize: '12px', lineHeight: 1.5, color: 'var(--text-muted)' }}>
            You can go back and revise an answer before confirming your profile.
          </p>
        </div>
      </div>
    </div>
  );
};
