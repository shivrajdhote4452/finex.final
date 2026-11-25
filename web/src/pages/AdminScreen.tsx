import React, { useState, useEffect, useCallback } from 'react';
import { useFinancial } from '../context/FinancialContext';
import {
  apiClient,
  AdminOverviewResponse,
  AdminSystemHealthResponse,
} from '../api/client';
import { AdminErrorsPanel } from '../components/admin/AdminErrorsPanel';
import { AdminOrdersPanel } from '../components/admin/AdminOrdersPanel';
import { AdminUsersPanel } from '../components/admin/AdminUsersPanel';
import {
  formatOrderTimestamp,
  normalizeOrderStatusCounts,
  resolveOrderFailureDetails,
} from '../domain/paperTradingOverview';
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

  // Load data when active tab changes
  useEffect(() => {
    if (!isOwner) return;
    if (activeTab === 'overview') fetchOverview();
    else if (activeTab === 'health') fetchHealth();
  }, [activeTab, isOwner, fetchOverview, fetchHealth]);

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
            else if (activeTab === 'users') setUsersRefreshTick((n) => n + 1);
            else if (activeTab === 'orders') setOrdersRefreshTick((n) => n + 1);
            else if (activeTab === 'health') fetchHealth();
            else if (activeTab === 'errors') setErrorsRefreshTick((n) => n + 1);
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
                  {Object.entries(normalizeOrderStatusCounts(overviewData.orders_by_status)).map(([status, count]) => (
                    <div
                      key={status}
                      style={{
                        backgroundColor: 'var(--bg-input)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-xs)',
                        padding: '12px 16px',
                      }}
                    >
                      <span
                        className={`admin-pill ${
                          status === 'FILLED'
                            ? 'admin-pill-positive'
                            : status === 'REJECTED'
                              ? 'admin-pill-negative'
                              : status === 'PENDING'
                                ? 'admin-pill-warning'
                                : 'admin-pill-neutral'
                        }`}
                      >
                        {status}
                      </span>
                      <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-main)', fontFamily: 'var(--font-mono)', marginTop: '6px' }}>
                        {count.toLocaleString()}
                      </div>
                    </div>
                  ))}
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
                      setOrdersPresetStatus('REJECTED');
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
                          <th style={{ padding: '8px 12px' }}>Safeguard / Failure Details</th>
                        </tr>
                      </thead>
                      <tbody>
                        {overviewData.recent_rejected_orders.map((o) => (
                          <tr key={o.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                            <td style={{ padding: '10px 12px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                              {formatOrderTimestamp(o.created_at)}
                            </td>
                            <td style={{ padding: '10px 12px', fontWeight: 700, color: 'var(--text-main)' }}>
                              {o.symbol}
                            </td>
                            <td style={{ padding: '10px 12px' }}>
                              <span className={`admin-pill ${o.side === 'BUY' ? 'admin-pill-positive' : 'admin-pill-negative'}`}>
                                {o.side}
                              </span>
                            </td>
                            <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)' }}>{o.quantity}</td>
                            <td style={{ padding: '10px 12px', color: 'var(--color-loss)', fontWeight: 500 }}>
                              {resolveOrderFailureDetails(o)}
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
        <AdminUsersPanel
          refreshTrigger={usersRefreshTick}
          onLoadingChange={setUsersLoading}
        />
      )}

      {/* ===================================================================== */}
      {/* 3. PAPER TRADING TAB */}
      {/* ===================================================================== */}
      {activeTab === 'orders' && (
        <AdminOrdersPanel
          refreshTrigger={ordersRefreshTick}
          initialStatusFilter={ordersPresetStatus}
          onLoadingChange={setOrdersLoading}
        />
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
        <AdminErrorsPanel
          refreshTrigger={errorsRefreshTick}
          onLoadingChange={setErrorsLoading}
        />
      )}
    </div>
  );
};

export default AdminScreen;
