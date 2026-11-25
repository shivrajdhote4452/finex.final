/**
 * Shared chronological date-range validation and UTC timestamp formatting helpers for Admin panels.
 */

export const DATE_ONLY_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

/**
 * Validates that optional YYYY-MM-DD boundaries form a valid chronological date window.
 */
export function validateChronologicalDateRange(dateFrom: string, dateTo: string): string | null {
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
 * Formats an ISO timestamp into a readable date/time string, with safe fallback for missing/invalid values.
 */
export function formatAdminTimestamp(iso?: string | null): string {
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

/**
 * Formats an ISO timestamp into a readable date + short time string suitable for directory registration dates.
 */
export function formatAdminDateTimeShort(iso?: string | null): string {
  if (!iso) return '—';
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return '—';
  return dt.toLocaleString('en-IN', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}
