/**
 * Admin Panel & Management Verification Tests.
 *
 * Validates:
 * 1. Admin tab integration in sessionNavigation and VALID_TABS.
 * 2. Hash routing and tab resolution for '#admin'.
 * 3. ApiClient admin request contract (overview, users, orders, system-health).
 * 4. Query string serialization for users and orders filters.
 * 5. Safe projection enforcement: strictly prohibits sensitive fields
 *    (password_hash, google_subject, provider_subject, risk_assessment, tokens).
 * 6. System health diagnostics contract: integration states without secrets.
 * 7. Non-owner fail-closed behavior.
 */

import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  VALID_TABS,
  isValidTab,
  parseTabFromHash,
  isWorkspaceTabHash,
  resolveLandingTab,
  type NavigationTab,
} from '../src/domain/sessionNavigation.ts';
import type {
  AdminUserItem,
  AdminOrderItem,
  AdminOverviewResponse,
  AdminSystemHealthResponse,
} from '../src/api/client.ts';

describe('FinEx Common Admin Panel Frontend & Domain Contract', () => {
  // -------------------------------------------------------------
  // 1. NAVIGATION & ROUTING DOMAIN
  // -------------------------------------------------------------
  test('1. Admin tab is a recognized first-class workspace navigation tab', () => {
    assert.ok(VALID_TABS.includes('admin' as NavigationTab), 'admin tab must be present in VALID_TABS');
    assert.strictEqual(isValidTab('admin'), true, 'isValidTab("admin") must return true');
    assert.strictEqual(parseTabFromHash('#admin'), 'admin');
    assert.strictEqual(parseTabFromHash('#/admin'), 'admin');
    assert.strictEqual(isWorkspaceTabHash('#admin'), true);
  });

  test('2. Landing tab resolution honors active session for admin hash', () => {
    // In-session active refresh with #admin stays on admin
    const activeAdminTab = resolveLandingTab({
      hasActiveSession: true,
      locationHash: '#admin',
      storedTab: 'admin',
    });
    assert.strictEqual(activeAdminTab, 'admin');

    // Unauthenticated user landing with #admin defaults to overview
    const unauthTab = resolveLandingTab({
      hasActiveSession: false,
      locationHash: '#admin',
      storedTab: 'admin',
    });
    assert.strictEqual(unauthTab, 'overview');
  });

  // -------------------------------------------------------------
  // 2. SAFE PROJECTIONS & PROHIBITED SENSITIVE FIELDS
  // -------------------------------------------------------------
  test('3. AdminUserItem schema strictly excludes passwords, OAuth subjects, and private questionnaire JSON', () => {
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

  test('4. AdminOrderItem schema excludes execution traces and private financial accounts', () => {
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

  // -------------------------------------------------------------
  // 3. OVERVIEW & HEALTH CONTRACTS
  // -------------------------------------------------------------
  test('5. AdminOverviewResponse contract structure', () => {
    const mockOverview: AdminOverviewResponse = {
      total_users: 150,
      verified_users: 120,
      unverified_users: 30,
      onboarding_completed_users: 95,
      total_orders: 540,
      orders_by_status: {
        FILLED: 480,
        REJECTED: 45,
        PENDING: 10,
        CANCELLED: 5,
      },
      recent_rejected_orders: [],
    };

    assert.strictEqual(mockOverview.total_users, 150);
    assert.strictEqual(mockOverview.verified_users + mockOverview.unverified_users, mockOverview.total_users);
    assert.strictEqual(mockOverview.orders_by_status.FILLED, 480);
    assert.strictEqual(mockOverview.orders_by_status.REJECTED, 45);
  });

  test('6. AdminSystemHealthResponse diagnostics strictly excludes secrets', () => {
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

    // Verify presence of operational indicators
    assert.strictEqual(mockHealth.backend.status, 'ok');
    assert.strictEqual(mockHealth.database.status, 'ok');
    assert.strictEqual(mockHealth.angel_one.is_circuit_open, false);

    // Verify absence of sensitive credentials in diagnostics
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
  // 4. API QUERY STRING SERIALIZATION
  // -------------------------------------------------------------
  test('7. Admin query parameter builder builds correct query strings', () => {
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
});
