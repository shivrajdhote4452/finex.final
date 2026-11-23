import React, { useState, useEffect, useCallback } from 'react';
import { useFinancial } from '../context/FinancialContext';
import {
  apiClient,
  AdminOverviewResponse,
  AdminUsersResponse,
  AdminOrdersResponse,
  AdminSystemHealthResponse,
  AdminErrorItem,
  AdminErrorsResponse,
  AdminErrorSummaryResponse,
} from '../api/client';
import { NavigationTab } from '../domain/sessionNavigation';

interface AdminScreenProps {
  onNavigate?: (tab: NavigationTab) => void;
}

type AdminTab = 'overview' | 'users' | 'orders' | 'health' | 'errors';

export const AdminScreen: React.FC<AdminScreenProps> = ({ onNavigate }) => {
  const { isOwner } = useFinancial();

  const [activeTab, setActiveTab] = useState<AdminTab>('overview');

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

  // Fetch Overview
  const fetchOverview = useCallback(async () => {
    if (!isOwner) return;
    setOverviewLoading(true);
    setOverviewError(null);
    try {
      const data = await apiClient.admin.getOverview();
      setOverviewData(data);
    } catch (err: any) {
      setOverviewError(err?.message || 'Failed to load administrative overview');
    } finally {
      setOverviewLoading(false);
    }
  }, [isOwner]);

  // Fetch Users
  const fetchUsers = useCallback(async () => {
    if (!isOwner) return;
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
      setUsersError(err?.message || 'Failed to load user directory');
    } finally {
      setUsersLoading(false);
    }
  }, [isOwner, userPage, userSearch, userFilterActive, userFilterVerified, userFilterOnboarded]);

  // Fetch Orders
  const fetchOrders = useCallback(async () => {
    if (!isOwner) return;
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
      setOrdersError(err?.message || 'Failed to load paper trading orders');
    } finally {
      setOrdersLoading(false);
    }
  }, [isOwner, orderPage, orderSearch, orderStatus, orderSide]);

  // Fetch Health
  const fetchHealth = useCallback(async () => {
    if (!isOwner) return;
    setHealthLoading(true);
    setHealthError(null);
    try {
      const data = await apiClient.admin.getSystemHealth();
      setHealthData(data);
    } catch (err: any) {
      setHealthError(err?.message || 'Failed to load system diagnostics');
    } finally {
      setHealthLoading(false);
    }
  }, [isOwner]);

  // Fetch Errors
  const fetchErrors = useCallback(async () => {
    if (!isOwner) return;
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
      setErrorsError(err?.message || 'Failed to load error monitoring log');
    } finally {
      setErrorsLoading(false);
    }
  }, [isOwner, errorPage, errorStatusCode, errorCategory, errorSearch]);

  // Load data when active tab changes
  useEffect(() => {
    if (!isOwner) return;
    if (activeTab === 'overview') fetchOverview();
    else if (activeTab === 'users') fetchUsers();
    else if (activeTab === 'orders') fetchOrders();
    else if (activeTab === 'health') fetchHealth();
    else if (activeTab === 'errors') fetchErrors();
  }, [activeTab, isOwner, fetchOverview, fetchUsers, fetchOrders, fetchHealth, fetchErrors]);

  // If not owner, show Access Denied Guard
  if (!isOwner) {
    return (
      <div style={{ padding: '40px 24px', maxWidth: '800px', margin: '0 auto', textAlign: 'center' }}>
        <div
          style={{
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm)',
            padding: '48px 24px',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)',
          }}
        >
          <div
            style={{
              width: '56px',
              height: '56px',
              borderRadius: '50%',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              color: 'var(--color-loss, #EF4444)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '24px',
              margin: '0 auto 20px auto',
            }}
          >
            🔒
          </div>
          <h2 style={{ fontSize: '22px', fontWeight: 700, color: 'var(--text-main)', marginBottom: '8px' }}>
            Access Restricted
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px', maxWidth: '480px', margin: '0 auto 24px auto' }}>
            The FinEx Admin Panel is strictly reserved for the platform owner with an authenticated Google identity.
          </p>
          {onNavigate && (
            <button
              onClick={() => onNavigate('overview')}
              className="btn btn-action"
              style={{ padding: '8px 20px', fontSize: '13px', cursor: 'pointer' }}
            >
              Return to Overview
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: '24px', maxWidth: '1280px', margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>
      {/* Header & Badges */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: '16px',
          marginBottom: '24px',
          paddingBottom: '16px',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                color: 'var(--color-action)',
              }}
            >
              Operations & Governance
            </span>
            <span
              style={{
                fontSize: '11px',
                padding: '2px 8px',
                borderRadius: 'var(--radius-xs)',
                backgroundColor: 'rgba(5, 150, 105, 0.12)',
                color: 'var(--color-profit, #059669)',
                fontWeight: 600,
              }}
            >
              Read-Only
            </span>
          </div>
          <h1
            style={{
              fontSize: '28px',
              fontWeight: 800,
              color: 'var(--text-main)',
              letterSpacing: '-0.02em',
              margin: 0,
            }}
          >
            Platform Administration
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '13px', margin: '4px 0 0 0' }}>
            Cross-client operational oversight for users, paper trades, and service diagnostics.
          </p>
        </div>

        {/* Global Refresh Button */}
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
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-xs)',
            color: 'var(--text-main)',
            padding: '8px 16px',
            fontSize: '12px',
            fontWeight: 600,
            cursor: overviewLoading || usersLoading || ordersLoading || healthLoading || errorsLoading ? 'wait' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <span>↻</span>
          <span>{overviewLoading || usersLoading || ordersLoading || healthLoading || errorsLoading ? 'Refreshing...' : 'Refresh View'}</span>
        </button>
      </div>

      {/* Navigation Sub-Tabs */}
      <div
        style={{
          display: 'flex',
          gap: '8px',
          marginBottom: '24px',
          overflowX: 'auto',
          paddingBottom: '4px',
        }}
      >
        {[
          { id: 'overview' as const, label: 'Overview', icon: '📊' },
          { id: 'users' as const, label: 'User Directory', icon: '👥' },
          { id: 'orders' as const, label: 'Paper Trading', icon: '📈' },
          { id: 'health' as const, label: 'System Health', icon: '⚙️' },
          { id: 'errors' as const, label: 'Error Monitoring', icon: '🚨' },
        ].map((tab) => {
          const isSelected = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                backgroundColor: isSelected ? 'var(--color-action)' : 'var(--bg-card)',
                color: isSelected ? '#FFFFFF' : 'var(--text-muted)',
                border: isSelected ? '1px solid var(--color-action)' : '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-xs)',
                padding: '8px 16px',
                fontSize: '13px',
                fontWeight: isSelected ? 700 : 500,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                whiteSpace: 'nowrap',
                transition: 'all 0.15s ease',
              }}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* ===================================================================== */}
      {/* 1. OVERVIEW TAB */}
      {/* ===================================================================== */}
      {activeTab === 'overview' && (
        <div>
          {overviewLoading && !overviewData && (
            <div style={{ padding: '60px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
              Loading operational metrics...
            </div>
          )}

          {overviewError && (
            <div
              style={{
                backgroundColor: 'rgba(239, 68, 68, 0.08)',
                border: '1px solid var(--color-loss, #EF4444)',
                borderRadius: 'var(--radius-xs)',
                padding: '16px',
                color: 'var(--color-loss, #EF4444)',
                fontSize: '13px',
                marginBottom: '20px',
              }}
            >
              {overviewError}
            </div>
          )}

          {overviewData && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              {/* Metric Cards Grid */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                  gap: '16px',
                }}
              >
                <div
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '20px',
                  }}
                >
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '6px' }}>
                    Total Registered Users
                  </div>
                  <div style={{ fontSize: '32px', fontWeight: 800, color: 'var(--text-main)', fontFamily: 'var(--font-mono)' }}>
                    {overviewData.total_users.toLocaleString()}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                    Verified: {overviewData.verified_users} | Unverified: {overviewData.unverified_users}
                  </div>
                </div>

                <div
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '20px',
                  }}
                >
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '6px' }}>
                    Risk Onboarding Complete
                  </div>
                  <div style={{ fontSize: '32px', fontWeight: 800, color: 'var(--color-profit, #059669)', fontFamily: 'var(--font-mono)' }}>
                    {overviewData.onboarding_completed_users.toLocaleString()}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                    {overviewData.total_users > 0
                      ? `${Math.round((overviewData.onboarding_completed_users / overviewData.total_users) * 100)}% of total users`
                      : '0% completed'}
                  </div>
                </div>

                <div
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '20px',
                  }}
                >
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '6px' }}>
                    Total Paper Orders
                  </div>
                  <div style={{ fontSize: '32px', fontWeight: 800, color: 'var(--text-main)', fontFamily: 'var(--font-mono)' }}>
                    {overviewData.total_orders.toLocaleString()}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                    Filled: {overviewData.orders_by_status['FILLED'] || 0} | Rejected: {overviewData.orders_by_status['REJECTED'] || 0}
                  </div>
                </div>

                <div
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '20px',
                  }}
                >
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '6px' }}>
                    Execution Success Rate
                  </div>
                  <div
                    style={{
                      fontSize: overviewData.total_orders > 0 ? '32px' : '22px',
                      fontWeight: 800,
                      color: overviewData.total_orders > 0 ? 'var(--color-action)' : 'var(--text-muted)',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    {overviewData.total_orders > 0
                      ? `${Math.round(
                          ((overviewData.orders_by_status['FILLED'] || 0) / overviewData.total_orders) * 100
                        )}%`
                      : 'No orders yet'}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                    Pending: {overviewData.orders_by_status['PENDING'] || 0} | Cancelled: {overviewData.orders_by_status['CANCELLED'] || 0}
                  </div>
                </div>
              </div>

              {/* Order Status Distribution */}
              <div
                style={{
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '20px',
                }}
              >
                <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-main)', margin: '0 0 16px 0' }}>
                  Paper Trading Execution Distribution
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
                  {Object.entries(overviewData.orders_by_status).map(([status, count]) => {
                    let badgeColor = 'var(--text-muted)';
                    let bg = 'rgba(128, 128, 128, 0.1)';
                    if (status === 'FILLED') {
                      badgeColor = 'var(--color-profit, #059669)';
                      bg = 'rgba(5, 150, 105, 0.1)';
                    } else if (status === 'REJECTED') {
                      badgeColor = 'var(--color-loss, #EF4444)';
                      bg = 'rgba(239, 68, 68, 0.1)';
                    } else if (status === 'PENDING') {
                      badgeColor = '#D97706';
                      bg = 'rgba(217, 119, 6, 0.1)';
                    }
                    return (
                      <div
                        key={status}
                        style={{
                          backgroundColor: bg,
                          border: '1px solid var(--border-subtle)',
                          borderRadius: 'var(--radius-xs)',
                          padding: '12px 16px',
                        }}
                      >
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>{status}</div>
                        <div style={{ fontSize: '20px', fontWeight: 800, color: badgeColor, fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
                          {count.toLocaleString()}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Recent Rejected Orders */}
              <div
                style={{
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '20px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
                    Recent Order Rejections & Failure Reasons
                  </h3>
                  <button
                    onClick={() => {
                      setOrderStatus('REJECTED');
                      setActiveTab('orders');
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--color-action)',
                      fontSize: '12px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      padding: 0,
                    }}
                  >
                    View all in Orders →
                  </button>
                </div>

                {overviewData.recent_rejected_orders.length === 0 ? (
                  <div style={{ padding: '24px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                    No rejected orders recorded.
                  </div>
                ) : (
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', color: 'var(--text-muted)' }}>
                          <th style={{ padding: '8px 12px' }}>Time</th>
                          <th style={{ padding: '8px 12px' }}>Symbol</th>
                          <th style={{ padding: '8px 12px' }}>Side</th>
                          <th style={{ padding: '8px 12px' }}>Quantity</th>
                          <th style={{ padding: '8px 12px' }}>Rejection Reason</th>
                        </tr>
                      </thead>
                      <tbody>
                        {overviewData.recent_rejected_orders.map((o) => (
                          <tr key={o.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                            <td style={{ padding: '10px 12px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                              {o.created_at ? new Date(o.created_at).toLocaleString() : 'N/A'}
                            </td>
                            <td style={{ padding: '10px 12px', fontWeight: 700, color: 'var(--text-main)' }}>
                              {o.symbol}
                            </td>
                            <td style={{ padding: '10px 12px' }}>
                              <span
                                style={{
                                  fontSize: '11px',
                                  padding: '2px 6px',
                                  borderRadius: 'var(--radius-xs)',
                                  backgroundColor: o.side === 'BUY' ? 'rgba(5, 150, 105, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                                  color: o.side === 'BUY' ? 'var(--color-profit, #059669)' : 'var(--color-loss, #EF4444)',
                                  fontWeight: 700,
                                }}
                              >
                                {o.side}
                              </span>
                            </td>
                            <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)' }}>{o.quantity}</td>
                            <td style={{ padding: '10px 12px', color: 'var(--color-loss, #EF4444)', fontWeight: 500 }}>
                              {o.rejection_reason || 'Unknown'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ===================================================================== */}
      {/* 2. USER DIRECTORY TAB */}
      {/* ===================================================================== */}
      {activeTab === 'users' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Search & Filters */}
          <div
            style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '16px',
              display: 'flex',
              flexWrap: 'wrap',
              gap: '12px',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', flex: '1 1 280px', gap: '8px' }}>
              <input
                type="text"
                placeholder="Search by name, email, or user ID..."
                value={userSearch}
                onChange={(e) => {
                  setUserSearch(e.target.value);
                  setUserPage(1);
                }}
                style={{
                  flex: 1,
                  backgroundColor: 'var(--bg-input, var(--bg-main))',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-xs)',
                  padding: '8px 12px',
                  fontSize: '13px',
                  color: 'var(--text-main)',
                  outline: 'none',
                }}
              />
            </div>

            {/* Filter Badges */}
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button
                onClick={() => {
                  setUserFilterVerified(userFilterVerified === true ? undefined : true);
                  setUserPage(1);
                }}
                style={{
                  backgroundColor: userFilterVerified === true ? 'var(--color-action)' : 'var(--bg-main)',
                  color: userFilterVerified === true ? '#FFFFFF' : 'var(--text-muted)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-xs)',
                  padding: '6px 12px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Verified Only
              </button>

              <button
                onClick={() => {
                  setUserFilterOnboarded(userFilterOnboarded === true ? undefined : true);
                  setUserPage(1);
                }}
                style={{
                  backgroundColor: userFilterOnboarded === true ? 'var(--color-action)' : 'var(--bg-main)',
                  color: userFilterOnboarded === true ? '#FFFFFF' : 'var(--text-muted)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-xs)',
                  padding: '6px 12px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Onboarded Only
              </button>

              {(userSearch || userFilterVerified !== undefined || userFilterOnboarded !== undefined) && (
                <button
                  onClick={() => {
                    setUserSearch('');
                    setUserFilterVerified(undefined);
                    setUserFilterOnboarded(undefined);
                    setUserFilterActive(undefined);
                    setUserPage(1);
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-muted)',
                    fontSize: '12px',
                    cursor: 'pointer',
                    textDecoration: 'underline',
                  }}
                >
                  Reset
                </button>
              )}
            </div>
          </div>

          {/* User Table */}
          <div
            style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '16px',
            }}
          >
            {usersLoading && (
              <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
                Loading users...
              </div>
            )}

            {usersError && (
              <div
                style={{
                  backgroundColor: 'rgba(239, 68, 68, 0.08)',
                  border: '1px solid var(--color-loss, #EF4444)',
                  borderRadius: 'var(--radius-xs)',
                  padding: '16px',
                  color: 'var(--color-loss, #EF4444)',
                  fontSize: '13px',
                }}
              >
                {usersError}
              </div>
            )}

            {!usersLoading && usersData && usersData.users.length === 0 && (
              <div style={{ padding: '48px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
                No registered users matched the active filters.
              </div>
            )}

            {!usersLoading && usersData && usersData.users.length > 0 && (
              <>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', color: 'var(--text-muted)' }}>
                        <th style={{ padding: '10px 12px' }}>Investor</th>
                        <th style={{ padding: '10px 12px' }}>Email</th>
                        <th style={{ padding: '10px 12px' }}>Registered</th>
                        <th style={{ padding: '10px 12px' }}>Verification</th>
                        <th style={{ padding: '10px 12px' }}>Onboarding</th>
                        <th style={{ padding: '10px 12px' }}>Risk Band</th>
                        <th style={{ padding: '10px 12px' }}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {usersData.users.map((u) => (
                        <tr key={u.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                          <td style={{ padding: '12px', fontWeight: 600, color: 'var(--text-main)' }}>
                            {u.full_name || u.display_name || 'Investor'}
                          </td>
                          <td style={{ padding: '12px', color: 'var(--text-main)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                            {u.email}
                          </td>
                          <td style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '12px', whiteSpace: 'nowrap' }}>
                            {u.created_at ? new Date(u.created_at).toLocaleDateString() : 'N/A'}
                          </td>
                          <td style={{ padding: '12px' }}>
                            <span
                              style={{
                                fontSize: '11px',
                                padding: '2px 8px',
                                borderRadius: 'var(--radius-xs)',
                                backgroundColor: u.email_verified ? 'rgba(5, 150, 105, 0.1)' : 'rgba(156, 163, 175, 0.15)',
                                color: u.email_verified ? 'var(--color-profit, #059669)' : 'var(--text-muted)',
                                fontWeight: 600,
                              }}
                            >
                              {u.email_verified ? 'Verified' : 'Unverified'}
                            </span>
                          </td>
                          <td style={{ padding: '12px' }}>
                            <span
                              style={{
                                fontSize: '11px',
                                padding: '2px 8px',
                                borderRadius: 'var(--radius-xs)',
                                backgroundColor: u.onboarding_completed ? 'rgba(5, 150, 105, 0.1)' : 'rgba(217, 119, 6, 0.1)',
                                color: u.onboarding_completed ? 'var(--color-profit, #059669)' : '#D97706',
                                fontWeight: 600,
                              }}
                            >
                              {u.onboarding_completed ? 'Completed' : 'Pending'}
                            </span>
                          </td>
                          <td style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '12px' }}>
                            {u.risk_band || 'Unscored'}
                          </td>
                          <td style={{ padding: '12px' }}>
                            <span
                              style={{
                                fontSize: '11px',
                                padding: '2px 8px',
                                borderRadius: 'var(--radius-xs)',
                                backgroundColor: u.is_active ? 'rgba(5, 150, 105, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                                color: u.is_active ? 'var(--color-profit, #059669)' : 'var(--color-loss, #EF4444)',
                                fontWeight: 600,
                              }}
                            >
                              {u.is_active ? 'Active' : 'Disabled'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination Controls */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginTop: '16px',
                    paddingTop: '12px',
                    borderTop: '1px solid var(--border-subtle)',
                    fontSize: '12px',
                    color: 'var(--text-muted)',
                  }}
                >
                  <div>
                    Showing {usersData.users.length} of {usersData.total} users (Page {usersData.page} of {usersData.total_pages})
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      onClick={() => setUserPage((p) => Math.max(1, p - 1))}
                      disabled={userPage <= 1}
                      style={{
                        backgroundColor: 'var(--bg-main)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-xs)',
                        padding: '6px 12px',
                        color: userPage <= 1 ? 'var(--text-muted)' : 'var(--text-main)',
                        cursor: userPage <= 1 ? 'not-allowed' : 'pointer',
                      }}
                    >
                      ← Previous
                    </button>
                    <button
                      onClick={() => setUserPage((p) => Math.min(usersData.total_pages, p + 1))}
                      disabled={userPage >= usersData.total_pages}
                      style={{
                        backgroundColor: 'var(--bg-main)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-xs)',
                        padding: '6px 12px',
                        color: userPage >= usersData.total_pages ? 'var(--text-muted)' : 'var(--text-main)',
                        cursor: userPage >= usersData.total_pages ? 'not-allowed' : 'pointer',
                      }}
                    >
                      Next →
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* 3. PAPER TRADING TAB */}
      {/* ===================================================================== */}
      {activeTab === 'orders' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Search & Filters */}
          <div
            style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '16px',
              display: 'flex',
              flexWrap: 'wrap',
              gap: '12px',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', flex: '1 1 260px', gap: '8px' }}>
              <input
                type="text"
                placeholder="Search symbol, user email, or reason..."
                value={orderSearch}
                onChange={(e) => {
                  setOrderSearch(e.target.value);
                  setOrderPage(1);
                }}
                style={{
                  flex: 1,
                  backgroundColor: 'var(--bg-input, var(--bg-main))',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-xs)',
                  padding: '8px 12px',
                  fontSize: '13px',
                  color: 'var(--text-main)',
                  outline: 'none',
                }}
              />
            </div>

            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {/* Side Filter */}
              <select
                value={orderSide}
                onChange={(e) => {
                  setOrderSide(e.target.value);
                  setOrderPage(1);
                }}
                style={{
                  backgroundColor: 'var(--bg-main)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-xs)',
                  padding: '6px 10px',
                  fontSize: '12px',
                  color: 'var(--text-main)',
                  cursor: 'pointer',
                }}
              >
                <option value="">All Sides</option>
                <option value="BUY">BUY</option>
                <option value="SELL">SELL</option>
              </select>

              {/* Status Filter */}
              <select
                value={orderStatus}
                onChange={(e) => {
                  setOrderStatus(e.target.value);
                  setOrderPage(1);
                }}
                style={{
                  backgroundColor: 'var(--bg-main)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-xs)',
                  padding: '6px 10px',
                  fontSize: '12px',
                  color: 'var(--text-main)',
                  cursor: 'pointer',
                }}
              >
                <option value="">All Statuses</option>
                <option value="FILLED">FILLED</option>
                <option value="REJECTED">REJECTED</option>
                <option value="PENDING">PENDING</option>
                <option value="CANCELLED">CANCELLED</option>
              </select>

              {(orderSearch || orderSide || orderStatus) && (
                <button
                  onClick={() => {
                    setOrderSearch('');
                    setOrderSide('');
                    setOrderStatus('');
                    setOrderPage(1);
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-muted)',
                    fontSize: '12px',
                    cursor: 'pointer',
                    textDecoration: 'underline',
                  }}
                >
                  Reset
                </button>
              )}
            </div>
          </div>

          {/* Orders Table */}
          <div
            style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '16px',
            }}
          >
            {ordersLoading && (
              <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
                Loading orders...
              </div>
            )}

            {ordersError && (
              <div
                style={{
                  backgroundColor: 'rgba(239, 68, 68, 0.08)',
                  border: '1px solid var(--color-loss, #EF4444)',
                  borderRadius: 'var(--radius-xs)',
                  padding: '16px',
                  color: 'var(--color-loss, #EF4444)',
                  fontSize: '13px',
                }}
              >
                {ordersError}
              </div>
            )}

            {!ordersLoading && ordersData && ordersData.orders.length === 0 && (
              <div style={{ padding: '48px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
                No paper orders match the selected filters.
              </div>
            )}

            {!ordersLoading && ordersData && ordersData.orders.length > 0 && (
              <>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', color: 'var(--text-muted)' }}>
                        <th style={{ padding: '10px 12px' }}>Time</th>
                        <th style={{ padding: '10px 12px' }}>User Email</th>
                        <th style={{ padding: '10px 12px' }}>Symbol</th>
                        <th style={{ padding: '10px 12px' }}>Side</th>
                        <th style={{ padding: '10px 12px' }}>Type</th>
                        <th style={{ padding: '10px 12px' }}>Qty</th>
                        <th style={{ padding: '10px 12px' }}>Fill / Limit</th>
                        <th style={{ padding: '10px 12px' }}>Status</th>
                        <th style={{ padding: '10px 12px' }}>Note / Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ordersData.orders.map((o) => {
                        let statusColor = 'var(--text-muted)';
                        let statusBg = 'rgba(156, 163, 175, 0.15)';
                        if (o.status === 'FILLED') {
                          statusColor = 'var(--color-profit, #059669)';
                          statusBg = 'rgba(5, 150, 105, 0.1)';
                        } else if (o.status === 'REJECTED') {
                          statusColor = 'var(--color-loss, #EF4444)';
                          statusBg = 'rgba(239, 68, 68, 0.1)';
                        } else if (o.status === 'PENDING') {
                          statusColor = '#D97706';
                          statusBg = 'rgba(217, 119, 6, 0.1)';
                        }

                        return (
                          <tr key={o.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                            <td style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '12px', whiteSpace: 'nowrap' }}>
                              {o.created_at ? new Date(o.created_at).toLocaleString() : 'N/A'}
                            </td>
                            <td style={{ padding: '12px', color: 'var(--text-main)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                              {o.user_email || o.user_id.substring(0, 12)}
                            </td>
                            <td style={{ padding: '12px', fontWeight: 700, color: 'var(--text-main)' }}>
                              {o.symbol}
                            </td>
                            <td style={{ padding: '12px' }}>
                              <span
                                style={{
                                  fontSize: '11px',
                                  padding: '2px 8px',
                                  borderRadius: 'var(--radius-xs)',
                                  backgroundColor: o.side === 'BUY' ? 'rgba(5, 150, 105, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                                  color: o.side === 'BUY' ? 'var(--color-profit, #059669)' : 'var(--color-loss, #EF4444)',
                                  fontWeight: 700,
                                }}
                              >
                                {o.side}
                              </span>
                            </td>
                            <td style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '11px', textTransform: 'uppercase' }}>
                              {o.order_type}
                            </td>
                            <td style={{ padding: '12px', fontFamily: 'var(--font-mono)' }}>{o.quantity}</td>
                            <td style={{ padding: '12px', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                              {o.fill_price ? `₹${o.fill_price.toLocaleString('en-IN')}` : o.limit_price ? `₹${o.limit_price.toLocaleString('en-IN')}` : '-'}
                            </td>
                            <td style={{ padding: '12px' }}>
                              <span
                                style={{
                                  fontSize: '11px',
                                  padding: '2px 8px',
                                  borderRadius: 'var(--radius-xs)',
                                  backgroundColor: statusBg,
                                  color: statusColor,
                                  fontWeight: 600,
                                }}
                              >
                                {o.status}
                              </span>
                            </td>
                            <td style={{ padding: '12px', color: o.rejection_reason ? 'var(--color-loss, #EF4444)' : 'var(--text-muted)', fontSize: '12px' }}>
                              {o.rejection_reason || '-'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Pagination Controls */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginTop: '16px',
                    paddingTop: '12px',
                    borderTop: '1px solid var(--border-subtle)',
                    fontSize: '12px',
                    color: 'var(--text-muted)',
                  }}
                >
                  <div>
                    Showing {ordersData.orders.length} of {ordersData.total} orders (Page {ordersData.page} of {ordersData.total_pages})
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      onClick={() => setOrderPage((p) => Math.max(1, p - 1))}
                      disabled={orderPage <= 1}
                      style={{
                        backgroundColor: 'var(--bg-main)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-xs)',
                        padding: '6px 12px',
                        color: orderPage <= 1 ? 'var(--text-muted)' : 'var(--text-main)',
                        cursor: orderPage <= 1 ? 'not-allowed' : 'pointer',
                      }}
                    >
                      ← Previous
                    </button>
                    <button
                      onClick={() => setOrderPage((p) => Math.min(ordersData.total_pages, p + 1))}
                      disabled={orderPage >= ordersData.total_pages}
                      style={{
                        backgroundColor: 'var(--bg-main)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-xs)',
                        padding: '6px 12px',
                        color: orderPage >= ordersData.total_pages ? 'var(--text-muted)' : 'var(--text-main)',
                        cursor: orderPage >= ordersData.total_pages ? 'not-allowed' : 'pointer',
                      }}
                    >
                      Next →
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* 4. SYSTEM HEALTH & INTEGRATIONS TAB */}
      {/* ===================================================================== */}
      {activeTab === 'health' && (
        <div>
          {healthLoading && !healthData && (
            <div style={{ padding: '60px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
              Checking backing service diagnostics...
            </div>
          )}

          {healthError && (
            <div
              style={{
                backgroundColor: 'rgba(239, 68, 68, 0.08)',
                border: '1px solid var(--color-loss, #EF4444)',
                borderRadius: 'var(--radius-xs)',
                padding: '16px',
                color: 'var(--color-loss, #EF4444)',
                fontSize: '13px',
                marginBottom: '20px',
              }}
            >
              {healthError}
            </div>
          )}

          {healthData && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                gap: '20px',
              }}
            >
              {/* Backend Process Card */}
              <div
                style={{
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '24px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '18px' }}>⚡</span>
                    <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
                      FastAPI Process
                    </h3>
                  </div>
                  <span
                    style={{
                      fontSize: '11px',
                      padding: '2px 8px',
                      borderRadius: 'var(--radius-xs)',
                      backgroundColor: healthData.backend.status === 'ok' ? 'rgba(5, 150, 105, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                      color: healthData.backend.status === 'ok' ? 'var(--color-profit, #059669)' : 'var(--color-loss, #EF4444)',
                      fontWeight: 700,
                    }}
                  >
                    {healthData.backend.status.toUpperCase()}
                  </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Application:</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>{healthData.backend.app}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Environment:</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>{healthData.backend.environment}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Deployment Build:</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-main)' }}>
                      {healthData.backend.version}
                    </span>
                  </div>
                </div>
              </div>

              {/* Database Readiness Card */}
              <div
                style={{
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '24px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '18px' }}>🐘</span>
                    <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
                      PostgreSQL Database
                    </h3>
                  </div>
                  <span
                    style={{
                      fontSize: '11px',
                      padding: '2px 8px',
                      borderRadius: 'var(--radius-xs)',
                      backgroundColor: healthData.database.status === 'ok' ? 'rgba(5, 150, 105, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                      color: healthData.database.status === 'ok' ? 'var(--color-profit, #059669)' : 'var(--color-loss, #EF4444)',
                      fontWeight: 700,
                    }}
                  >
                    {healthData.database.status === 'ok' ? 'HEALTHY' : 'UNAVAILABLE'}
                  </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Connection Check:</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                      {healthData.database.message || (healthData.database.status === 'ok' ? 'Ping Succeeded' : 'Failed')}
                    </span>
                  </div>
                  {healthData.database.error && (
                    <div style={{ color: 'var(--color-loss, #EF4444)', fontSize: '12px', marginTop: '4px' }}>
                      Error: {healthData.database.error}
                    </div>
                  )}
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Engine:</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>PostgreSQL asyncpg</span>
                  </div>
                </div>
              </div>

              {/* Market Data Mode Card */}
              <div
                style={{
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '24px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '18px' }}>📊</span>
                    <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
                      Market Data Feed
                    </h3>
                  </div>
                  <span
                    style={{
                      fontSize: '11px',
                      padding: '2px 8px',
                      borderRadius: 'var(--radius-xs)',
                      backgroundColor: 'rgba(5, 150, 105, 0.1)',
                      color: 'var(--color-profit, #059669)',
                      fontWeight: 700,
                    }}
                  >
                    ACTIVE
                  </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Configured Mode:</span>
                    <span style={{ fontWeight: 700, color: 'var(--color-action)' }}>
                      {healthData.market_data.mode}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Demo Simulation:</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                      {healthData.market_data.enable_demo_simulation ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Fixture Fallback:</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                      {healthData.market_data.allow_fixtures ? 'Permitted' : 'Blocked'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Angel One SmartAPI Card */}
              <div
                style={{
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '24px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '18px' }}>🛡️</span>
                    <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
                      Angel One SmartAPI
                    </h3>
                  </div>
                  <span
                    style={{
                      fontSize: '11px',
                      padding: '2px 8px',
                      borderRadius: 'var(--radius-xs)',
                      backgroundColor: healthData.angel_one.is_configured ? 'rgba(5, 150, 105, 0.1)' : 'rgba(217, 119, 6, 0.1)',
                      color: healthData.angel_one.is_configured ? 'var(--color-profit, #059669)' : '#D97706',
                      fontWeight: 700,
                    }}
                  >
                    {healthData.angel_one.is_configured ? 'CONFIGURED (UNVERIFIED LIVE)' : 'NOT CONFIGURED'}
                  </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>SmartAPI SDK:</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                      {healthData.angel_one.smartapi_library_available ? 'Available' : 'Unavailable'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Circuit Breaker:</span>
                    <span
                      style={{
                        fontWeight: 600,
                        color: healthData.angel_one.is_circuit_open ? 'var(--color-loss, #EF4444)' : 'var(--color-profit, #059669)',
                      }}
                    >
                      {healthData.angel_one.is_circuit_open ? 'Open (Tripped)' : 'Closed (Normal)'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Live Session:</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                      {healthData.angel_one.has_active_session ? 'Active' : 'No Active Session'}
                    </span>
                  </div>
                  {healthData.angel_one.missing_fields && healthData.angel_one.missing_fields.length > 0 && (
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                      Missing: {healthData.angel_one.missing_fields.join(', ')}
                    </div>
                  )}
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '6px', padding: '6px 8px', backgroundColor: 'rgba(255, 255, 255, 0.03)', borderRadius: 'var(--radius-xs)', borderLeft: '2px solid var(--color-action)' }}>
                    ℹ️ <strong>Operational Notice:</strong> Configuration reflects present environment credentials. It does not prove that live market data or exchange streaming is working.
                  </div>
                </div>
              </div>

              {/* Transactional Email / SMTP Card */}
              <div
                style={{
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '24px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '18px' }}>✉️</span>
                    <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
                      Transactional Email
                    </h3>
                  </div>
                  <span
                    style={{
                      fontSize: '11px',
                      padding: '2px 8px',
                      borderRadius: 'var(--radius-xs)',
                      backgroundColor: healthData.email.is_configured ? 'rgba(5, 150, 105, 0.1)' : 'rgba(156, 163, 175, 0.15)',
                      color: healthData.email.is_configured ? 'var(--color-profit, #059669)' : 'var(--text-muted)',
                      fontWeight: 700,
                    }}
                  >
                    {healthData.email.is_configured ? 'CONFIGURED (DELIVERY UNVERIFIED)' : 'UNAVAILABLE'}
                  </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>SMTP Server:</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-main)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                      {healthData.email.host}
                    </span>
                  </div>
                  {healthData.email.is_configured && (
                    <>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-muted)' }}>Port / TLS:</span>
                        <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                          {healthData.email.port} ({healthData.email.use_tls ? 'TLS' : 'Plain'})
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-muted)' }}>From Sender:</span>
                        <span style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '12px' }}>
                          {healthData.email.from_email}
                        </span>
                      </div>
                    </>
                  )}
                  {!healthData.email.is_configured && (
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                      Development fallback queue active. Outbound delivery is disabled.
                    </div>
                  )}
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '6px', padding: '6px 8px', backgroundColor: 'rgba(255, 255, 255, 0.03)', borderRadius: 'var(--radius-xs)', borderLeft: '2px solid var(--color-action)' }}>
                    ℹ️ <strong>Operational Notice:</strong> SMTP host configuration detected. It does not prove that email delivery to recipient inboxes is working.
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ===================================================================== */}
      {/* 5. ERRORS MONITORING TAB */}
      {/* ===================================================================== */}
      {activeTab === 'errors' && (
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
              Database writes are bounded by a 250ms ceiling and concurrency limits (max 5 simultaneous writes); during storage degradation, events are dropped fail-open to preserve database connection pool capacity.
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
              <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--color-loss, #EF4444)', marginTop: '4px' }}>
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
              <div style={{ padding: '24px', backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--color-loss, #EF4444)', borderRadius: '4px' }}>
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
                                  color: is5xx ? 'var(--color-loss, #EF4444)' : '#F59E0B',
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
                                      color: copiedId === item.correlation_id ? 'var(--color-profit, #059669)' : 'var(--text-muted)',
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
      )}
    </div>
  );
};

export default AdminScreen;
