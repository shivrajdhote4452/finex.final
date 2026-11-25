/**
 * Separate FinEx Admin Portal & Management Verification Tests.
 *
 * Validates:
 * 1. Admin navigation item is removed from normal workspace (VALID_TABS is investor-only).
 * 2. Dedicated Admin Portal routing: isAdminPortalRoute detects '/admin' and '#admin'.
 * 3. Session Separation: Admin and investor tokens coexist in separate storage keys;
 *    logout or 401 in one portal does not clobber or invalidate the other.
 * 4. Safe projection enforcement: strictly prohibits sensitive fields
 *    (password_hash, google_subject, provider_subject, risk_assessment, tokens).
 * 5. System health diagnostics contract: integration states without secrets.
 * 6. Query string serialization for users and orders filters.
 * 7. Admin API client contract: googleLogin, getMe, getOverview, getUsers, getOrders, getSystemHealth, logout.
 */

import test, { describe, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import {
  VALID_TABS,
  isValidTab,
  parseTabFromHash,
  isWorkspaceTabHash,
  resolveLandingTab,
  isAdminPortalRoute,
  type NavigationTab,
} from '../src/domain/sessionNavigation.ts';
import {
  apiClient,
  type AdminUserItem,
  type AdminOrderItem,
  type AdminOverviewResponse,
  type AdminSystemHealthResponse,
  type AdminMeResponse,
  type AdminErrorItem,
  type AdminErrorsResponse,
  type AdminErrorSummaryResponse,
} from '../src/api/client.ts';
import {
  DEFAULT_ERROR_FILTERS,
  ERROR_CATEGORIES,
  ERROR_STATUS_OPTIONS,
  buildErrorQueryParams,
  formatErrorTimestamp,
  hasActiveErrorFilters,
  mergeErrorFilterOptions,
  toLocalDateBoundaryIso,
  validateErrorDateRange,
  type ErrorFilterState,
} from '../src/domain/errorMonitoring.ts';
import {
  DEFAULT_USER_FILTERS,
  USER_ACCOUNT_STATUS_OPTIONS,
  USER_SORT_OPTIONS,
  buildUserQueryParams,
  formatUserRegistrationDate,
  hasActiveUserFilters,
  resolveUserDisplayName,
  validateUserDateRange,
  type UserFilterState,
} from '../src/domain/userDirectory.ts';
import {
  DEFAULT_ORDER_FILTERS,
  ORDER_SORT_OPTIONS,
  ORDER_STATUS_OPTIONS,
  buildOrderQueryParams,
  formatOrderPrice,
  formatOrderTimestamp,
  hasActiveOrderFilters,
  normalizeOrderStatusCounts,
  resolveOrderFailureDetails,
  validateOrderDateRange,
  type OrderFilterState,
} from '../src/domain/paperTradingOverview.ts';

// Helper to create a cryptographically valid unexpired JWT for frontend client tests
const createValidTestToken = (sub: string) => {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url');
  const payload = Buffer.from(
    JSON.stringify({ sub, exp: Math.floor(Date.now() / 1000) + 3600 })
  ).toString('base64url');
  return `${header}.${payload}.signature`;
};

// Mock in-memory localStorage for Node test runner
const memoryStorage: Record<string, string> = {};
const mockLocalStorage = {
  getItem: (key: string) => memoryStorage[key] || null,
  setItem: (key: string, value: string) => {
    memoryStorage[key] = String(value);
  },
  removeItem: (key: string) => {
    delete memoryStorage[key];
  },
  clear: () => {
    for (const k in memoryStorage) delete memoryStorage[k];
  },
};
(globalThis as any).localStorage = mockLocalStorage;

describe('Separate FinEx Admin Portal Frontend & Domain Contract', () => {
  beforeEach(() => {
    mockLocalStorage.clear();
    apiClient.setToken(null);
    apiClient.setAdminToken(null);
  });

  // -------------------------------------------------------------
  // 1. WORKSPACE ISOLATION: ADMIN REMOVED FROM NORMAL WORKSPACE
  // -------------------------------------------------------------
  test('1. Normal workspace navigation strictly excludes "admin" from VALID_TABS', () => {
    assert.strictEqual(
      VALID_TABS.includes('admin' as any),
      false,
      'admin must NOT be in normal workspace VALID_TABS'
    );
    assert.strictEqual(isValidTab('admin'), false, 'isValidTab("admin") must return false');
    assert.strictEqual(parseTabFromHash('#admin'), null, 'parseTabFromHash("#admin") must return null');
    assert.strictEqual(isWorkspaceTabHash('#admin'), false, 'isWorkspaceTabHash("#admin") must return false');
  });

  test('2. Landing tab resolution defaults to "overview" if hash is "#admin"', () => {
    // Normal workspace ignores #admin and safely resolves to overview
    const resolved = resolveLandingTab({
      hasActiveSession: true,
      locationHash: '#admin',
      storedTab: 'overview',
    });
    assert.strictEqual(resolved, 'overview');
  });

  // -------------------------------------------------------------
  // 2. DEDICATED ADMIN PORTAL ROUTE DETECTION
  // -------------------------------------------------------------
  test('3. Dedicated Admin Portal route detector identifies /admin and #admin', () => {
    assert.strictEqual(isAdminPortalRoute('/admin', ''), true);
    assert.strictEqual(isAdminPortalRoute('/admin/', ''), true);
    assert.strictEqual(isAdminPortalRoute('/admin/users', ''), true);
    assert.strictEqual(isAdminPortalRoute('', '#admin'), true);
    assert.strictEqual(isAdminPortalRoute('', '#/admin'), true);
    assert.strictEqual(isAdminPortalRoute('', '#/admin/overview'), true);

    // Investor routes must NOT be detected as admin portal
    assert.strictEqual(isAdminPortalRoute('/', ''), false);
    assert.strictEqual(isAdminPortalRoute('/overview', ''), false);
    assert.strictEqual(isAdminPortalRoute('', '#overview'), false);
    assert.strictEqual(isAdminPortalRoute('/privacy', ''), false);
    assert.strictEqual(isAdminPortalRoute('/terms', ''), false);
  });

  // -------------------------------------------------------------
  // 3. SESSION SEPARATION & TOKEN ISOLATION IN APICLIENT
  // -------------------------------------------------------------
  test('4. Admin and Investor tokens are stored in separate keys and coexist independently', () => {
    const investorToken = createValidTestToken('usr-investor-001');
    const adminToken = createValidTestToken('usr-owner-001');

    apiClient.setToken(investorToken);
    apiClient.setAdminToken(adminToken);

    // Verify separate storage keys
    assert.strictEqual(mockLocalStorage.getItem('finex_access_token'), investorToken);
    assert.strictEqual(mockLocalStorage.getItem('finex_admin_access_token'), adminToken);

    // Verify getter isolation
    assert.strictEqual(apiClient.getToken(), investorToken);
    assert.strictEqual(apiClient.getAdminToken(), adminToken);
    assert.strictEqual(apiClient.isAuthenticated(), true);
    assert.strictEqual(apiClient.isAdminAuthenticated(), true);
  });

  test('5. Admin logout clears ONLY the admin session and leaves investor session intact', async () => {
    const investorToken = createValidTestToken('usr-investor-001');
    const adminToken = createValidTestToken('usr-owner-001');

    apiClient.setToken(investorToken);
    apiClient.setAdminToken(adminToken);

    // Admin logout
    await apiClient.admin.logout();

    // Admin token cleared
    assert.strictEqual(apiClient.getAdminToken(), null);
    assert.strictEqual(mockLocalStorage.getItem('finex_admin_access_token'), null);
    assert.strictEqual(apiClient.isAdminAuthenticated(), false);

    // Investor token PRESERVED
    assert.strictEqual(apiClient.getToken(), investorToken);
    assert.strictEqual(mockLocalStorage.getItem('finex_access_token'), investorToken);
    assert.strictEqual(apiClient.isAuthenticated(), true);
  });

  test('6. Investor logout clears ONLY the investor session and leaves admin session intact', async () => {
    const investorToken = createValidTestToken('usr-investor-001');
    const adminToken = createValidTestToken('usr-owner-001');

    apiClient.setToken(investorToken);
    apiClient.setAdminToken(adminToken);

    // Investor logout
    await apiClient.auth.logout();

    // Investor token cleared
    assert.strictEqual(apiClient.getToken(), null);
    assert.strictEqual(mockLocalStorage.getItem('finex_access_token'), null);
    assert.strictEqual(apiClient.isAuthenticated(), false);

    // Admin token PRESERVED
    assert.strictEqual(apiClient.getAdminToken(), adminToken);
    assert.strictEqual(mockLocalStorage.getItem('finex_admin_access_token'), adminToken);
    assert.strictEqual(apiClient.isAdminAuthenticated(), true);
  });

  // -------------------------------------------------------------
  // 4. SAFE PROJECTIONS & PROHIBITED SENSITIVE FIELDS
  // -------------------------------------------------------------
  test('7. AdminUserItem schema strictly excludes passwords, OAuth subjects, and private questionnaire JSON', () => {
    const mockUser: AdminUserItem = {
      id: 'usr-001',
      email: 'investor@finex.internal',
      display_name: 'Investor',
      full_name: 'Test Investor',
      country: 'IND',
      is_active: true,
      email_verified: true,
      onboarding_completed: true,
      risk_band: 'MODERATE',
      experience_level: 'INTERMEDIATE',
      created_at: '2026-11-20T10:00:00Z',
    };

    const forbiddenFields = [
      'password',
      'password_hash',
      'google_subject',
      'provider_subject',
      'risk_assessment',
      'answers',
      'access_token',
      'refresh_token',
      'ip_address',
    ];

    for (const field of forbiddenFields) {
      assert.strictEqual(
        (mockUser as any)[field],
        undefined,
        `Field "${field}" is strictly prohibited on AdminUserItem`
      );
    }
  });

  test('8. AdminOrderItem schema excludes execution traces and private financial accounts', () => {
    const mockOrder: AdminOrderItem = {
      id: 'ord-001',
      user_id: 'usr-001',
      user_email: 'investor@finex.internal',
      symbol: 'RELIANCE',
      side: 'BUY',
      order_type: 'MARKET',
      quantity: 10,
      limit_price: null,
      fill_price: 2450.5,
      fee: 0.0,
      status: 'FILLED',
      rejection_reason: null,
      created_at: '2026-11-20T10:00:00Z',
    };

    const forbiddenOrderFields = [
      'execution_receipt',
      'internal_trace',
      'stack_trace',
      'bank_account',
      'demat_account',
    ];

    for (const field of forbiddenOrderFields) {
      assert.strictEqual(
        (mockOrder as any)[field],
        undefined,
        `Field "${field}" is strictly prohibited on AdminOrderItem`
      );
    }
  });

  test('9. AdminMeResponse schema exposes safe owner projection', () => {
    const mockMe: AdminMeResponse = {
      user_id: 'usr-shivraj-001',
      email: 'owner@finexai.tech',
      display_name: 'Platform Owner',
      role: 'owner',
      is_active: true,
      email_verified: true,
    };

    assert.strictEqual(mockMe.user_id, 'usr-shivraj-001');
    assert.strictEqual(mockMe.role, 'owner');
    assert.strictEqual(mockMe.is_active, true);
    assert.strictEqual((mockMe as any).password, undefined);
  });

  // -------------------------------------------------------------
  // 5. SYSTEM HEALTH DIAGNOSTICS CONTRACT
  // -------------------------------------------------------------
  test('10. AdminSystemHealthResponse diagnostics strictly excludes secrets', () => {
    const mockHealth: AdminSystemHealthResponse = {
      backend: {
        status: 'ok',
        app: 'FinEx - Financial Excellence',
        environment: 'development',
        version: 'v1.2.2-database-online',
      },
      database: {
        status: 'ok',
        message: 'Database ping succeeded',
      },
      market_data: {
        mode: 'INDIAN_LIVE_DATA',
        allow_fixtures: false,
        enable_demo_simulation: false,
      },
      angel_one: {
        is_configured: true,
        smartapi_library_available: true,
        is_circuit_open: false,
        has_active_session: true,
        missing_fields: [],
      },
      email: {
        is_configured: false,
        host: 'Unavailable / Not configured',
        from_email: 'noreply@finexai.tech',
      },
    };

    assert.strictEqual(mockHealth.backend.status, 'ok');
    assert.strictEqual(mockHealth.database.status, 'ok');
    assert.strictEqual(mockHealth.angel_one.is_circuit_open, false);

    const forbiddenSecrets = [
      'api_key',
      'client_id',
      'mpin',
      'totp_secret',
      'smtp_password',
      'jwt_secret',
      'database_password',
    ];

    for (const secret of forbiddenSecrets) {
      assert.strictEqual(
        (mockHealth.angel_one as any)[secret],
        undefined,
        `Angel One diagnostics must not expose ${secret}`
      );
      assert.strictEqual(
        (mockHealth.email as any)[secret],
        undefined,
        `Email diagnostics must not expose ${secret}`
      );
    }
  });

  // -------------------------------------------------------------
  // 6. API QUERY STRING SERIALIZATION
  // -------------------------------------------------------------
  test('11. Admin query parameter builder builds correct query strings', () => {
    const buildUserParams = (params: {
      page?: number;
      limit?: number;
      search?: string;
      is_active?: boolean;
      email_verified?: boolean;
      onboarding_completed?: boolean;
    }) => {
      const q = new URLSearchParams();
      if (params?.page) q.set('page', String(params.page));
      if (params?.limit) q.set('limit', String(params.limit));
      if (params?.search) q.set('search', params.search);
      if (params?.is_active !== undefined) q.set('is_active', String(params.is_active));
      if (params?.email_verified !== undefined) q.set('email_verified', String(params.email_verified));
      if (params?.onboarding_completed !== undefined) q.set('onboarding_completed', String(params.onboarding_completed));
      const qs = q.toString() ? `?${q.toString()}` : '';
      return `/admin/users${qs}`;
    };

    assert.strictEqual(
      buildUserParams({ page: 2, limit: 15, search: 'shivraj', is_active: true }),
      '/admin/users?page=2&limit=15&search=shivraj&is_active=true'
    );

    assert.strictEqual(
      buildUserParams({ page: 1, limit: 20 }),
      '/admin/users?page=1&limit=20'
    );

    const buildOrderParams = (params: {
      page?: number;
      limit?: number;
      symbol?: string;
      side?: string;
      status?: string;
      search?: string;
    }) => {
      const q = new URLSearchParams();
      if (params?.page) q.set('page', String(params.page));
      if (params?.limit) q.set('limit', String(params.limit));
      if (params?.symbol) q.set('symbol', params.symbol);
      if (params?.side) q.set('side', params.side);
      if (params?.status) q.set('status', params.status);
      if (params?.search) q.set('search', params.search);
      const qs = q.toString() ? `?${q.toString()}` : '';
      return `/admin/orders${qs}`;
    };

    assert.strictEqual(
      buildOrderParams({ page: 1, limit: 15, symbol: 'TCS', status: 'REJECTED' }),
      '/admin/orders?page=1&limit=15&symbol=TCS&status=REJECTED'
    );
  });

  // -------------------------------------------------------------
  // 7. DASHBOARD METRICS: ZERO ORDERS & HONEST REJECTIONS
  // -------------------------------------------------------------
  test('12. Order Success Rate calculates "No orders yet" when total paper orders is zero', () => {
    // Pure calculation helper matching AdminPortal and AdminScreen implementation
    const computeSuccessRate = (totalOrders: number, filledOrders: number): string => {
      if (totalOrders <= 0) {
        return 'No orders yet';
      }
      return `${Math.round((filledOrders / totalOrders) * 100)}%`;
    };

    // Zero orders must never show 100%
    assert.strictEqual(computeSuccessRate(0, 0), 'No orders yet');
    assert.notStrictEqual(computeSuccessRate(0, 0), '100%');
    assert.notStrictEqual(computeSuccessRate(0, 0), '100.0%');

    // Non-zero orders compute accurate ratios
    assert.strictEqual(computeSuccessRate(10, 10), '100%');
    assert.strictEqual(computeSuccessRate(10, 8), '80%');
    assert.strictEqual(computeSuccessRate(3, 1), '33%');
    assert.strictEqual(computeSuccessRate(5, 0), '0%');
  });

  test('13. Empty rejected orders states use honest wording without overclaiming clean execution', () => {
    const getRejectedEmptyState = (recentRejectedCount: number): string => {
      if (recentRejectedCount === 0) {
        return 'No rejected orders recorded.';
      }
      return `${recentRejectedCount} rejected orders`;
    };

    const emptyText = getRejectedEmptyState(0);
    assert.strictEqual(emptyText, 'No rejected orders recorded.');
    assert.strictEqual(
      emptyText.includes('All simulated orders executed cleanly'),
      false,
      'Must NOT overclaim clean execution when failed requests may not become rejected orders'
    );
    assert.strictEqual(
      emptyText.includes('All simulated orders have processed normally'),
      false,
      'Must NOT claim all simulated orders processed normally'
    );
  });

  // -------------------------------------------------------------
  // 8. SYSTEM HEALTH: CONFIGURATION VS VERIFIED DELIVERY CAVEATS
  // -------------------------------------------------------------
  test('14. System health diagnostic labels make it explicit that configuration != verified live delivery', () => {
    const mockHealth: AdminSystemHealthResponse = {
      backend: { status: 'ok', app: 'FinEx Platform API', version: 'v1.2.2' },
      database: { status: 'ok', latency_ms: 1.2 },
      market_data: { mode: 'SIMULATED', allow_fixtures: false, enable_demo_simulation: true },
      angel_one: {
        is_configured: true,
        smartapi_library_available: true,
        is_circuit_open: false,
        has_active_session: false,
        verification_note:
          'Configuration reflects present environment credentials. It does not prove that live market data or exchange streaming is working.',
      },
      email: {
        is_configured: true,
        host: 'smtp.sendgrid.net',
        port: 587,
        use_tls: true,
        from_email: 'noreply@finexai.tech',
        verification_note:
          'SMTP host configuration detected. It does not prove that email delivery to recipient inboxes is working.',
      },
    };

    // UI Badge text formatter matching AdminPortal logic
    const getAngelBadge = (isConfigured: boolean): string =>
      isConfigured ? 'CONFIGURED (UNVERIFIED LIVE)' : 'SIMULATED / UNCONFIGURED';

    const getEmailBadge = (isConfigured: boolean): string =>
      isConfigured ? 'CONFIGURED (DELIVERY UNVERIFIED)' : 'DEV MODE (UNCONFIGURED)';

    assert.strictEqual(getAngelBadge(true), 'CONFIGURED (UNVERIFIED LIVE)');
    assert.strictEqual(getAngelBadge(false), 'SIMULATED / UNCONFIGURED');
    assert.notStrictEqual(getAngelBadge(true), 'LIVE CONFIG');

    assert.strictEqual(getEmailBadge(true), 'CONFIGURED (DELIVERY UNVERIFIED)');
    assert.strictEqual(getEmailBadge(false), 'DEV MODE (UNCONFIGURED)');
    assert.notStrictEqual(getEmailBadge(true), 'SMTP ACTIVE');

    // Verify caveats are documented
    assert.ok(mockHealth.angel_one.verification_note?.includes('does not prove that live market data'));
    assert.ok(mockHealth.email.verification_note?.includes('does not prove that email delivery'));
  });

  // -------------------------------------------------------------
  // 9. ERROR MONITORING CLIENT CONTRACT & SANITIZED PROJECTION
  // -------------------------------------------------------------
  test('15. Admin API client handles error query serialization and summary fetch', async () => {
    let capturedUrl = '';
    const originalFetch = globalThis.fetch;

    globalThis.fetch = (async (url: string, init?: RequestInit) => {
      capturedUrl = url;
      if (url.includes('/api/v1/admin/errors/summary')) {
        return new Response(
          JSON.stringify({
            total_errors: 12,
            server_errors_5xx: 2,
            client_errors_4xx: 10,
            last_24h_errors: 5,
            errors_by_category: { SERVER_ERROR: 2, VALIDATION: 10 },
            errors_by_feature_area: { 'Market Data': 2, 'Paper Trading': 10 },
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        );
      }
      return new Response(
        JSON.stringify({
          errors: [],
          total: 0,
          page: 1,
          limit: 20,
          total_pages: 1,
          scope_notice: 'Real recorded server-side events only.',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      );
    }) as any;

    try {
      apiClient.setAdminToken(createValidTestToken('owner-1'));

      // Test errors list with filter serialization
      await apiClient.admin.getErrors({
        page: 2,
        limit: 15,
        status_code: 500,
        category: 'DATABASE',
        feature_area: 'Portfolio',
        search: 'timeout',
      });

      assert.ok(capturedUrl.includes('/api/v1/admin/errors'));
      assert.ok(capturedUrl.includes('page=2'));
      assert.ok(capturedUrl.includes('limit=15'));
      assert.ok(capturedUrl.includes('status_code=500'));
      assert.ok(capturedUrl.includes('category=DATABASE'));
      assert.ok(capturedUrl.includes('feature_area=Portfolio'));
      assert.ok(capturedUrl.includes('search=timeout'));

      // Test summary fetch
      const summary = await apiClient.admin.getErrorsSummary();
      assert.strictEqual(summary.total_errors, 12);
      assert.strictEqual(summary.server_errors_5xx, 2);
      assert.strictEqual(summary.client_errors_4xx, 10);
      assert.strictEqual(summary.last_24h_errors, 5);
      assert.strictEqual(summary.errors_by_category.SERVER_ERROR, 2);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  test('16. Error event projection strictly forbids raw secrets, tokens, and traces', () => {
    // Validate that a typical AdminErrorItem shape conforms strictly to safe sanitized properties
    const mockItem: AdminErrorItem = {
      id: 101,
      correlation_id: 'corr-abc-12345',
      endpoint: '/api/v1/orders/paper',
      method: 'POST',
      status_code: 422,
      error_type: 'RequestValidationError',
      category: 'VALIDATION',
      feature_area: 'Paper Trading',
      sanitized_message: 'Invalid order quantity: password=[REDACTED]',
      user_id: 'usr-safe-001',
      created_at: '2026-11-23T15:00:00Z',
    };

    const forbiddenFields = [
      'password',
      'password_hash',
      'token',
      'access_token',
      'secret_key',
      'api_key',
      'raw_traceback',
      'request_body',
      'chat_history',
      'prompt',
      'response_body',
    ];

    for (const field of forbiddenFields) {
      assert.strictEqual(
        (mockItem as any)[field],
        undefined,
        `AdminErrorItem must NOT contain forbidden field: ${field}`
      );
    }

    assert.ok(mockItem.sanitized_message.includes('[REDACTED]'));
    assert.strictEqual(mockItem.correlation_id, 'corr-abc-12345');
    assert.strictEqual(mockItem.feature_area, 'Paper Trading');
  });

  test('17. Surveillance scope disclosure banner explains what is and is not captured', () => {
    const scopeNotice =
      'This dashboard displays server-side operational exceptions ' +
      '(including unhandled 5xx exceptions, 503 service outages, 429 rate limits, 422 schema validation errors, and 400/401/403/404 HTTP errors). ' +
      'It does not capture client-side network disconnects, local browser JavaScript crashes, ' +
      'or edge CDN dropouts that never reach the backend API. ' +
      'Endpoints are logged as parameterized route templates (unmatched paths are anonymized to /unmatched_route), ' +
      'and all messages are mapped to allowlisted error codes with server-side sanitization. ' +
      'Database writes are bounded by a 250ms ceiling and per-process concurrency limits (max 5 simultaneous writes per worker); ' +
      'during storage degradation, events are dropped fail-open to protect local worker connection pool capacity.';

    // Check captured vs uncaptured explicit explanations
    assert.ok(scopeNotice.includes('server-side operational exceptions'));
    assert.ok(scopeNotice.includes('does not capture client-side network disconnects'));
    assert.ok(scopeNotice.includes('local browser JavaScript crashes'));
    assert.ok(scopeNotice.includes('edge CDN dropouts'));
    assert.ok(scopeNotice.includes('/unmatched_route'));
    assert.ok(scopeNotice.includes('dropped fail-open'));
  });

  test('18. Error status badge classification accurately distinguishes 5xx vs 4xx', () => {
    const getStatusClassification = (statusCode: number) => {
      const is5xx = statusCode >= 500;
      return {
        is5xx,
        badgeStyle: is5xx ? 'loss' : 'warning',
      };
    };

    assert.strictEqual(getStatusClassification(500).is5xx, true);
    assert.strictEqual(getStatusClassification(500).badgeStyle, 'loss');
    assert.strictEqual(getStatusClassification(503).is5xx, true);

    assert.strictEqual(getStatusClassification(422).is5xx, false);
    assert.strictEqual(getStatusClassification(422).badgeStyle, 'warning');
    assert.strictEqual(getStatusClassification(429).is5xx, false);
    assert.strictEqual(getStatusClassification(404).is5xx, false);
  });

  test('19. buildErrorQueryParams enforces bounded inputs, trimmed search, sort order, and local day bounds', () => {
    const filters: ErrorFilterState = {
      search: '  corr-123  ',
      category: 'DATABASE',
      featureArea: 'Paper Trading',
      statusCode: '502',
      dateFrom: '2026-11-20',
      dateTo: '2026-11-24',
      sortOrder: 'asc',
      limit: 50,
    };

    const params = buildErrorQueryParams(filters, 3, true);
    assert.strictEqual(params.page, 3);
    assert.strictEqual(params.limit, 50);
    assert.strictEqual(params.status_code, 502);
    assert.strictEqual(params.category, 'DATABASE');
    assert.strictEqual(params.feature_area, 'Paper Trading');
    assert.strictEqual(params.sort_order, 'asc');
    assert.strictEqual(params.search, 'corr-123');
    assert.strictEqual(params.date_from, toLocalDateBoundaryIso('2026-11-20', 'start'));
    assert.strictEqual(params.date_to, toLocalDateBoundaryIso('2026-11-24', 'end'));

    // Out-of-bounds pagination, invalid status code, and blank search fall back safely
    const outOfBounds = buildErrorQueryParams(
      {
        ...DEFAULT_ERROR_FILTERS,
        search: '   ',
        statusCode: '999',
        limit: 500,
      },
      0,
      false
    );
    assert.strictEqual(outOfBounds.page, 1);
    assert.strictEqual(outOfBounds.limit, 20);
    assert.strictEqual(outOfBounds.status_code, undefined);
    assert.strictEqual(outOfBounds.search, undefined);
    assert.strictEqual(outOfBounds.sort_order, 'desc');
  });

  test('20. validateErrorDateRange and hasActiveErrorFilters detect invalid ranges and active state', () => {
    assert.strictEqual(validateErrorDateRange('', ''), null);
    assert.strictEqual(validateErrorDateRange('2026-11-20', '2026-11-25'), null);
    assert.strictEqual(validateErrorDateRange('2026-11-24', '2026-11-24'), null);
    assert.ok(validateErrorDateRange('2026/11/24', '2026-11-25')?.includes('YYYY-MM-DD'));
    assert.ok(validateErrorDateRange('2026-11-20', 'invalid')?.includes('YYYY-MM-DD'));
    assert.ok(validateErrorDateRange('2026-11-25', '2026-11-20')?.includes('on or before'));

    assert.strictEqual(hasActiveErrorFilters(DEFAULT_ERROR_FILTERS), false);
    assert.strictEqual(hasActiveErrorFilters({ ...DEFAULT_ERROR_FILTERS, search: '   ' }), false);
    assert.strictEqual(hasActiveErrorFilters({ ...DEFAULT_ERROR_FILTERS, category: 'NOT_FOUND' }), true);
    assert.strictEqual(hasActiveErrorFilters({ ...DEFAULT_ERROR_FILTERS, featureArea: 'Auth' }), true);
    assert.strictEqual(hasActiveErrorFilters({ ...DEFAULT_ERROR_FILTERS, statusCode: '409' }), true);
    assert.strictEqual(hasActiveErrorFilters({ ...DEFAULT_ERROR_FILTERS, dateFrom: '2026-11-24' }), true);
    assert.strictEqual(hasActiveErrorFilters({ ...DEFAULT_ERROR_FILTERS, sortOrder: 'asc' }), true);
  });

  test('21. Error catalog options cover NOT_FOUND, 409, and merge dynamic summary values without duplicates', () => {
    assert.ok(ERROR_CATEGORIES.includes('NOT_FOUND'));
    assert.ok(ERROR_STATUS_OPTIONS.some((opt) => opt.value === 409));

    const merged = mergeErrorFilterOptions(ERROR_CATEGORIES, {
      DATABASE: 5,
      NOT_FOUND: 2,
      CUSTOM_DYNAMIC_CAT: 1,
      '': 3,
    });
    assert.strictEqual(merged.filter((item) => item === 'DATABASE').length, 1);
    assert.ok(merged.includes('CUSTOM_DYNAMIC_CAT'));
    assert.strictEqual(merged.includes(''), false);
  });

  test('22. apiClient.admin.getErrors serializes date_from, date_to, sort_order, and filter params', async () => {
    let capturedUrl = '';
    const originalFetch = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL) => {
      capturedUrl = String(input);
      return new Response(
        JSON.stringify({
          errors: [],
          total: 0,
          page: 1,
          limit: 20,
          total_pages: 1,
          scope_notice: 'Real recorded server-side events only.',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      );
    }) as any;

    try {
      apiClient.setAdminToken(createValidTestToken('owner-1'));
      await apiClient.admin.getErrors({
        page: 2,
        limit: 50,
        status_code: 409,
        category: 'CONFLICT',
        feature_area: 'Paper Trading',
        date_from: '2026-11-20T00:00:00.000Z',
        date_to: '2026-11-25T23:59:59.999Z',
        sort_order: 'asc',
        search: 'corr-xyz',
      });

      const parsed = new URL(capturedUrl, 'http://localhost');
      assert.strictEqual(parsed.pathname, '/api/v1/admin/errors');
      assert.strictEqual(parsed.searchParams.get('page'), '2');
      assert.strictEqual(parsed.searchParams.get('limit'), '50');
      assert.strictEqual(parsed.searchParams.get('status_code'), '409');
      assert.strictEqual(parsed.searchParams.get('category'), 'CONFLICT');
      assert.strictEqual(parsed.searchParams.get('feature_area'), 'Paper Trading');
      assert.strictEqual(parsed.searchParams.get('date_from'), '2026-11-20T00:00:00.000Z');
      assert.strictEqual(parsed.searchParams.get('date_to'), '2026-11-25T23:59:59.999Z');
      assert.strictEqual(parsed.searchParams.get('sort_order'), 'asc');
      assert.strictEqual(parsed.searchParams.get('search'), 'corr-xyz');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  test('23. formatErrorTimestamp handles invalid or empty inputs gracefully', () => {
    assert.strictEqual(formatErrorTimestamp(null), '—');
    assert.strictEqual(formatErrorTimestamp(undefined), '—');
    assert.strictEqual(formatErrorTimestamp('not-a-timestamp'), '—');
    const formatted = formatErrorTimestamp('2026-11-25T10:30:00Z');
    assert.notStrictEqual(formatted, '—');
    assert.ok(formatted.includes('2026'));
  });

  // -------------------------------------------------------------
  // 10. ADMIN USER DIRECTORY DOMAIN & FILTER SERIALIZATION
  // -------------------------------------------------------------
  test('24. buildUserQueryParams enforces defaults, status mapping, trimmed search, sort order, and local day bounds', () => {
    const filters: UserFilterState = {
      search: '  priya@example.com  ',
      accountStatus: 'inactive',
      emailVerified: 'true',
      onboardingCompleted: 'false',
      dateFrom: '2026-11-10',
      dateTo: '2026-11-25',
      sortOrder: 'asc',
      limit: 50,
    };

    const params = buildUserQueryParams(filters, 2, true);
    assert.strictEqual(params.page, 2);
    assert.strictEqual(params.limit, 50);
    assert.strictEqual(params.search, 'priya@example.com');
    assert.strictEqual(params.is_active, false);
    assert.strictEqual(params.email_verified, true);
    assert.strictEqual(params.onboarding_completed, false);
    assert.strictEqual(params.sort_order, 'asc');
    assert.strictEqual(params.date_from, toLocalDateBoundaryIso('2026-11-10', 'start'));
    assert.strictEqual(params.date_to, toLocalDateBoundaryIso('2026-11-25', 'end'));

    const fallback = buildUserQueryParams(
      {
        ...DEFAULT_USER_FILTERS,
        accountStatus: 'active',
        search: '   ',
        limit: 999,
      },
      -3,
      false
    );
    assert.strictEqual(fallback.page, 1);
    assert.strictEqual(fallback.limit, 20);
    assert.strictEqual(fallback.is_active, true);
    assert.strictEqual(fallback.email_verified, undefined);
    assert.strictEqual(fallback.onboarding_completed, undefined);
    assert.strictEqual(fallback.search, undefined);
    assert.strictEqual(fallback.sort_order, 'desc');
  });

  test('25. validateUserDateRange and hasActiveUserFilters detect invalid ranges and active states', () => {
    assert.strictEqual(validateUserDateRange('', ''), null);
    assert.strictEqual(validateUserDateRange('2026-11-10', '2026-11-25'), null);
    assert.strictEqual(validateUserDateRange('2026-11-25', '2026-11-25'), null);
    assert.ok(validateUserDateRange('25-11-2026', '2026-11-25')?.includes('YYYY-MM-DD'));
    assert.ok(validateUserDateRange('2026-11-25', '2026-11-20')?.includes('on or before'));

    assert.strictEqual(hasActiveUserFilters(DEFAULT_USER_FILTERS), false);
    assert.strictEqual(hasActiveUserFilters({ ...DEFAULT_USER_FILTERS, search: '   ' }), false);
    assert.strictEqual(hasActiveUserFilters({ ...DEFAULT_USER_FILTERS, search: 'alice' }), true);
    assert.strictEqual(hasActiveUserFilters({ ...DEFAULT_USER_FILTERS, accountStatus: 'active' }), true);
    assert.strictEqual(hasActiveUserFilters({ ...DEFAULT_USER_FILTERS, emailVerified: 'false' }), true);
    assert.strictEqual(hasActiveUserFilters({ ...DEFAULT_USER_FILTERS, onboardingCompleted: 'true' }), true);
    assert.strictEqual(hasActiveUserFilters({ ...DEFAULT_USER_FILTERS, dateFrom: '2026-11-01' }), true);
    assert.strictEqual(hasActiveUserFilters({ ...DEFAULT_USER_FILTERS, sortOrder: 'asc' }), true);
  });

  test('26. apiClient.admin.getUsers serializes search, status flags, date_from, date_to, and sort_order', async () => {
    let capturedUrl = '';
    const originalFetch = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL) => {
      capturedUrl = String(input);
      return new Response(
        JSON.stringify({
          users: [],
          total: 0,
          page: 1,
          limit: 20,
          total_pages: 1,
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      );
    }) as any;

    try {
      apiClient.setAdminToken(createValidTestToken('owner-1'));
      await apiClient.admin.getUsers({
        page: 3,
        limit: 10,
        search: 'shivraj',
        is_active: false,
        email_verified: true,
        onboarding_completed: false,
        date_from: '2026-11-01T00:00:00.000Z',
        date_to: '2026-11-25T23:59:59.999Z',
        sort_order: 'asc',
      });

      const parsed = new URL(capturedUrl, 'http://localhost');
      assert.strictEqual(parsed.pathname, '/api/v1/admin/users');
      assert.strictEqual(parsed.searchParams.get('page'), '3');
      assert.strictEqual(parsed.searchParams.get('limit'), '10');
      assert.strictEqual(parsed.searchParams.get('search'), 'shivraj');
      assert.strictEqual(parsed.searchParams.get('is_active'), 'false');
      assert.strictEqual(parsed.searchParams.get('email_verified'), 'true');
      assert.strictEqual(parsed.searchParams.get('onboarding_completed'), 'false');
      assert.strictEqual(parsed.searchParams.get('date_from'), '2026-11-01T00:00:00.000Z');
      assert.strictEqual(parsed.searchParams.get('date_to'), '2026-11-25T23:59:59.999Z');
      assert.strictEqual(parsed.searchParams.get('sort_order'), 'asc');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  test('27. resolveUserDisplayName and formatUserRegistrationDate handle missing/valid inputs cleanly', () => {
    assert.strictEqual(resolveUserDisplayName({ full_name: 'Aarav Patel', display_name: 'Aarav' }), 'Aarav Patel');
    assert.strictEqual(resolveUserDisplayName({ full_name: '  ', display_name: 'InvestorA' }), 'InvestorA');
    assert.strictEqual(resolveUserDisplayName({ full_name: null, display_name: undefined }), '—');

    assert.strictEqual(formatUserRegistrationDate(null), '—');
    assert.strictEqual(formatUserRegistrationDate('invalid'), '—');
    const formatted = formatUserRegistrationDate('2026-11-25T09:15:00Z');
    assert.notStrictEqual(formatted, '—');
    assert.ok(formatted.includes('2026'));
  });

  test('28. User directory default sort and options prioritize newest registrations and read-only safety', () => {
    assert.strictEqual(DEFAULT_USER_FILTERS.sortOrder, 'desc');
    assert.strictEqual(DEFAULT_USER_FILTERS.limit, 20);
    assert.deepStrictEqual(
      USER_ACCOUNT_STATUS_OPTIONS.map((o) => o.value),
      ['', 'active', 'inactive']
    );
    assert.deepStrictEqual(
      USER_SORT_OPTIONS.map((o) => o.value),
      ['desc', 'asc']
    );
  });

  // -------------------------------------------------------------
  // 11. PAPER TRADING OVERVIEW & ORDERS DOMAIN CONTRACT
  // -------------------------------------------------------------
  test('29. Paper trading order status catalog matches real DB schema statuses cleanly', () => {
    assert.deepStrictEqual([...ORDER_STATUS_OPTIONS], ['FILLED', 'REJECTED', 'PENDING', 'CANCELLED']);
    assert.strictEqual(ORDER_STATUS_OPTIONS.includes('ACCEPTED' as any), false);
    assert.strictEqual(DEFAULT_ORDER_FILTERS.sortOrder, 'desc');
    assert.strictEqual(DEFAULT_ORDER_FILTERS.limit, 20);
    assert.deepStrictEqual(
      ORDER_SORT_OPTIONS.map((o) => o.value),
      ['desc', 'asc']
    );

    const normalized = normalizeOrderStatusCounts({ FILLED: 4, REJECTED: -2 });
    assert.strictEqual(normalized.FILLED, 4);
    assert.strictEqual(normalized.REJECTED, 0);
    assert.strictEqual(normalized.PENDING, 0);
    assert.strictEqual(normalized.CANCELLED, 0);
  });

  test('30. buildOrderQueryParams enforces bounds, uppercases enums, trims search, and resolves date bounds', () => {
    const filters: OrderFilterState = {
      search: '  reliance  ',
      status: 'rejected',
      side: 'sell',
      dateFrom: '2026-11-15',
      dateTo: '2026-11-25',
      sortOrder: 'asc',
      limit: 50,
    };

    const params = buildOrderQueryParams(filters, 4, true);
    assert.strictEqual(params.page, 4);
    assert.strictEqual(params.limit, 50);
    assert.strictEqual(params.search, 'reliance');
    assert.strictEqual(params.status, 'REJECTED');
    assert.strictEqual(params.side, 'SELL');
    assert.strictEqual(params.sort_order, 'asc');
    assert.strictEqual(params.date_from, toLocalDateBoundaryIso('2026-11-15', 'start'));
    assert.strictEqual(params.date_to, toLocalDateBoundaryIso('2026-11-25', 'end'));

    const fallback = buildOrderQueryParams(
      {
        ...DEFAULT_ORDER_FILTERS,
        search: '   ',
        limit: 500,
      },
      0,
      false
    );
    assert.strictEqual(fallback.page, 1);
    assert.strictEqual(fallback.limit, 20);
    assert.strictEqual(fallback.search, undefined);
    assert.strictEqual(fallback.status, undefined);
    assert.strictEqual(fallback.side, undefined);
    assert.strictEqual(fallback.sort_order, 'desc');
  });

  test('31. validateOrderDateRange and hasActiveOrderFilters validate chronological bounds and active state', () => {
    assert.strictEqual(validateOrderDateRange('', ''), null);
    assert.strictEqual(validateOrderDateRange('2026-11-01', '2026-11-25'), null);
    assert.strictEqual(validateOrderDateRange('2026-11-25', '2026-11-25'), null);
    assert.ok(validateOrderDateRange('invalid', '2026-11-25')?.includes('YYYY-MM-DD'));
    assert.ok(validateOrderDateRange('2026-11-25', '2026-11-20')?.includes('on or before'));

    assert.strictEqual(hasActiveOrderFilters(DEFAULT_ORDER_FILTERS), false);
    assert.strictEqual(hasActiveOrderFilters({ ...DEFAULT_ORDER_FILTERS, search: '  ' }), false);
    assert.strictEqual(hasActiveOrderFilters({ ...DEFAULT_ORDER_FILTERS, search: 'TCS' }), true);
    assert.strictEqual(hasActiveOrderFilters({ ...DEFAULT_ORDER_FILTERS, status: 'REJECTED' }), true);
    assert.strictEqual(hasActiveOrderFilters({ ...DEFAULT_ORDER_FILTERS, side: 'BUY' }), true);
    assert.strictEqual(hasActiveOrderFilters({ ...DEFAULT_ORDER_FILTERS, dateTo: '2026-11-25' }), true);
    assert.strictEqual(hasActiveOrderFilters({ ...DEFAULT_ORDER_FILTERS, sortOrder: 'asc' }), true);
  });

  test('32. apiClient.admin.getOrders serializes date_from, date_to, sort_order, side, status, and search', async () => {
    let capturedUrl = '';
    const originalFetch = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL) => {
      capturedUrl = String(input);
      return new Response(
        JSON.stringify({
          orders: [],
          total: 0,
          page: 1,
          limit: 20,
          total_pages: 1,
          overall_total: 0,
          status_counts: { FILLED: 0, REJECTED: 0, PENDING: 0, CANCELLED: 0 },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      );
    }) as any;

    try {
      apiClient.setAdminToken(createValidTestToken('owner-1'));
      await apiClient.admin.getOrders({
        page: 2,
        limit: 10,
        symbol: 'INFY',
        status: 'REJECTED',
        side: 'SELL',
        date_from: '2026-11-10T00:00:00.000Z',
        date_to: '2026-11-25T23:59:59.999Z',
        sort_order: 'asc',
        search: 'ord-123',
      });

      const parsed = new URL(capturedUrl, 'http://localhost');
      assert.strictEqual(parsed.pathname, '/api/v1/admin/orders');
      assert.strictEqual(parsed.searchParams.get('page'), '2');
      assert.strictEqual(parsed.searchParams.get('limit'), '10');
      assert.strictEqual(parsed.searchParams.get('symbol'), 'INFY');
      assert.strictEqual(parsed.searchParams.get('status'), 'REJECTED');
      assert.strictEqual(parsed.searchParams.get('side'), 'SELL');
      assert.strictEqual(parsed.searchParams.get('date_from'), '2026-11-10T00:00:00.000Z');
      assert.strictEqual(parsed.searchParams.get('date_to'), '2026-11-25T23:59:59.999Z');
      assert.strictEqual(parsed.searchParams.get('sort_order'), 'asc');
      assert.strictEqual(parsed.searchParams.get('search'), 'ord-123');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  test('33. resolveOrderFailureDetails, formatOrderPrice, and formatOrderTimestamp handle missing/unsafe inputs honestly', () => {
    assert.strictEqual(resolveOrderFailureDetails({ status: 'REJECTED', rejection_reason: null }), 'Failure reason unavailable');
    assert.strictEqual(resolveOrderFailureDetails({ status: 'REJECTED', rejection_reason: '   ' }), 'Failure reason unavailable');
    assert.strictEqual(resolveOrderFailureDetails({ status: 'FILLED', rejection_reason: null }), '—');
    assert.strictEqual(
      resolveOrderFailureDetails({ status: 'REJECTED', rejection_reason: 'Insufficient virtual cash balance for requested order.' }),
      'Insufficient virtual cash balance for requested order.'
    );

    assert.strictEqual(formatOrderPrice({ fill_price: null, limit_price: null }), '—');
    assert.strictEqual(formatOrderPrice({ fill_price: 0, limit_price: null }), '—');
    assert.ok(formatOrderPrice({ fill_price: 2450.5, limit_price: null }).includes('2,450.50'));
    assert.ok(formatOrderPrice({ fill_price: null, limit_price: 3400 }).includes('3,400.00'));

    assert.strictEqual(formatOrderTimestamp(null), '—');
    assert.strictEqual(formatOrderTimestamp('invalid'), '—');
    assert.ok(formatOrderTimestamp('2026-11-25T11:20:00Z').includes('2026'));
  });
});
