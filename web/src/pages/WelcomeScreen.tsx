import React, { useState } from 'react';
import { apiClient } from '../api/client';

interface WelcomeScreenProps {
  onLoginSuccess: () => void;
}

declare global {
  interface Window {
    google?: any;
  }
}

export const WelcomeScreen: React.FC<WelcomeScreenProps> = ({ onLoginSuccess }) => {
  const [consentChecked, setConsentChecked] = useState(true);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const googleClientId =
    (import.meta as any).env?.VITE_GOOGLE_CLIENT_ID ||
    '71626572471-2333p55kgim64b3738oabca9l9ss9th0.apps.googleusercontent.com';

  React.useEffect(() => {
    if (window.google?.accounts?.id) {
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: async (response: { credential?: string }) => {
          if (!response?.credential) {
            setErrorMessage('Google Sign-In did not return an identity token.');
            return;
          }
          if (!consentChecked) {
            setErrorMessage('You must accept the Terms and Privacy Policy to proceed.');
            return;
          }
          setLoading(true);
          setErrorMessage(null);
          try {
            await apiClient.auth.googleLogin(response.credential);
            await apiClient.auth.recordConsent('v1.0');
            onLoginSuccess();
          } catch (err: any) {
            setErrorMessage(err?.message || 'Google token verification failed.');
          } finally {
            setLoading(false);
          }
        },
      });
    }
  }, [consentChecked, googleClientId]);

  const handleGoogleSignIn = async () => {
    if (!consentChecked) {
      setErrorMessage('You must accept the Terms and Privacy Policy to proceed.');
      return;
    }
    setLoading(true);
    setErrorMessage(null);

    const timer = setTimeout(() => {
      setLoading(false);
    }, 4000);

    try {
      if (window.google?.accounts?.id) {
        window.google.accounts.id.prompt((notification: any) => {
          clearTimeout(timer);
          if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
            setLoading(false);
          }
        });
      } else {
        clearTimeout(timer);
        throw new Error('Google Identity Services script is loading. Please try again.');
      }
    } catch (err: any) {
      clearTimeout(timer);
      setErrorMessage(err?.message || 'Google sign-in initialization failed.');
      setLoading(false);
    }
  };

  const handleDevLogin = async () => {
    if (!consentChecked) {
      setErrorMessage('You must accept the Terms and Privacy Policy to proceed.');
      return;
    }
    setLoading(true);
    setErrorMessage(null);
    try {
      await apiClient.auth.devLogin('shivraj.dhote@finex.internal', 'Shivraj Dhote');
      await apiClient.auth.recordConsent('v1.0');
      onLoginSuccess();
    } catch (err: any) {
      setErrorMessage(err?.message || 'Development login failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="welcome-container">
      {/* Left Column: Brand & Terminal Mission (Page 4 Screen 01) */}
      <div className="welcome-left-col">
        <div>
          {/* Logo Mark */}
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '3px' }}>
            <span style={{ fontSize: '28px', fontWeight: 900, color: '#FFFFFF', letterSpacing: '-0.03em' }}>Fin</span>
            <span style={{ fontSize: '28px', fontWeight: 900, color: 'var(--color-action)', letterSpacing: '-0.03em' }}>Ex</span>
          </div>

          <div className="welcome-mission-box" style={{ marginTop: '72px', maxWidth: '480px' }}>
            <h1 className="welcome-title">
              Learn the market.<br />Practice with intent.
            </h1>
            <p className="welcome-subtitle">
              A workspace for understanding your money, exploring evidence and practicing with virtual funds.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ borderLeft: '2px solid var(--color-action)', paddingLeft: '14px' }}>
                <div style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.06em', color: 'var(--color-action)', textTransform: 'uppercase' }}>
                  REAL INFORMATION
                </div>
                <div style={{ fontSize: '13px', color: '#D4D4D8', marginTop: '3px' }}>
                  Source labels. Data timestamps. Clear evidence.
                </div>
              </div>

              <div style={{ borderLeft: '2px solid var(--color-positive)', paddingLeft: '14px' }}>
                <div style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.06em', color: 'var(--color-positive)', textTransform: 'uppercase' }}>
                  VIRTUAL EXECUTION
                </div>
                <div style={{ fontSize: '13px', color: '#D4D4D8', marginTop: '3px' }}>
                  No real-money orders or brokerage connection.
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Meta */}
        <div className="desktop-only" style={{ fontSize: '11px', color: '#52525B', fontFamily: 'var(--font-mono)' }}>
          FinEx Terminal v1.0 · Dedicated to Shivraj Dhote · Pure Black Edition
        </div>
      </div>

      {/* Right Column: Sign In Card */}
      <div className="welcome-right-col">
        <div style={{ maxWidth: '400px', width: '100%' }}>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#FFFFFF', marginBottom: '6px' }}>
            Sign in to FinEx
          </div>
          <div style={{ fontSize: '14px', color: 'var(--color-action)', fontWeight: 500, marginBottom: '6px' }}>
            Your workspace starts here.
          </div>
          <div style={{ fontSize: '13px', color: '#8E8E93', lineHeight: 1.5, marginBottom: '28px' }}>
            Use Google sign-in to create or return to your personal workspace.
          </div>

          {errorMessage && (
            <div
              style={{
                backgroundColor: 'var(--color-loss-bg)',
                border: '1px solid var(--color-loss-border)',
                color: 'var(--color-loss)',
                padding: '10px 14px',
                borderRadius: 'var(--radius-xs)',
                fontSize: '12px',
                marginBottom: '18px',
              }}
            >
              {errorMessage}
            </div>
          )}

          {/* Consent Checkbox */}
          <label
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '10px',
              fontSize: '12px',
              lineHeight: 1.5,
              color: '#A1A1AA',
              cursor: 'pointer',
              marginBottom: '24px',
              backgroundColor: '#0A0A0A',
              border: '1px solid #1F1F1F',
              borderRadius: 'var(--radius-xs)',
              padding: '12px',
            }}
          >
            <input
              type="checkbox"
              checked={consentChecked}
              onChange={(e) => setConsentChecked(e.target.checked)}
              style={{ marginTop: '2px', accentColor: 'var(--color-action)', cursor: 'pointer' }}
            />
            <span>
              I accept the <strong style={{ color: '#FFFFFF' }}>Terms and Privacy Policy</strong>, and understand FinEx is an <strong style={{ color: 'var(--color-action)' }}>educational platform</strong>.
            </span>
          </label>

          {/* Primary Action: Continue as Shivraj Dhote (One-Click Local Sandbox) */}
          <button
            onClick={handleDevLogin}
            disabled={loading}
            className="btn btn-action"
            style={{
              width: '100%',
              padding: '12px',
              fontSize: '14px',
              borderRadius: 'var(--radius-xs)',
              gap: '10px',
              opacity: consentChecked ? 1 : 0.5,
              cursor: consentChecked ? 'pointer' : 'not-allowed',
              marginBottom: '10px',
            }}
          >
            <span>⚡ {loading ? 'Initializing session...' : 'Continue as Shivraj Dhote (Local Sandbox)'}</span>
          </button>

          {/* Secondary Action: Continue with Google */}
          <button
            onClick={handleGoogleSignIn}
            disabled={loading}
            style={{
              width: '100%',
              padding: '11px',
              fontSize: '13px',
              backgroundColor: '#121214',
              color: '#FFFFFF',
              border: '1px solid #2C2C2E',
              borderRadius: 'var(--radius-xs)',
              gap: '10px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              opacity: consentChecked ? 1 : 0.5,
              cursor: consentChecked ? 'pointer' : 'not-allowed',
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24">
              <path
                fill="#FFFFFF"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#FFFFFF"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FFFFFF"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
              />
              <path
                fill="#FFFFFF"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
              />
            </svg>
            <span>Continue with Google (Requires OAuth Credentials)</span>
          </button>

          {/* Consent and Security Subtext */}
          <div style={{ fontSize: '11px', color: '#71717A', lineHeight: 1.5, marginTop: '16px', textAlign: 'center' }}>
            Your consent is recorded with its policy version. Real PostgreSQL records & paper balances load securely.
          </div>

          <div style={{ display: 'flex', justifyContent: 'center', gap: '16px', marginTop: '24px', fontSize: '11px', color: '#A1A1AA' }}>
            <span style={{ cursor: 'pointer', textDecoration: 'underline' }}>Privacy policy</span>
            <span>·</span>
            <span style={{ cursor: 'pointer', textDecoration: 'underline' }}>Terms</span>
            <span>·</span>
            <span style={{ cursor: 'pointer', textDecoration: 'underline' }}>Need help?</span>
          </div>
        </div>
      </div>
    </div>
  );
};
