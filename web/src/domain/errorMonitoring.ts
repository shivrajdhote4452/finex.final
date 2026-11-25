/**
 * Pure domain constants, query builders, and validation helpers for Admin Error Monitoring.
 */

export const ERROR_CATEGORIES = [
  'SERVER_ERROR',
  'DATABASE',
  'UPSTREAM_API',
  'RATE_LIMIT',
  'VALIDATION',
  'AUTHENTICATION',
  'CONFLICT',
  'NOT_FOUND',
  'CLIENT_ERROR',
] as const;

export const ERROR_FEATURE_AREAS = [
  'Auth',
  'Market Data',
  'Charts',
  'Paper Trading',
  'Portfolio',
  'AI Assistant',
  'Risk Assessment',
  'Spending',
  'Goals',
  'Admin',
  'Health',
  'System',
] as const;

export const ERROR_STATUS_OPTIONS: ReadonlyArray<{ value: number; label: string }> = [
  { value: 500, label: '500 Internal Error' },
  { value: 502, label: '502 Bad Gateway' },
  { value: 503, label: '503 Service Unavailable' },
  { value: 504, label: '504 Gateway Timeout' },
  { value: 429, label: '429 Rate Limited' },
  { value: 422, label: '422 Unprocessable Content' },
  { value: 409, label: '409 Conflict' },
  { value: 404, label: '404 Not Found' },
  { value: 403, label: '403 Forbidden' },
  { value: 401, label: '401 Unauthorized' },
  { value: 400, label: '400 Bad Request' },
];

export const ERROR_PAGE_SIZE_OPTIONS = [10, 20, 50] as const;

export type ErrorSortOrder = 'desc' | 'asc';

export interface ErrorFilterState {
  search: string;
  category: string;
  featureArea: string;
  statusCode: string;
  dateFrom: string;
  dateTo: string;
  sortOrder: ErrorSortOrder;
  limit: number;
}

export const DEFAULT_ERROR_FILTERS: ErrorFilterState = {
  search: '',
  category: '',
  featureArea: '',
  statusCode: '',
  dateFrom: '',
  dateTo: '',
  sortOrder: 'desc',
  limit: 20,
};

export interface ErrorQueryParams {
  page: number;
  limit: number;
  status_code?: number;
  category?: string;
  feature_area?: string;
  date_from?: string;
  date_to?: string;
  sort_order: ErrorSortOrder;
  search?: string;
}

const DATE_ONLY_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

/**
 * Checks whether any search, filter, or non-default sort is currently applied.
 */
export function hasActiveErrorFilters(filters: ErrorFilterState): boolean {
  return Boolean(
    filters.search.trim() ||
      filters.category ||
      filters.featureArea ||
      filters.statusCode ||
      filters.dateFrom ||
      filters.dateTo ||
      filters.sortOrder !== 'desc'
  );
}

/**
 * Validates that selected YYYY-MM-DD date boundaries form a coherent chronological range.
 */
export function validateErrorDateRange(dateFrom: string, dateTo: string): string | null {
  if (dateFrom && !DATE_ONLY_PATTERN.test(dateFrom)) {
    return 'Start date must use YYYY-MM-DD format.';
  }
  if (dateTo && !DATE_ONLY_PATTERN.test(dateTo)) {
    return 'End date must use YYYY-MM-DD format.';
  }
  if (dateFrom && dateTo && dateFrom > dateTo) {
    return 'Start date must be on or before end date.';
  }
  return null;
}

/**
 * Converts a local YYYY-MM-DD input value into an ISO-8601 UTC start or end-of-day boundary.
 */
export function toLocalDateBoundaryIso(dateStr: string, boundary: 'start' | 'end'): string | undefined {
  if (!dateStr || !DATE_ONLY_PATTERN.test(dateStr)) {
    return undefined;
  }
  const [y, m, d] = dateStr.split('-').map((n) => parseInt(n, 10));
  const dt =
    boundary === 'start'
      ? new Date(y, m - 1, d, 0, 0, 0, 0)
      : new Date(y, m - 1, d, 23, 59, 59, 999);
  if (Number.isNaN(dt.getTime())) {
    return undefined;
  }
  return dt.toISOString();
}

/**
 * Builds typed, bounded API query parameters from UI filter state.
 */
export function buildErrorQueryParams(
  filters: ErrorFilterState,
  page: number,
  useLocalDayBounds: boolean = true
): ErrorQueryParams {
  const safePage = Number.isFinite(page) && page >= 1 ? Math.floor(page) : 1;
  const safeLimit =
    Number.isFinite(filters.limit) && filters.limit >= 1 && filters.limit <= 100
      ? Math.floor(filters.limit)
      : 20;

  const parsedStatus = filters.statusCode ? parseInt(filters.statusCode, 10) : undefined;
  const validStatus =
    parsedStatus !== undefined && Number.isFinite(parsedStatus) && parsedStatus >= 100 && parsedStatus <= 599
      ? parsedStatus
      : undefined;

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
    status_code: validStatus,
    category: filters.category || undefined,
    feature_area: filters.featureArea || undefined,
    date_from: dateFrom,
    date_to: dateTo,
    sort_order: filters.sortOrder === 'asc' ? 'asc' : 'desc',
    search: filters.search.trim() || undefined,
  };
}

/**
 * Merges static catalog options with any live categories or feature areas observed in summary data.
 */
export function mergeErrorFilterOptions(
  defaults: readonly string[],
  summaryMap?: Record<string, number> | null
): string[] {
  const seen = new Set<string>(defaults);
  if (summaryMap) {
    for (const key of Object.keys(summaryMap)) {
      if (key && key.trim()) {
        seen.add(key.trim());
      }
    }
  }
  return Array.from(seen);
}

/**
 * Formats an ISO timestamp for readable admin inspection, preserving safe fallback.
 */
export function formatErrorTimestamp(iso?: string | null): string {
  if (!iso) return '—';
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return '—';
  return dt.toLocaleString('en-IN', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}
