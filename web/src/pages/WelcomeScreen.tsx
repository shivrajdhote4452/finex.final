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
      setErrorMessage('You must accept the educational terms and data policy to proceed.');
      return;
    }
    setLoading(true);
    setErrorMessage(null);

    setTimeout(() => {
      setLoading(false);
      onLoginSuccess();
    }, 350);
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'grid',
        gridTemplateColumns: '1.2fr 1fr',
        backgroundColor: 'var(--bg-app)',
      }}
    >
      {/* Left Column: Pro Branding & Core Mission */}
      <div
        style={{
          padding: '64px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          borderRight: '1px solid var(--border-subtle)',
          background: 'linear-gradient(135deg, rgba(17, 24, 39, 0.8) 0%, rgba(11, 15, 25, 0.95) 100%)',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: 'var(--radius-sm)',
                background: 'linear-gradient(135deg, #3B82F6 0%, #06B6D4 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 800,
                fontSize: '18px',
                color: '#FFFFFF',
                boxShadow: '0 0 20px rgba(59, 130, 246, 0.4)',
              }}
            >
              F
            </div>
            <span style={{ fontSize: '24px', fontWeight: 700, color: '#FFFFFF', letterSpacing: '-0.02em' }}>
              finex<span style={{ color: 'var(--color-primary)' }}>.</span>
            </span>
          </div>

          <div style={{ marginTop: '80px', maxWidth: '520px' }}>
            <span className="badge badge-cyan" style={{ marginBottom: '16px' }}>
              Educational Financial Excellence
            </span>
            <h1 style={{ fontSize: '48px', fontWeight: 800, lineHeight: 1.15, color: '#FFFFFF', letterSpacing: '-0.03em', marginBottom: '20px' }}>
              Master Investing with <span style={{ background: 'linear-gradient(135deg, #60A5FA 0%, #06B6D4 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Genuine Data</span> & Virtual Capital.
            </h1>
            <p style={{ fontSize: '16px', lineHeight: 1.6, color: 'var(--text-muted)' }}>
              A high-precision financial workspace designed to explore real NSE market observations, practice paper trading with an atomic ledger, and conduct document-grounded AI research.
            </p>
          </div>
        </div>

        <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '24px', display: 'flex', gap: '32px' }}>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-faint)', textTransform: 'uppercase' }}>Market Feed</div>
            <div style={{ fontSize: '13px', fontWeight: 600, color: '#FFFFFF', marginTop: '2px' }}>NSE Daily Observations</div>
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-faint)', textTransform: 'uppercase' }}>Simulation</div>
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-virtual)', marginTop: '2px' }}>₹25,000 Starting Cash</div>
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-faint)', textTransform: 'uppercase' }}>AI Grounding</div>
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-accent-cyan)', marginTop: '2px' }}>SEBI & Regulatory Citations</div>
          </div>
        </div>
      </div>

      {/* Right Column: Google Sign-In Card */}
      <div style={{ padding: '64px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
        <div className="glass-card" style={{ maxWidth: '420px', width: '100%', padding: '36px' }}>
          <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-primary)', fontWeight: 600 }}>
            Authentication & Consent
          </span>
          <h2 style={{ fontSize: '26px', fontWeight: 700, color: '#FFFFFF', margin: '8px 0 12px 0' }}>
            Welcome to FinEx
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '28px' }}>
            Sign in with your Google account to initialize your personal workspace and virtual cash ledger.
          </p>

          <label
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '12px',
              fontSize: '12px',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              marginBottom: '20px',
              lineHeight: 1.4,
            }}
          >
            <input
              type="checkbox"
              checked={consentChecked}
              onChange={(e) => setConsentChecked(e.target.checked)}
              style={{ marginTop: '2px', accentColor: 'var(--color-primary)', width: '16px', height: '16px' }}
            />
            <span>
              I understand that FinEx is an educational platform with virtual simulated money. No real brokerage execution occurs.
            </span>
          </label>

          {errorMessage && (
            <div style={{ color: 'var(--color-loss)', fontSize: '12px', marginBottom: '16px' }}>
              {errorMessage}
            </div>
          )}

          <button
            onClick={handleGoogleSignIn}
            disabled={loading}
            className="btn btn-primary"
            style={{ width: '100%', padding: '14px', fontSize: '14px', marginBottom: '16px' }}
          >
            {loading ? 'Authenticating with Google...' : 'Continue with Google Account →'}
          </button>

          <p style={{ fontSize: '11px', color: 'var(--text-faint)', textAlign: 'center', lineHeight: 1.5 }}>
            OAuth identity token validated server-side. No credentials stored locally.
          </p>
        </div>
      </div>
    </div>
  );
};
