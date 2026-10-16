import React, { useState } from 'react';

interface WelcomeScreenProps {
  onLoginSuccess: () => void;
}

export const WelcomeScreen: React.FC<WelcomeScreenProps> = ({ onLoginSuccess }) => {
  const [consentChecked, setConsentChecked] = useState(true);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleGoogleSignIn = () => {
    if (!consentChecked) {
      setErrorMessage('You must accept the terms to continue.');
      return;
    }
    setLoading(true);
    setErrorMessage(null);

    // Call mock auth / Sprint 2 Google callback
    setTimeout(() => {
      setLoading(false);
      onLoginSuccess();
    }, 400);
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'grid',
        gridTemplateColumns: 'minmax(320px, 1fr) minmax(360px, 1fr)',
        backgroundColor: 'var(--color-paper)',
      }}
    >
      {/* Left Blue Hero Column */}
      <div
        style={{
          backgroundColor: 'var(--color-cobalt)',
          color: '#FFFFFF',
          padding: '64px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
        }}
      >
        <div>
          <span style={{ fontFamily: 'var(--font-serif)', fontSize: '32px', fontWeight: 600, letterSpacing: '-0.02em' }}>
            finex.
          </span>

          <div style={{ marginTop: '96px', maxWidth: '440px' }}>
            <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: '56px', lineHeight: 1.1, color: '#FFFFFF', marginBottom: '24px' }}>
              Start with<br />
              <em style={{ fontStyle: 'italic', fontWeight: 400 }}>understanding.</em>
            </h1>
            <p style={{ fontSize: '18px', lineHeight: 1.5, opacity: 0.9, fontWeight: 300 }}>
              A place to explore markets, ask better questions and practice with virtual money.
            </p>
          </div>
        </div>

        <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.2)', paddingTop: '24px' }}>
          <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', opacity: 0.8, display: 'block', marginBottom: '8px' }}>
            Your Financial Workspace
          </span>
          <p style={{ fontSize: '16px', fontWeight: 500 }}>
            Learn. Compare. Practice.
          </p>
        </div>
      </div>

      {/* Right Sign-in / Consent Column */}
      <div
        style={{
          padding: '64px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          backgroundColor: 'var(--color-paper)',
        }}
      >
        <div />

        <div style={{ maxWidth: '420px', margin: '0 auto', width: '100%' }}>
          <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-cobalt)', fontWeight: 600, display: 'block', marginBottom: '16px' }}>
            Welcome to FinEx
          </span>

          <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '42px', lineHeight: 1.15, color: 'var(--color-ink)', marginBottom: '16px' }}>
            Make yourself<br />
            <em style={{ fontStyle: 'italic' }}>at home.</em>
          </h2>

          <p style={{ color: 'var(--color-ink-muted)', fontSize: '15px', marginBottom: '32px' }}>
            Create your personal workspace with your Google account.
          </p>

          {/* Consent Checkbox */}
          <label
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '12px',
              fontSize: '13px',
              color: 'var(--color-ink)',
              cursor: 'pointer',
              marginBottom: '24px',
              lineHeight: 1.4,
            }}
          >
            <input
              type="checkbox"
              checked={consentChecked}
              onChange={(e) => setConsentChecked(e.target.checked)}
              style={{ marginTop: '2px', accentColor: 'var(--color-cobalt)', width: '16px', height: '16px' }}
            />
            <span>
              I agree to the Terms and Privacy Policy, and understand FinEx is an educational platform.
            </span>
          </label>

          {errorMessage && (
            <div style={{ color: 'var(--color-loss)', fontSize: '13px', marginBottom: '16px' }}>
              {errorMessage}
            </div>
          )}

          {/* Google Sign-in Button */}
          <button
            onClick={handleGoogleSignIn}
            disabled={loading}
            className="button-primary"
            style={{ width: '100%', padding: '14px 20px', fontSize: '15px', marginBottom: '24px' }}
          >
            {loading ? 'Signing in...' : 'Continue with Google →'}
          </button>

          <p style={{ fontSize: '12px', color: 'var(--color-ink-faint)', lineHeight: 1.5 }}>
            Virtual trading only. No real-money orders or brokerage connection are created.
          </p>
        </div>

        {/* Footer Links */}
        <div style={{ display: 'flex', gap: '24px', fontSize: '13px', color: 'var(--color-ink-faint)', justifyContent: 'center' }}>
          <span style={{ cursor: 'pointer' }}>Privacy policy</span>
          <span style={{ cursor: 'pointer' }}>Terms</span>
          <span style={{ cursor: 'pointer' }}>Need help?</span>
        </div>
      </div>
    </div>
  );
};
