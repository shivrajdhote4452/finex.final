import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  apiClient,
  AdminUserItem,
  AdminUsersResponse,
} from '../../api/client';
import {
  DEFAULT_USER_FILTERS,
  USER_ACCOUNT_STATUS_OPTIONS,
  USER_ONBOARDING_OPTIONS,
  USER_PAGE_SIZE_OPTIONS,
  USER_SORT_OPTIONS,
  USER_VERIFICATION_OPTIONS,
  UserAccountStatusFilter,
  UserBooleanFilter,
  UserFilterState,
  UserSortOrder,
  buildUserQueryParams,
  formatUserRegistrationDate,
  hasActiveUserFilters,
  resolveUserDisplayName,
  validateUserDateRange,
} from '../../domain/userDirectory';

interface AdminUsersPanelProps {
  /** Incremented by parent Refresh button to trigger re-fetch. */
  refreshTrigger?: number;
  /** Called when an admin API call receives HTTP 401 Unauthorized. */
  onUnauthorized?: () => void;
  /** Reports loading status to parent shell (e.g. header Refresh button). */
  onLoadingChange?: (loading: boolean) => void;
}

export const AdminUsersPanel: React.FC<AdminUsersPanelProps> = ({
  refreshTrigger = 0,
  onUnauthorized,
  onLoadingChange,
}) => {
  const [usersData, setUsersData] = useState<AdminUsersResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [filters, setFilters] = useState<UserFilterState>(DEFAULT_USER_FILTERS);
  const [searchInput, setSearchInput] = useState<string>('');
  const [page, setPage] = useState<number>(1);

  // Debounce search text cleanly so typing does not fire on every keystroke
  useEffect(() => {
    if (filters.search === searchInput) return;
    const timer = setTimeout(() => {
      setFilters((prev) => {
        if (prev.search === searchInput) return prev;
        return { ...prev, search: searchInput };
      });
      setPage(1);
    }, 280);
    return () => clearTimeout(timer);
  }, [searchInput, filters.search]);

  const dateRangeError = useMemo(
    () => validateUserDateRange(filters.dateFrom, filters.dateTo),
    [filters.dateFrom, filters.dateTo]
  );

  const fetchUsers = useCallback(async () => {
    if (dateRangeError) {
      return;
    }
    setLoading(true);
    onLoadingChange?.(true);
    setErrorMsg(null);
    try {
      const queryParams = buildUserQueryParams(filters, page, true);
      const listData = await apiClient.admin.getUsers(queryParams);
      setUsersData(listData);
      if (listData.total_pages > 0 && page > listData.total_pages) {
        setPage(listData.total_pages);
      }
    } catch (err: any) {
      if (err?.status === 401) {
        onUnauthorized?.();
        return;
      }
      setErrorMsg(err?.message || 'Failed to load registered user directory.');
    } finally {
      setLoading(false);
      onLoadingChange?.(false);
    }
  }, [filters, page, dateRangeError, onUnauthorized, onLoadingChange]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers, refreshTrigger]);

  const handleClearFilters = () => {
    setSearchInput('');
    setFilters(DEFAULT_USER_FILTERS);
    setPage(1);
  };

  const filtersActive = hasActiveUserFilters({ ...filters, search: searchInput });

  const showingFrom =
    usersData && usersData.total > 0 ? (usersData.page - 1) * usersData.limit + 1 : 0;
  const showingTo =
    usersData && usersData.total > 0
      ? Math.min(usersData.total, (usersData.page - 1) * usersData.limit + usersData.users.length)
      : 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Read-Only Privacy Notice */}
      <div className="admin-errors-notice">
        <div
          style={{
            fontWeight: 700,
            color: 'var(--color-action)',
            marginBottom: '4px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <span>🔒</span>
          <span>Read-Only User Directory &amp; Privacy Guardrails</span>
        </div>
        <div>
          Displays safe administrative user fields only (name, email, account status, verification, onboarding progress,
          and registration date). Password hashes, tokens, OAuth subjects, and private questionnaire answers are
          strictly excluded.
        </div>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="admin-panel-toolbar" role="search" aria-label="Filter registered users">
        <div className="admin-panel-search-row">
          <div style={{ position: 'relative', flex: 1, minWidth: 0 }}>
            <input
              type="text"
              aria-label="Search registered users"
              maxLength={120}
              placeholder="Search by name or email..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  setFilters((prev) => ({ ...prev, search: searchInput }));
                  setPage(1);
                }
              }}
              className="admin-panel-input"
              style={{ width: '100%', paddingRight: searchInput ? '32px' : '12px' }}
            />
            {searchInput && (
              <button
                type="button"
                aria-label="Clear search text"
                onClick={() => {
                  setSearchInput('');
                  setFilters((prev) => ({ ...prev, search: '' }));
                  setPage(1);
                }}
                style={{
                  position: 'absolute',
                  right: '8px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  fontSize: '14px',
                  lineHeight: 1,
                  padding: '2px 4px',
                }}
              >
                ×
              </button>
            )}
          </div>

          {filtersActive && (
            <button
              type="button"
              onClick={handleClearFilters}
              className="admin-panel-clear-btn"
            >
              Clear Filters
            </button>
          )}
        </div>

        <div className="admin-panel-filter-grid">
          <label className="admin-panel-filter-field">
            <span className="admin-panel-filter-label">Account Status</span>
            <select
              aria-label="Filter by account status"
              value={filters.accountStatus}
              onChange={(e) => {
                setFilters((prev) => ({
                  ...prev,
                  accountStatus: e.target.value as UserAccountStatusFilter,
                }));
                setPage(1);
              }}
              className="admin-panel-select"
            >
              {USER_ACCOUNT_STATUS_OPTIONS.map((opt) => (
                <option key={opt.value || 'all'} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>

          <label className="admin-panel-filter-field">
            <span className="admin-panel-filter-label">Email Verification</span>
            <select
              aria-label="Filter by email verification status"
              value={filters.emailVerified}
              onChange={(e) => {
                setFilters((prev) => ({
                  ...prev,
                  emailVerified: e.target.value as UserBooleanFilter,
                }));
                setPage(1);
              }}
              className="admin-panel-select"
            >
              {USER_VERIFICATION_OPTIONS.map((opt) => (
                <option key={opt.value || 'all'} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>

          <label className="admin-panel-filter-field">
            <span className="admin-panel-filter-label">Onboarding</span>
            <select
              aria-label="Filter by onboarding status"
              value={filters.onboardingCompleted}
              onChange={(e) => {
                setFilters((prev) => ({
                  ...prev,
                  onboardingCompleted: e.target.value as UserBooleanFilter,
                }));
                setPage(1);
              }}
              className="admin-panel-select"
            >
              {USER_ONBOARDING_OPTIONS.map((opt) => (
                <option key={opt.value || 'all'} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>

          <label className="admin-panel-filter-field">
            <span className="admin-panel-filter-label">Registered From</span>
            <input
              type="date"
              aria-label="Registered from date"
              value={filters.dateFrom}
              max={filters.dateTo || undefined}
              onChange={(e) => {
                setFilters((prev) => ({ ...prev, dateFrom: e.target.value }));
                setPage(1);
              }}
              className="admin-panel-input"
            />
          </label>

          <label className="admin-panel-filter-field">
            <span className="admin-panel-filter-label">Registered To</span>
            <input
              type="date"
              aria-label="Registered to date"
              value={filters.dateTo}
              min={filters.dateFrom || undefined}
              onChange={(e) => {
                setFilters((prev) => ({ ...prev, dateTo: e.target.value }));
                setPage(1);
              }}
              className="admin-panel-input"
            />
          </label>

          <div className="admin-panel-filter-field">
            <span className="admin-panel-filter-label">Sort &amp; Page Size</span>
            <div style={{ display: 'flex', gap: '6px' }}>
              <select
                aria-label="Sort users by registration date"
                value={filters.sortOrder}
                onChange={(e) => {
                  setFilters((prev) => ({
                    ...prev,
                    sortOrder: e.target.value as UserSortOrder,
                  }));
                  setPage(1);
                }}
                className="admin-panel-select"
                style={{ flex: 1 }}
              >
                {USER_SORT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <select
                aria-label="Users per page"
                value={String(filters.limit)}
                onChange={(e) => {
                  setFilters((prev) => ({
                    ...prev,
                    limit: parseInt(e.target.value, 10) || 20,
                  }));
                  setPage(1);
                }}
                className="admin-panel-select"
                style={{ width: '78px' }}
              >
                {USER_PAGE_SIZE_OPTIONS.map((sz) => (
                  <option key={sz} value={String(sz)}>
                    {sz} / pg
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {dateRangeError && (
          <div className="admin-panel-inline-alert" role="alert">
            <span>⚠️ {dateRangeError}</span>
            <button
              type="button"
              onClick={() => {
                setFilters((prev) => ({ ...prev, dateFrom: '', dateTo: '' }));
                setPage(1);
              }}
              className="admin-panel-clear-btn"
              style={{ padding: '4px 8px', fontSize: '11px' }}
            >
              Reset Dates
            </button>
          </div>
        )}
      </div>

      {/* Results Container */}
      <div className="admin-panel-results-card">
        {loading && !usersData ? (
          <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: '13px', fontWeight: 600 }}>Loading user directory...</div>
            <div style={{ fontSize: '12px', marginTop: '6px' }}>Applying active search and filter parameters</div>
          </div>
        ) : errorMsg ? (
          <div className="admin-panel-error-banner" role="alert">
            <div>
              <div style={{ fontWeight: 700, marginBottom: '4px' }}>Unable to load user directory</div>
              <div style={{ fontSize: '12px' }}>{errorMsg}</div>
            </div>
            <button
              type="button"
              onClick={fetchUsers}
              className="admin-panel-retry-btn"
            >
              Retry
            </button>
          </div>
        ) : !usersData || usersData.users.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '56px 16px', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: '28px', marginBottom: '8px' }}>
              {filtersActive ? '🔍' : '👥'}
            </div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-main)' }}>
              {filtersActive ? 'No matching users found' : 'No registered users found'}
            </div>
            <div style={{ fontSize: '12px', marginTop: '6px', maxWidth: '460px', marginInline: 'auto' }}>
              {filtersActive
                ? 'No users match your current name/email search, status filters, or registration date window.'
                : 'No user accounts are currently present in the directory.'}
            </div>
            {filtersActive && (
              <button
                type="button"
                onClick={handleClearFilters}
                className="admin-panel-clear-btn"
                style={{ marginTop: '16px' }}
              >
                Clear All Filters
              </button>
            )}
          </div>
        ) : (
          <>
            {/* Status header above table/cards */}
            <div className="admin-panel-results-header">
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Showing <strong style={{ color: 'var(--text-main)' }}>{showingFrom}–{showingTo}</strong> of{' '}
                <strong style={{ color: 'var(--text-main)' }}>{usersData.total.toLocaleString()}</strong>{' '}
                {filtersActive ? 'matching users' : 'registered users'}
                {filters.sortOrder === 'desc' ? ' · Newest registered first' : ' · Oldest registered first'}
              </div>
              {loading && (
                <span style={{ fontSize: '11px', color: 'var(--color-action)', fontWeight: 600 }}>
                  Updating directory...
                </span>
              )}
            </div>

            {/* Desktop Table Layout */}
            <div className="admin-panel-desktop-table">
              <div className="table-scroll-wrapper" style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                      <th style={{ padding: '10px 8px' }}>Name</th>
                      <th style={{ padding: '10px 8px' }}>Email</th>
                      <th style={{ padding: '10px 8px' }}>Account Status</th>
                      <th style={{ padding: '10px 8px' }}>Verification</th>
                      <th style={{ padding: '10px 8px' }}>Onboarding</th>
                      <th style={{ padding: '10px 8px' }}>Registration Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {usersData.users.map((u: AdminUserItem) => {
                      const primaryName = resolveUserDisplayName(u);
                      return (
                        <tr key={u.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                          <td style={{ padding: '10px 8px', fontWeight: 600, color: 'var(--text-main)' }}>
                            {primaryName}
                          </td>
                          <td
                            style={{
                              padding: '10px 8px',
                              fontFamily: 'var(--font-mono)',
                              color: 'var(--text-main)',
                              wordBreak: 'break-word',
                            }}
                          >
                            {u.email}
                          </td>
                          <td style={{ padding: '10px 8px' }}>
                            <span
                              className={`admin-pill ${
                                u.is_active ? 'admin-pill-positive' : 'admin-pill-negative'
                              }`}
                            >
                              {u.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </td>
                          <td style={{ padding: '10px 8px' }}>
                            <span
                              className={`admin-pill ${
                                u.email_verified ? 'admin-pill-positive' : 'admin-pill-neutral'
                              }`}
                            >
                              {u.email_verified ? 'Verified' : 'Unverified'}
                            </span>
                          </td>
                          <td style={{ padding: '10px 8px' }}>
                            <span
                              className={`admin-pill ${
                                u.onboarding_completed ? 'admin-pill-positive' : 'admin-pill-warning'
                              }`}
                            >
                              {u.onboarding_completed ? 'Completed' : 'Pending'}
                            </span>
                          </td>
                          <td
                            style={{ padding: '10px 8px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}
                            title={u.created_at || undefined}
                          >
                            {formatUserRegistrationDate(u.created_at)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Mobile Stacked Card Layout */}
            <div className="admin-panel-mobile-list">
              {usersData.users.map((u: AdminUserItem) => {
                const primaryName = resolveUserDisplayName(u);
                return (
                  <article key={u.id} className="admin-panel-card">
                    <div className="admin-panel-card-top">
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-main)' }}>
                          {primaryName}
                        </div>
                        <div
                          style={{
                            fontSize: '12px',
                            fontFamily: 'var(--font-mono)',
                            color: 'var(--text-muted)',
                            wordBreak: 'break-word',
                            marginTop: '2px',
                          }}
                        >
                          {u.email}
                        </div>
                      </div>
                      <span
                        className={`admin-pill ${
                          u.is_active ? 'admin-pill-positive' : 'admin-pill-negative'
                        }`}
                      >
                        {u.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>

                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      <span
                        className={`admin-pill ${
                          u.email_verified ? 'admin-pill-positive' : 'admin-pill-neutral'
                        }`}
                      >
                        {u.email_verified ? 'Email Verified' : 'Unverified Email'}
                      </span>
                      <span
                        className={`admin-pill ${
                          u.onboarding_completed ? 'admin-pill-positive' : 'admin-pill-warning'
                        }`}
                      >
                        Onboarding: {u.onboarding_completed ? 'Completed' : 'Pending'}
                      </span>
                    </div>

                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: '8px',
                        paddingTop: '6px',
                        borderTop: '1px solid var(--border-subtle)',
                        fontSize: '11px',
                        color: 'var(--text-muted)',
                      }}
                    >
                      <span>Registered</span>
                      <span title={u.created_at || undefined}>
                        {formatUserRegistrationDate(u.created_at)}
                      </span>
                    </div>
                  </article>
                );
              })}
            </div>

            {/* Bounded Pagination Footer */}
            <div className="admin-panel-pagination">
              <div style={{ color: 'var(--text-muted)' }}>
                Page <strong style={{ color: 'var(--text-main)' }}>{usersData.page}</strong> of{' '}
                <strong style={{ color: 'var(--text-main)' }}>{usersData.total_pages}</strong> · Total{' '}
                {usersData.total.toLocaleString()}
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={loading || usersData.page <= 1}
                  className="admin-panel-page-btn"
                >
                  ← Previous
                </button>
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.min(usersData.total_pages, p + 1))}
                  disabled={loading || usersData.page >= usersData.total_pages}
                  className="admin-panel-page-btn"
                >
                  Next →
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
