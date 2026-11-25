/**
 * Pure domain constants, query builders, and validation helpers for Admin User Directory.
 */

import type { AdminUserItem } from '../api/client.ts';
import {
  formatAdminDateTimeShort,
  toLocalDateBoundaryIso,
  validateChronologicalDateRange,
} from './dateRange.ts';

export { toLocalDateBoundaryIso };

export type UserSortOrder = 'desc' | 'asc';
export type UserAccountStatusFilter = '' | 'active' | 'inactive';
export type UserBooleanFilter = '' | 'true' | 'false';

export const USER_PAGE_SIZE_OPTIONS = [10, 20, 50] as const;

export const USER_ACCOUNT_STATUS_OPTIONS: ReadonlyArray<{ value: UserAccountStatusFilter; label: string }> = [
  { value: '', label: 'All Account Statuses' },
  { value: 'active', label: 'Active Only' },
  { value: 'inactive', label: 'Inactive Only' },
];

export const USER_VERIFICATION_OPTIONS: ReadonlyArray<{ value: UserBooleanFilter; label: string }> = [
  { value: '', label: 'All Email States' },
  { value: 'true', label: 'Verified Email' },
  { value: 'false', label: 'Unverified' },
];

export const USER_ONBOARDING_OPTIONS: ReadonlyArray<{ value: UserBooleanFilter; label: string }> = [
  { value: '', label: 'All Onboarding' },
  { value: 'true', label: 'Completed' },
  { value: 'false', label: 'Pending' },
];

export const USER_SORT_OPTIONS: ReadonlyArray<{ value: UserSortOrder; label: string }> = [
  { value: 'desc', label: 'Newest registered' },
  { value: 'asc', label: 'Oldest registered' },
];

export interface UserFilterState {
  search: string;
  accountStatus: UserAccountStatusFilter;
  emailVerified: UserBooleanFilter;
  onboardingCompleted: UserBooleanFilter;
  dateFrom: string;
  dateTo: string;
  sortOrder: UserSortOrder;
  limit: number;
}

export const DEFAULT_USER_FILTERS: UserFilterState = {
  search: '',
  accountStatus: '',
  emailVerified: '',
  onboardingCompleted: '',
  dateFrom: '',
  dateTo: '',
  sortOrder: 'desc',
  limit: 20,
};

export interface UserQueryParams {
  page: number;
  limit: number;
  search?: string;
  is_active?: boolean;
  email_verified?: boolean;
  onboarding_completed?: boolean;
  date_from?: string;
  date_to?: string;
  sort_order: UserSortOrder;
}

/**
 * Checks whether any search, filter, or non-default sort order is currently applied.
 */
export function hasActiveUserFilters(filters: UserFilterState): boolean {
  return Boolean(
    filters.search.trim() ||
      filters.accountStatus ||
      filters.emailVerified ||
      filters.onboardingCompleted ||
      filters.dateFrom ||
      filters.dateTo ||
      filters.sortOrder !== 'desc'
  );
}

/**
 * Validates that selected YYYY-MM-DD registration date bounds form a coherent range.
 */
export function validateUserDateRange(dateFrom: string, dateTo: string): string | null {
  return validateChronologicalDateRange(dateFrom, dateTo);
}

/**
 * Converts UI user directory filter state into bounded, strongly typed API query parameters.
 */
export function buildUserQueryParams(
  filters: UserFilterState,
  page: number,
  useLocalDayBounds: boolean = true
): UserQueryParams {
  const safePage = Number.isFinite(page) && page >= 1 ? Math.floor(page) : 1;
  const safeLimit =
    Number.isFinite(filters.limit) && filters.limit >= 1 && filters.limit <= 100
      ? Math.floor(filters.limit)
      : 20;

  const isActive =
    filters.accountStatus === 'active'
      ? true
      : filters.accountStatus === 'inactive'
        ? false
        : undefined;

  const emailVerified =
    filters.emailVerified === 'true'
      ? true
      : filters.emailVerified === 'false'
        ? false
        : undefined;

  const onboardingCompleted =
    filters.onboardingCompleted === 'true'
      ? true
      : filters.onboardingCompleted === 'false'
        ? false
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
    search: filters.search.trim() || undefined,
    is_active: isActive,
    email_verified: emailVerified,
    onboarding_completed: onboardingCompleted,
    date_from: dateFrom,
    date_to: dateTo,
    sort_order: filters.sortOrder === 'asc' ? 'asc' : 'desc',
  };
}

/**
 * Resolves the cleanest administrative display name from safe user profile attributes.
 */
export function resolveUserDisplayName(user: Pick<AdminUserItem, 'full_name' | 'display_name'>): string {
  const full = user.full_name?.trim();
  if (full) return full;
  const display = user.display_name?.trim();
  if (display) return display;
  return '—';
}

/**
 * Formats an ISO registration timestamp for readable administrative display.
 */
export function formatUserRegistrationDate(iso?: string | null): string {
  return formatAdminDateTimeShort(iso);
}
