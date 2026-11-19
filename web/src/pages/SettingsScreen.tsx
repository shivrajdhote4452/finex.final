import React, { useState } from 'react';
import { useFinancial } from '../context/FinancialContext';
import { ThemeToggle } from '../components/common/ThemeToggle';
import { apiClient } from '../api/client';

interface SettingsScreenProps {
  onSignOut: () => void;
}

export const SettingsScreen: React.FC<SettingsScreenProps> = ({ onSignOut }) => {
  const { virtualCash, resetAccount, isOwner, userProfile } = useFinancial();
  const [resetSuccess, setResetSuccess] = useState(false);
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [activeSubTab, setActiveSubTab] = useState<'profile' | 'security' | 'appearance' | 'sandbox' | 'compliance'>('profile');

  // Security & Password state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [pwLoading, setPwLoading] = useState(false);
  const [pwSuccess, setPwSuccess] = useState<string | null>(null);
  const [pwError, setPwError] = useState<string | null>(null);

  const handleReset = () => {
    resetAccount();
    setResetSuccess(true);
    setTimeout(() => setResetSuccess(false), 2500);
  };

  const handleSavePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPassword || newPassword.length < 8) {
      setPwError('New password must be at least 8 characters long.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPwError('Passwords do not match. Please re-enter.');
      return;
    }
    setPwLoading(true);
    setPwError(null);
    setPwSuccess(null);
    try {
      const res = await apiClient.auth.setPassword(newPassword, currentPassword || undefined);
      setPwSuccess(res.message || 'Password saved successfully.');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      if (userProfile) {
        userProfile.has_password = true;
      }
    } catch (err: any) {
      setPwError(err?.message || 'Failed to update password.');
    } finally {
      setPwLoading(false);
    }
  };

  const fullName = userProfile?.full_name || userProfile?.display_name || (isOwner ? 'Platform Owner' : 'FinEx Investor');
  const roleTitle = isOwner ? 'Sole Developer & Admin' : 'Active Investor';
  const initials = fullName
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0].toUpperCase())
    .join('') || (isOwner ? 'PO' : 'FI');

  const tabs: { id: 'profile' | 'security' | 'appearance' | 'sandbox' | 'compliance'; label: string }[] = [
    { id: 'profile', label: 'Investor Profile' },
    { id: 'security', label: 'Security & Sign-In' },
    { id: 'appearance', label: 'Theme & Appearance' },
    ...(isOwner ? [{ id: 'sandbox' as const, label: 'Sandbox & Trading Rules' }] : []),
    { id: 'compliance', label: 'Consent & Regulatory' },
  ];

  return (
    <div style={{ maxWidth: '1240px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '32px' }}>
      {/* Header */}
      <div>
        <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-primary)', fontWeight: 600 }}>
          {isOwner ? 'User Preferences & Sandbox Governance' : 'User Preferences & Trading Rules'}
        </span>
        <h1 style={{ fontSize: '36px', fontWeight: 700, color: 'var(--text-main)', marginTop: '4px', letterSpacing: '-0.02em' }}>
          Workspace Settings
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
          Manage your investor profile, simulated paper trading account rules, and compliance acknowledgments.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '36px', alignItems: 'start' }}>
        {/* Left Profile Summary Card */}
        <div className="glass-card" style={{ padding: '32px' }}>
          <div
            style={{
              width: '56px',
              height: '56px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--color-action)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 800,
              fontSize: '20px',
              color: '#FFFFFF',
              boxShadow: '0 0 16px rgba(242, 154, 96, 0.35)',
              marginBottom: '20px',
            }}
          >
            {initials}
          </div>

          <h2 style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-main)', margin: '0 0 4px 0' }}>
            {fullName}
          </h2>
          <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '28px' }}>
            {roleTitle}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {tabs.map((tab) => {
              const isActive = activeSubTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveSubTab(tab.id as any)}
                  style={{
                    textAlign: 'left',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-sm)',
                    background: isActive ? 'var(--color-action-bg)' : 'transparent',
                    border: isActive ? '1px solid var(--color-action)' : '1px solid transparent',
                    color: isActive ? 'var(--color-action)' : 'var(--text-muted)',
                    fontWeight: isActive ? 600 : 500,
                    cursor: 'pointer',
                    fontSize: '13px',
                    transition: 'all 0.15s ease',
                  }}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>

          <div style={{ borderTop: '1px solid var(--border-subtle)', marginTop: '32px', paddingTop: '24px' }}>
            <button
              onClick={onSignOut}
              style={{
                width: '100%',
                padding: '10px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--color-loss-border)',
                background: 'rgba(239, 68, 68, 0.1)',
                color: 'var(--color-loss)',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Sign Out of Session
            </button>
          </div>
        </div>

        {/* Right Tab Content */}
        <div className="glass-card" style={{ padding: '32px' }}>
          {activeSubTab === 'profile' && (
            <div>
              <h3 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '20px' }}>
                Investor Profile & Risk Parameters
              </h3>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '16px', borderBottom: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)' }}>Display Name</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>{fullName}</div>
                  </div>
                  <span className="badge badge-neutral">{isOwner ? 'Primary Admin' : 'Active Investor'}</span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '16px', borderBottom: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)' }}>Assessed Risk Profile</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Deterministic Score: 68/100 (Balanced Equity-Debt)</div>
                  </div>
                  <span className="badge badge-cyan">Moderate</span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '16px', borderBottom: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)' }}>Investment Horizon</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>3 to 5 Years Capital Target</div>
                  </div>
                  <span className="badge badge-profit">3–5 Years</span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '16px', borderBottom: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)' }}>In-App Market Alerts</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Push notifications for price thresholds & allocation drift</div>
                  </div>
                  <button
                    onClick={() => setNotificationsEnabled(!notificationsEnabled)}
                    className={notificationsEnabled ? 'btn-emerald' : 'btn btn-secondary'}
                    style={{ padding: '6px 14px', fontSize: '12px', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }}
                  >
                    {notificationsEnabled ? 'Enabled ✓' : 'Disabled'}
                  </button>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '4px' }}>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)' }}>Interface Theme</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Computer theme sync, daylight light mode, or graphite dark mode</div>
                  </div>
                  <ThemeToggle variant="segmented" />
                </div>
              </div>
            </div>
          )}

          {activeSubTab === 'security' && (
            <div>
              <h3 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '8px' }}>
                Account Security &amp; Sign-In Methods
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '24px' }}>
                Manage your credentials and access the same FinEx account using Google OAuth or email and password.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                {/* Linked Methods Status Card */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                  <div style={{ padding: '16px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <strong style={{ fontSize: '13px', color: 'var(--text-main)' }}>Google Sign-In</strong>
                      <span className="badge badge-profit">Connected</span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      Verified via {userProfile?.email || 'Google Account'}
                    </div>
                  </div>

                  <div style={{ padding: '16px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <strong style={{ fontSize: '13px', color: 'var(--text-main)' }}>Email &amp; Password</strong>
                      <span className={userProfile?.has_password ? 'badge badge-profit' : 'badge badge-neutral'}>
                        {userProfile?.has_password ? 'Password Active' : 'Not Set'}
                      </span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      {userProfile?.has_password
                        ? 'Sign in directly with your email and password'
                        : 'Set a password below to enable email login'}
                    </div>
                  </div>
                </div>

                {/* Password Form Card */}
                <div style={{ padding: '24px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)' }}>
                  <h4 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '6px' }}>
                    {userProfile?.has_password ? 'Change Account Password' : 'Set Account Password'}
                  </h4>
                  <p style={{ fontSize: '12.5px', color: 'var(--text-muted)', marginBottom: '18px' }}>
                    {userProfile?.has_password
                      ? 'Update your account password. Must be at least 8 characters with letters and numbers.'
                      : 'Create a password for your account. You will then be able to log in with either Google or your email address and password.'}
                  </p>

                  {pwError && (
                    <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#FCA5A5', padding: '10px 14px', borderRadius: 'var(--radius-xs)', fontSize: '12px', marginBottom: '16px' }}>
                      {pwError}
                    </div>
                  )}

                  {pwSuccess && (
                    <div style={{ backgroundColor: 'rgba(34, 197, 94, 0.1)', border: '1px solid rgba(34, 197, 94, 0.3)', color: '#86EFAC', padding: '10px 14px', borderRadius: 'var(--radius-xs)', fontSize: '12px', marginBottom: '16px' }}>
                      {pwSuccess}
                    </div>
                  )}

                  <form onSubmit={handleSavePassword} style={{ maxWidth: '420px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    {userProfile?.has_password && (
                      <div>
                        <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase' }}>
                          Current Password
                        </label>
                        <input
                          type="password"
                          value={currentPassword}
                          onChange={(e) => setCurrentPassword(e.target.value)}
                          required
                          placeholder="••••••••"
                          style={{ width: '100%', padding: '9px 12px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-medium)', borderRadius: 'var(--radius-xs)', color: 'var(--text-main)', fontSize: '13px', outline: 'none', boxSizing: 'border-box' }}
                        />
                      </div>
                    )}

                    <div>
                      <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase' }}>
                        New Password (min 8 characters)
                      </label>
                      <input
                        type="password"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        required
                        placeholder="••••••••"
                        style={{ width: '100%', padding: '9px 12px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-medium)', borderRadius: 'var(--radius-xs)', color: 'var(--text-main)', fontSize: '13px', outline: 'none', boxSizing: 'border-box' }}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase' }}>
                        Confirm New Password
                      </label>
                      <input
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        required
                        placeholder="••••••••"
                        style={{ width: '100%', padding: '9px 12px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-medium)', borderRadius: 'var(--radius-xs)', color: 'var(--text-main)', fontSize: '13px', outline: 'none', boxSizing: 'border-box' }}
                      />
                    </div>

                    <div>
                      <button
                        type="submit"
                        disabled={pwLoading}
                        style={{
                          padding: '10px 20px',
                          fontSize: '13px',
                          fontWeight: 600,
                          backgroundColor: 'var(--color-action)',
                          color: '#FFFFFF',
                          border: 'none',
                          borderRadius: 'var(--radius-xs)',
                          cursor: pwLoading ? 'not-allowed' : 'pointer',
                          opacity: pwLoading ? 0.6 : 1,
                        }}
                      >
                        {pwLoading ? 'Saving Password...' : (userProfile?.has_password ? 'Update Password' : 'Save & Link Password')}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            </div>
          )}

          {activeSubTab === 'appearance' && (
            <div>
              <h3 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '8px' }}>
                Theme & Display Preferences
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '24px' }}>
                FinEx adapts smoothly to your environment. Choose between automatic computer system matching, clean daylight light mode, or deep graphite dark mode.
              </p>

              <ThemeToggle variant="cards" />
            </div>
          )}

          {isOwner && activeSubTab === 'sandbox' && (
            <div>
              <h3 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '8px' }}>
                Paper Trading Sandbox Controls
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '24px' }}>
                Manage the isolated virtual cash balance and simulated matching engine rules.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ padding: '20px', borderRadius: 'var(--radius-sm)', backgroundColor: 'rgba(245, 158, 11, 0.08)', border: '1px solid var(--color-virtual-border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-main)' }}>Current Virtual Cash</div>
                      <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Available capital for simulated execution</div>
                    </div>
                    <div className="tabular-nums" style={{ fontSize: '24px', fontWeight: 700, color: 'var(--color-virtual)' }}>
                      ₹{virtualCash.toLocaleString('en-IN')}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)' }}>Reset Sandbox Account</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Restores virtual cash to ₹50,000 and resets initial holdings</div>
                  </div>
                  <button
                    onClick={handleReset}
                    className="btn btn-secondary"
                    style={{ color: 'var(--color-virtual)', borderColor: 'var(--color-virtual-border)' }}
                  >
                    {resetSuccess ? 'Account Reset ✓' : 'Reset to ₹50,000'}
                  </button>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)' }}>Matching Engine Reference</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>NSE Real-time observation quotes with zero-slippage paper fills</div>
                  </div>
                  <span className="badge badge-profit">Active (Live)</span>
                </div>
              </div>
            </div>
          )}

          {activeSubTab === 'compliance' && (
            <div>
              <h3 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '8px' }}>
                Regulatory Consent & Educational Grounding
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '24px' }}>
                FinEx operates strictly within SEBI and RBI educational research frameworks.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ padding: '16px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <strong style={{ color: 'var(--text-main)' }}>SEBI Paper Trading Risk Disclosure</strong>
                    <span className="badge badge-profit">Accepted v1.0</span>
                  </div>
                  <p style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                    FinEx is an educational platform designed for learning portfolio management, risk evaluation, and asset allocation. All transactions use simulated virtual currency with zero brokerage or financial liability.
                  </p>
                </div>

                <div style={{ padding: '16px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <strong style={{ color: 'var(--text-main)' }}>AI Answer Grounding Policy</strong>
                    <span className="badge badge-cyan">Active Enforcement</span>
                  </div>
                  <p style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                    FinEx AI strictly cites authentic regulatory corpus documents (SEBI Master Circular, RBI Master Directions, NSE Guidelines). Hallucinated recommendations or speculative stock tips are deterministically rejected.
                  </p>
                </div>

                <div style={{ padding: '16px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <strong style={{ color: 'var(--text-main)', fontSize: '13px' }}>Public Legal &amp; Governance Documents</strong>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                      Review our verified data privacy commitments and terms of service.
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '12px' }}>
                    <a
                      href="/privacy"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-secondary"
                      style={{ fontSize: '12px', padding: '6px 12px', textDecoration: 'none' }}
                    >
                      Privacy Policy ↗
                    </a>
                    <a
                      href="/terms"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-secondary"
                      style={{ fontSize: '12px', padding: '6px 12px', textDecoration: 'none' }}
                    >
                      Terms of Service ↗
                    </a>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
