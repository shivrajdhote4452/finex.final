import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';

interface WelcomeScreenProps {
  onLoginSuccess: () => void;
  onOpenPrivacy?: () => void;
  onOpenTerms?: () => void;
}

declare global {
  interface Window {
    google?: any;
  }
}

type AuthMode = 'signin' | 'signup' | 'forgot' | 'reset' | 'verify';

export const WelcomeScreen: React.FC<WelcomeScreenProps> = ({
  onLoginSuccess,
  onOpenPrivacy,
  onOpenTerms,
}) => {
  const [mode, setMode] = useState<AuthMode>('signin');
  const [consentChecked, setConsentChecked] = useState(true);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Form fields
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [resetToken, setResetToken] = useState<string | null>(null);

  const googleClientId =
    (import.meta as any).env?.VITE_GOOGLE_CLIENT_ID ||
    '71626572471-2333p55kgim64b3738oabca9l9ss9th0.apps.googleusercontent.com';

  // 1. Scroll right-hand auth container to top whenever authentication mode changes
  useEffect(() => {
    const rightCol = document.getElementById('signin-card');
    if (rightCol) {
      rightCol.scrollTo({ top: 0, behavior: 'instant' });
    }
  }, [mode]);

  // 2. Deep-link token detection from URL hash (e.g. #verify-email?token=... or #reset-password?token=...)
  useEffect(() => {
    const handleHash = async () => {
      const hash = window.location.hash || '';
      if (hash.includes('verify-email')) {
        const match = hash.match(/token=([^&]+)/);
        if (match && match[1]) {
          const token = decodeURIComponent(match[1]);
          setMode('verify');
          setLoading(true);
          setErrorMessage(null);
          try {
            const res = await apiClient.auth.verifyEmail(token);
            setSuccessMessage(res.message || 'Email verified successfully! You can now sign in.');
            setMode('signin');
          } catch (err: any) {
            setErrorMessage(err?.message || 'Verification link is invalid or expired.');
          } finally {
            setLoading(false);
          }
        }
      } else if (hash.includes('reset-password')) {
        const match = hash.match(/token=([^&]+)/);
        if (match && match[1]) {
          const token = decodeURIComponent(match[1]);
          setResetToken(token);
          setMode('reset');
        }
      }
    };

    handleHash();
    window.addEventListener('hashchange', handleHash);
    return () => window.removeEventListener('hashchange', handleHash);
  }, []);

  // 2. Google Identity Services Initialization
  useEffect(() => {
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
  }, [consentChecked, googleClientId, onLoginSuccess]);

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

  // 3. Email & Password Handlers
  const handleEmailSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!consentChecked) {
      setErrorMessage('You must accept the Terms and Privacy Policy to proceed.');
      return;
    }
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail || !password) {
      setErrorMessage('Please enter both your email address and password.');
      return;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(cleanEmail)) {
      setErrorMessage('Please enter a valid email address.');
      return;
    }

    setLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const res = await apiClient.auth.login(cleanEmail, password);
      if (!res?.access_token) {
        throw new Error('Authentication succeeded but server returned no access token.');
      }
      try {
        await apiClient.auth.recordConsent('v1.0');
      } catch (consentErr) {
        console.warn('Consent recording deferred:', consentErr);
      }
      onLoginSuccess();
    } catch (err: any) {
      console.error('Email sign-in failed:', err);
      const isRateLimit = err?.status === 429;
      const isUnverified = err?.status === 403 && err?.message?.toLowerCase().includes('not verified');
      if (isRateLimit) {
        setErrorMessage(err?.message || 'Too many failed login attempts. Please wait before trying again.');
      } else if (isUnverified) {
        setErrorMessage('Your email address is not verified yet. Please check your inbox or click resend.');
      } else {
        setErrorMessage(err?.message || 'Invalid email or password.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleEmailSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!consentChecked) {
      setErrorMessage('You must accept the Terms and Privacy Policy to proceed.');
      return;
    }
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail || !password) {
      setErrorMessage('Please enter an email address and password.');
      return;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(cleanEmail)) {
      setErrorMessage('Please enter a valid email address.');
      return;
    }
    if (password.length < 8) {
      setErrorMessage('Password must be at least 8 characters long.');
      return;
    }

    setLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const res = await apiClient.auth.signup(cleanEmail, password, name.trim() || 'Investor');
      if (res && (res as any).sent === false) {
        setErrorMessage((res as any).message || 'Account registration via email is currently unavailable.');
      } else {
        setSuccessMessage(
          res.message || 'If this email address is not already registered, a verification link has been sent. Please check your inbox.'
        );
        setMode('signin');
        setPassword('');
      }
    } catch (err: any) {
      console.error('Signup failed:', err);
      setErrorMessage(err?.message || 'Account registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail) {
      setErrorMessage('Please enter your email address to receive password reset instructions.');
      return;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(cleanEmail)) {
      setErrorMessage('Please enter a valid email address.');
      return;
    }

    setLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const res = await apiClient.auth.forgotPassword(cleanEmail);
      if (res && (res as any).sent === false) {
        setErrorMessage((res as any).message || 'Password reset via email is currently unavailable.');
      } else {
        setSuccessMessage(
          res.message || 'If an account exists for this email, password reset instructions have been sent.'
        );
      }
    } catch (err: any) {
      console.error('Forgot password error:', err);
      setErrorMessage(err?.message || 'Could not process password reset request.');
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetToken) {
      setErrorMessage('Missing password reset token. Please request a new link.');
      return;
    }
    if (!newPassword || newPassword.length < 8) {
      setErrorMessage('New password must be at least 8 characters long.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setErrorMessage('Passwords do not match. Please re-enter.');
      return;
    }

    setLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const res = await apiClient.auth.resetPassword(resetToken, newPassword);
      setSuccessMessage(res.message || 'Password successfully updated. You can now sign in.');
      setMode('signin');
      setPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setResetToken(null);
      window.location.hash = '';
    } catch (err: any) {
      console.error('Password reset failed:', err);
      setErrorMessage(err?.message || 'Password reset failed. Link may be expired.');
    } finally {
      setLoading(false);
    }
  };

  const handleResendVerification = async () => {
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail) {
      setErrorMessage('Please enter your email address above to receive a new verification link.');
      return;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(cleanEmail)) {
      setErrorMessage('Please enter a valid email address.');
      return;
    }

    setLoading(true);
    setErrorMessage(null);
    try {
      const res = await apiClient.auth.resendVerification(cleanEmail, password.trim() || undefined);
      if (res && (res as any).sent === false) {
        setErrorMessage((res as any).message || 'Could not resend verification link.');
      } else {
        setSuccessMessage(res.message || 'Verification link sent. Please check your inbox.');
      }
    } catch (err: any) {
      setErrorMessage(err?.message || 'Could not resend verification link.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="welcome-container">
      {/* Left Column: Brand & Educational Platform Overview */}
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

            {/* Mobile Jump Link */}
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

          {/* Feature 1: Platform Overview */}
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

          {/* Feature 2: Paper Trading & Virtual Funds */}
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

          {/* Feature 3: Security & Dual Sign-In */}
          <section className="welcome-section-card">
            <span className="welcome-section-badge" style={{ color: '#A5B4FC' }}>
              03 · Unified Identity
            </span>
            <h2 className="welcome-section-heading">
              Secure Email &amp; Google Account Linking
            </h2>
            <p className="welcome-section-text">
              Sign in with your Google account or create a password-protected email account. When using the same verified email address, both sign-in methods link seamlessly to your exact same workspace, cash balance, portfolio holdings, and trading journal.
            </p>
          </section>

          {/* Educational Notice */}
          <div
            style={{
              padding: '14px 16px',
              backgroundColor: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid #1F1F1F',
              borderRadius: 'var(--radius-xs)',
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

      {/* Right Column: Authentication Card */}
      <div className="welcome-right-col" id="signin-card">
        <div className="auth-card">
          {/* Header */}
          <h2 className="auth-header-title">
            {mode === 'signup' && 'Create Your FinEx Account'}
            {mode === 'signin' && 'Sign In to FinEx'}
            {mode === 'forgot' && 'Reset Your Password'}
            {mode === 'reset' && 'Set New Password'}
            {mode === 'verify' && 'Verifying Email'}
          </h2>
          <p className="auth-header-subtitle">
            {mode === 'signup' && 'Start with ₹1,00,000 in virtual funds today.'}
            {mode === 'signin' && 'Your personal market workspace awaits.'}
            {mode === 'forgot' && 'Enter your email to receive single-use recovery instructions.'}
            {mode === 'reset' && 'Choose a strong, unique password (min. 8 characters).'}
            {mode === 'verify' && 'Confirming identity credentials...'}
          </p>

          {/* Tab Switcher: Sign In vs Create Account */}
          {(mode === 'signin' || mode === 'signup') && (
            <div className="auth-tabs" role="tablist" aria-label="Authentication Options">
              <button
                type="button"
                role="tab"
                aria-selected={mode === 'signin'}
                className={`auth-tab-btn ${mode === 'signin' ? 'active' : ''}`}
                onClick={() => {
                  setMode('signin');
                  setErrorMessage(null);
                  setSuccessMessage(null);
                }}
              >
                Sign In
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={mode === 'signup'}
                className={`auth-tab-btn ${mode === 'signup' ? 'active' : ''}`}
                onClick={() => {
                  setMode('signup');
                  setErrorMessage(null);
                  setSuccessMessage(null);
                }}
              >
                Create Account
              </button>
            </div>
          )}

          {/* Status Messages */}
          {errorMessage && (
            <div className="auth-status-error" role="alert">
              <div>{errorMessage}</div>
              {mode === 'signin' && errorMessage.toLowerCase().includes('invalid email or password') && (
                <div style={{ marginTop: '8px', display: 'flex', gap: '14px', flexWrap: 'wrap', alignItems: 'center' }}>
                  <button
                    type="button"
                    className="auth-inline-action-btn"
                    onClick={() => {
                      setMode('signup');
                      setErrorMessage(null);
                    }}
                  >
                    New user? Create an account →
                  </button>
                  <button
                    type="button"
                    className="auth-inline-secondary-btn"
                    onClick={() => {
                      setMode('forgot');
                      setErrorMessage(null);
                    }}
                  >
                    Forgot password?
                  </button>
                </div>
              )}
              {(errorMessage.includes('not verified') || errorMessage.includes('mail server issue') || errorMessage.includes('resend verification')) && (
                <div style={{ marginTop: '6px' }}>
                  <button
                    type="button"
                    className="auth-inline-action-btn"
                    onClick={handleResendVerification}
                  >
                    Resend verification link →
                  </button>
                </div>
              )}
              {mode === 'signup' && errorMessage.toLowerCase().includes('already exists') && (
                <div style={{ marginTop: '6px' }}>
                  <button
                    type="button"
                    className="auth-inline-action-btn"
                    onClick={() => {
                      setMode('signin');
                      setErrorMessage(null);
                    }}
                  >
                    Switch to Sign In →
                  </button>
                </div>
              )}
            </div>
          )}

          {successMessage && (
            <div className="auth-status-success" role="status">
              {successMessage}
            </div>
          )}

          {/* Google Sign In (Available on signin & signup) */}
          {(mode === 'signin' || mode === 'signup') && (
            <>
              <button
                type="button"
                className="auth-google-btn"
                onClick={handleGoogleSignIn}
                disabled={loading || !consentChecked}
                title={!consentChecked ? 'Please accept Terms and Privacy Policy first' : undefined}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                  />
                </svg>
                <span>{loading ? 'Initializing...' : 'Continue with Google'}</span>
              </button>

              <div className="auth-divider">
                <div className="auth-divider-line" />
                <span>or with email &amp; password</span>
                <div className="auth-divider-line" />
              </div>
            </>
          )}

          {/* Email & Password Forms */}
          {mode === 'signin' && (
            <form onSubmit={handleEmailSignIn}>
              <div className="auth-form-group">
                <label className="auth-label" htmlFor="signin-email">
                  Email Address
                </label>
                <input
                  id="signin-email"
                  type="email"
                  className="auth-input"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  required
                  autoComplete="email"
                />
              </div>

              <div className="auth-form-group">
                <div className="auth-label-row">
                  <label className="auth-label" htmlFor="signin-password">
                    Password
                  </label>
                  <button
                    type="button"
                    className="auth-forgot-link"
                    onClick={() => {
                      setMode('forgot');
                      setErrorMessage(null);
                      setSuccessMessage(null);
                    }}
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="auth-password-wrapper">
                  <input
                    id="signin-password"
                    type={showPassword ? 'text' : 'password'}
                    className="auth-input auth-password-input"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    className="auth-password-toggle"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? 'Hide' : 'Show'}
                  </button>
                </div>
              </div>

              {/* Consent Checkbox */}
              <label className="auth-consent-card">
                <input
                  type="checkbox"
                  className="auth-checkbox"
                  checked={consentChecked}
                  onChange={(e) => setConsentChecked(e.target.checked)}
                />
                <span>
                  I accept the{' '}
                  <a
                    href="/terms"
                    className="auth-consent-link"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onOpenTerms) {
                        e.preventDefault();
                        onOpenTerms();
                      }
                    }}
                  >
                    Terms of Service
                  </a>{' '}
                  and{' '}
                  <a
                    href="/privacy"
                    className="auth-consent-link"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onOpenPrivacy) {
                        e.preventDefault();
                        onOpenPrivacy();
                      }
                    }}
                  >
                    Privacy Policy
                  </a>
                  .
                </span>
              </label>

              <button
                type="submit"
                className="auth-primary-btn"
                disabled={loading || !consentChecked}
              >
                {loading ? 'Signing In...' : 'Sign In to Workspace →'}
              </button>

              <div className="auth-switch-row">
                Don&apos;t have an account?{' '}
                <button
                  type="button"
                  className="auth-switch-btn"
                  onClick={() => {
                    setMode('signup');
                    setErrorMessage(null);
                    setSuccessMessage(null);
                  }}
                >
                  Create Account
                </button>
              </div>
            </form>
          )}

          {mode === 'signup' && (
            <form onSubmit={handleEmailSignUp}>
              <div className="auth-form-group">
                <label className="auth-label" htmlFor="signup-name">
                  Your Full Name
                </label>
                <input
                  id="signup-name"
                  type="text"
                  className="auth-input"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Aditi Sharma"
                  autoComplete="name"
                />
              </div>

              <div className="auth-form-group">
                <label className="auth-label" htmlFor="signup-email">
                  Email Address
                </label>
                <input
                  id="signup-email"
                  type="email"
                  className="auth-input"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  required
                  autoComplete="email"
                />
              </div>

              <div className="auth-form-group">
                <label className="auth-label" htmlFor="signup-password">
                  Password (min. 8 characters)
                </label>
                <div className="auth-password-wrapper">
                  <input
                    id="signup-password"
                    type={showPassword ? 'text' : 'password'}
                    className="auth-input auth-password-input"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="At least 8 characters with letters & numbers"
                    required
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="auth-password-toggle"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? 'Hide' : 'Show'}
                  </button>
                </div>
              </div>

              {/* Consent Checkbox */}
              <label className="auth-consent-card">
                <input
                  type="checkbox"
                  className="auth-checkbox"
                  checked={consentChecked}
                  onChange={(e) => setConsentChecked(e.target.checked)}
                />
                <span>
                  I accept the{' '}
                  <a
                    href="/terms"
                    className="auth-consent-link"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onOpenTerms) {
                        e.preventDefault();
                        onOpenTerms();
                      }
                    }}
                  >
                    Terms of Service
                  </a>{' '}
                  and{' '}
                  <a
                    href="/privacy"
                    className="auth-consent-link"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onOpenPrivacy) {
                        e.preventDefault();
                        onOpenPrivacy();
                      }
                    }}
                  >
                    Privacy Policy
                  </a>
                  , and understand FinEx is an educational simulation platform.
                </span>
              </label>

              <button
                type="submit"
                className="auth-primary-btn"
                disabled={loading || !consentChecked}
              >
                {loading ? 'Creating Account...' : 'Create Account & Verify Email →'}
              </button>

              <div className="auth-switch-row">
                Already have an account?{' '}
                <button
                  type="button"
                  className="auth-switch-btn"
                  onClick={() => {
                    setMode('signin');
                    setErrorMessage(null);
                    setSuccessMessage(null);
                  }}
                >
                  Sign In
                </button>
              </div>
            </form>
          )}

          {mode === 'forgot' && (
            <form onSubmit={handleForgotPassword}>
              <p style={{ fontSize: '13px', color: '#A1A1AA', lineHeight: 1.5, marginBottom: '18px' }}>
                Enter the email address registered with your FinEx account. We will send you a single-use link to reset your password.
              </p>

              <div className="auth-form-group">
                <label className="auth-label" htmlFor="forgot-email">
                  Account Email
                </label>
                <input
                  id="forgot-email"
                  type="email"
                  className="auth-input"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  required
                  autoComplete="email"
                />
              </div>

              <button
                type="submit"
                className="auth-primary-btn"
                disabled={loading}
                style={{ marginBottom: '12px' }}
              >
                {loading ? 'Sending Instructions...' : 'Send Password Reset Link →'}
              </button>

              <button
                type="button"
                className="auth-secondary-btn"
                onClick={() => {
                  setMode('signin');
                  setErrorMessage(null);
                  setSuccessMessage(null);
                }}
              >
                ← Back to Sign In
              </button>
            </form>
          )}

          {mode === 'reset' && (
            <form onSubmit={handleResetPassword}>
              <div className="auth-form-group">
                <label className="auth-label" htmlFor="reset-new-password">
                  New Password (min 8 characters)
                </label>
                <input
                  id="reset-new-password"
                  type="password"
                  className="auth-input"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                />
              </div>

              <div className="auth-form-group">
                <label className="auth-label" htmlFor="reset-confirm-password">
                  Confirm New Password
                </label>
                <input
                  id="reset-confirm-password"
                  type="password"
                  className="auth-input"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                />
              </div>

              <button
                type="submit"
                className="auth-primary-btn"
                disabled={loading}
                style={{ marginBottom: '12px' }}
              >
                {loading ? 'Updating Password...' : 'Save New Password & Sign In →'}
              </button>

              <button
                type="button"
                className="auth-secondary-btn"
                onClick={() => {
                  setMode('signin');
                  setResetToken(null);
                  window.location.hash = '';
                }}
              >
                ← Back to Sign In
              </button>
            </form>
          )}

          {/* Quick Platform Pillars Recap */}
          <div className="auth-pillars-grid">
            <div className="auth-pillar-card">
              <div className="auth-pillar-value" style={{ color: 'var(--color-positive)' }}>
                ₹1,00,000
              </div>
              <div className="auth-pillar-label">
                Virtual Funds
              </div>
            </div>
            <div className="auth-pillar-card">
              <div className="auth-pillar-value" style={{ color: '#A5B4FC' }}>
                AI Guided
              </div>
              <div className="auth-pillar-label">
                Educational Insights
              </div>
            </div>
          </div>

          {/* Subtext */}
          <div className="auth-subtext">
            FinEx is an educational platform. Paper trading uses virtual funds.
          </div>

          <div className="auth-footer-links">
            <a
              href="/privacy"
              className="auth-footer-link"
              onClick={(e) => {
                if (onOpenPrivacy) {
                  e.preventDefault();
                  onOpenPrivacy();
                }
              }}
            >
              Privacy Policy
            </a>
            <span style={{ color: '#3F3F46' }}>•</span>
            <a
              href="/terms"
              className="auth-footer-link"
              onClick={(e) => {
                if (onOpenTerms) {
                  e.preventDefault();
                  onOpenTerms();
                }
              }}
            >
              Terms of Service
            </a>
            <span style={{ color: '#3F3F46' }}>•</span>
            <a
              href="mailto:shivrajdhote4452@gmail.com"
              className="auth-footer-link"
            >
              Need help?
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};
