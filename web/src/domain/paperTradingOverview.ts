/**
 * Pure domain constants, query builders, validation helpers, and status formatters
 * for Admin Paper Trading Overview & Orders monitoring.
 */

import type { AdminOrderItem } from '../api/client.ts';
import {
  formatAdminDateTimeShort,
  toLocalDateBoundaryIso,
  validateChronologicalDateRange,
} from './dateRange.ts';

export { toLocalDateBoundaryIso };

/**
 * Actual persisted paper_orders status values from DDL constraint & domain execution.
 * Pre-persistence client/network/validation failures do not create order rows.
 */
export const ORDER_STATUS_OPTIONS = ['FILLED', 'REJECTED', 'PENDING', 'CANCELLED'] as const;
export const ORDER_SIDE_OPTIONS = ['BUY', 'SELL'] as const;
export const ORDER_PAGE_SIZE_OPTIONS = [10, 20, 50] as const;

export type OrderSortOrder = 'desc' | 'asc';
export type OrderStatusFilter = '' | (typeof ORDER_STATUS_OPTIONS)[number];
export type OrderSideFilter = '' | (typeof ORDER_SIDE_OPTIONS)[number];

export const ORDER_SORT_OPTIONS: ReadonlyArray<{ value: OrderSortOrder; label: string }> = [
  { value: 'desc', label: 'Newest first' },
  { value: 'asc', label: 'Oldest first' },
];

export interface OrderFilterState {
  search: string;
  status: string;
  side: string;
  dateFrom: string;
  dateTo: string;
  sortOrder: OrderSortOrder;
  limit: number;
}

export const DEFAULT_ORDER_FILTERS: OrderFilterState = {
  search: '',
  status: '',
  side: '',
  dateFrom: '',
  dateTo: '',
  sortOrder: 'desc',
  limit: 20,
};

export interface OrderQueryParams {
  page: number;
  limit: number;
  search?: string;
  status?: string;
  side?: string;
  date_from?: string;
  date_to?: string;
  sort_order: OrderSortOrder;
}

/**
 * Checks whether any search, filter, or non-default sort order is applied.
 */
export function hasActiveOrderFilters(filters: OrderFilterState): boolean {
  return Boolean(
    filters.search.trim() ||
      filters.status ||
      filters.side ||
      filters.dateFrom ||
      filters.dateTo ||
      filters.sortOrder !== 'desc'
  );
}

/**
 * Validates that optional YYYY-MM-DD order date boundaries form a coherent range.
 */
export function validateOrderDateRange(dateFrom: string, dateTo: string): string | null {
  return validateChronologicalDateRange(dateFrom, dateTo);
}

/**
 * Converts UI order filter state into bounded, typed API query parameters.
 */
export function buildOrderQueryParams(
  filters: OrderFilterState,
  page: number,
  useLocalDayBounds: boolean = true
): OrderQueryParams {
  const safePage = Number.isFinite(page) && page >= 1 ? Math.floor(page) : 1;
  const safeLimit =
    Number.isFinite(filters.limit) && filters.limit >= 1 && filters.limit <= 100
      ? Math.floor(filters.limit)
      : 20;

  const dateFrom = filters.dateFrom
    ? useLocalDayBounds
      ? toLocalDateBoundaryIso(filters.dateFrom, 'start')
      : filters.dateFrom
    : undefined;
  const dateTo = filters.dateTo
    ? useLocalDayBounds
      ? toLocalDateBoundaryIso(filters.dateTo, 'end')
      : filters.dateTo
    : undefined;

  return {
    page: safePage,
    limit: safeLimit,
    search: filters.search.trim() || undefined,
    status: filters.status ? filters.status.trim().toUpperCase() : undefined,
    side: filters.side ? filters.side.trim().toUpperCase() : undefined,
    date_from: dateFrom,
    date_to: dateTo,
    sort_order: filters.sortOrder === 'asc' ? 'asc' : 'desc',
  };
}

/**
 * Computes normalized recorded status counts without inventing metrics or mislabeling missing rows.
 */
export function normalizeOrderStatusCounts(
  rawCounts?: Record<string, number> | null
): Record<(typeof ORDER_STATUS_OPTIONS)[number] | string, number> {
  const normalized: Record<string, number> = {
    FILLED: 0,
    REJECTED: 0,
    PENDING: 0,
    CANCELLED: 0,
  };
  if (rawCounts) {
    for (const [k, v] of Object.entries(rawCounts)) {
      if (k && typeof v === 'number' && Number.isFinite(v)) {
        normalized[k.toUpperCase()] = Math.max(0, Math.floor(v));
      }
    }
  }
  return normalized;
}

/**
 * Formats execution/limit price for administrative display without implying unavailable fills.
 */
export function formatOrderPrice(order: Pick<AdminOrderItem, 'fill_price' | 'limit_price'>): string {
  const raw = order.fill_price ?? order.limit_price;
  if (raw === null || raw === undefined || !Number.isFinite(raw) || raw <= 0) {
    return '—';
  }
  return `₹${raw.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/**
 * Resolves safe administrative failure/safeguard text without inventing missing reasons.
 */
export function resolveOrderFailureDetails(
  order: Pick<AdminOrderItem, 'status' | 'rejection_reason'>
): string {
  const clean = order.rejection_reason?.trim();
  if (clean) return clean;
  if (order.status === 'REJECTED') {
    return 'Failure reason unavailable';
  }
  return '—';
}

/**
 * Formats an ISO order timestamp into a readable administrative timestamp.
 */
export function formatOrderTimestamp(iso?: string | null): string {
  return formatAdminDateTimeShort(iso);
}
