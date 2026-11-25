import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  apiClient,
  AdminOrderItem,
  AdminOrdersResponse,
} from '../../api/client';
import {
  DEFAULT_ORDER_FILTERS,
  ORDER_PAGE_SIZE_OPTIONS,
  ORDER_SIDE_OPTIONS,
  ORDER_SORT_OPTIONS,
  ORDER_STATUS_OPTIONS,
  OrderFilterState,
  OrderSortOrder,
  buildOrderQueryParams,
  formatOrderPrice,
  formatOrderTimestamp,
  hasActiveOrderFilters,
  normalizeOrderStatusCounts,
  resolveOrderFailureDetails,
  validateOrderDateRange,
} from '../../domain/paperTradingOverview';

interface AdminOrdersPanelProps {
  /** Incremented by parent Refresh button to trigger re-fetch. */
  refreshTrigger?: number;
  /** Optional initial status preset (e.g. from Overview quick link). */
  initialStatusFilter?: string;
  /** Called when an admin API call receives HTTP 401 Unauthorized. */
  onUnauthorized?: () => void;
  /** Reports loading status to parent shell (e.g. header Refresh button). */
  onLoadingChange?: (loading: boolean) => void;
}

const getOrderStatusPillClass = (status: string): string => {
  switch (status) {
    case 'FILLED':
      return 'admin-pill admin-pill-positive';
    case 'REJECTED':
      return 'admin-pill admin-pill-negative';
    case 'PENDING':
      return 'admin-pill admin-pill-warning';
    default:
      return 'admin-pill admin-pill-neutral';
  }
};

