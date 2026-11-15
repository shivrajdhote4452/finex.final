import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  processOrderExecution,
  isNetworkOrTimeoutError,
  calculateNewHoldings,
  generateIdempotencyKey,
  type OrderExecutionParams,
  type OrderExecutionContext,
} from '../src/domain/orderExecution.ts';
import type { HoldingItem, LedgerEntry } from '../src/context/FinancialContext.ts';

/**
 * Frontend Paper-Order Verification Suite.
 *
 * This test suite directly exercises the production paper-order execution logic in
 * `web/src/domain/orderExecution.ts` (used by `web/src/context/FinancialContext.tsx`).
 * It tests real business logic, error paths, and state transitions without copying code.
 */

interface TestHarnessOptions {
  isAuthenticated?: boolean;
  submitOrderMock?: (order: any, idempotencyKey?: string) => Promise<any>;
  getOrdersMock?: (limit?: number) => Promise<{ orders: any[]; total: number }>;
  quotePrice?: number;
}

function createTestHarness(
  initialState: { virtualCash?: number; holdings?: HoldingItem[]; ledger?: LedgerEntry[] } = {},
  options: TestHarnessOptions = {}
) {
  const state = {
    virtualCash: initialState.virtualCash ?? 100000,
    holdings: initialState.holdings ? [...initialState.holdings] : [],
    ledger: initialState.ledger ? [...initialState.ledger] : [],
    accountRefreshed: false,
    notifications: [] as Array<{ title: string; message: string; type?: string }>,
  };

  const context: OrderExecutionContext = {
    virtualCash: state.virtualCash,
    updateVirtualCash: (newCash: number) => {
      state.virtualCash = newCash;
      context.virtualCash = newCash;
    },
    getHoldings: () => state.holdings,
    setHoldings: (updater) => {
      state.holdings = updater(state.holdings);
    },
    setLedger: (updater) => {
      state.ledger = updater(state.ledger);
    },
    addNotification: (title, message, type) => {
      state.notifications.push({ title, message, type });
    },
    refreshAccount: async () => {
      state.accountRefreshed = true;
    },
    apiClient: {
      isAuthenticated: () => options.isAuthenticated ?? true,
      paperTrading: {
        submitOrder: options.submitOrderMock || (async () => { throw new Error('submitOrder not mocked'); }),
        getOrders: options.getOrdersMock || (async () => ({ orders: [], total: 0 })),
      },
    },
    getQuotePrice: () => options.quotePrice ?? 1000,
  };

  const execute = (params: OrderExecutionParams) => processOrderExecution(params, context);

  return { state, context, execute };
}

