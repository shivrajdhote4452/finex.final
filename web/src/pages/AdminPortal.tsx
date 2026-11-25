import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  apiClient,
  AdminMeResponse,
  AdminOverviewResponse,
  AdminUsersResponse,
  AdminOrdersResponse,
  AdminSystemHealthResponse,
  AdminErrorItem,
  AdminErrorsResponse,
  AdminErrorSummaryResponse,
  AdminUserItem,
  AdminOrderItem,
} from '../api/client';
import { ThemeToggle } from '../components/common/ThemeToggle';

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

  // Users State
  const [usersData, setUsersData] = useState<AdminUsersResponse | null>(null);
  const [usersLoading, setUsersLoading] = useState<boolean>(false);
  const [usersError, setUsersError] = useState<string | null>(null);
  const [userSearch, setUserSearch] = useState<string>('');
  const [userPage, setUserPage] = useState<number>(1);
  const [userFilterActive, setUserFilterActive] = useState<boolean | undefined>(undefined);
  const [userFilterVerified, setUserFilterVerified] = useState<boolean | undefined>(undefined);
  const [userFilterOnboarded, setUserFilterOnboarded] = useState<boolean | undefined>(undefined);

  // Orders State
  const [ordersData, setOrdersData] = useState<AdminOrdersResponse | null>(null);
  const [ordersLoading, setOrdersLoading] = useState<boolean>(false);
  const [ordersError, setOrdersError] = useState<string | null>(null);
  const [orderSearch, setOrderSearch] = useState<string>('');
  const [orderStatus, setOrderStatus] = useState<string>('');
  const [orderSide, setOrderSide] = useState<string>('');
  const [orderPage, setOrderPage] = useState<number>(1);

  // System Health State
  const [healthData, setHealthData] = useState<AdminSystemHealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(false);
  const [healthError, setHealthError] = useState<string | null>(null);

  // Errors Monitoring State
  const [errorsData, setErrorsData] = useState<AdminErrorsResponse | null>(null);
  const [errorsLoading, setErrorsLoading] = useState<boolean>(false);
  const [errorsError, setErrorsError] = useState<string | null>(null);
  const [errorSummary, setErrorSummary] = useState<AdminErrorSummaryResponse | null>(null);
  const [errorSearch, setErrorSearch] = useState<string>('');
  const [errorCategory, setErrorCategory] = useState<string>('');
  const [errorStatusCode, setErrorStatusCode] = useState<string>('');
  const [errorPage, setErrorPage] = useState<number>(1);
  const [copiedId, setCopiedId] = useState<string | null>(null);

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

  const fetchUsers = useCallback(async () => {
    setUsersLoading(true);
    setUsersError(null);
    try {
      const data = await apiClient.admin.getUsers({
        page: userPage,
        limit: 15,
        search: userSearch.trim() || undefined,
        is_active: userFilterActive,
        email_verified: userFilterVerified,
        onboarding_completed: userFilterOnboarded,
      });
      setUsersData(data);
    } catch (err: any) {
      if (err?.status === 401) {
        setAdminAuthState('login');
        return;
      }
      setUsersError(err?.message || 'Failed to load user directory');
    } finally {
      setUsersLoading(false);
    }
  }, [userPage, userSearch, userFilterActive, userFilterVerified, userFilterOnboarded]);

  const fetchOrders = useCallback(async () => {
    setOrdersLoading(true);
    setOrdersError(null);
    try {
      const data = await apiClient.admin.getOrders({
        page: orderPage,
        limit: 15,
        search: orderSearch.trim() || undefined,
        status: orderStatus || undefined,
        side: orderSide || undefined,
      });
      setOrdersData(data);
    } catch (err: any) {
      if (err?.status === 401) {
        setAdminAuthState('login');
        return;
      }
      setOrdersError(err?.message || 'Failed to load paper trading orders');
    } finally {
      setOrdersLoading(false);
    }
  }, [orderPage, orderSearch, orderStatus, orderSide]);

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

  const fetchErrors = useCallback(async () => {
    setErrorsLoading(true);
    setErrorsError(null);
    try {
      const parsedStatus = errorStatusCode ? parseInt(errorStatusCode, 10) : undefined;
      const [data, summary] = await Promise.all([
        apiClient.admin.getErrors({
          page: errorPage,
          limit: 20,
          status_code: parsedStatus,
          category: errorCategory || undefined,
          search: errorSearch.trim() || undefined,
        }),
        apiClient.admin.getErrorsSummary(),
      ]);
      setErrorsData(data);
      setErrorSummary(summary);
    } catch (err: any) {
      if (err?.status === 401) {
        setAdminAuthState('login');
        return;
      }
      setErrorsError(err?.message || 'Failed to load error monitoring log');
    } finally {
      setErrorsLoading(false);
    }
  }, [errorPage, errorStatusCode, errorCategory, errorSearch]);

  useEffect(() => {
    if (adminAuthState !== 'authenticated') return;
    if (activeTab === 'overview') fetchOverview();
    else if (activeTab === 'users') fetchUsers();
    else if (activeTab === 'orders') fetchOrders();
    else if (activeTab === 'health') fetchHealth();
    else if (activeTab === 'errors') fetchErrors();
  }, [adminAuthState, activeTab, fetchOverview, fetchUsers, fetchOrders, fetchHealth, fetchErrors]);

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
    const filledOrders = overviewData.orders_by_status?.FILLED || 0;
    const rejectedOrders = overviewData.orders_by_status?.REJECTED || 0;
    const hasOrders = totalOrders > 0;
    const successRateText = hasOrders ? `${((filledOrders / totalOrders) * 100).toFixed(1)}%` : 'No orders yet';

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
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Total Orders</div>
            <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>{totalOrders.toLocaleString()}</div>
            <div style={{ fontSize: '11px', color: 'var(--color-action)', marginTop: '4px' }}>{filledOrders} filled</div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '20px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Order Success Rate</div>
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
              {hasOrders ? `${rejectedOrders} rejected` : 'Awaiting initial simulated trade'}
            </div>
          </div>
        </div>

        {/* Recent Rejected Orders Table */}
        <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div>
              <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>Recent Rejected Orders</h2>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>Latest execution safeguards triggered by risk or liquidity checks</div>
            </div>
            <button
              onClick={() => setActiveTab('orders')}
              style={{ background: 'none', border: 'none', color: 'var(--color-action)', fontSize: '12px', cursor: 'pointer', padding: 0 }}
            >
              View all orders →
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
                    <th style={{ padding: '8px' }}>User Email</th>
                    <th style={{ padding: '8px' }}>Symbol</th>
                    <th style={{ padding: '8px' }}>Side</th>
                    <th style={{ padding: '8px' }}>Qty</th>
                    <th style={{ padding: '8px' }}>Rejection Reason</th>
                    <th style={{ padding: '8px' }}>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {overviewData.recent_rejected_orders.map((o: AdminOrderItem) => (
                    <tr key={o.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                      <td style={{ padding: '10px 8px', fontFamily: 'var(--font-mono)' }}>{o.id.substring(0, 12)}...</td>
                      <td style={{ padding: '10px 8px' }}>{o.user_email || o.user_id}</td>
                      <td style={{ padding: '10px 8px', fontWeight: 700 }}>{o.symbol}</td>
                      <td style={{ padding: '10px 8px' }}>
                        <span style={{ color: o.side === 'BUY' ? 'var(--color-profit)' : 'var(--color-loss)', fontWeight: 600 }}>{o.side}</span>
                      </td>
                      <td style={{ padding: '10px 8px' }}>{o.quantity}</td>
                      <td style={{ padding: '10px 8px', color: 'var(--color-loss)' }}>{o.rejection_reason}</td>
                      <td style={{ padding: '10px 8px', color: 'var(--text-muted)' }}>
                        {o.created_at ? new Date(o.created_at).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' }) : '—'}
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

  const renderUsersTab = () => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Search & Filters */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '12px',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: 'var(--bg-card)',
            padding: '16px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ display: 'flex', flex: 1, minWidth: '240px', gap: '8px' }}>
            <input
              type="text"
              placeholder="Search by email, name, or user ID..."
              value={userSearch}
              onChange={(e) => {
                setUserSearch(e.target.value);
                setUserPage(1);
              }}
              style={{
                width: '100%',
                padding: '8px 12px',
                fontSize: '13px',
                borderRadius: 'var(--radius-xs)',
                border: '1px solid var(--border-subtle)',
                backgroundColor: 'var(--bg-main)',
                color: 'var(--text-main)',
              }}
            />
          </div>

          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <select
              value={userFilterActive === undefined ? '' : String(userFilterActive)}
              onChange={(e) => {
                setUserFilterActive(e.target.value === '' ? undefined : e.target.value === 'true');
                setUserPage(1);
              }}
              style={{
                padding: '8px 12px',
                fontSize: '12px',
                borderRadius: 'var(--radius-xs)',
                border: '1px solid var(--border-subtle)',
                backgroundColor: 'var(--bg-main)',
                color: 'var(--text-main)',
              }}
            >
              <option value="">All Statuses</option>
              <option value="true">Active Only</option>
              <option value="false">Inactive</option>
            </select>

            <select
              value={userFilterVerified === undefined ? '' : String(userFilterVerified)}
              onChange={(e) => {
                setUserFilterVerified(e.target.value === '' ? undefined : e.target.value === 'true');
                setUserPage(1);
              }}
              style={{
                padding: '8px 12px',
                fontSize: '12px',
                borderRadius: 'var(--radius-xs)',
                border: '1px solid var(--border-subtle)',
                backgroundColor: 'var(--bg-main)',
                color: 'var(--text-main)',
              }}
            >
              <option value="">All Email States</option>
              <option value="true">Verified Email</option>
              <option value="false">Unverified</option>
            </select>

            <select
              value={userFilterOnboarded === undefined ? '' : String(userFilterOnboarded)}
              onChange={(e) => {
                setUserFilterOnboarded(e.target.value === '' ? undefined : e.target.value === 'true');
                setUserPage(1);
              }}
              style={{
                padding: '8px 12px',
                fontSize: '12px',
                borderRadius: 'var(--radius-xs)',
                border: '1px solid var(--border-subtle)',
                backgroundColor: 'var(--bg-main)',
                color: 'var(--text-main)',
              }}
            >
              <option value="">All Onboarding</option>
              <option value="true">Completed</option>
              <option value="false">Pending</option>
            </select>
          </div>
        </div>

        {/* Users Table */}
        <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '20px' }}>
          {usersLoading ? (
            <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-muted)' }}>Loading user directory...</div>
          ) : usersError ? (
            <div style={{ padding: '16px', color: 'var(--color-loss)' }}>{usersError}</div>
          ) : !usersData || usersData.users.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-muted)' }}>No matching users found.</div>
          ) : (
            <>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                      <th style={{ padding: '10px 8px' }}>User ID</th>
                      <th style={{ padding: '10px 8px' }}>Email</th>
                      <th style={{ padding: '10px 8px' }}>Name</th>
                      <th style={{ padding: '10px 8px' }}>Verified</th>
                      <th style={{ padding: '10px 8px' }}>Onboarded</th>
                      <th style={{ padding: '10px 8px' }}>Risk Band</th>
                      <th style={{ padding: '10px 8px' }}>Status</th>
                      <th style={{ padding: '10px 8px' }}>Registered</th>
                    </tr>
                  </thead>
                  <tbody>
                    {usersData.users.map((u: AdminUserItem) => (
                      <tr key={u.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                        <td style={{ padding: '10px 8px', fontFamily: 'var(--font-mono)' }}>{u.id}</td>
                        <td style={{ padding: '10px 8px', fontWeight: 600 }}>{u.email}</td>
                        <td style={{ padding: '10px 8px' }}>{u.display_name || u.full_name || '—'}</td>
                        <td style={{ padding: '10px 8px' }}>
                          <span style={{ color: u.email_verified ? 'var(--color-profit)' : 'var(--text-muted)' }}>
                            {u.email_verified ? '✓ Yes' : 'No'}
                          </span>
                        </td>
                        <td style={{ padding: '10px 8px' }}>
                          <span style={{ color: u.onboarding_completed ? 'var(--color-profit)' : 'var(--text-muted)' }}>
                            {u.onboarding_completed ? '✓ Yes' : 'Pending'}
                          </span>
                        </td>
                        <td style={{ padding: '10px 8px' }}>
                          <span
                            style={{
                              padding: '2px 6px',
                              borderRadius: 'var(--radius-xs)',
                              backgroundColor: 'rgba(255,255,255,0.06)',
                              fontSize: '11px',
                            }}
                          >
                            {u.risk_band || 'UNASSESSED'}
                          </span>
                        </td>
                        <td style={{ padding: '10px 8px' }}>
                          <span style={{ color: u.is_active ? 'var(--color-profit)' : 'var(--color-loss)', fontWeight: 600 }}>
                            {u.is_active ? 'Active' : 'Disabled'}
                          </span>
                        </td>
                        <td style={{ padding: '10px 8px', color: 'var(--text-muted)' }}>
                          {u.created_at ? new Date(u.created_at).toLocaleDateString('en-IN') : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '16px', fontSize: '12px' }}>
                <div style={{ color: 'var(--text-muted)' }}>
                  Total {usersData.total} users · Page {usersData.page} of {usersData.total_pages}
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={() => setUserPage((p) => Math.max(1, p - 1))}
                    disabled={usersData.page <= 1}
                    style={{
                      padding: '4px 10px',
                      backgroundColor: 'var(--bg-main)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-xs)',
                      color: 'var(--text-main)',
                      cursor: usersData.page <= 1 ? 'not-allowed' : 'pointer',
                      opacity: usersData.page <= 1 ? 0.5 : 1,
                    }}
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setUserPage((p) => Math.min(usersData.total_pages, p + 1))}
                    disabled={usersData.page >= usersData.total_pages}
                    style={{
                      padding: '4px 10px',
                      backgroundColor: 'var(--bg-main)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-xs)',
                      color: 'var(--text-main)',
                      cursor: usersData.page >= usersData.total_pages ? 'not-allowed' : 'pointer',
                      opacity: usersData.page >= usersData.total_pages ? 0.5 : 1,
                    }}
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    );
  };

  const renderOrdersTab = () => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Search & Filters */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '12px',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: 'var(--bg-card)',
            padding: '16px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ display: 'flex', flex: 1, minWidth: '240px', gap: '8px' }}>
            <input
              type="text"
              placeholder="Search by symbol, rejection reason, or user ID..."
              value={orderSearch}
              onChange={(e) => {
                setOrderSearch(e.target.value);
                setOrderPage(1);
              }}
              style={{
                width: '100%',
                padding: '8px 12px',
                fontSize: '13px',
                borderRadius: 'var(--radius-xs)',
                border: '1px solid var(--border-subtle)',
                backgroundColor: 'var(--bg-main)',
                color: 'var(--text-main)',
              }}
            />
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <select
              value={orderSide}
              onChange={(e) => {
                setOrderSide(e.target.value);
                setOrderPage(1);
              }}
              style={{
                padding: '8px 12px',
                fontSize: '12px',
                borderRadius: 'var(--radius-xs)',
                border: '1px solid var(--border-subtle)',
                backgroundColor: 'var(--bg-main)',
                color: 'var(--text-main)',
              }}
            >
              <option value="">All Sides</option>
              <option value="BUY">BUY</option>
              <option value="SELL">SELL</option>
            </select>

            <select
              value={orderStatus}
              onChange={(e) => {
                setOrderStatus(e.target.value);
                setOrderPage(1);
              }}
              style={{
                padding: '8px 12px',
                fontSize: '12px',
                borderRadius: 'var(--radius-xs)',
                border: '1px solid var(--border-subtle)',
                backgroundColor: 'var(--bg-main)',
                color: 'var(--text-main)',
              }}
            >
              <option value="">All Statuses</option>
              <option value="FILLED">FILLED</option>
              <option value="REJECTED">REJECTED</option>
              <option value="ACCEPTED">ACCEPTED</option>
              <option value="CANCELLED">CANCELLED</option>
            </select>
          </div>
        </div>

        {/* Orders Table */}
        <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '20px' }}>
          {ordersLoading ? (
            <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-muted)' }}>Loading paper trading orders...</div>
          ) : ordersError ? (
            <div style={{ padding: '16px', color: 'var(--color-loss)' }}>{ordersError}</div>
          ) : !ordersData || ordersData.orders.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-muted)' }}>No orders found.</div>
          ) : (
            <>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                      <th style={{ padding: '10px 8px' }}>Order ID</th>
                      <th style={{ padding: '10px 8px' }}>User</th>
                      <th style={{ padding: '10px 8px' }}>Symbol</th>
                      <th style={{ padding: '10px 8px' }}>Side</th>
                      <th style={{ padding: '10px 8px' }}>Type</th>
                      <th style={{ padding: '10px 8px' }}>Qty</th>
                      <th style={{ padding: '10px 8px' }}>Price</th>
                      <th style={{ padding: '10px 8px' }}>Status</th>
                      <th style={{ padding: '10px 8px' }}>Details / Reason</th>
                      <th style={{ padding: '10px 8px' }}>Timestamp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ordersData.orders.map((o: AdminOrderItem) => (
                      <tr key={o.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                        <td style={{ padding: '10px 8px', fontFamily: 'var(--font-mono)' }}>{o.id.substring(0, 12)}...</td>
                        <td style={{ padding: '10px 8px' }}>{o.user_email || o.user_id}</td>
                        <td style={{ padding: '10px 8px', fontWeight: 700 }}>{o.symbol}</td>
                        <td style={{ padding: '10px 8px' }}>
                          <span style={{ color: o.side === 'BUY' ? 'var(--color-profit)' : 'var(--color-loss)', fontWeight: 600 }}>{o.side}</span>
                        </td>
                        <td style={{ padding: '10px 8px' }}>{o.order_type}</td>
                        <td style={{ padding: '10px 8px' }}>{o.quantity}</td>
                        <td style={{ padding: '10px 8px' }}>₹{(o.fill_price || o.limit_price || 0).toLocaleString('en-IN')}</td>
                        <td style={{ padding: '10px 8px' }}>
                          <span
                            style={{
                              padding: '2px 6px',
                              borderRadius: 'var(--radius-xs)',
                              backgroundColor:
                                o.status === 'FILLED'
                                  ? 'rgba(5, 150, 105, 0.12)'
                                  : o.status === 'REJECTED'
                                    ? 'rgba(239, 68, 68, 0.12)'
                                    : 'rgba(59, 130, 246, 0.12)',
                              color:
                                o.status === 'FILLED'
                                  ? 'var(--color-profit)'
                                  : o.status === 'REJECTED'
                                    ? 'var(--color-loss)'
                                    : 'var(--color-action)',
                              fontWeight: 600,
                            }}
                          >
                            {o.status}
                          </span>
                        </td>
                        <td style={{ padding: '10px 8px', color: o.status === 'REJECTED' ? 'var(--color-loss)' : 'var(--text-muted)' }}>
                          {o.rejection_reason || '—'}
                        </td>
                        <td style={{ padding: '10px 8px', color: 'var(--text-muted)' }}>
                          {o.created_at ? new Date(o.created_at).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' }) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '16px', fontSize: '12px' }}>
                <div style={{ color: 'var(--text-muted)' }}>
                  Total {ordersData.total} orders · Page {ordersData.page} of {ordersData.total_pages}
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={() => setOrderPage((p) => Math.max(1, p - 1))}
                    disabled={ordersData.page <= 1}
                    style={{
                      padding: '4px 10px',
                      backgroundColor: 'var(--bg-main)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-xs)',
                      color: 'var(--text-main)',
                      cursor: ordersData.page <= 1 ? 'not-allowed' : 'pointer',
                      opacity: ordersData.page <= 1 ? 0.5 : 1,
                    }}
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setOrderPage((p) => Math.min(ordersData.total_pages, p + 1))}
                    disabled={ordersData.page >= ordersData.total_pages}
                    style={{
                      padding: '4px 10px',
                      backgroundColor: 'var(--bg-main)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-xs)',
                      color: 'var(--text-main)',
                      cursor: ordersData.page >= ordersData.total_pages ? 'not-allowed' : 'pointer',
                      opacity: ordersData.page >= ordersData.total_pages ? 0.5 : 1,
                    }}
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    );
  };

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

  const renderErrorsTab = () => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Transparency / Honesty Scope Notice */}
        <div
          style={{
            padding: '14px 18px',
            backgroundColor: 'rgba(59, 130, 246, 0.08)',
            border: '1px solid rgba(59, 130, 246, 0.25)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '12px',
            lineHeight: 1.5,
            color: 'var(--text-main)',
          }}
        >
          <div style={{ fontWeight: 700, color: 'var(--color-action)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>ℹ️</span>
            <span>Surveillance Scope & Data Hygiene Notice</span>
          </div>
          <div>
            This dashboard displays server-side operational exceptions (including unhandled 5xx exceptions, 503 service outages, 429 rate limits, 422 schema validation errors, and 400/401/403/404 HTTP errors).
            It <strong>does not</strong> capture client-side network disconnects, local browser JavaScript crashes, or edge CDN dropouts that never reach the backend API.
            Endpoints are logged as parameterized route templates (unmatched paths are anonymized to /unmatched_route), and all messages are mapped to allowlisted error codes with server-side sanitization.
            Database writes are bounded by a 250ms ceiling and per-process concurrency limits (max 5 simultaneous writes per worker); during storage degradation, events are dropped fail-open to protect local worker connection pool capacity.
          </div>
        </div>

        {/* Aggregate KPI Cards */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(200px, 100%), 1fr))',
            gap: '16px',
          }}
        >
          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '20px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Total Recorded Errors</div>
            <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--text-main)', marginTop: '4px' }}>
              {errorSummary ? errorSummary.total_errors.toLocaleString() : '—'}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>Bounded to max 5,000 events</div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '20px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Server Errors (5xx)</div>
            <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--color-loss)', marginTop: '4px' }}>
              {errorSummary ? errorSummary.server_errors_5xx.toLocaleString() : '—'}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>Unhandled & upstream 5xx</div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '20px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Client / Validation (4xx)</div>
            <div style={{ fontSize: '28px', fontWeight: 800, color: '#F59E0B', marginTop: '4px' }}>
              {errorSummary ? errorSummary.client_errors_4xx.toLocaleString() : '—'}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>Rate limits & schema rejects</div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '20px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Past 24 Hours</div>
            <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--color-action)', marginTop: '4px' }}>
              {errorSummary ? errorSummary.last_24h_errors.toLocaleString() : '—'}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>Rolling 24h event volume</div>
          </div>
        </div>

        {/* Filter and Search Bar */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '12px',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: 'var(--bg-card)',
            padding: '16px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ display: 'flex', flex: 1, minWidth: '240px', gap: '8px' }}>
            <input
              type="text"
              placeholder="Search by correlation ID, sanitized message, endpoint, or error type..."
              value={errorSearch}
              onChange={(e) => {
                setErrorSearch(e.target.value);
                setErrorPage(1);
              }}
              style={{
                width: '100%',
                padding: '8px 12px',
                fontSize: '13px',
                borderRadius: 'var(--radius-xs)',
                border: '1px solid var(--border-subtle)',
                backgroundColor: 'var(--bg-main)',
                color: 'var(--text-main)',
              }}
            />
          </div>

          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <select
              value={errorCategory}
              onChange={(e) => {
                setErrorCategory(e.target.value);
                setErrorPage(1);
              }}
              style={{
                padding: '8px 12px',
                fontSize: '12px',
                borderRadius: 'var(--radius-xs)',
                border: '1px solid var(--border-subtle)',
                backgroundColor: 'var(--bg-main)',
                color: 'var(--text-main)',
              }}
            >
              <option value="">All Categories</option>
              <option value="SERVER_ERROR">SERVER_ERROR</option>
              <option value="DATABASE">DATABASE</option>
              <option value="UPSTREAM_API">UPSTREAM_API</option>
              <option value="RATE_LIMIT">RATE_LIMIT</option>
              <option value="VALIDATION">VALIDATION</option>
              <option value="AUTHENTICATION">AUTHENTICATION</option>
              <option value="CONFLICT">CONFLICT</option>
              <option value="CLIENT_ERROR">CLIENT_ERROR</option>
            </select>

            <select
              value={errorStatusCode}
              onChange={(e) => {
                setErrorStatusCode(e.target.value);
                setErrorPage(1);
              }}
              style={{
                padding: '8px 12px',
                fontSize: '12px',
                borderRadius: 'var(--radius-xs)',
                border: '1px solid var(--border-subtle)',
                backgroundColor: 'var(--bg-main)',
                color: 'var(--text-main)',
              }}
            >
              <option value="">All Status Codes</option>
              <option value="500">500 Internal Error</option>
              <option value="502">502 Bad Gateway</option>
              <option value="503">503 Service Unavailable</option>
              <option value="504">504 Gateway Timeout</option>
              <option value="429">429 Rate Limited</option>
              <option value="422">422 Unprocessable Content</option>
              <option value="400">400 Bad Request</option>
              <option value="401">401 Unauthorized</option>
              <option value="403">403 Forbidden</option>
              <option value="404">404 Not Found</option>
            </select>

            {(errorSearch || errorCategory || errorStatusCode) && (
              <button
                onClick={() => {
                  setErrorSearch('');
                  setErrorCategory('');
                  setErrorStatusCode('');
                  setErrorPage(1);
                }}
                style={{
                  padding: '8px 12px',
                  fontSize: '12px',
                  borderRadius: 'var(--radius-xs)',
                  border: '1px solid var(--border-subtle)',
                  backgroundColor: 'transparent',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                }}
              >
                Clear
              </button>
            )}
          </div>
        </div>

        {/* Error Events Table */}
        <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '20px' }}>
          {errorsLoading && !errorsData ? (
            <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)' }}>
              Loading recorded server-side error events...
            </div>
          ) : errorsError ? (
            <div style={{ padding: '24px', backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--color-loss)', borderRadius: '4px' }}>
              {errorsError}
            </div>
          ) : !errorsData || errorsData.errors.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)' }}>
              <div style={{ fontSize: '32px', marginBottom: '8px' }}>✓</div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)' }}>No error events recorded</div>
              <div style={{ fontSize: '12px', marginTop: '4px' }}>
                {errorSearch || errorCategory || errorStatusCode
                  ? 'No recorded errors match your filter criteria.'
                  : 'No server-side runtime exceptions or HTTP failures recorded in retention window.'}
              </div>
            </div>
          ) : (
            <>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                      <th style={{ padding: '10px 8px' }}>Timestamp</th>
                      <th style={{ padding: '10px 8px' }}>Status</th>
                      <th style={{ padding: '10px 8px' }}>Category</th>
                      <th style={{ padding: '10px 8px' }}>Feature & Endpoint</th>
                      <th style={{ padding: '10px 8px' }}>Correlation ID</th>
                      <th style={{ padding: '10px 8px' }}>Sanitized Message</th>
                    </tr>
                  </thead>
                  <tbody>
                    {errorsData.errors.map((item: AdminErrorItem) => {
                      const is5xx = item.status_code >= 500;
                      return (
                        <tr key={item.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                          <td style={{ padding: '10px 8px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                            {item.created_at ? new Date(item.created_at).toLocaleString('en-IN') : '—'}
                          </td>
                          <td style={{ padding: '10px 8px' }}>
                            <span
                              style={{
                                padding: '2px 8px',
                                borderRadius: 'var(--radius-xs)',
                                fontSize: '11px',
                                fontWeight: 700,
                                backgroundColor: is5xx ? 'rgba(239, 68, 68, 0.12)' : 'rgba(245, 158, 11, 0.12)',
                                color: is5xx ? 'var(--color-loss)' : '#F59E0B',
                              }}
                            >
                              {item.status_code}
                            </span>
                          </td>
                          <td style={{ padding: '10px 8px' }}>
                            <span
                              style={{
                                padding: '2px 6px',
                                borderRadius: 'var(--radius-xs)',
                                backgroundColor: 'rgba(255, 255, 255, 0.06)',
                                fontSize: '11px',
                                fontWeight: 600,
                              }}
                            >
                              {item.category}
                            </span>
                          </td>
                          <td style={{ padding: '10px 8px' }}>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                              <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>{item.feature_area}</span>
                              <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                                {item.method} {item.endpoint}
                              </span>
                            </div>
                          </td>
                          <td style={{ padding: '10px 8px', fontFamily: 'var(--font-mono)' }}>
                            {item.correlation_id ? (
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <span style={{ fontSize: '11px' }}>{item.correlation_id.slice(0, 8)}...</span>
                                <button
                                  onClick={() => {
                                    if (typeof navigator !== 'undefined' && navigator.clipboard) {
                                      navigator.clipboard.writeText(item.correlation_id || '').then(() => {
                                        setCopiedId(item.correlation_id || null);
                                        setTimeout(() => setCopiedId(null), 2000);
                                      }).catch(() => {});
                                    }
                                  }}
                                  title={`Copy full correlation ID: ${item.correlation_id}`}
                                  style={{
                                    padding: '2px 6px',
                                    fontSize: '10px',
                                    backgroundColor: copiedId === item.correlation_id ? 'rgba(5, 150, 105, 0.2)' : 'var(--bg-main)',
                                    color: copiedId === item.correlation_id ? 'var(--color-profit)' : 'var(--text-muted)',
                                    border: '1px solid var(--border-subtle)',
                                    borderRadius: 'var(--radius-xs)',
                                    cursor: 'pointer',
                                  }}
                                >
                                  {copiedId === item.correlation_id ? 'Copied' : 'Copy'}
                                </button>
                              </div>
                            ) : (
                              <span style={{ color: 'var(--text-muted)' }}>—</span>
                            )}
                          </td>
                          <td style={{ padding: '10px 8px', maxWidth: '380px' }}>
                            <div
                              style={{
                                fontSize: '12px',
                                color: 'var(--text-main)',
                                wordBreak: 'break-word',
                                fontFamily: 'var(--font-mono)',
                                lineHeight: 1.4,
                              }}
                            >
                              {item.sanitized_message}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '16px', fontSize: '12px' }}>
                <div style={{ color: 'var(--text-muted)' }}>
                  Total {errorsData.total} error events · Page {errorsData.page} of {errorsData.total_pages}
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={() => setErrorPage((p) => Math.max(1, p - 1))}
                    disabled={errorsData.page <= 1}
                    style={{
                      padding: '4px 10px',
                      backgroundColor: 'var(--bg-main)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-xs)',
                      color: 'var(--text-main)',
                      cursor: errorsData.page <= 1 ? 'not-allowed' : 'pointer',
                      opacity: errorsData.page <= 1 ? 0.5 : 1,
                    }}
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setErrorPage((p) => Math.min(errorsData.total_pages, p + 1))}
                    disabled={errorsData.page >= errorsData.total_pages}
                    style={{
                      padding: '4px 10px',
                      backgroundColor: 'var(--bg-main)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-xs)',
                      color: 'var(--text-main)',
                      cursor: errorsData.page >= errorsData.total_pages ? 'not-allowed' : 'pointer',
                      opacity: errorsData.page >= errorsData.total_pages ? 0.5 : 1,
                    }}
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    );
  };

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
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
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
              else if (activeTab === 'users') fetchUsers();
              else if (activeTab === 'orders') fetchOrders();
              else if (activeTab === 'health') fetchHealth();
              else if (activeTab === 'errors') fetchErrors();
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
