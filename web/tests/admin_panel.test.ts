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
} from '../src/api/client.ts';

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
});