describe('Frontend Paper-Order Execution (Actual Production Logic)', () => {
  it('1. Backend rejection does NOT mutate cash, holdings, or create fake filled receipt', async () => {
    let submitCallCount = 0;
    const { state, execute } = createTestHarness(
      { virtualCash: 100000, holdings: [], ledger: [] },
      {
        isAuthenticated: true,
        submitOrderMock: async () => {
          submitCallCount++;
          return {
            status: 'REJECTED',
            rejection_reason: 'Market quote is stale or unavailable. Trade rejected.',
          };
        },
      }
    );

    const result = await execute({
      symbol: 'RELIANCE',
      type: 'BUY',
      shares: 10,
      orderType: 'MARKET',
    });

    assert.equal(result.success, false, 'Expected order execution to fail');
    assert.match(result.error || '', /stale/i, 'Expected error message to explain stale quote rejection');
    assert.equal(result.receipt, undefined, 'Must not return an order receipt on rejection');
    assert.equal(submitCallCount, 1, 'Expected exactly one submission');
    assert.equal(state.virtualCash, 100000, 'Virtual cash must NOT be deducted');
    assert.equal(state.holdings.length, 0, 'Holdings must NOT be mutated');
    assert.equal(state.ledger.length, 0, 'No ledger receipt should be recorded');
  });

  it('2. Backend HTTP 500 error does NOT mutate cash, holdings, or create local fill receipt', async () => {
    const { state, execute } = createTestHarness(
      { virtualCash: 85000, holdings: [], ledger: [] },
      {
        isAuthenticated: true,
        submitOrderMock: async () => {
          const err: any = new Error('Database transaction lock conflict in paper trading engine');
          err.status = 500;
          throw err;
        },
      }
    );

    const result = await execute({
      symbol: 'TCS',
      type: 'BUY',
      shares: 5,
      orderType: 'MARKET',
    });

    assert.equal(result.success, false, 'HTTP 500 must report failure');
    assert.match(result.error || '', /lock conflict/i, 'Must propagate error message');
    assert.equal(result.receipt, undefined, 'No receipt on HTTP 500');
    assert.equal(state.virtualCash, 85000, 'Virtual cash must remain intact');
    assert.equal(state.holdings.length, 0, 'Holdings must not change');
    assert.equal(state.ledger.length, 0, 'Ledger must not contain fake fill');
  });

  it('3. Network timeout treats outcome as uncertain and instructs user to check order activity before retry', async () => {
    let reconcileOrdersCalled = false;
    const { state, execute } = createTestHarness(
      { virtualCash: 50000, holdings: [], ledger: [] },
      {
        isAuthenticated: true,
        submitOrderMock: async () => {
          const err: any = new Error('Request timed out while connecting to FinEx server. The server may be waking up.');
          err.code = 'TIMEOUT';
          err.status = 408;
          throw err;
        },
        getOrdersMock: async () => {
          reconcileOrdersCalled = true;
          // Orders list does not yet have this key (outcome still uncertain)
          return { orders: [], total: 0 };
        },
      }
    );

    const result = await execute({
      symbol: 'INFY',
      type: 'BUY',
      shares: 10,
      orderType: 'MARKET',
      idempotencyKey: 'idemp-timeout-test-123',
    });

    assert.equal(result.success, false, 'Must fail closed with uncertain status');
    assert.match(result.error || '', /network timeout/i, 'Must explain timeout reason');
    assert.match(result.error || '', /check your order activity/i, 'Must advise user before retrying');
    assert.equal(reconcileOrdersCalled, true, 'Must have attempted reconciliation');
    assert.equal(result.receipt, undefined, 'Must not manufacture a local fill receipt');
    assert.equal(state.virtualCash, 50000, 'Must not mutate cash on timeout');
    assert.equal(state.holdings.length, 0, 'Must not mutate holdings on timeout');
    assert.equal(state.ledger.length, 0, 'Must not append uncertain order to ledger');
  });

  it('4. Successful order found during reconciliation is adopted without duplicate receipts', async () => {
    const idempKey = 'idemp-reconcile-success-456';
    const { state, execute } = createTestHarness(
      { virtualCash: 100000, holdings: [], ledger: [] },
      {
        isAuthenticated: true,
        submitOrderMock: async () => {
          // Network connection dropped while awaiting backend response
          const err: any = new Error('Network error connecting to FinEx server.');
          err.code = 'NETWORK_ERROR';
          throw err;
        },
        getOrdersMock: async () => {
          return {
            orders: [
              {
                id: 'ord-backend-rec-888',
                order_id: 'ord-backend-rec-888',
                symbol: 'RELIANCE',
                side: 'BUY',
                quantity: 10,
                fill_price: 2500.0,
                gross_value: 25000.0,
                cash_balance_after: 75000.0,
                status: 'FILLED',
                idempotency_key: idempKey,
              },
            ],
            total: 1,
          };
        },
      }
    );

    const result = await execute({
      symbol: 'RELIANCE',
      type: 'BUY',
      shares: 10,
      orderType: 'MARKET',
      idempotencyKey: idempKey,
    });

    assert.equal(result.success, true, 'Order reconciliation should succeed');
    assert.ok(result.receipt, 'Must provide reconciled receipt');
    assert.equal(result.receipt?.id, 'ord-backend-rec-888', 'Must use backend order id');
    assert.equal(result.receipt?.status, 'FILLED');
    assert.equal(result.receipt?.fillPrice, 2500.0);
    assert.equal(result.receipt?.total, 25000.0);
    assert.equal(state.virtualCash, 75000.0, 'Virtual cash updated to authoritative server value');
    assert.equal(state.ledger.length, 1, 'Only one receipt added to ledger');
    assert.match(state.ledger[0].notes || '', /reconciled order/i, 'Receipt must note reconciliation');
  });

  it('5. ACCEPTED / PENDING limit order creates pending receipt without cash deduction or fill price', async () => {
    const { state, execute } = createTestHarness(
      { virtualCash: 100000, holdings: [], ledger: [] },
      {
        isAuthenticated: true,
        submitOrderMock: async (payload) => {
          return {
            order_id: 'ord-limit-pending-999',
            symbol: payload.symbol,
            side: payload.side,
            quantity: payload.quantity,
            status: 'PENDING',
            limit_price: payload.limit_price,
            fill_price: null,
            cash_balance_after: 100000,
          };
        },
      }
    );

    const result = await execute({
      symbol: 'TCS',
      type: 'BUY',
      shares: 5,
      orderType: 'LIMIT',
      customPrice: 3200.0,
    });

    assert.equal(result.success, true, 'Pending order should be acknowledged');
    assert.ok(result.receipt, 'Must return pending receipt');
    assert.equal(result.receipt?.status, 'PENDING');
    assert.equal(result.receipt?.fillPrice, 0, 'Fill price must be 0 while pending');
    assert.equal(result.receipt?.total, 16000.0, 'Limit total calculated');
    assert.equal(state.virtualCash, 100000, 'Cash must NOT be deducted while order is pending fill');
    assert.equal(state.holdings.length, 0, 'Holdings must NOT be added while order is pending');
    assert.equal(state.ledger.length, 1, 'Pending order recorded in ledger');
    assert.equal(state.ledger[0].status, 'PENDING');
  });

  it('6. FILLED order synchronizes cash balance and triggers backend account refresh', async () => {
    let refreshCalled = false;
    const { state, execute } = createTestHarness(
      { virtualCash: 100000, holdings: [], ledger: [] },
      {
        isAuthenticated: true,
        submitOrderMock: async () => {
          return {
            order_id: 'ord-fill-777',
            symbol: 'INFY',
            side: 'BUY',
            quantity: 20,
            fill_price: 1500.0,
            gross_value: 30000.0,
            cash_balance_after: 70000.0,
            status: 'FILLED',
          };
        },
      }
    );

    // Track refreshAccount
    const origRefresh = state.accountRefreshed;

    const result = await execute({
      symbol: 'INFY',
      type: 'BUY',
      shares: 20,
      orderType: 'MARKET',
    });

    assert.equal(result.success, true);
    assert.ok(result.receipt);
    assert.equal(result.receipt?.id, 'ord-fill-777');
    assert.equal(result.receipt?.fillPrice, 1500.0);
    assert.equal(result.receipt?.status, 'FILLED');
    assert.equal(state.virtualCash, 70000.0, 'Authoritative cash synchronized');
    assert.equal(state.accountRefreshed, true, 'refreshAccount must be called');
  });

  it('7. Replay trading remains segregated with [REPLAY] notes and notifications', async () => {
    const { state, execute } = createTestHarness(
      { virtualCash: 50000, holdings: [], ledger: [] },
      { isAuthenticated: true }
    );

    const result = await execute({
      symbol: 'RELIANCE',
      type: 'BUY',
      shares: 10,
      orderType: 'MARKET',
      customPrice: 2000.0,
      isReplay: true,
      replayDate: '2025-01-15',
    });

    assert.equal(result.success, true);
    assert.ok(result.receipt);
    assert.equal(result.receipt?.isReplay, true);
    assert.equal(result.receipt?.replayDate, '2025-01-15');
    assert.match(result.receipt?.notes || '', /\[REPLAY - 2025-01-15\]/);
    assert.equal(state.virtualCash, 30000.0);
    assert.equal(state.holdings.length, 1);
    assert.equal(state.holdings[0].shares, 10);
    assert.equal(state.notifications.length, 1);
    assert.match(state.notifications[0].message, /\[REPLAY\]/);
  });

  it('8. Unauthenticated demo sandbox mode explicitly labels simulated trades with [DEMO]', async () => {
    const { state, execute } = createTestHarness(
      { virtualCash: 100000, holdings: [], ledger: [] },
      {
        isAuthenticated: false, // Unauthenticated sandbox
        quotePrice: 2400.0,
      }
    );

    const result = await execute({
      symbol: 'TATAMOTORS',
      type: 'BUY',
      shares: 10,
      orderType: 'MARKET',
    });

    assert.equal(result.success, true);
    assert.ok(result.receipt);
    assert.match(result.receipt?.id || '', /^ord-demo-/);
    assert.match(result.receipt?.notes || '', /\[DEMO - Unauthenticated Sandbox\]/);
    assert.equal(state.virtualCash, 76000.0);
    assert.equal(state.holdings.length, 1);
    assert.equal(state.notifications.length, 1);
    assert.match(state.notifications[0].title, /Demo Order/);
  });

  it('9. Helper functions: isNetworkOrTimeoutError, calculateNewHoldings, and generateIdempotencyKey', () => {
    assert.equal(isNetworkOrTimeoutError({ code: 'TIMEOUT' }), true);
    assert.equal(isNetworkOrTimeoutError({ status: 408 }), true);
    assert.equal(isNetworkOrTimeoutError({ status: 500, message: 'Internal Server Error' }), false);

    const key = generateIdempotencyKey();
    assert.match(key, /^web-ord-\d+-[a-z0-9]+$/);

    const initialHoldings: HoldingItem[] = [];
    const afterBuy = calculateNewHoldings(initialHoldings, 'TCS', 'BUY', 10, 3000, 30000);
    assert.equal(afterBuy.length, 1);
    assert.equal(afterBuy[0].shares, 10);
    assert.equal(afterBuy[0].avgPrice, 3000);

    const afterSecondBuy = calculateNewHoldings(afterBuy, 'TCS', 'BUY', 10, 4000, 40000);
    assert.equal(afterSecondBuy.length, 1);
    assert.equal(afterSecondBuy[0].shares, 20);
    assert.equal(afterSecondBuy[0].avgPrice, 3500);

    const afterSell = calculateNewHoldings(afterSecondBuy, 'TCS', 'SELL', 5, 4500, 22500);
    assert.equal(afterSell.length, 1);
    assert.equal(afterSell[0].shares, 15);
    assert.equal(afterSell[0].avgPrice, 3500);

    const afterCompleteSell = calculateNewHoldings(afterSell, 'TCS', 'SELL', 15, 4500, 67500);
    assert.equal(afterCompleteSell.length, 0);
  });
});
