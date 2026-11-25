import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  apiClient,
  AdminErrorItem,
  AdminErrorsResponse,
  AdminErrorSummaryResponse,
} from '../../api/client';
import {
  DEFAULT_ERROR_FILTERS,
  ERROR_CATEGORIES,
  ERROR_FEATURE_AREAS,
  ERROR_PAGE_SIZE_OPTIONS,
  ERROR_STATUS_OPTIONS,
  ErrorFilterState,
  ErrorSortOrder,
  buildErrorQueryParams,
  formatErrorTimestamp,
  hasActiveErrorFilters,
  mergeErrorFilterOptions,
  validateErrorDateRange,
} from '../../domain/errorMonitoring';

interface AdminErrorsPanelProps {
  /** Incremented by parent Refresh button to trigger re-fetch. */
  refreshTrigger?: number;
  /** Called when an admin API call receives HTTP 401 Unauthorized. */
  onUnauthorized?: () => void;
  /** Reports loading status to parent shell (e.g. header Refresh button). */
  onLoadingChange?: (loading: boolean) => void;
}

export const AdminErrorsPanel: React.FC<AdminErrorsPanelProps> = ({
  refreshTrigger = 0,
  onUnauthorized,
  onLoadingChange,
}) => {
  const [errorsData, setErrorsData] = useState<AdminErrorsResponse | null>(null);
  const [errorSummary, setErrorSummary] = useState<AdminErrorSummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [filters, setFilters] = useState<ErrorFilterState>(DEFAULT_ERROR_FILTERS);
  const [searchInput, setSearchInput] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const [copiedId, setCopiedId] = useState<string | null>(null);

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
    () => validateErrorDateRange(filters.dateFrom, filters.dateTo),
    [filters.dateFrom, filters.dateTo]
  );

  const categoryOptions = useMemo(
    () => mergeErrorFilterOptions(ERROR_CATEGORIES, errorSummary?.errors_by_category),
    [errorSummary]
  );

  const featureAreaOptions = useMemo(
    () => mergeErrorFilterOptions(ERROR_FEATURE_AREAS, errorSummary?.errors_by_feature),
    [errorSummary]
  );

  const fetchErrors = useCallback(async () => {
    if (dateRangeError) {
      return;
    }
    setLoading(true);
    onLoadingChange?.(true);
    setErrorMsg(null);
    try {
      const queryParams = buildErrorQueryParams(filters, page, true);
      const [listData, summaryData] = await Promise.all([
        apiClient.admin.getErrors(queryParams),
        apiClient.admin.getErrorsSummary(),
      ]);
      setErrorsData(listData);
      setErrorSummary(summaryData);
      // If retention pruning reduced total pages below current page, clamp safely back
      if (listData.total_pages > 0 && page > listData.total_pages) {
        setPage(listData.total_pages);
      }
    } catch (err: any) {
      if (err?.status === 401) {
        onUnauthorized?.();
        return;
      }
      setErrorMsg(err?.message || 'Failed to load server-side error monitoring log.');
    } finally {
      setLoading(false);
      onLoadingChange?.(false);
    }
  }, [filters, page, dateRangeError, onUnauthorized, onLoadingChange]);

  useEffect(() => {
    fetchErrors();
  }, [fetchErrors, refreshTrigger]);

  const handleClearFilters = () => {
    setSearchInput('');
    setFilters(DEFAULT_ERROR_FILTERS);
    setPage(1);
  };

  const handleCopyCorrelationId = (cid: string) => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard
        .writeText(cid)
        .then(() => {
          setCopiedId(cid);
          setTimeout(() => setCopiedId(null), 2000);
        })
        .catch(() => {});
    }
  };

  const filtersActive = hasActiveErrorFilters({ ...filters, search: searchInput });

  const showingFrom =
    errorsData && errorsData.total > 0 ? (errorsData.page - 1) * errorsData.limit + 1 : 0;
  const showingTo =
    errorsData && errorsData.total > 0
      ? Math.min(errorsData.total, (errorsData.page - 1) * errorsData.limit + errorsData.errors.length)
      : 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Surveillance Scope & Data Hygiene Notice */}
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
          <span>ℹ️</span>
          <span>Observability Scope &amp; Data Hygiene Notice</span>
        </div>
        <div>
          This dashboard displays real recorded server-side operational exceptions (400, 401, 403, 404, 413, 422, 429,
          500, and 503). It <strong>does not</strong> capture client-side network disconnects, browser script crashes, or
          edge CDN drops that never reach the backend API. Routes are stored as templates (unmatched paths are
          anonymized to <code style={{ fontFamily: 'var(--font-mono)' }}>/unmatched_route</code>), client secrets and
          request bodies are excluded, and database writes fail open under storage degradation to protect connection
          pool capacity.
        </div>
      </div>

      {/* Aggregate KPI Cards */}
      <div className="admin-errors-kpi-grid">
        <div className="admin-errors-kpi-card">
          <div className="admin-errors-kpi-label">Total Recorded Errors</div>
          <div className="admin-errors-kpi-value" style={{ color: 'var(--text-main)' }}>
            {errorSummary ? errorSummary.total_errors.toLocaleString() : '—'}
          </div>
          <div className="admin-errors-kpi-sub">30d / 5,000-row retention target</div>
        </div>

        <div className="admin-errors-kpi-card">
          <div className="admin-errors-kpi-label">Server Errors (5xx)</div>
          <div className="admin-errors-kpi-value" style={{ color: 'var(--color-loss)' }}>
            {errorSummary ? errorSummary.server_errors_5xx.toLocaleString() : '—'}
          </div>
          <div className="admin-errors-kpi-sub">Unhandled &amp; upstream 5xx</div>
        </div>

        <div className="admin-errors-kpi-card">
          <div className="admin-errors-kpi-label">Client / Validation (4xx)</div>
          <div className="admin-errors-kpi-value" style={{ color: 'var(--color-warning)' }}>
            {errorSummary ? errorSummary.client_errors_4xx.toLocaleString() : '—'}
          </div>
          <div className="admin-errors-kpi-sub">Auth, rate limits &amp; validation</div>
        </div>

        <div className="admin-errors-kpi-card">
          <div className="admin-errors-kpi-label">Past 24 Hours</div>
          <div className="admin-errors-kpi-value" style={{ color: 'var(--color-action)' }}>
            {errorSummary ? errorSummary.last_24h_errors.toLocaleString() : '—'}
          </div>
          <div className="admin-errors-kpi-sub">Rolling 24h event volume</div>
        </div>
      </div>

      {/* Search & Multi-Facet Filter Toolbar */}
      <div className="admin-errors-toolbar" role="search" aria-label="Filter recorded error events">
        <div className="admin-errors-search-row">
          <div style={{ position: 'relative', flex: 1, minWidth: 0 }}>
            <input
              type="text"
              aria-label="Search recorded errors"
              maxLength={120}
              placeholder="Search correlation ID, endpoint, category, feature area, error type, or message..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  setFilters((prev) => ({ ...prev, search: searchInput }));
                  setPage(1);
                }
              }}
              className="admin-errors-input"
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
              className="admin-errors-clear-btn"
            >
              Clear Filters
            </button>
          )}
        </div>

        <div className="admin-errors-filter-grid">
          <label className="admin-errors-filter-field">
            <span className="admin-errors-filter-label">Category</span>
            <select
              aria-label="Filter by error category"
              value={filters.category}
              onChange={(e) => {
                setFilters((prev) => ({ ...prev, category: e.target.value }));
                setPage(1);
              }}
              className="admin-errors-select"
            >
              <option value="">All Categories</option>
              {categoryOptions.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </label>

          <label className="admin-errors-filter-field">
            <span className="admin-errors-filter-label">Feature Area</span>
            <select
              aria-label="Filter by feature area"
              value={filters.featureArea}
              onChange={(e) => {
                setFilters((prev) => ({ ...prev, featureArea: e.target.value }));
                setPage(1);
              }}
              className="admin-errors-select"
            >
              <option value="">All Feature Areas</option>
              {featureAreaOptions.map((area) => (
                <option key={area} value={area}>
                  {area}
                </option>
              ))}
            </select>
          </label>

          <label className="admin-errors-filter-field">
            <span className="admin-errors-filter-label">Status Code</span>
            <select
              aria-label="Filter by HTTP status code"
              value={filters.statusCode}
              onChange={(e) => {
                setFilters((prev) => ({ ...prev, statusCode: e.target.value }));
                setPage(1);
              }}
              className="admin-errors-select"
            >
              <option value="">All Status Codes</option>
              {ERROR_STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={String(opt.value)}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>

          <label className="admin-errors-filter-field">
            <span className="admin-errors-filter-label">From Date</span>
            <input
              type="date"
              aria-label="From date"
              value={filters.dateFrom}
              max={filters.dateTo || undefined}
              onChange={(e) => {
                setFilters((prev) => ({ ...prev, dateFrom: e.target.value }));
                setPage(1);
              }}
              className="admin-errors-input"
            />
          </label>

          <label className="admin-errors-filter-field">
            <span className="admin-errors-filter-label">To Date</span>
            <input
              type="date"
              aria-label="To date"
              value={filters.dateTo}
              min={filters.dateFrom || undefined}
              onChange={(e) => {
                setFilters((prev) => ({ ...prev, dateTo: e.target.value }));
                setPage(1);
              }}
              className="admin-errors-input"
            />
          </label>

          <div className="admin-errors-filter-field">
            <span className="admin-errors-filter-label">Sort &amp; Page Size</span>
            <div style={{ display: 'flex', gap: '6px' }}>
              <select
                aria-label="Sort order"
                value={filters.sortOrder}
                onChange={(e) => {
                  setFilters((prev) => ({ ...prev, sortOrder: e.target.value as ErrorSortOrder }));
                  setPage(1);
                }}
                className="admin-errors-select"
                style={{ flex: 1 }}
              >
                <option value="desc">Latest first</option>
                <option value="asc">Oldest first</option>
              </select>
              <select
                aria-label="Results per page"
                value={String(filters.limit)}
                onChange={(e) => {
                  setFilters((prev) => ({ ...prev, limit: parseInt(e.target.value, 10) || 20 }));
                  setPage(1);
                }}
                className="admin-errors-select"
                style={{ width: '78px' }}
              >
                {ERROR_PAGE_SIZE_OPTIONS.map((sz) => (
                  <option key={sz} value={String(sz)}>
                    {sz} / pg
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {dateRangeError && (
          <div className="admin-errors-inline-alert" role="alert">
            <span>⚠️ {dateRangeError}</span>
            <button
              type="button"
              onClick={() => {
                setFilters((prev) => ({ ...prev, dateFrom: '', dateTo: '' }));
                setPage(1);
              }}
              className="admin-errors-clear-btn"
              style={{ padding: '4px 8px', fontSize: '11px' }}
            >
              Reset Dates
            </button>
          </div>
        )}
      </div>

      {/* Results Container */}
      <div className="admin-errors-results-card">
        {loading && !errorsData ? (
          <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: '13px', fontWeight: 600 }}>Loading recorded server-side error events...</div>
            <div style={{ fontSize: '12px', marginTop: '6px' }}>Applying active search and filter parameters</div>
          </div>
        ) : errorMsg ? (
          <div className="admin-errors-error-banner" role="alert">
            <div>
              <div style={{ fontWeight: 700, marginBottom: '4px' }}>Unable to load error events</div>
              <div style={{ fontSize: '12px' }}>{errorMsg}</div>
            </div>
            <button
              type="button"
              onClick={fetchErrors}
              className="admin-errors-retry-btn"
            >
              Retry
            </button>
          </div>
        ) : !errorsData || errorsData.errors.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '56px 16px', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: '28px', marginBottom: '8px' }}>
              {filtersActive ? '🔍' : '✓'}
            </div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-main)' }}>
              {filtersActive ? 'No matching error events found' : 'No error events recorded'}
            </div>
            <div style={{ fontSize: '12px', marginTop: '6px', maxWidth: '460px', marginInline: 'auto' }}>
              {filtersActive
                ? 'No recorded server-side errors match your current search, status code, category, feature area, or date range filters.'
                : 'No server-side operational exceptions or HTTP failures are recorded in the current retention window.'}
            </div>
            {filtersActive && (
              <button
                type="button"
                onClick={handleClearFilters}
                className="admin-errors-clear-btn"
                style={{ marginTop: '16px' }}
              >
                Clear All Filters
              </button>
            )}
          </div>
        ) : (
          <>
            {/* Status bar above table/cards */}
            <div className="admin-errors-results-header">
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Showing <strong style={{ color: 'var(--text-main)' }}>{showingFrom}–{showingTo}</strong> of{' '}
                <strong style={{ color: 'var(--text-main)' }}>{errorsData.total.toLocaleString()}</strong>{' '}
                {filtersActive ? 'matching error events' : 'recorded error events'}
                {filters.sortOrder === 'desc' ? ' · Latest first' : ' · Oldest first'}
              </div>
              {loading && (
                <span style={{ fontSize: '11px', color: 'var(--color-action)', fontWeight: 600 }}>
                  Updating results...
                </span>
              )}
            </div>

            {/* Desktop Table Layout */}
            <div className="admin-errors-desktop-table">
              <div className="table-scroll-wrapper" style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                      <th style={{ padding: '10px 8px' }}>Time</th>
                      <th style={{ padding: '10px 8px' }}>Status</th>
                      <th style={{ padding: '10px 8px' }}>Category</th>
                      <th style={{ padding: '10px 8px' }}>Feature &amp; Endpoint</th>
                      <th style={{ padding: '10px 8px' }}>Correlation ID</th>
                      <th style={{ padding: '10px 8px' }}>Safe Error Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {errorsData.errors.map((item: AdminErrorItem) => {
                      const is5xx = item.status_code >= 500;
                      return (
                        <tr key={item.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                          <td
                            style={{ padding: '10px 8px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}
                            title={item.created_at || undefined}
                          >
                            {formatErrorTimestamp(item.created_at)}
                          </td>
                          <td style={{ padding: '10px 8px' }}>
                            <span className={is5xx ? 'admin-errors-status-5xx' : 'admin-errors-status-4xx'}>
                              {item.status_code}
                            </span>
                          </td>
                          <td style={{ padding: '10px 8px' }}>
                            <span className="admin-errors-category-badge">{item.category}</span>
                          </td>
                          <td style={{ padding: '10px 8px' }}>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                              <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>{item.feature_area}</span>
                              <span
                                style={{
                                  fontSize: '11px',
                                  color: 'var(--text-muted)',
                                  fontFamily: 'var(--font-mono)',
                                  wordBreak: 'break-word',
                                }}
                              >
                                {item.method} {item.endpoint}
                              </span>
                            </div>
                          </td>
                          <td style={{ padding: '10px 8px', fontFamily: 'var(--font-mono)' }}>
                            {item.correlation_id ? (
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <span style={{ fontSize: '11px', color: 'var(--text-main)' }} title={item.correlation_id}>
                                  {item.correlation_id.slice(0, 8)}…
                                </span>
                                <button
                                  type="button"
                                  onClick={() => handleCopyCorrelationId(item.correlation_id!)}
                                  title={`Copy correlation ID: ${item.correlation_id}`}
                                  className={`admin-errors-copy-btn ${
                                    copiedId === item.correlation_id ? 'is-copied' : ''
                                  }`}
                                >
                                  {copiedId === item.correlation_id ? 'Copied' : 'Copy'}
                                </button>
                              </div>
                            ) : (
                              <span style={{ color: 'var(--text-muted)' }}>—</span>
                            )}
                          </td>
                          <td style={{ padding: '10px 8px', maxWidth: '380px' }}>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                              <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)' }}>
                                {item.error_type}
                              </span>
                              <span
                                style={{
                                  fontSize: '12px',
                                  color: 'var(--text-main)',
                                  wordBreak: 'break-word',
                                  fontFamily: 'var(--font-mono)',
                                  lineHeight: 1.4,
                                }}
                              >
                                {item.sanitized_message}
                              </span>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Mobile Stacked Card Layout */}
            <div className="admin-errors-mobile-list">
              {errorsData.errors.map((item: AdminErrorItem) => {
                const is5xx = item.status_code >= 500;
                return (
                  <article key={item.id} className="admin-error-card">
                    <div className="admin-error-card-top">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                        <span className={is5xx ? 'admin-errors-status-5xx' : 'admin-errors-status-4xx'}>
                          {item.status_code}
                        </span>
                        <span className="admin-errors-category-badge">{item.category}</span>
                        <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-main)' }}>
                          {item.feature_area}
                        </span>
                      </div>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        {formatErrorTimestamp(item.created_at)}
                      </span>
                    </div>

                    <div
                      style={{
                        fontSize: '12px',
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--text-main)',
                        wordBreak: 'break-word',
                      }}
                    >
                      {item.method} {item.endpoint}
                    </div>

                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', wordBreak: 'break-word' }}>
                      <strong style={{ color: 'var(--text-main)' }}>{item.error_type}:</strong>{' '}
                      <span style={{ fontFamily: 'var(--font-mono)' }}>{item.sanitized_message}</span>
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
                      }}
                    >
                      <span style={{ color: 'var(--text-muted)' }}>Correlation ID</span>
                      {item.correlation_id ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: 0 }}>
                          <span
                            style={{
                              fontFamily: 'var(--font-mono)',
                              color: 'var(--text-main)',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                            }}
                            title={item.correlation_id}
                          >
                            {item.correlation_id.slice(0, 12)}…
                          </span>
                          <button
                            type="button"
                            onClick={() => handleCopyCorrelationId(item.correlation_id!)}
                            className={`admin-errors-copy-btn ${
                              copiedId === item.correlation_id ? 'is-copied' : ''
                            }`}
                          >
                            {copiedId === item.correlation_id ? 'Copied' : 'Copy'}
                          </button>
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>—</span>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>

            {/* Bounded Pagination Footer */}
            <div className="admin-errors-pagination">
              <div style={{ color: 'var(--text-muted)' }}>
                Page <strong style={{ color: 'var(--text-main)' }}>{errorsData.page}</strong> of{' '}
                <strong style={{ color: 'var(--text-main)' }}>{errorsData.total_pages}</strong> · Total{' '}
                {errorsData.total.toLocaleString()}
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={loading || errorsData.page <= 1}
                  className="admin-errors-page-btn"
                >
                  ← Previous
                </button>
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.min(errorsData.total_pages, p + 1))}
                  disabled={loading || errorsData.page >= errorsData.total_pages}
                  className="admin-errors-page-btn"
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
