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

  // 1. Deep-link token detection from URL hash (e.g. #verify-email?token=... or #reset-password?token=...)
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
      const res = await apiClient.auth.resendVerification(cleanEmail);
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
        <div style={{ maxWidth: '420px', width: '100%' }}>
          {/* Header */}
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#FFFFFF', marginBottom: '4px' }}>
            {mode === 'signup' && 'Create Your FinEx Account'}
            {mode === 'signin' && 'Sign In to FinEx'}
            {mode === 'forgot' && 'Reset Your Password'}
            {mode === 'reset' && 'Set New Password'}
            {mode === 'verify' && 'Verifying Email'}
          </div>
          <div style={{ fontSize: '13px', color: 'var(--color-action)', fontWeight: 500, marginBottom: '20px' }}>
            {mode === 'signup' && 'Start with ₹1,00,000 in virtual funds today.'}
            {mode === 'signin' && 'Your personal market workspace awaits.'}
            {mode === 'forgot' && 'We’ll send single-use recovery instructions.'}
            {mode === 'reset' && 'Choose a strong, unique password.'}
            {mode === 'verify' && 'Confirming identity credentials...'}
          </div>

          {/* Tab Switcher: Sign In vs Create Account */}
          {(mode === 'signin' || mode === 'signup') && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                backgroundColor: '#0A0A0C',
                border: '1px solid #1F1F23',
                borderRadius: 'var(--radius-xs)',
                padding: '3px',
                marginBottom: '20px',
              }}
            >
              <button
                type="button"
                onClick={() => {
                  setMode('signin');
                  setErrorMessage(null);
                  setSuccessMessage(null);
                }}
                style={{
                  padding: '8px',
                  fontSize: '12px',
                  fontWeight: 600,
                  borderRadius: 'var(--radius-xs)',
                  border: 'none',
                  cursor: 'pointer',
                  backgroundColor: mode === 'signin' ? '#18181B' : 'transparent',
                  color: mode === 'signin' ? '#FFFFFF' : '#71717A',
                  transition: 'all 0.15s ease',
                }}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => {
                  setMode('signup');
                  setErrorMessage(null);
                  setSuccessMessage(null);
                }}
                style={{
                  padding: '8px',
                  fontSize: '12px',
                  fontWeight: 600,
                  borderRadius: 'var(--radius-xs)',
                  border: 'none',
                  cursor: 'pointer',
                  backgroundColor: mode === 'signup' ? '#18181B' : 'transparent',
                  color: mode === 'signup' ? '#FFFFFF' : '#71717A',
                  transition: 'all 0.15s ease',
                }}
              >
                Create Account
              </button>
            </div>
          )}

          {/* Status Messages */}
          {errorMessage && (
            <div
              style={{
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#FCA5A5',
                padding: '10px 14px',
                borderRadius: 'var(--radius-xs)',
                fontSize: '12px',
                lineHeight: 1.5,
                marginBottom: '18px',
              }}
            >
              {errorMessage}
              {mode === 'signin' && errorMessage.toLowerCase().includes('invalid email or password') && (
                <div style={{ marginTop: '8px', display: 'flex', gap: '14px', flexWrap: 'wrap', alignItems: 'center' }}>
                  <button
                    type="button"
                    onClick={() => {
                      setMode('signup');
                      setErrorMessage(null);
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--color-action)',
                      textDecoration: 'underline',
                      fontSize: '11.5px',
                      cursor: 'pointer',
                      padding: 0,
                      fontWeight: 600,
                    }}
                  >
                    New user? Create an account →
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setMode('forgot');
                      setErrorMessage(null);
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#D4D4D8',
                      textDecoration: 'underline',
                      fontSize: '11.5px',
                      cursor: 'pointer',
                      padding: 0,
                    }}
                  >
                    Forgot password?
                  </button>
                </div>
              )}
              {errorMessage.includes('not verified') && (
                <div style={{ marginTop: '6px' }}>
                  <button
                    type="button"
                    onClick={handleResendVerification}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--color-action)',
                      textDecoration: 'underline',
                      fontSize: '11.5px',
                      cursor: 'pointer',
                      padding: 0,
                    }}
                  >
                    Resend verification link →
                  </button>
                </div>
              )}
              {mode === 'signup' && errorMessage.toLowerCase().includes('already exists') && (
                <div style={{ marginTop: '6px' }}>
                  <button
                    type="button"
                    onClick={() => {
                      setMode('signin');
                      setErrorMessage(null);
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--color-action)',
                      textDecoration: 'underline',
                      fontSize: '11.5px',
                      cursor: 'pointer',
                      padding: 0,
                    }}
                  >
                    Switch to Sign In →
                  </button>
                </div>
              )}
            </div>
          )}

          {successMessage && (
            <div
              style={{
                backgroundColor: 'rgba(34, 197, 94, 0.1)',
                border: '1px solid rgba(34, 197, 94, 0.3)',
                color: '#86EFAC',
                padding: '10px 14px',
                borderRadius: 'var(--radius-xs)',
                fontSize: '12px',
                lineHeight: 1.5,
                marginBottom: '18px',
              }}
            >
              {successMessage}
            </div>
          )}

          {/* Google Sign In (Available on signin & signup) */}
          {(mode === 'signin' || mode === 'signup') && (
            <>
              <button
                type="button"
                onClick={handleGoogleSignIn}
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '11px',
                  fontSize: '13px',
                  backgroundColor: '#121214',
                  color: '#FFFFFF',
                  border: '1px solid #27272A',
                  borderRadius: 'var(--radius-xs)',
                  gap: '10px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: consentChecked ? 'pointer' : 'not-allowed',
                  opacity: consentChecked ? 1 : 0.5,
                  transition: 'background-color 0.15s ease',
                  marginBottom: '18px',
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

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  margin: '18px 0',
                  gap: '12px',
                  color: '#52525B',
                  fontSize: '11px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                }}
              >
                <div style={{ flex: 1, height: '1px', backgroundColor: '#1F1F23' }} />
                <span>or with email &amp; password</span>
                <div style={{ flex: 1, height: '1px', backgroundColor: '#1F1F23' }} />
              </div>
            </>
          )}

          {/* Email & Password Forms */}
          {mode === 'signin' && (
            <form onSubmit={handleEmailSignIn}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: '#A1A1AA', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  required
                  autoComplete="email"
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    backgroundColor: '#0A0A0C',
                    border: '1px solid #27272A',
                    borderRadius: 'var(--radius-xs)',
                    color: '#FFFFFF',
                    fontSize: '13px',
                    outline: 'none',
                    boxSizing: 'border-box',
                    fontFamily: 'inherit',
                  }}
                />
              </div>

              <div style={{ marginBottom: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <label style={{ fontSize: '11px', fontWeight: 600, color: '#A1A1AA', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Password
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      setMode('forgot');
                      setErrorMessage(null);
                      setSuccessMessage(null);
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--color-action)',
                      fontSize: '11.5px',
                      cursor: 'pointer',
                      padding: 0,
                    }}
                  >
                    Forgot password?
                  </button>
                </div>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    autoComplete="current-password"
                    style={{
                      width: '100%',
                      padding: '10px 40px 10px 12px',
                      backgroundColor: '#0A0A0C',
                      border: '1px solid #27272A',
                      borderRadius: 'var(--radius-xs)',
                      color: '#FFFFFF',
                      fontSize: '13px',
                      outline: 'none',
                      boxSizing: 'border-box',
                      fontFamily: 'inherit',
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{
                      position: 'absolute',
                      right: '10px',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      background: 'none',
                      border: 'none',
                      color: '#71717A',
                      cursor: 'pointer',
                      fontSize: '11px',
                    }}
                  >
                    {showPassword ? 'Hide' : 'Show'}
                  </button>
                </div>
              </div>

              {/* Consent Checkbox */}
              <label
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                  fontSize: '11.5px',
                  lineHeight: 1.5,
                  color: '#A1A1AA',
                  cursor: 'pointer',
                  marginBottom: '18px',
                  backgroundColor: '#0A0A0C',
                  border: '1px solid #1F1F23',
                  borderRadius: 'var(--radius-xs)',
                  padding: '10px 12px',
                }}
              >
                <input
                  type="checkbox"
                  checked={consentChecked}
                  onChange={(e) => setConsentChecked(e.target.checked)}
                  style={{ marginTop: '2px', accentColor: 'var(--color-action)', cursor: 'pointer' }}
                />
                <span>
                  I accept the{' '}
                  <a
                    href="/terms"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onOpenTerms) {
                        e.preventDefault();
                        onOpenTerms();
                      }
                    }}
                    style={{ color: '#FFFFFF', textDecoration: 'underline' }}
                  >
                    Terms of Service
                  </a>{' '}
                  and{' '}
                  <a
                    href="/privacy"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onOpenPrivacy) {
                        e.preventDefault();
                        onOpenPrivacy();
                      }
                    }}
                    style={{ color: '#FFFFFF', textDecoration: 'underline' }}
                  >
                    Privacy Policy
                  </a>
                  .
                </span>
              </label>

              <button
                type="submit"
                disabled={loading || !consentChecked}
                style={{
                  width: '100%',
                  padding: '11px',
                  fontSize: '13px',
                  fontWeight: 600,
                  backgroundColor: 'var(--color-action)',
                  color: '#000000',
                  border: 'none',
                  borderRadius: 'var(--radius-xs)',
                  cursor: consentChecked && !loading ? 'pointer' : 'not-allowed',
                  opacity: consentChecked && !loading ? 1 : 0.6,
                  transition: 'opacity 0.15s ease',
                }}
              >
                {loading ? 'Signing In...' : 'Sign In to Workspace →'}
              </button>

              <div style={{ marginTop: '16px', textAlign: 'center', fontSize: '12px', color: '#71717A' }}>
                Don&apos;t have an account?{' '}
                <button
                  type="button"
                  onClick={() => {
                    setMode('signup');
                    setErrorMessage(null);
                    setSuccessMessage(null);
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--color-action)',
                    textDecoration: 'underline',
                    fontSize: '12px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    padding: 0,
                  }}
                >
                  Create Account
                </button>
              </div>
            </form>
          )}

          {mode === 'signup' && (
            <form onSubmit={handleEmailSignUp}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: '#A1A1AA', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Your Full Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Aditi Sharma"
                  autoComplete="name"
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    backgroundColor: '#0A0A0C',
                    border: '1px solid #27272A',
                    borderRadius: 'var(--radius-xs)',
                    color: '#FFFFFF',
                    fontSize: '13px',
                    outline: 'none',
                    boxSizing: 'border-box',
                    fontFamily: 'inherit',
                  }}
                />
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: '#A1A1AA', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  required
                  autoComplete="email"
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    backgroundColor: '#0A0A0C',
                    border: '1px solid #27272A',
                    borderRadius: 'var(--radius-xs)',
                    color: '#FFFFFF',
                    fontSize: '13px',
                    outline: 'none',
                    boxSizing: 'border-box',
                    fontFamily: 'inherit',
                  }}
                />
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: '#A1A1AA', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Password (min. 8 characters)
                </label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="At least 8 characters with letters & numbers"
                    required
                    autoComplete="new-password"
                    style={{
                      width: '100%',
                      padding: '10px 40px 10px 12px',
                      backgroundColor: '#0A0A0C',
                      border: '1px solid #27272A',
                      borderRadius: 'var(--radius-xs)',
                      color: '#FFFFFF',
                      fontSize: '13px',
                      outline: 'none',
                      boxSizing: 'border-box',
                      fontFamily: 'inherit',
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{
                      position: 'absolute',
                      right: '10px',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      background: 'none',
                      border: 'none',
                      color: '#71717A',
                      cursor: 'pointer',
                      fontSize: '11px',
                    }}
                  >
                    {showPassword ? 'Hide' : 'Show'}
                  </button>
                </div>
              </div>

              {/* Consent Checkbox */}
              <label
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                  fontSize: '11.5px',
                  lineHeight: 1.5,
                  color: '#A1A1AA',
                  cursor: 'pointer',
                  marginBottom: '18px',
                  backgroundColor: '#0A0A0C',
                  border: '1px solid #1F1F23',
                  borderRadius: 'var(--radius-xs)',
                  padding: '10px 12px',
                }}
              >
                <input
                  type="checkbox"
                  checked={consentChecked}
                  onChange={(e) => setConsentChecked(e.target.checked)}
                  style={{ marginTop: '2px', accentColor: 'var(--color-action)', cursor: 'pointer' }}
                />
                <span>
                  I accept the{' '}
                  <a
                    href="/terms"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onOpenTerms) {
                        e.preventDefault();
                        onOpenTerms();
                      }
                    }}
                    style={{ color: '#FFFFFF', textDecoration: 'underline' }}
                  >
                    Terms of Service
                  </a>{' '}
                  and{' '}
                  <a
                    href="/privacy"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onOpenPrivacy) {
                        e.preventDefault();
                        onOpenPrivacy();
                      }
                    }}
                    style={{ color: '#FFFFFF', textDecoration: 'underline' }}
                  >
                    Privacy Policy
                  </a>
                  , and understand FinEx is an educational simulation platform.
                </span>
              </label>

              <button
                type="submit"
                disabled={loading || !consentChecked}
                style={{
                  width: '100%',
                  padding: '11px',
                  fontSize: '13px',
                  fontWeight: 600,
                  backgroundColor: 'var(--color-action)',
                  color: '#000000',
                  border: 'none',
                  borderRadius: 'var(--radius-xs)',
                  cursor: consentChecked && !loading ? 'pointer' : 'not-allowed',
                  opacity: consentChecked && !loading ? 1 : 0.6,
                  transition: 'opacity 0.15s ease',
                }}
              >
                {loading ? 'Creating Account...' : 'Create Account & Verify Email →'}
              </button>

              <div style={{ marginTop: '16px', textAlign: 'center', fontSize: '12px', color: '#71717A' }}>
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => {
                    setMode('signin');
                    setErrorMessage(null);
                    setSuccessMessage(null);
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--color-action)',
                    textDecoration: 'underline',
                    fontSize: '12px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    padding: 0,
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

              <div style={{ marginBottom: '18px' }}>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: '#A1A1AA', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Account Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  required
                  autoComplete="email"
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    backgroundColor: '#0A0A0C',
                    border: '1px solid #27272A',
                    borderRadius: 'var(--radius-xs)',
                    color: '#FFFFFF',
                    fontSize: '13px',
                    outline: 'none',
                    boxSizing: 'border-box',
                    fontFamily: 'inherit',
                  }}
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '11px',
                  fontSize: '13px',
                  fontWeight: 600,
                  backgroundColor: 'var(--color-action)',
                  color: '#000000',
                  border: 'none',
                  borderRadius: 'var(--radius-xs)',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  opacity: loading ? 0.6 : 1,
                  marginBottom: '12px',
                }}
              >
                {loading ? 'Sending Instructions...' : 'Send Password Reset Link →'}
              </button>

              <button
                type="button"
                onClick={() => {
                  setMode('signin');
                  setErrorMessage(null);
                  setSuccessMessage(null);
                }}
                style={{
                  width: '100%',
                  padding: '10px',
                  background: 'none',
                  border: '1px solid #27272A',
                  color: '#A1A1AA',
                  fontSize: '12px',
                  borderRadius: 'var(--radius-xs)',
                  cursor: 'pointer',
                }}
              >
                ← Back to Sign In
              </button>
            </form>
          )}

          {mode === 'reset' && (
            <form onSubmit={handleResetPassword}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: '#A1A1AA', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  New Password (min 8 characters)
                </label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    backgroundColor: '#0A0A0C',
                    border: '1px solid #27272A',
                    borderRadius: 'var(--radius-xs)',
                    color: '#FFFFFF',
                    fontSize: '13px',
                    outline: 'none',
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              <div style={{ marginBottom: '18px' }}>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: '#A1A1AA', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Confirm New Password
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    backgroundColor: '#0A0A0C',
                    border: '1px solid #27272A',
                    borderRadius: 'var(--radius-xs)',
                    color: '#FFFFFF',
                    fontSize: '13px',
                    outline: 'none',
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '11px',
                  fontSize: '13px',
                  fontWeight: 600,
                  backgroundColor: 'var(--color-action)',
                  color: '#000000',
                  border: 'none',
                  borderRadius: 'var(--radius-xs)',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  opacity: loading ? 0.6 : 1,
                  marginBottom: '12px',
                }}
              >
                {loading ? 'Updating Password...' : 'Save New Password & Sign In →'}
              </button>

              <button
                type="button"
                onClick={() => {
                  setMode('signin');
                  setResetToken(null);
                  window.location.hash = '';
                }}
                style={{
                  width: '100%',
                  padding: '10px',
                  background: 'none',
                  border: '1px solid #27272A',
                  color: '#A1A1AA',
                  fontSize: '12px',
                  borderRadius: 'var(--radius-xs)',
                  cursor: 'pointer',
                }}
              >
                ← Back to Sign In
              </button>
            </form>
          )}

          {/* Quick Platform Pillars Recap */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: '8px',
              marginTop: '28px',
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
                Dual Login
              </div>
              <div style={{ fontSize: '10.5px', color: '#71717A', marginTop: '2px' }}>
                Google + Email
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

          {/* Subtext */}
          <div style={{ fontSize: '11px', color: '#71717A', lineHeight: 1.5, marginTop: '16px', textAlign: 'center' }}>
            Your consent is recorded with its policy version. Real PostgreSQL records &amp; paper balances load securely.
          </div>

          <div style={{ display: 'flex', justifyContent: 'center', gap: '16px', marginTop: '20px', fontSize: '11px', color: '#A1A1AA' }}>
            <a
              href="/privacy"
              onClick={(e) => {
                if (onOpenPrivacy) {
                  e.preventDefault();
                  onOpenPrivacy();
                }
              }}
              style={{ color: '#A1A1AA', textDecoration: 'underline', cursor: 'pointer' }}
            >
              Privacy Policy
            </a>
            <span>·</span>
            <a
              href="/terms"
              onClick={(e) => {
                if (onOpenTerms) {
                  e.preventDefault();
                  onOpenTerms();
                }
              }}
              style={{ color: '#A1A1AA', textDecoration: 'underline', cursor: 'pointer' }}
            >
              Terms of Service
            </a>
            <span>·</span>
            <a
              href="mailto:shivrajdhote4452@gmail.com"
              style={{ color: '#A1A1AA', textDecoration: 'underline', cursor: 'pointer' }}
            >
              Need help?
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};
