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
            const loginRes = await apiClient.auth.googleLogin(response.credential);
            if (!loginRes?.access_token) {
              throw new Error('Authentication succeeded but server returned no access token.');
            }
            try {
              await apiClient.auth.recordConsent('v1.0');
            } catch (consentErr) {
              console.warn('Consent recording deferred:', consentErr);
            }
            onLoginSuccess();
          } catch (err: any) {
            console.error('Google Sign-In backend verification error:', err);
            const isTimeout = err?.code === 'TIMEOUT' || err?.status === 408 || err?.message?.includes('timed out');
            const msg = isTimeout
              ? 'The FinEx backend server is warming up. Please click Continue with Google again in a moment.'
              : err?.message || 'Google sign-in verification failed. Please try again.';
            setErrorMessage(msg);
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

  return (
    <div className="welcome-container">
      {/* Left Column: Brand & Comprehensive Educational Platform Overview */}
      <div className="welcome-left-col">
        <div style={{ maxWidth: '640px', width: '100%', margin: '0 auto' }}>
          {/* Logo Mark & Platform Pill */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
              <span style={{ fontSize: '28px', fontWeight: 900, color: '#FFFFFF', letterSpacing: '-0.03em' }}>Fin</span>
              <span style={{ fontSize: '28px', fontWeight: 900, color: 'var(--color-action)', letterSpacing: '-0.03em' }}>Ex</span>
              <span style={{ fontSize: '11px', color: '#71717A', marginLeft: '10px', fontFamily: 'var(--font-mono)', letterSpacing: '0.04em' }}>
                TERMINAL
              </span>
            </div>

            {/* Mobile-Only Jump to Sign In Pill */}
            <a
              href="#signin-card"
              className="mobile-only"
              style={{
                fontSize: '11px',
                fontWeight: 600,
                color: 'var(--color-action)',
                backgroundColor: 'var(--color-action-bg)',
                border: '1px solid var(--color-action-border)',
                padding: '5px 12px',
                borderRadius: 'var(--radius-full)',
                textDecoration: 'none',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              Sign In to Workspace ↓
            </a>
          </div>

          {/* Hero Mission */}
          <div className="welcome-mission-box" style={{ marginTop: '48px', marginBottom: '36px' }}>
            <h1 className="welcome-title">
              Learn the market.<br />
              <span style={{ color: 'var(--color-action)' }}>Practice with intent.</span>
            </h1>
            <p className="welcome-subtitle">
              FinEx is a zero-risk financial education platform and market workspace built for students, beginner investors, and self-directed learners to understand Indian equity markets, test portfolio strategies, and practice disciplined investing with virtual funds.
            </p>
          </div>

          {/* Feature 1: What FinEx Is & Who It Is For */}
          <section className="welcome-section-card">
            <span className="welcome-section-badge" style={{ color: 'var(--color-action)' }}>
              01 · Platform Overview
            </span>
            <h2 className="welcome-section-heading">
              What is FinEx and Who Is It For?
            </h2>
            <p className="welcome-section-text">
              FinEx is designed for university students, new retail market participants, and curious learners looking to understand Indian capital markets (NSE & BSE) without taking financial risk. It bridges the gap between textbook financial theory and practical market mechanics, offering interactive charts, risk assessments, and portfolio tracking in an accessible learning environment.
            </p>
          </section>

          {/* Feature 2: Simulated Paper Trading & Virtual Funds */}
          <section className="welcome-section-card">
            <span className="welcome-section-badge" style={{ color: 'var(--color-positive)' }}>
              02 · Virtual Execution
            </span>
            <h2 className="welcome-section-heading">
              How Simulated Paper Trading Works
            </h2>
            <p className="welcome-section-text" style={{ marginBottom: '14px' }}>
              Every user begins with <strong style={{ color: '#FFFFFF' }}>₹1,00,000 in virtual funds</strong>. You can research stocks and indices, practice placing simulated buy and sell market orders, inspect position allocations, and observe how market volatility affects portfolio profit and loss.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px' }}>
              <div style={{ padding: '10px 12px', backgroundColor: '#050505', border: '1px solid #1F1F1F', borderRadius: '4px' }}>
                <div style={{ fontSize: '11px', color: 'var(--color-positive)', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                  ₹1,00,000 CAPITAL
                </div>
                <div style={{ fontSize: '12px', color: '#D4D4D8', marginTop: '2px' }}>
                  Risk-free virtual cash to practice order sizing and asset allocation.
                </div>
              </div>
              <div style={{ padding: '10px 12px', backgroundColor: '#050505', border: '1px solid #1F1F1F', borderRadius: '4px' }}>
                <div style={{ fontSize: '11px', color: '#E0E0E0', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                  NO BROKERAGE LINK
                </div>
                <div style={{ fontSize: '12px', color: '#D4D4D8', marginTop: '2px' }}>
                  Zero real money, no demat account connection, and zero financial liability.
                </div>
              </div>
            </div>
          </section>

          {/* Feature 3: Educational Risk Assessment & AskFinEx AI */}
          <section className="welcome-section-card">
            <span className="welcome-section-badge" style={{ color: '#A5B4FC' }}>
              03 · Learning &amp; Analysis
            </span>
            <h2 className="welcome-section-heading">
              Educational Risk Profiling &amp; AskFinEx Assistant
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '6px' }}>
              <div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#FFFFFF' }}>
                  Behavioral Risk Assessment
                </div>
                <p className="welcome-section-text" style={{ marginTop: '2px' }}>
                  Complete a 4-question risk-tolerance questionnaire paired with your preferred investment horizon. FinEx calculates your risk profile (Conservative, Moderate, or Aggressive) to demonstrate how asset allocation and risk management work in practice.
                </p>
              </div>
              <div style={{ borderTop: '1px solid #1F1F1F', paddingTop: '10px' }}>
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#FFFFFF' }}>
                  AskFinEx AI Assistant
                </div>
                <p className="welcome-section-text" style={{ marginTop: '2px' }}>
                  Explore financial definitions, portfolio diversification rules, and market structures. AskFinEx synthesizes plain-English educational summaries grounded in official SEBI circulars and regulations. It is strictly for financial education—not SEBI-registered investment advice or buy/sell recommendations.
                </p>
              </div>
            </div>
          </section>

          {/* Feature 4: Transparent Market Data (Live, Cached & Unavailable) */}
          <section className="welcome-section-card">
            <span className="welcome-section-badge" style={{ color: '#38BDF8' }}>
              04 · Data Transparency
            </span>
            <h2 className="welcome-section-heading">
              Understanding Market Data: Live, Cached &amp; Unavailable
            </h2>
            <p className="welcome-section-text" style={{ marginBottom: '14px' }}>
              FinEx clearly communicates the freshness and origin of market information across three distinct data states:
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', fontSize: '12.5px', color: '#D4D4D8' }}>
                <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#4DD5AD', marginTop: '5px', flexShrink: 0 }} />
                <div>
                  <strong style={{ color: '#FFFFFF' }}>Live Quotes:</strong> During official Indian trading hours, symbols display real-time price updates with active timestamps.
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', fontSize: '12.5px', color: '#D4D4D8' }}>
                <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#F29A60', marginTop: '5px', flexShrink: 0 }} />
                <div>
                  <strong style={{ color: '#FFFFFF' }}>Cached Snapshots:</strong> After trading hours, on weekends, or during rate-limit pauses, FinEx displays recent session snapshots explicitly marked with capture timestamps so data recency is always clear.
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', fontSize: '12.5px', color: '#D4D4D8' }}>
                <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#71717A', marginTop: '5px', flexShrink: 0 }} />
                <div>
                  <strong style={{ color: '#FFFFFF' }}>Unavailable Feeds:</strong> If an upstream exchange feed is disconnected or a symbol is unavailable, FinEx shows a clear offline notice rather than generating artificial prices.
                </div>
              </div>
            </div>
          </section>

          {/* Educational Disclaimer Banner */}
          <div
            style={{
              padding: '16px 18px',
              backgroundColor: '#0A0A0A',
              border: '1px solid #1F1F1F',
              borderRadius: '6px',
              fontSize: '11.5px',
              lineHeight: 1.6,
              color: '#71717A',
              marginBottom: '32px',
            }}
          >
            <strong style={{ color: '#A1A1AA' }}>Educational Notice:</strong> FinEx is an educational simulation platform developed for learning financial concepts and practicing paper trading. It does not execute real-money orders, connect to brokerages, or provide SEBI-registered investment advisory services.
          </div>

          {/* Footer Meta */}
          <div style={{ fontSize: '11px', color: '#52525B', fontFamily: 'var(--font-mono)', paddingBottom: '24px' }}>
            FinEx Terminal v1.0 · Financial Education &amp; Paper Trading Platform
          </div>
        </div>
      </div>

      {/* Right Column: Sign In Card */}
      <div className="welcome-right-col" id="signin-card">
        <div style={{ maxWidth: '400px', width: '100%' }}>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#FFFFFF', marginBottom: '6px' }}>
            Sign in to FinEx
          </div>
          <div style={{ fontSize: '14px', color: 'var(--color-action)', fontWeight: 500, marginBottom: '6px' }}>
            Your personal workspace starts here.
          </div>
          <div style={{ fontSize: '13px', color: '#8E8E93', lineHeight: 1.5, marginBottom: '24px' }}>
            Use Google sign-in to access your simulated paper portfolio, risk assessment, and practice journal.
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
              marginBottom: '20px',
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

          {/* Action: Continue with Google */}
          <button
            onClick={handleGoogleSignIn}
            disabled={loading}
            style={{
              width: '100%',
              padding: '12px',
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
              transition: 'background-color 0.15s ease',
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
            <span>{loading ? 'Initializing...' : 'Continue with Google'}</span>
          </button>

          {/* Quick Platform Pillars Recap */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: '8px',
              marginTop: '24px',
              paddingTop: '20px',
              borderTop: '1px solid #1F1F1F',
              textAlign: 'center',
            }}
          >
            <div style={{ padding: '8px 4px' }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-positive)', fontFamily: 'var(--font-mono)' }}>
                ₹1,00,000
              </div>
              <div style={{ fontSize: '10.5px', color: '#71717A', marginTop: '2px' }}>
                Virtual Funds
              </div>
            </div>
            <div style={{ padding: '8px 4px' }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-action)', fontFamily: 'var(--font-mono)' }}>
                Zero Risk
              </div>
              <div style={{ fontSize: '10.5px', color: '#71717A', marginTop: '2px' }}>
                Paper Trading
              </div>
            </div>
            <div style={{ padding: '8px 4px' }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: '#A5B4FC', fontFamily: 'var(--font-mono)' }}>
                SEBI Grounded
              </div>
              <div style={{ fontSize: '10.5px', color: '#71717A', marginTop: '2px' }}>
                AI Learning
              </div>
            </div>
          </div>

          {/* Consent and Security Subtext */}
          <div style={{ fontSize: '11px', color: '#71717A', lineHeight: 1.5, marginTop: '16px', textAlign: 'center' }}>
            Your consent is recorded with its policy version. Real PostgreSQL records &amp; paper balances load securely.
          </div>

          <div style={{ display: 'flex', justifyContent: 'center', gap: '16px', marginTop: '20px', fontSize: '11px', color: '#A1A1AA' }}>
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
