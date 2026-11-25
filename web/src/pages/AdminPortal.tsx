import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  apiClient,
  AdminMeResponse,
  AdminOverviewResponse,
  AdminSystemHealthResponse,
  AdminOrderItem,
} from '../api/client';
import { AdminErrorsPanel } from '../components/admin/AdminErrorsPanel';
import { AdminOrdersPanel } from '../components/admin/AdminOrdersPanel';
import { AdminUsersPanel } from '../components/admin/AdminUsersPanel';
import { ThemeToggle } from '../components/common/ThemeToggle';
import {
  formatOrderTimestamp,
  normalizeOrderStatusCounts,
  resolveOrderFailureDetails,
} from '../domain/paperTradingOverview';

interface AdminPortalProps {
  onNavigateToApp?: () => void;
}

type AdminTab = 'overview' | 'users' | 'orders' | 'health' | 'errors';

export const AdminPortal: React.FC<AdminPortalProps> = ({ onNavigateToApp }) => {
  const [adminAuthState, setAdminAuthState] = useState<'checking' | 'login' | 'authenticated'>('checking');
  const [adminUser, setAdminUser] = useState<AdminMeResponse | null>(null);
  const [activeTab, setActiveTab] = useState<AdminTab>('overview');
  const [loginLoading, setLoginLoading] = useState<boolean>(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  // Overview State
  const [overviewData, setOverviewData] = useState<AdminOverviewResponse | null>(null);
  const [overviewLoading, setOverviewLoading] = useState<boolean>(false);
  const [overviewError, setOverviewError] = useState<string | null>(null);

  // Users State (managed inside AdminUsersPanel)
  const [usersLoading, setUsersLoading] = useState<boolean>(false);
  const [usersRefreshTick, setUsersRefreshTick] = useState<number>(0);

  // Orders State (managed inside AdminOrdersPanel)
  const [ordersLoading, setOrdersLoading] = useState<boolean>(false);
  const [ordersRefreshTick, setOrdersRefreshTick] = useState<number>(0);
  const [ordersPresetStatus, setOrdersPresetStatus] = useState<string>('');

  // System Health State
  const [healthData, setHealthData] = useState<AdminSystemHealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(false);
  const [healthError, setHealthError] = useState<string | null>(null);

  // Errors Monitoring State
  const [errorsLoading, setErrorsLoading] = useState<boolean>(false);
  const [errorsRefreshTick, setErrorsRefreshTick] = useState<number>(0);

  const googleClientId =
    (import.meta as any).env?.VITE_GOOGLE_CLIENT_ID ||
    '71626572471-2333p55kgim64b3738oabca9l9ss9th0.apps.googleusercontent.com';

  const googleBtnContainerRef = useRef<HTMLDivElement>(null);

  // 1. Initial Session Check (Dedicated Admin Token)
  useEffect(() => {
    let isMounted = true;
    const verifySession = async () => {
      const token = apiClient.getAdminToken();
      if (!token || apiClient.isTokenExpired(token)) {
        if (isMounted) setAdminAuthState('login');
        return;
      }

      try {
        const me = await apiClient.admin.getMe();
        if (!isMounted) return;
        setAdminUser(me);
        setAdminAuthState('authenticated');
      } catch (err: any) {
        if (!isMounted) return;
        // On 401 or 403, clear only admin token and show login
        apiClient.setAdminToken(null);
        if (
          err?.status === 403 ||
          err?.message?.includes('403') ||
          err?.message?.toLowerCase().includes('restricted') ||
          err?.message?.toLowerCase().includes('forbidden')
        ) {
          setLoginError('Access restricted: Admin portal is strictly restricted to the platform owner.');
        }
        setAdminAuthState('login');
      }
    };

    verifySession();
    return () => {
      isMounted = false;
    };
  }, []);

  // 2. Google Identity Services Setup for Admin Login
  useEffect(() => {
    if (adminAuthState !== 'login') return;

    if (typeof window !== 'undefined' && (window as any).google?.accounts?.id) {
      try {
        (window as any).google.accounts.id.initialize({
          client_id: googleClientId,
          callback: async (response: { credential?: string }) => {
            if (!response?.credential) {
              setLoginError('Google Sign-In did not return an identity token.');
              return;
            }
            setLoginLoading(true);
            setLoginError(null);
            try {
              await apiClient.admin.googleLogin(response.credential);
              const me = await apiClient.admin.getMe();
              setAdminUser(me);
              setAdminAuthState('authenticated');
            } catch (err: any) {
              console.error('Admin Google sign-in failed:', err);
              const msg =
                err?.status === 403
                  ? 'Access Restricted: This Google account is not authorized for administrative access. Only the platform owner may access this portal.'
                  : err?.message || 'Administrative Google sign-in failed. Please try again.';
              setLoginError(msg);
            } finally {
              setLoginLoading(false);
            }
          },
        });

        if (googleBtnContainerRef.current && (window as any).google?.accounts?.id?.renderButton) {
          (window as any).google.accounts.id.renderButton(googleBtnContainerRef.current, {
            theme: 'outline',
            size: 'large',
            width: 280,
            text: 'continue_with',
            shape: 'rectangular',
          });
        }
      } catch (gisErr) {
        console.warn('GIS initialization notice:', gisErr);
      }
    }
  }, [adminAuthState, googleClientId]);

  const handleGoogleSignInClick = () => {
    setLoginLoading(true);
    setLoginError(null);

    const timer = setTimeout(() => {
      setLoginLoading(false);
    }, 4000);

    try {
      if (typeof window !== 'undefined' && (window as any).google?.accounts?.id) {
        (window as any).google.accounts.id.prompt((notification: any) => {
          clearTimeout(timer);
          if (notification?.isNotDisplayed?.() || notification?.isSkippedMoment?.()) {
            setLoginLoading(false);
          }
        });
      } else {
        clearTimeout(timer);
        throw new Error('Google Identity Services script is loading. Please try again.');
      }
    } catch (err: any) {
      clearTimeout(timer);
      setLoginError(err?.message || 'Google sign-in initialization failed.');
      setLoginLoading(false);
    }
  };

  const handleSignOut = async () => {
    try {
      await apiClient.admin.logout();
    } catch {
      // Ignore logout errors
    }
    setAdminUser(null);
    setAdminAuthState('login');
  };

  const handleNavigateToInvestor = () => {
    if (onNavigateToApp) {
      onNavigateToApp();
      return;
    }
    if (typeof window !== 'undefined') {
      window.history.pushState(null, '', '/');
      window.location.hash = 'overview';
      window.dispatchEvent(new PopStateEvent('popstate'));
    }
  };

  // ---------------------------------------------------------------------------
  // Data Fetching for Authenticated Dashboard
  // ---------------------------------------------------------------------------
  const fetchOverview = useCallback(async () => {
    setOverviewLoading(true);
    setOverviewError(null);
    try {
      const data = await apiClient.admin.getOverview();
      setOverviewData(data);
    } catch (err: any) {
      if (err?.status === 401) {
        setAdminAuthState('login');
        return;
      }
      setOverviewError(err?.message || 'Failed to load administrative overview');
    } finally {
      setOverviewLoading(false);
    }
  }, []);

  const fetchHealth = useCallback(async () => {
    setHealthLoading(true);
    setHealthError(null);
    try {
      const data = await apiClient.admin.getSystemHealth();
      setHealthData(data);
    } catch (err: any) {
      if (err?.status === 401) {
        setAdminAuthState('login');
        return;
      }
      setHealthError(err?.message || 'Failed to load system diagnostics');
    } finally {
      setHealthLoading(false);
    }
  }, []);

  useEffect(() => {
    if (adminAuthState !== 'authenticated') return;
    if (activeTab === 'overview') fetchOverview();
    else if (activeTab === 'health') fetchHealth();
  }, [adminAuthState, activeTab, fetchOverview, fetchHealth]);

  // ---------------------------------------------------------------------------
  // RENDER: Checking Session
  // ---------------------------------------------------------------------------
  if (adminAuthState === 'checking') {
    return (
      <div
        style={{
          minHeight: '100vh',
          backgroundColor: '#000000',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
          <span style={{ fontSize: '32px', fontWeight: 900, color: '#FFFFFF', letterSpacing: '-0.03em' }}>Fin</span>
          <span style={{ fontSize: '32px', fontWeight: 900, color: 'var(--color-action, #3B82F6)', letterSpacing: '-0.03em' }}>Ex</span>
          <span
            style={{
              marginLeft: '8px',
              fontSize: '12px',
              fontWeight: 700,
              padding: '2px 8px',
              borderRadius: '4px',
              backgroundColor: 'rgba(59, 130, 246, 0.2)',
              color: '#60A5FA',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
            }}
          >
            Admin Portal
          </span>
        </div>
        <div style={{ fontSize: '12px', color: '#8E8E93', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
          Verifying Owner Authorization...
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // RENDER: Admin Login Screen
  // ---------------------------------------------------------------------------
  if (adminAuthState === 'login') {
    return (
      <div
        style={{
          minHeight: '100vh',
          backgroundColor: 'var(--bg-main, #0A0A0C)',
          display: 'flex',
          flexDirection: 'column',
          boxSizing: 'border-box',
        }}
      >
        {/* Top Navbar */}
        <header className="admin-portal-header">
          <div className="admin-header-brand-group">
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '2px', whiteSpace: 'nowrap' }}>
              <span style={{ fontSize: '20px', fontWeight: 900, color: 'var(--text-main, #FFFFFF)', letterSpacing: '-0.03em' }}>Fin</span>
              <span style={{ fontSize: '20px', fontWeight: 900, color: 'var(--color-action, #3B82F6)', letterSpacing: '-0.03em' }}>Ex</span>
            </div>
            <span className="admin-header-badge">
              <span className="admin-badge-full">Admin Portal</span>
              <span className="admin-badge-short">Admin</span>
            </span>
          </div>

          <div className="admin-header-actions-group">
            <ThemeToggle variant="segmented" />
            <button
              onClick={handleNavigateToInvestor}
              className="admin-investor-btn"
              title="Open Investor Workspace"
            >
              <span className="investor-link-full">Investor Workspace ↗</span>
              <span className="investor-link-short">Investor ↗</span>
              <span className="investor-link-mini">App ↗</span>
            </button>
          </div>
        </header>

        {/* Center Card */}
        <main
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px 12px',
            boxSizing: 'border-box',
            width: '100%',
            maxWidth: '100vw',
            overflowX: 'hidden',
          }}
        >
          <div className="admin-login-card">
            <div
              style={{
                width: '46px',
                height: '46px',
                borderRadius: '50%',
                backgroundColor: 'rgba(59, 130, 246, 0.12)',
                color: 'var(--color-action, #3B82F6)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '20px',
                margin: '0 auto 14px auto',
              }}
            >
              🛡️
            </div>

            <h1 style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-main, #FFFFFF)', margin: '0 0 6px 0', letterSpacing: '-0.02em' }}>
              Platform Administration
            </h1>
            <p style={{ fontSize: '13px', color: 'var(--text-muted, #8E8E93)', margin: '0 0 20px 0', lineHeight: 1.5 }}>
              Dedicated operational portal for platform diagnostics, user oversight, and paper order verification.
            </p>

            {loginError && (
              <div
                style={{
                  backgroundColor: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid var(--color-loss, #EF4444)',
                  borderRadius: 'var(--radius-xs, 4px)',
                  padding: '10px 12px',
                  marginBottom: '16px',
                  fontSize: '12px',
                  color: 'var(--color-loss, #EF4444)',
                  textAlign: 'left',
                  lineHeight: 1.4,
                }}
              >
                {loginError}
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', alignItems: 'center' }}>
              {/* Google GIS rendered button container */}
              <div id="admin-google-btn-container" ref={googleBtnContainerRef} style={{ display: 'none' }} />

              {/* Custom Google Button */}
              <button
                type="button"
                onClick={handleGoogleSignInClick}
                disabled={loginLoading}
                className="auth-google-btn"
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '10px',
                  padding: '11px 18px',
                  borderRadius: 'var(--radius-xs, 4px)',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: loginLoading ? 'wait' : 'pointer',
                  transition: 'background 0.2s ease, border-color 0.2s ease',
                }}
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
                <span>{loginLoading ? 'Authenticating Owner...' : 'Sign in with Google'}</span>
              </button>

              <button
                type="button"
                onClick={handleNavigateToInvestor}
                style={{
                  width: '100%',
                  padding: '10px 16px',
                  backgroundColor: 'transparent',
                  border: 'none',
                  color: 'var(--text-muted, #8E8E93)',
                  fontSize: '13px',
                  cursor: 'pointer',
                  textDecoration: 'underline',
                }}
              >
                ← Return to FinEx Investor App
              </button>
            </div>

            <div
              style={{
                marginTop: '28px',
                paddingTop: '20px',
                borderTop: '1px solid var(--border-subtle, rgba(255,255,255,0.08))',
                fontSize: '11px',
                color: 'var(--text-muted, #8E8E93)',
                textAlign: 'left',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                lineHeight: 1.4,
              }}
            >
              <div>🔒 <strong>Owner Verification:</strong> Access is restricted strictly to the configured platform owner Google account.</div>
              <div>👁️ <strong>Read-Only Governance:</strong> Administrative controls are strictly observation-only.</div>
            </div>
          </div>
        </main>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // RENDER: Authenticated Dashboard Tabs
  // ---------------------------------------------------------------------------

  const renderOverviewTab = () => {
    if (overviewLoading && !overviewData) {
      return (
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)' }}>
          Loading operational overview...
        </div>
      );
    }
    if (overviewError) {
      return (
        <div style={{ padding: '24px', backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--color-loss)', borderRadius: '4px' }}>
          {overviewError}
        </div>
      );
    }
    if (!overviewData) return null;

    const totalOrders = overviewData.total_orders || 0;
    const statusMap = normalizeOrderStatusCounts(overviewData.orders_by_status);
    const filledOrders = statusMap.FILLED || 0;
    const rejectedOrders = statusMap.REJECTED || 0;
    const hasOrders = totalOrders > 0;
    const successRateText = hasOrders ? `${((filledOrders / totalOrders) * 100).toFixed(1)}%` : 'No orders yet';
    const recentOrders = overviewData.recent_orders || [];

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {/* Metric Cards Grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(200px, 100%), 1fr))',
            gap: '16px',
          }}
        >
          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '20px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Total Users</div>
            <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>{overviewData.total_users.toLocaleString()}</div>
            <div style={{ fontSize: '11px', color: 'var(--color-profit)', marginTop: '4px' }}>{overviewData.verified_users} verified emails</div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '20px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Onboarded Users</div>
            <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>{overviewData.onboarding_completed_users.toLocaleString()}</div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
              {overviewData.total_users > 0 ? ((overviewData.onboarding_completed_users / overviewData.total_users) * 100).toFixed(0) : 0}% completion
            </div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '20px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Recorded Paper Orders</div>
            <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>{totalOrders.toLocaleString()}</div>
            <div style={{ fontSize: '11px', color: 'var(--color-action)', marginTop: '4px' }}>
              {hasOrders ? `${filledOrders} filled · ${rejectedOrders} rejected` : 'No persisted order records'}
            </div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '20px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Recorded Fill Share</div>
            <div
              style={{
                fontSize: hasOrders ? '28px' : '20px',
                fontWeight: 800,
                color: hasOrders ? 'var(--color-profit)' : 'var(--text-muted)',
                marginTop: '4px',
              }}
            >
              {successRateText}
            </div>
            <div style={{ fontSize: '11px', color: hasOrders && rejectedOrders > 0 ? 'var(--color-loss)' : 'var(--text-muted)', marginTop: '4px' }}>
              {hasOrders
                ? `${statusMap.PENDING || 0} pending · ${statusMap.CANCELLED || 0} cancelled`
                : 'Unpersisted client/network errors excluded'}
            </div>
          </div>
        </div>

        {/* Recorded Status Breakdown & Recent Activity */}
        <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px', marginBottom: '14px' }}>
            <div>
              <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>Paper Order Status Breakdown</h2>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Counts across persisted paper order records only (failed pre-persistence requests are excluded)
              </div>
            </div>
            <button
              type="button"
              onClick={() => {
                setOrdersPresetStatus('');
                setActiveTab('orders');
              }}
              style={{ background: 'none', border: 'none', color: 'var(--color-action)', fontSize: '12px', cursor: 'pointer', padding: 0, fontWeight: 600 }}
            >
              Open Paper Trading →
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(150px, 100%), 1fr))', gap: '10px', marginBottom: recentOrders.length > 0 ? '18px' : '0' }}>
            {Object.entries(statusMap).map(([statusKey, count]) => (
              <div
                key={statusKey}
                style={{
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-xs)',
                  border: '1px solid var(--border-subtle)',
                  backgroundColor: 'var(--bg-input)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <span
                  className={`admin-pill ${
                    statusKey === 'FILLED'
                      ? 'admin-pill-positive'
                      : statusKey === 'REJECTED'
                        ? 'admin-pill-negative'
                        : statusKey === 'PENDING'
                          ? 'admin-pill-warning'
                          : 'admin-pill-neutral'
                  }`}
                >
                  {statusKey}
                </span>
                <strong style={{ fontSize: '16px', fontFamily: 'var(--font-mono)', color: 'var(--text-main)' }}>
                  {count.toLocaleString()}
                </strong>
              </div>
            ))}
          </div>

          {recentOrders.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '16px 0 4px 0', color: 'var(--text-muted)', fontSize: '12px' }}>
              No paper orders recorded yet.
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                    <th style={{ padding: '8px' }}>Time</th>
                    <th style={{ padding: '8px' }}>Order ID</th>
                    <th style={{ padding: '8px' }}>Symbol</th>
                    <th style={{ padding: '8px' }}>Side</th>
                    <th style={{ padding: '8px' }}>Qty</th>
                    <th style={{ padding: '8px' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {recentOrders.map((o: AdminOrderItem) => (
                    <tr key={o.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                      <td style={{ padding: '9px 8px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                        {formatOrderTimestamp(o.created_at)}
                      </td>
                      <td style={{ padding: '9px 8px', fontFamily: 'var(--font-mono)', color: 'var(--text-main)' }}>
                        {o.id.length > 12 ? `${o.id.slice(0, 12)}…` : o.id}
                      </td>
                      <td style={{ padding: '9px 8px', fontWeight: 700, color: 'var(--text-main)' }}>{o.symbol}</td>
                      <td style={{ padding: '9px 8px' }}>
                        <span className={`admin-pill ${o.side === 'BUY' ? 'admin-pill-positive' : 'admin-pill-negative'}`}>
                          {o.side}
                        </span>
                      </td>
                      <td style={{ padding: '9px 8px', fontFamily: 'var(--font-mono)' }}>{o.quantity}</td>
                      <td style={{ padding: '9px 8px' }}>
                        <span
                          className={`admin-pill ${
                            o.status === 'FILLED'
                              ? 'admin-pill-positive'
                              : o.status === 'REJECTED'
                                ? 'admin-pill-negative'
                                : o.status === 'PENDING'
                                  ? 'admin-pill-warning'
                                  : 'admin-pill-neutral'
                          }`}
                        >
                          {o.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Recent Rejected Orders Table */}
        <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px', marginBottom: '16px' }}>
            <div>
              <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>Recent Rejected Orders</h2>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>Latest execution safeguards triggered by risk or liquidity checks</div>
            </div>
            <button
              type="button"
              onClick={() => {
                setOrdersPresetStatus('REJECTED');
                setActiveTab('orders');
              }}
              style={{ background: 'none', border: 'none', color: 'var(--color-action)', fontSize: '12px', cursor: 'pointer', padding: 0, fontWeight: 600 }}
            >
              View rejected orders →
            </button>
          </div>

          {overviewData.recent_rejected_orders.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--text-muted)', fontSize: '13px' }}>
              No rejected orders recorded.
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                    <th style={{ padding: '8px' }}>Order ID</th>
                    <th style={{ padding: '8px' }}>Symbol</th>
                    <th style={{ padding: '8px' }}>Side</th>
                    <th style={{ padding: '8px' }}>Qty</th>
                    <th style={{ padding: '8px' }}>Safeguard / Failure Details</th>
                    <th style={{ padding: '8px' }}>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {overviewData.recent_rejected_orders.map((o: AdminOrderItem) => (
                    <tr key={o.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                      <td style={{ padding: '10px 8px', fontFamily: 'var(--font-mono)' }}>
                        {o.id.length > 12 ? `${o.id.slice(0, 12)}…` : o.id}
                      </td>
                      <td style={{ padding: '10px 8px', fontWeight: 700 }}>{o.symbol}</td>
                      <td style={{ padding: '10px 8px' }}>
                        <span className={`admin-pill ${o.side === 'BUY' ? 'admin-pill-positive' : 'admin-pill-negative'}`}>
                          {o.side}
                        </span>
                      </td>
                      <td style={{ padding: '10px 8px', fontFamily: 'var(--font-mono)' }}>{o.quantity}</td>
                      <td style={{ padding: '10px 8px', color: 'var(--color-loss)' }}>
                        {resolveOrderFailureDetails(o)}
                      </td>
                      <td style={{ padding: '10px 8px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                        {formatOrderTimestamp(o.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderUsersTab = () => (
    <AdminUsersPanel
      refreshTrigger={usersRefreshTick}
      onLoadingChange={setUsersLoading}
      onUnauthorized={() => setAdminAuthState('login')}
    />
  );

  const renderOrdersTab = () => (
    <AdminOrdersPanel
      refreshTrigger={ordersRefreshTick}
      initialStatusFilter={ordersPresetStatus}
      onLoadingChange={setOrdersLoading}
      onUnauthorized={() => setAdminAuthState('login')}
    />
  );

  const renderHealthTab = () => {
    if (healthLoading && !healthData) {
      return (
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)' }}>
          Loading system health diagnostics...
        </div>
      );
    }
    if (healthError) {
      return (
        <div style={{ padding: '24px', backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--color-loss)', borderRadius: '4px' }}>
          {healthError}
        </div>
      );
    }
    if (!healthData) return null;

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(260px, 100%), 1fr))', gap: '16px' }}>
          {/* Backend Process */}
          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-main)' }}>FastAPI Backend Process</div>
              <span
                style={{
                  fontSize: '11px',
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-xs)',
                  backgroundColor: 'rgba(5, 150, 105, 0.12)',
                  color: 'var(--color-profit)',
                  fontWeight: 600,
                }}
              >
                ONLINE
              </span>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div>App Name: <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>{healthData.backend.app}</span></div>
              <div>Environment: <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>{healthData.backend.environment}</span></div>
              <div>Release: <span style={{ color: 'var(--text-main)', fontFamily: 'var(--font-mono)' }}>{healthData.backend.version}</span></div>
            </div>
          </div>

          {/* Database Connectivity */}
          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-main)' }}>PostgreSQL Database</div>
              <span
                style={{
                  fontSize: '11px',
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-xs)',
                  backgroundColor: healthData.database.status === 'ready' ? 'rgba(5, 150, 105, 0.12)' : 'rgba(239, 68, 68, 0.12)',
                  color: healthData.database.status === 'ready' ? 'var(--color-profit)' : 'var(--color-loss)',
                  fontWeight: 600,
                }}
              >
                {healthData.database.status === 'ready' ? 'CONNECTED' : 'DOWN'}
              </span>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div>Status: <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>{healthData.database.status}</span></div>
              <div>Engine: <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>{(healthData.database as any).target || healthData.database.message || 'Live PostgreSQL Engine'}</span></div>
              {healthData.database.error && (
                <div style={{ color: 'var(--color-loss)' }}>Error: {healthData.database.error}</div>
              )}
            </div>
          </div>

          {/* Market Feed Integration */}
          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-main)' }}>Angel One SmartAPI Feed</div>
              <span
                style={{
                  fontSize: '11px',
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-xs)',
                  backgroundColor: healthData.angel_one.is_configured ? 'rgba(59, 130, 246, 0.12)' : 'rgba(255, 255, 255, 0.08)',
                  color: healthData.angel_one.is_configured ? 'var(--color-action)' : 'var(--text-muted)',
                  fontWeight: 600,
                }}
              >
                {healthData.angel_one.is_configured ? 'CONFIGURED (UNVERIFIED LIVE)' : 'SIMULATED / UNCONFIGURED'}
              </span>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div>Mode: <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>{healthData.market_data.mode}</span></div>
              <div>Credentials: <span style={{ color: healthData.angel_one.is_configured ? 'var(--color-action)' : 'var(--text-muted)', fontWeight: 600 }}>{healthData.angel_one.is_configured ? 'Configured (Live stream unverified)' : 'Unconfigured'}</span></div>
              <div>Demo Simulation: <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>{healthData.market_data.enable_demo_simulation ? 'Enabled' : 'Disabled'}</span></div>
              <div>Circuit Breaker: <span style={{ color: healthData.angel_one.is_circuit_open ? 'var(--color-loss)' : 'var(--color-profit)', fontWeight: 600 }}>
                {healthData.angel_one.is_circuit_open ? 'TRIPPED' : 'CLOSED (NORMAL)'}
              </span></div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '6px', padding: '6px 8px', backgroundColor: 'rgba(255, 255, 255, 0.03)', borderRadius: 'var(--radius-xs)', borderLeft: '2px solid var(--color-action)' }}>
                ℹ️ <strong>Operational Notice:</strong> Configuration reflects present environment credentials. It does not prove that live market data or exchange streaming is working.
              </div>
            </div>
          </div>

          {/* Email Integration */}
          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-main)' }}>Email Service (SMTP)</div>
              <span
                style={{
                  fontSize: '11px',
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-xs)',
                  backgroundColor: healthData.email.is_configured ? 'rgba(59, 130, 246, 0.12)' : 'rgba(255, 255, 255, 0.08)',
                  color: healthData.email.is_configured ? 'var(--color-action)' : 'var(--text-muted)',
                  fontWeight: 600,
                }}
              >
                {healthData.email.is_configured ? 'CONFIGURED (DELIVERY UNVERIFIED)' : 'DEV MODE (UNCONFIGURED)'}
              </span>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div>Host: <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>{healthData.email.host}</span></div>
              <div>From Address: <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>{healthData.email.from_email}</span></div>
              <div>TLS: <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>{healthData.email.use_tls ? 'Active' : 'Disabled'}</span></div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '6px', padding: '6px 8px', backgroundColor: 'rgba(255, 255, 255, 0.03)', borderRadius: 'var(--radius-xs)', borderLeft: '2px solid var(--color-action)' }}>
                ℹ️ <strong>Operational Notice:</strong> SMTP host configuration detected. It does not prove that email delivery to recipient inboxes is working.
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderErrorsTab = () => (
    <AdminErrorsPanel
      refreshTrigger={errorsRefreshTick}
      onLoadingChange={setErrorsLoading}
      onUnauthorized={() => setAdminAuthState('login')}
    />
  );

  // ---------------------------------------------------------------------------
  // RENDER: Authenticated Dashboard Shell
  // ---------------------------------------------------------------------------
  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: 'var(--bg-main, #0A0A0C)',
        color: 'var(--text-main, #FFFFFF)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Dedicated Admin Header */}
      <header
        style={{
          borderBottom: '1px solid var(--border-subtle, rgba(255,255,255,0.08))',
          backgroundColor: 'var(--bg-card, #141418)',
          position: 'sticky',
          top: 0,
          zIndex: 100,
          width: '100%',
          maxWidth: '100vw',
          overflowX: 'hidden',
          boxSizing: 'border-box',
        }}
      >
        <div className="admin-signedin-header-inner">
          {/* Brand + Admin Tag */}
          <div className="admin-header-brand-group">
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '3px', whiteSpace: 'nowrap' }}>
              <span style={{ fontSize: '20px', fontWeight: 900, color: 'var(--text-main)', letterSpacing: '-0.03em' }}>Fin</span>
              <span style={{ fontSize: '20px', fontWeight: 900, color: 'var(--color-action, #3B82F6)', letterSpacing: '-0.03em' }}>Ex</span>
            </div>
            <span className="admin-header-badge">
              <span className="admin-badge-full">Admin Portal</span>
              <span className="admin-badge-short">Admin</span>
            </span>
            <span className="admin-readonly-pill">
              Read-Only
            </span>
          </div>

          {/* Navigation Tabs */}
          <nav className="admin-signedin-nav">
            {[
              { id: 'overview' as const, label: 'Overview' },
              { id: 'users' as const, label: 'Users' },
              { id: 'orders' as const, label: 'Paper Trading' },
              { id: 'health' as const, label: 'System Health' },
              { id: 'errors' as const, label: 'Errors' },
            ].map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    padding: '6px 12px',
                    fontSize: '12px',
                    fontWeight: isActive ? 700 : 500,
                    borderRadius: 'var(--radius-xs, 4px)',
                    backgroundColor: isActive ? 'var(--bg-card, #141418)' : 'transparent',
                    color: isActive ? 'var(--text-main, #FFFFFF)' : 'var(--text-muted, #8E8E93)',
                    border: isActive ? '1px solid var(--border-subtle, rgba(255,255,255,0.12))' : '1px solid transparent',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  {tab.label}
                </button>
              );
            })}
          </nav>

          {/* Right Actions: Theme, Owner Pill, Investor Link, Sign Out */}
          <div className="admin-header-actions-group">
            <ThemeToggle variant="segmented" />

            {adminUser && (
              <div className="admin-owner-pill">
                <span style={{ color: 'var(--color-profit, #059669)' }}>●</span>
                <span style={{ color: 'var(--text-main, #FFFFFF)', fontWeight: 600 }}>{adminUser.display_name}</span>
                <span className="admin-owner-verified-tag" style={{ fontSize: '11px', color: 'var(--color-action, #3B82F6)' }}>(Google Verified)</span>
              </div>
            )}

            <button
              onClick={handleNavigateToInvestor}
              className="admin-investor-btn"
              title="Open investor workspace without terminating admin session"
            >
              <span className="investor-link-full">Investor Workspace ↗</span>
              <span className="investor-link-short">Investor ↗</span>
              <span className="investor-link-mini">App ↗</span>
            </button>

            <button
              onClick={handleSignOut}
              className="admin-signout-btn"
              title="Sign out of Admin Portal"
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="admin-main-container">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', marginBottom: '20px' }}>
          <div>
            <h1 style={{ fontSize: '24px', fontWeight: 800, margin: 0, letterSpacing: '-0.02em' }}>
              {activeTab === 'overview' && 'Platform Overview & Safe Diagnostics'}
              {activeTab === 'users' && 'User Directory & Onboarding Status'}
              {activeTab === 'orders' && 'Paper Trading Orders & Audit Trail'}
              {activeTab === 'health' && 'System Health & Backing Services'}
              {activeTab === 'errors' && 'Server Error Monitoring & Diagnostics'}
            </h1>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
              {activeTab === 'overview' && 'Executive KPIs, order success ratios, and recent rejected simulated trades.'}
              {activeTab === 'users' && 'Searchable registry of registered users with safe public projections.'}
              {activeTab === 'orders' && 'Full append-only simulated trading order stream and execution safeguards.'}
              {activeTab === 'health' && 'Live operational status of PostgreSQL, Angel One SmartAPI, and SMTP services.'}
              {activeTab === 'errors' && 'Durable, sanitized server-side error logs and correlation ID tracking.'}
            </p>
          </div>

          <button
            onClick={() => {
              if (activeTab === 'overview') fetchOverview();
              else if (activeTab === 'users') setUsersRefreshTick((n) => n + 1);
              else if (activeTab === 'orders') setOrdersRefreshTick((n) => n + 1);
              else if (activeTab === 'health') fetchHealth();
              else if (activeTab === 'errors') setErrorsRefreshTick((n) => n + 1);
            }}
            disabled={overviewLoading || usersLoading || ordersLoading || healthLoading || errorsLoading}
            style={{
              padding: '6px 14px',
              fontSize: '12px',
              fontWeight: 600,
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-xs)',
              color: 'var(--text-main)',
              cursor: overviewLoading || usersLoading || ordersLoading || healthLoading || errorsLoading ? 'wait' : 'pointer',
            }}
          >
            {overviewLoading || usersLoading || ordersLoading || healthLoading || errorsLoading ? 'Refreshing...' : '↻ Refresh'}
          </button>
        </div>

        {activeTab === 'overview' && renderOverviewTab()}
        {activeTab === 'users' && renderUsersTab()}
        {activeTab === 'orders' && renderOrdersTab()}
        {activeTab === 'health' && renderHealthTab()}
        {activeTab === 'errors' && renderErrorsTab()}
      </main>

      {/* Footer */}
      <footer
        style={{
          borderTop: '1px solid var(--border-subtle, rgba(255,255,255,0.08))',
          padding: '16px 24px',
          textAlign: 'center',
          fontSize: '11px',
          color: 'var(--text-muted, #8E8E93)',
        }}
      >
        FinEx Operational Administration · Read-Only Mode · Protected by Cryptographic Server-Side Owner Verification
      </footer>
    </div>
  );
};

export default AdminPortal;