export const AdminOrdersPanel: React.FC<AdminOrdersPanelProps> = ({
  refreshTrigger = 0,
  initialStatusFilter = '',
  onUnauthorized,
  onLoadingChange,
}) => {
  const [ordersData, setOrdersData] = useState<AdminOrdersResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [filters, setFilters] = useState<OrderFilterState>(() => ({
    ...DEFAULT_ORDER_FILTERS,
    status: initialStatusFilter || '',
  }));
  const [searchInput, setSearchInput] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const [copiedOrderId, setCopiedOrderId] = useState<string | null>(null);

  // Sync optional preset status change from parent Overview link
  useEffect(() => {
    if (!initialStatusFilter) return;
    setFilters((prev) => ({ ...prev, status: initialStatusFilter }));
    setPage(1);
  }, [initialStatusFilter]);

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
    () => validateOrderDateRange(filters.dateFrom, filters.dateTo),
    [filters.dateFrom, filters.dateTo]
  );

  const fetchOrders = useCallback(async () => {
    if (dateRangeError) {
      return;
    }
    setLoading(true);
    onLoadingChange?.(true);
    setErrorMsg(null);
    try {
      const queryParams = buildOrderQueryParams(filters, page, true);
      const data = await apiClient.admin.getOrders(queryParams);
      setOrdersData(data);
      if (data.total_pages > 0 && page > data.total_pages) {
        setPage(data.total_pages);
      }
    } catch (err: any) {
      if (err?.status === 401) {
        onUnauthorized?.();
        return;
      }
      setErrorMsg(err?.message || 'Failed to load paper trading order records.');
    } finally {
      setLoading(false);
      onLoadingChange?.(false);
    }
  }, [filters, page, dateRangeError, onUnauthorized, onLoadingChange]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders, refreshTrigger]);

  const handleClearFilters = () => {
    setSearchInput('');
    setFilters(DEFAULT_ORDER_FILTERS);
    setPage(1);
  };

  const handleCopyOrderId = (orderId: string) => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard
        .writeText(orderId)
        .then(() => {
          setCopiedOrderId(orderId);
          setTimeout(() => setCopiedOrderId(null), 2000);
        })
        .catch(() => {});
    }
  };

  const filtersActive = hasActiveOrderFilters({ ...filters, search: searchInput });

  const statusCounts = useMemo(
    () => normalizeOrderStatusCounts(ordersData?.status_counts),
    [ordersData?.status_counts]
  );

  const overallTotalOrders = useMemo(() => {
    if (typeof ordersData?.overall_total === 'number') {
      return ordersData.overall_total;
    }
    return Object.values(statusCounts).reduce((acc, n) => acc + n, 0);
  }, [ordersData?.overall_total, statusCounts]);

  const showingFrom =
    ordersData && ordersData.total > 0 ? (ordersData.page - 1) * ordersData.limit + 1 : 0;
  const showingTo =
    ordersData && ordersData.total > 0
      ? Math.min(ordersData.total, (ordersData.page - 1) * ordersData.limit + ordersData.orders.length)
      : 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Read-Only & Capture Scope Notice */}
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
          <span>📊</span>
          <span>Paper Trading Audit Scope (Read-Only)</span>
        </div>
        <div>
          Displays persisted simulated <code style={{ fontFamily: 'var(--font-mono)' }}>paper_orders</code> records
          across recorded statuses (<strong>FILLED</strong>, <strong>REJECTED</strong>, <strong>PENDING</strong>, and{' '}
          <strong>CANCELLED</strong>). Network timeouts, client-side disconnects, and pre-execution request failures do
          not always produce order rows. Private cash balances and execution receipts are excluded.
        </div>
      </div>

      {/* Overview KPI & Status Breakdown Grid */}
      <div className="admin-errors-kpi-grid">
        <div className="admin-errors-kpi-card">
          <div className="admin-errors-kpi-label">Recorded Paper Orders</div>
          <div className="admin-errors-kpi-value" style={{ color: 'var(--text-main)' }}>
            {ordersData ? overallTotalOrders.toLocaleString() : '—'}
          </div>
          <div className="admin-errors-kpi-sub">
            {ordersData && overallTotalOrders === 0
              ? 'No paper orders recorded yet'
              : 'Total persisted order attempts'}
          </div>
        </div>

        <div className="admin-errors-kpi-card">
          <div className="admin-errors-kpi-label">Filled Orders</div>
          <div className="admin-errors-kpi-value" style={{ color: 'var(--color-profit)' }}>
            {ordersData ? (statusCounts.FILLED ?? 0).toLocaleString() : '—'}
          </div>
          <div className="admin-errors-kpi-sub">Simulated fills completed</div>
        </div>

        <div className="admin-errors-kpi-card">
          <div className="admin-errors-kpi-label">Rejected Orders</div>
          <div className="admin-errors-kpi-value" style={{ color: 'var(--color-loss)' }}>
            {ordersData ? (statusCounts.REJECTED ?? 0).toLocaleString() : '—'}
          </div>
          <div className="admin-errors-kpi-sub">Safeguard or quote rejections</div>
        </div>

        <div className="admin-errors-kpi-card">
          <div className="admin-errors-kpi-label">Pending / Cancelled</div>
          <div className="admin-errors-kpi-value" style={{ color: 'var(--color-warning)' }}>
            {ordersData ? ((statusCounts.PENDING ?? 0) + (statusCounts.CANCELLED ?? 0)).toLocaleString() : '—'}
          </div>
          <div className="admin-errors-kpi-sub">
            {ordersData
              ? `${statusCounts.PENDING ?? 0} pending · ${statusCounts.CANCELLED ?? 0} cancelled`
              : 'Schema status breakdown'}
          </div>
        </div>
      </div>

      {/* Search & Multi-Facet Filter Toolbar */}
      <div className="admin-panel-toolbar" role="search" aria-label="Filter paper trading orders">
        <div className="admin-panel-search-row">
          <div style={{ position: 'relative', flex: 1, minWidth: 0 }}>
            <input
              type="text"
              aria-label="Search paper orders"
              maxLength={80}
              placeholder="Search by symbol (e.g. RELIANCE) or order ID..."
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
            <span className="admin-panel-filter-label">Recorded Status</span>
            <select
              aria-label="Filter by order status"
              value={filters.status}
              onChange={(e) => {
                setFilters((prev) => ({ ...prev, status: e.target.value }));
                setPage(1);
              }}
              className="admin-panel-select"
            >
              <option value="">All Statuses</option>
              {ORDER_STATUS_OPTIONS.map((st) => (
                <option key={st} value={st}>
                  {st}
                </option>
              ))}
            </select>
          </label>

          <label className="admin-panel-filter-field">
            <span className="admin-panel-filter-label">Order Side</span>
            <select
              aria-label="Filter by order side"
              value={filters.side}
              onChange={(e) => {
                setFilters((prev) => ({ ...prev, side: e.target.value }));
                setPage(1);
              }}
              className="admin-panel-select"
            >
              <option value="">All Sides</option>
              {ORDER_SIDE_OPTIONS.map((side) => (
                <option key={side} value={side}>
                  {side}
                </option>
              ))}
            </select>
          </label>

          <label className="admin-panel-filter-field">
            <span className="admin-panel-filter-label">From Date</span>
            <input
              type="date"
              aria-label="Order from date"
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
            <span className="admin-panel-filter-label">To Date</span>
            <input
              type="date"
              aria-label="Order to date"
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
                aria-label="Sort paper orders"
                value={filters.sortOrder}
                onChange={(e) => {
                  setFilters((prev) => ({
                    ...prev,
                    sortOrder: e.target.value as OrderSortOrder,
                  }));
                  setPage(1);
                }}
                className="admin-panel-select"
                style={{ flex: 1 }}
              >
                {ORDER_SORT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <select
                aria-label="Orders per page"
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
                {ORDER_PAGE_SIZE_OPTIONS.map((sz) => (
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
        {loading && !ordersData ? (
          <div style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: '13px', fontWeight: 600 }}>Loading paper trading orders...</div>
            <div style={{ fontSize: '12px', marginTop: '6px' }}>Applying active search and filter parameters</div>
          </div>
        ) : errorMsg ? (
          <div className="admin-panel-error-banner" role="alert">
            <div>
              <div style={{ fontWeight: 700, marginBottom: '4px' }}>Unable to load paper trading orders</div>
              <div style={{ fontSize: '12px' }}>{errorMsg}</div>
            </div>
            <button
              type="button"
              onClick={fetchOrders}
              className="admin-panel-retry-btn"
            >
              Retry
            </button>
          </div>
        ) : !ordersData || ordersData.orders.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '56px 16px', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: '28px', marginBottom: '8px' }}>
              {filtersActive ? '🔍' : '📋'}
            </div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-main)' }}>
              {filtersActive ? 'No matching orders found' : 'No paper orders recorded'}
            </div>
            <div style={{ fontSize: '12px', marginTop: '6px', maxWidth: '460px', marginInline: 'auto' }}>
              {filtersActive
                ? 'No persisted simulated orders match your current symbol, order ID, status, side, or date range filters.'
                : 'No persisted simulated order attempts have been recorded yet. Unpersisted request failures are not recorded here.'}
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
                <strong style={{ color: 'var(--text-main)' }}>{ordersData.total.toLocaleString()}</strong>{' '}
                {filtersActive ? 'matching orders' : 'recorded orders'}
                {filters.sortOrder === 'desc' ? ' · Latest first' : ' · Oldest first'}
              </div>
              {loading && (
                <span style={{ fontSize: '11px', color: 'var(--color-action)', fontWeight: 600 }}>
                  Updating orders...
                </span>
              )}
            </div>

            {/* Desktop Table Layout */}
            <div className="admin-panel-desktop-table">
              <div className="table-scroll-wrapper" style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                      <th style={{ padding: '10px 8px' }}>Time</th>
                      <th style={{ padding: '10px 8px' }}>Order ID</th>
                      <th style={{ padding: '10px 8px' }}>Symbol</th>
                      <th style={{ padding: '10px 8px' }}>Side</th>
                      <th style={{ padding: '10px 8px' }}>Type</th>
                      <th style={{ padding: '10px 8px' }}>Qty</th>
                      <th style={{ padding: '10px 8px' }}>Exec / Limit</th>
                      <th style={{ padding: '10px 8px' }}>Status</th>
                      <th style={{ padding: '10px 8px' }}>Safeguard / Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ordersData.orders.map((o: AdminOrderItem) => {
                      const failureText = resolveOrderFailureDetails(o);
                      const isBuy = o.side === 'BUY';
                      return (
                        <tr key={o.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                          <td
                            style={{ padding: '10px 8px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}
                            title={o.created_at || undefined}
                          >
                            {formatOrderTimestamp(o.created_at)}
                          </td>
                          <td style={{ padding: '10px 8px', fontFamily: 'var(--font-mono)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <span style={{ fontSize: '11px', color: 'var(--text-main)' }} title={o.id}>
                                {o.id.length > 12 ? `${o.id.slice(0, 12)}…` : o.id}
                              </span>
                              <button
                                type="button"
                                onClick={() => handleCopyOrderId(o.id)}
                                title={`Copy Order ID: ${o.id}`}
                                className={`admin-errors-copy-btn ${
                                  copiedOrderId === o.id ? 'is-copied' : ''
                                }`}
                              >
                                {copiedOrderId === o.id ? 'Copied' : 'Copy'}
                              </button>
                            </div>
                          </td>
                          <td style={{ padding: '10px 8px', fontWeight: 700, color: 'var(--text-main)' }}>
                            {o.symbol}
                          </td>
                          <td style={{ padding: '10px 8px' }}>
                            <span
                              className={`admin-pill ${
                                isBuy ? 'admin-pill-positive' : 'admin-pill-negative'
                              }`}
                            >
                              {o.side}
                            </span>
                          </td>
                          <td style={{ padding: '10px 8px', color: 'var(--text-muted)' }}>
                            {o.order_type}
                          </td>
                          <td style={{ padding: '10px 8px', fontFamily: 'var(--font-mono)', color: 'var(--text-main)' }}>
                            {o.quantity}
                          </td>
                          <td style={{ padding: '10px 8px', fontFamily: 'var(--font-mono)', color: 'var(--text-main)' }}>
                            {formatOrderPrice(o)}
                          </td>
                          <td style={{ padding: '10px 8px' }}>
                            <span className={getOrderStatusPillClass(o.status)}>
                              {o.status}
                            </span>
                          </td>
                          <td
                            style={{
                              padding: '10px 8px',
                              maxWidth: '320px',
                              color: o.status === 'REJECTED' ? 'var(--color-loss)' : 'var(--text-muted)',
                              wordBreak: 'break-word',
                            }}
                          >
                            {failureText}
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
              {ordersData.orders.map((o: AdminOrderItem) => {
                const failureText = resolveOrderFailureDetails(o);
                const isBuy = o.side === 'BUY';
                return (
                  <article key={o.id} className="admin-panel-card">
                    <div className="admin-panel-card-top">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                        <span style={{ fontSize: '14px', fontWeight: 800, color: 'var(--text-main)' }}>
                          {o.symbol}
                        </span>
                        <span
                          className={`admin-pill ${
                            isBuy ? 'admin-pill-positive' : 'admin-pill-negative'
                          }`}
                        >
                          {o.side}
                        </span>
                        <span className={getOrderStatusPillClass(o.status)}>
                          {o.status}
                        </span>
                      </div>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        {formatOrderTimestamp(o.created_at)}
                      </span>
                    </div>

                    <div
                      style={{
                        display: 'flex',
                        flexWrap: 'wrap',
                        gap: '12px',
                        fontSize: '12px',
                        color: 'var(--text-muted)',
                      }}
                    >
                      <span>
                        Type: <strong style={{ color: 'var(--text-main)' }}>{o.order_type}</strong>
                      </span>
                      <span>
                        Qty:{' '}
                        <strong style={{ color: 'var(--text-main)', fontFamily: 'var(--font-mono)' }}>
                          {o.quantity}
                        </strong>
                      </span>
                      <span>
                        Price:{' '}
                        <strong style={{ color: 'var(--text-main)', fontFamily: 'var(--font-mono)' }}>
                          {formatOrderPrice(o)}
                        </strong>
                      </span>
                    </div>

                    {failureText !== '—' && (
                      <div
                        style={{
                          fontSize: '12px',
                          color: o.status === 'REJECTED' ? 'var(--color-loss)' : 'var(--text-muted)',
                          wordBreak: 'break-word',
                        }}
                      >
                        {failureText}
                      </div>
                    )}

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
                      <span style={{ color: 'var(--text-muted)' }}>Order ID</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: 0 }}>
                        <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-main)' }} title={o.id}>
                          {o.id.length > 14 ? `${o.id.slice(0, 14)}…` : o.id}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleCopyOrderId(o.id)}
                          className={`admin-errors-copy-btn ${
                            copiedOrderId === o.id ? 'is-copied' : ''
                          }`}
                        >
                          {copiedOrderId === o.id ? 'Copied' : 'Copy'}
                        </button>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>

            {/* Bounded Pagination Footer */}
            <div className="admin-panel-pagination">
              <div style={{ color: 'var(--text-muted)' }}>
                Page <strong style={{ color: 'var(--text-main)' }}>{ordersData.page}</strong> of{' '}
                <strong style={{ color: 'var(--text-main)' }}>{ordersData.total_pages}</strong> · Total{' '}
                {ordersData.total.toLocaleString()}
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={loading || ordersData.page <= 1}
                  className="admin-panel-page-btn"
                >
                  ← Previous
                </button>
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.min(ordersData.total_pages, p + 1))}
                  disabled={loading || ordersData.page >= ordersData.total_pages}
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
