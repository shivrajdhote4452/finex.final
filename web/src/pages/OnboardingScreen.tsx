import React, { useState } from 'react';

interface OnboardingScreenProps {
  onComplete: () => void;
}

export const OnboardingScreen: React.FC<OnboardingScreenProps> = ({ onComplete }) => {
  const [step, setStep] = useState<2 | 3>(2);
  const [selectedHorizon, setSelectedHorizon] = useState('3-5');

  const horizonOptions = [
    { id: '<1', title: 'Less than 1 year', desc: 'Near-term needs' },
    { id: '1-3', title: '1-3 years', desc: 'A shorter horizon' },
    { id: '3-5', title: '3-5 years', desc: 'Some time to stay invested' },
    { id: '>5', title: 'More than 5 years', desc: 'A longer horizon' },
  ];

  if (step === 3) {
    // Screen 03 / 05: Risk result explained
    return (
      <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '24px 0' }}>
        <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-cobalt)', fontWeight: 600 }}>
          Your Profile / Review
        </span>
        <h1 style={{ fontSize: '38px', lineHeight: 1.2, marginTop: '8px', marginBottom: '8px' }}>
          Your risk profile, explained.
        </h1>
        <p style={{ color: 'var(--color-ink-muted)', fontSize: '14px', marginBottom: '40px' }}>
          Illustrated result only. The application uses your approved questionnaire responses.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: '48px', alignItems: 'start' }}>
          {/* Left Navy Card */}
          <div
            style={{
              backgroundColor: '#162032',
              color: '#FFFFFF',
              borderRadius: 'var(--radius-md)',
              padding: '36px',
            }}
          >
            <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', opacity: 0.7 }}>
              Illustrated Profile
            </span>
            <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '48px', color: '#FFFFFF', margin: '16px 0 20px 0', fontWeight: 400 }}>
              Moderate
            </h2>
            <p style={{ fontSize: '14px', lineHeight: 1.6, opacity: 0.85, marginBottom: '32px' }}>
              Your willingness to take risk and your capacity to absorb loss are assessed separately.
            </p>
            <span
              onClick={() => setStep(2)}
              style={{ fontSize: '13px', color: '#FFFFFF', textDecoration: 'underline', cursor: 'pointer' }}
            >
              Review your answers →
            </span>
          </div>

          {/* Right Explanation Column */}
          <div>
            <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-cobalt)', fontWeight: 600 }}>
              What Influenced This Result
            </span>

            <div style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '28px' }}>
              <div style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '20px' }}>
                <span style={{ fontFamily: 'var(--font-serif)', fontSize: '20px', color: 'var(--color-cobalt)', marginRight: '16px' }}>
                  01
                </span>
                <strong style={{ fontSize: '16px', fontWeight: 600 }}>Investment horizon</strong>
                <p style={{ color: 'var(--color-ink-muted)', fontSize: '14px', marginTop: '4px', marginLeft: '36px' }}>
                  Your selected answer: 3-5 years
                </p>
              </div>

              <div style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '20px' }}>
                <span style={{ fontFamily: 'var(--font-serif)', fontSize: '20px', color: 'var(--color-cobalt)', marginRight: '16px' }}>
                  02
                </span>
                <strong style={{ fontSize: '16px', fontWeight: 600 }}>Willingness to take risk</strong>
                <p style={{ color: 'var(--color-ink-muted)', fontSize: '14px', marginTop: '4px', marginLeft: '36px' }}>
                  Explained using approved questionnaire responses
                </p>
              </div>

              <div style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '20px' }}>
                <span style={{ fontFamily: 'var(--font-serif)', fontSize: '20px', color: 'var(--color-cobalt)', marginRight: '16px' }}>
                  03
                </span>
                <strong style={{ fontSize: '16px', fontWeight: 600 }}>Capacity to absorb loss</strong>
                <p style={{ color: 'var(--color-ink-muted)', fontSize: '14px', marginTop: '4px', marginLeft: '36px' }}>
                  Considered separately from personal preference
                </p>
              </div>
            </div>

            <p style={{ fontSize: '13px', color: 'var(--color-ink-muted)', margin: '32px 0 24px 0' }}>
              This describes a profile, not a promise of returns or a recommendation to buy any asset.
            </p>

            <button onClick={onComplete} className="button-primary" style={{ padding: '12px 28px', fontSize: '14px' }}>
              Confirm profile →
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Screen 02 / 04: Questionnaire Question 02
  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '24px 0' }}>
      <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-cobalt)', fontWeight: 600 }}>
        Your Profile / Question 02
      </span>
      <h1 style={{ fontSize: '38px', lineHeight: 1.2, marginTop: '8px', marginBottom: '8px' }}>
        When might you need this money?
      </h1>
      <p style={{ color: 'var(--color-ink-muted)', fontSize: '14px', marginBottom: '32px' }}>
        Choose the answer that best reflects your situation. You can change it later.
      </p>

      {/* Stepper */}
      <div style={{ display: 'flex', gap: '32px', borderBottom: '1px solid var(--color-border)', paddingBottom: '16px', marginBottom: '40px' }}>
        <span style={{ fontSize: '13px', color: 'var(--color-ink-faint)' }}>01 Basics</span>
        <span style={{ fontSize: '13px', color: 'var(--color-cobalt)', fontWeight: 600, borderBottom: '2px solid var(--color-cobalt)', paddingBottom: '16px', marginBottom: '-17px' }}>
          02 Time horizon
        </span>
        <span style={{ fontSize: '13px', color: 'var(--color-ink-faint)' }}>03 Capacity</span>
        <span style={{ fontSize: '13px', color: 'var(--color-ink-faint)' }}>04 Review</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '56px', alignItems: 'start' }}>
        {/* Left Options */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {horizonOptions.map((opt) => {
            const isSelected = selectedHorizon === opt.id;
            return (
              <div
                key={opt.id}
                onClick={() => setSelectedHorizon(opt.id)}
                style={{
                  border: isSelected ? '1px solid var(--color-cobalt)' : '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '16px 20px',
                  backgroundColor: isSelected ? 'var(--color-paper-elevated)' : 'transparent',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                  transition: 'border-color var(--transition-fast)',
                }}
              >
                <div
                  style={{
                    width: '18px',
                    height: '18px',
                    borderRadius: '50%',
                    border: isSelected ? '5px solid var(--color-cobalt)' : '1.5px solid var(--color-border)',
                    backgroundColor: '#FFFFFF',
                  }}
                />
                <div>
                  <div style={{ fontWeight: 600, fontSize: '15px' }}>{opt.title}</div>
                  <div style={{ fontSize: '13px', color: 'var(--color-ink-muted)' }}>{opt.desc}</div>
                </div>
              </div>
            );
          })}

          <div style={{ display: 'flex', gap: '16px', marginTop: '24px' }}>
            <button className="button-secondary" style={{ padding: '10px 20px' }}>
              ← Back
            </button>
            <button onClick={() => setStep(3)} className="button-primary" style={{ padding: '10px 24px' }}>
              Continue →
            </button>
          </div>
        </div>

        {/* Right Editorial Context Column */}
        <div style={{ borderLeft: '1px solid var(--color-border-subtle)', paddingLeft: '40px' }}>
          <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-cobalt)', fontWeight: 600 }}>
            Why This Matters
          </span>
          <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '32px', lineHeight: 1.25, margin: '12px 0 16px 0' }}>
            Time changes<br />
            <em style={{ fontStyle: 'italic' }}>the conversation.</em>
          </h2>
          <p style={{ color: 'var(--color-ink-muted)', fontSize: '14px', lineHeight: 1.6, marginBottom: '24px' }}>
            An investment horizon helps explain how risk relates to your plans. It does not determine your profile on its own.
          </p>
          <span style={{ fontSize: '13px', color: 'var(--color-cobalt)', fontWeight: 500, cursor: 'pointer' }}>
            About risk profiles →
          </span>
        </div>
      </div>
    </div>
  );
};
