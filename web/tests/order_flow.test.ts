import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

/**
 * Frontend Paper-Order Execution Engine Simulation
 * Mirroring the exact state machine and backend integration in web/src/context/FinancialContext.tsx
 */
interface OrderPayload {
  symbol: string;
  side: 'BUY' | 'SELL';
  order_type: 'MARKET' | 'LIMIT' | 'STOP_LOSS' | 'SIP';
  quantity: number;
  limit_price?: number;
}

interface LedgerEntry {
  id: string;
  timestamp: string;
  type: 'BUY' | 'SELL' | 'SIP' | 'DEPOSIT';
  orderType: string;
  symbol: string;
  name?: string;
  shares: number;
  fillPrice: number;
  total: number;
  cashAfter: number;
  status: 'FILLED' | 'SETTLED' | 'PENDING' | 'REJECTED';
  notes?: string;
  isReplay?: boolean;
}

interface Holding {
  symbol: string;
  name: string;
  shares: number;
  avgPrice: number;
  currentPrice: number;
}

interface TestState {
  virtualCash: number;
  holdings: Holding[];
  ledger: LedgerEntry[];
  accountRefreshed: boolean;
  notifications: Array<{ title: string; message: string }>;
}

function createOrderEngine(
  initialState: { virtualCash?: number; holdings?: Holding[]; ledger?: LedgerEntry[] } = {},
  options: {
    isAuthenticated?: boolean;
    submitOrderMock?: (payload: OrderPayload, key: string) => Promise<any>;
    getOrdersMock?: () => Promise<{ orders: any[]; total: number }>;
  } = {}
) {
  const state: TestState = {
    virtualCash: initialState.virtualCash ?? 100000,
    holdings: initialState.holdings ? [...initialState.holdings] : [],
    ledger: initialState.ledger ? [...initialState.ledger] : [],
    accountRefreshed: false,
    notifications: [],
  };

  const isAuthenticated = options.isAuthenticated ?? true;

  const updateVirtualCash = (val: number) => {
    state.virtualCash = val;
  };

  const refreshAccount = async () => {
    state.accountRefreshed = true;
  };

  const addNotification = (title: string, message: string) => {
    state.notifications.push({ title, message });
  };

  const executeOrder = async (
    symbol: string,
    type: 'BUY' | 'SELL' | 'SIP',
    shares: number,
    orderType: 'MARKET' | 'LIMIT' = 'MARKET',
    customPrice?: number,
    isReplay?: boolean,
    replayDate?: string
  ): Promise<{ success: boolean; receipt?: LedgerEntry; error?: string }> => {
    const side = type === 'BUY' || type === 'SIP' ? 'BUY' : 'SELL';
    const idempotencyKey = `web-test-key-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

    // Replay mode isolation
    if (isReplay && customPrice !== undefined && customPrice > 0) {
      const fill = customPrice;
      const gross = fill * shares;
      if (side === 'BUY' && gross > state.virtualCash) {
        return {
          success: false,
          error: `Insufficient virtual cash balance for replay trade.`,
        };
      }
      const cashAfter = side === 'BUY' ? Math.max(0, state.virtualCash - gross) : state.virtualCash + gross;
      updateVirtualCash(cashAfter);

      const receipt: LedgerEntry = {
        id: `ord-rep-test`,
        timestamp: new Date().toISOString(),
        type: side,
        orderType,
        symbol,
        name: symbol,
        shares,
        fillPrice: fill,
        total: gross,
        cashAfter,
        status: 'FILLED',
        notes: `[REPLAY - ${replayDate || 'Past NSE'}] Executed via Trade Time Machine`,
        isReplay: true,
      };
      state.ledger.unshift(receipt);
      addNotification('Replay Order Executed', `[REPLAY] ${side} ${shares} shares of ${symbol}`);
      return { success: true, receipt };
    }

    if (isAuthenticated) {
      try {
        if (!options.submitOrderMock) {
          throw new Error('submitOrderMock not configured');
        }
        const res = await options.submitOrderMock(
          {
            symbol,
            side,
            order_type: orderType,
            quantity: shares,
            limit_price: customPrice,
          },
          idempotencyKey
        );

        if (res.status === 'FILLED') {
          const fill = Number(res.fill_price) || 0;
          const gross = Number(res.gross_value) || fill * shares;
          const cashAfter = Number(res.cash_balance_after);
          if (!isNaN(cashAfter) && res.cash_balance_after !== undefined) {
            updateVirtualCash(cashAfter);
          }

          const receipt: LedgerEntry = {
            id: res.order_id,
            timestamp: new Date().toISOString(),
            type: side,
            orderType,
            symbol: res.symbol,
            name: res.symbol,
            shares: Number(res.quantity) || shares,
            fillPrice: fill,
            total: gross,
            cashAfter: !isNaN(cashAfter) ? cashAfter : state.virtualCash,
            status: 'FILLED',
            notes: `Executed via FinEx Paper Matching Engine at ₹${fill}`,
          };

          await refreshAccount();
          addNotification('Order Executed', `${side} ${shares} ${symbol}`);
          return { success: true, receipt };
        } else if (res.status === 'ACCEPTED' || res.status === 'PENDING') {
          const receipt: LedgerEntry = {
            id: res.order_id,
            timestamp: new Date().toISOString(),
            type: side,
            orderType,
            symbol: res.symbol,
            name: res.symbol,
            shares: Number(res.quantity) || shares,
            fillPrice: 0,
            total: (customPrice || 0) * (Number(res.quantity) || shares),
            cashAfter: state.virtualCash,
            status: 'PENDING',
            notes: `Order placed and pending fill in FinEx Order Book. Limit: ₹${customPrice || 0}`,
          };
          state.ledger.unshift(receipt);
          await refreshAccount();
          addNotification('Order Placed (Pending)', `Order pending fill`);
          return { success: true, receipt };
        } else {
          const rejectionReason = res.rejection_reason || res.error || `Order ${res.status}: Order could not be filled.`;
          return {
            success: false,
            error: rejectionReason,
          };
        }
      } catch (err: any) {
        const isNetworkOrTimeout =
          err?.code === 'TIMEOUT' ||
          err?.code === 'NETWORK_ERROR' ||
          err?.status === 408 ||
          err?.status === 0 ||
          err?.name === 'TypeError' ||
          err?.message?.includes('fetch') ||
          err?.message?.includes('timeout') ||
          err?.message?.includes('NetworkError');

        if (isNetworkOrTimeout) {
          try {
            await refreshAccount();
            if (options.getOrdersMock) {
              const orderList = await options.getOrdersMock();
              const matchedOrder = orderList?.orders?.find((o: any) => o.idempotency_key === idempotencyKey);
              if (matchedOrder) {
                if (matchedOrder.status === 'FILLED') {
                  const fill = Number(matchedOrder.fill_price) || 0;
                  const gross = Number(matchedOrder.gross_value) || fill * shares;
                  const cashAfter = Number(matchedOrder.cash_balance_after);
                  if (!isNaN(cashAfter)) {
                    updateVirtualCash(cashAfter);
                  }
                  const receipt: LedgerEntry = {
                    id: matchedOrder.id,
                    timestamp: new Date().toISOString(),
                    type: side,
                    orderType,
                    symbol: matchedOrder.symbol,
                    shares: Number(matchedOrder.quantity) || shares,
                    fillPrice: fill,
                    total: gross,
                    cashAfter: !isNaN(cashAfter) ? cashAfter : state.virtualCash,
                    status: 'FILLED',
                    notes: `Reconciled order via FinEx Paper Matching Engine at ₹${fill}`,
                  };
                  state.ledger.unshift(receipt);
                  return { success: true, receipt };
                } else if (matchedOrder.status === 'ACCEPTED' || matchedOrder.status === 'PENDING') {
                  const receipt: LedgerEntry = {
                    id: matchedOrder.id,
                    timestamp: new Date().toISOString(),
                    type: side,
                    orderType,
                    symbol: matchedOrder.symbol,
                    shares: Number(matchedOrder.quantity) || shares,
                    fillPrice: 0,
                    total: (customPrice || 0) * (Number(matchedOrder.quantity) || shares),
                    cashAfter: state.virtualCash,
                    status: 'PENDING',
                    notes: 'Reconciled pending order in FinEx Order Book.',
                  };
                  state.ledger.unshift(receipt);
                  return { success: true, receipt };
                }
              }
            }
          } catch (reconcileErr) {
            // Reconcile error handled gracefully
          }

          return {
            success: false,
            error:
              'Order status uncertain due to network timeout. FinEx is reconciling your account. Please check your order activity before retrying to prevent duplicate trades.',
          };
        }

        return {
          success: false,
          error: err?.message || 'Order failed on the server.',
        };
      }
    }

    // Unauthenticated demo sandbox mode
    const fill = customPrice || 1000;
    const gross = fill * shares;
    if (side === 'BUY' && gross > state.virtualCash) {
      return {
        success: false,
        error: `Insufficient virtual cash balance for trade.`,
      };
    }
    const cashAfter = side === 'BUY' ? Math.max(0, state.virtualCash - gross) : state.virtualCash + gross;
    updateVirtualCash(cashAfter);

    const receipt: LedgerEntry = {
      id: `ord-demo-test`,
      timestamp: new Date().toISOString(),
      type: side,
      orderType,
      symbol,
      shares,
      fillPrice: fill,
      total: gross,
      cashAfter,
      status: 'FILLED',
      notes: `[DEMO - Unauthenticated Sandbox] Simulated locally at ₹${fill}. Log in for persistent paper trading.`,
    };
    state.ledger.unshift(receipt);
    addNotification('Demo Order Executed', `[Demo] ${side} ${shares} ${symbol}`);
    return { success: true, receipt };
  };

  return { state, executeOrder };
}

describe('Frontend Paper-Order Execution Verification Suite', () => {
  it('1. Backend rejection does NOT mutate cash, holdings, or create fake filled receipt', async () => {
    const { state, executeOrder } = createOrderEngine(
      { virtualCash: 100000, holdings: [{ symbol: 'RELIANCE', name: 'Reliance', shares: 10, avgPrice: 2400, currentPrice: 2450 }] },
      {
        isAuthenticated: true,
        submitOrderMock: async () => ({
          status: 'REJECTED',
          rejection_reason: 'Risk limit exceeded: maximum allocation 25% of virtual cash portfolio',
        }),
      }
    );

    const res = await executeOrder('TCS', 'BUY', 50, 'MARKET');

    assert.equal(res.success, false);
    assert.match(res.error || '', /Risk limit exceeded/);
    assert.equal(state.virtualCash, 100000, 'Cash balance must not be modified on rejection');
    assert.equal(state.holdings.length, 1, 'Holdings must not change on rejection');
    assert.equal(state.ledger.length, 0, 'No fake filled receipt should be added to ledger');
  });

  it('2. Backend HTTP 500 error does NOT mutate cash, holdings, or create local fill receipt', async () => {
    const { state, executeOrder } = createOrderEngine(
      { virtualCash: 85000 },
      {
        isAuthenticated: true,
        submitOrderMock: async () => {
          const err: any = new Error('HTTP 500: Internal Server Error');
          err.status = 500;
          throw err;
        },
      }
    );

    const res = await executeOrder('INFY', 'BUY', 20, 'MARKET');

    assert.equal(res.success, false);
    assert.match(res.error || '', /HTTP 500/);
    assert.equal(state.virtualCash, 85000, 'Virtual cash must remain intact');
    assert.equal(state.ledger.length, 0, 'Ledger must not record a fake order receipt');
  });

  it('3. Network timeout treats outcome as uncertain and instructs user to check order activity before retry', async () => {
    const { state, executeOrder } = createOrderEngine(
      { virtualCash: 50000 },
      {
        isAuthenticated: true,
        submitOrderMock: async () => {
          const err: any = new Error('Request timed out while connecting to FinEx server.');
          err.code = 'TIMEOUT';
          err.status = 408;
          throw err;
        },
        getOrdersMock: async () => ({ orders: [], total: 0 }), // Order not found in backend history yet
      }
    );

    const res = await executeOrder('HDFCBANK', 'BUY', 10, 'MARKET');

    assert.equal(res.success, false);
    assert.match(res.error || '', /Order status uncertain due to network timeout/);
    assert.match(res.error || '', /Please check your order activity before retrying/);
    assert.equal(state.virtualCash, 50000, 'Cash must not be prematurely deducted');
    assert.equal(state.ledger.length, 0, 'No premature filled receipt should exist');
  });

  it('4. Successful order reconciled during timeout is adopted without duplicate receipts', async () => {
    let capturedKey = '';
    const { state, executeOrder } = createOrderEngine(
      { virtualCash: 100000 },
      {
        isAuthenticated: true,
        submitOrderMock: async (_payload, key) => {
          capturedKey = key;
          const err: any = new Error('Network error connecting to FinEx server.');
          err.code = 'NETWORK_ERROR';
          err.status = 0;
          throw err;
        },
        getOrdersMock: async () => ({
          orders: [
            {
              id: 'ord-server-reconciled-99',
              symbol: 'WIPRO',
              quantity: 25,
              fill_price: 450.0,
              gross_value: 11250.0,
              cash_balance_after: 88750.0,
              status: 'FILLED',
              idempotency_key: capturedKey,
            },
          ],
          total: 1,
        }),
      }
    );

    const res = await executeOrder('WIPRO', 'BUY', 25, 'MARKET');

    assert.equal(res.success, true);
    assert.ok(res.receipt);
    assert.equal(res.receipt.status, 'FILLED');
    assert.equal(res.receipt.fillPrice, 450.0);
    assert.equal(res.receipt.id, 'ord-server-reconciled-99');
    assert.equal(state.virtualCash, 88750.0, 'Cash balance updated from server cash_balance_after');
    assert.equal(state.ledger.length, 1, 'Only one reconciled receipt should be recorded');
  });

  it('5. ACCEPTED / PENDING limit order creates pending receipt without cash deduction or fill price', async () => {
    const { state, executeOrder } = createOrderEngine(
      { virtualCash: 100000 },
      {
        isAuthenticated: true,
        submitOrderMock: async () => ({
          order_id: 'ord-limit-pending-01',
          symbol: 'RELIANCE',
          side: 'BUY',
          quantity: 10,
          limit_price: 2350.0,
          status: 'PENDING',
        }),
      }
    );

    const res = await executeOrder('RELIANCE', 'BUY', 10, 'LIMIT', 2350.0);

    assert.equal(res.success, true);
    assert.ok(res.receipt);
    assert.equal(res.receipt.status, 'PENDING');
    assert.equal(res.receipt.fillPrice, 0, 'Pending order must have fillPrice = 0');
    assert.equal(state.virtualCash, 100000, 'Cash must NOT be deducted while order is pending');
    assert.equal(state.ledger.length, 1);
    assert.equal(state.ledger[0].status, 'PENDING');
  });

  it('6. FILLED order synchronizes cash balance and triggers backend account refresh', async () => {
    const { state, executeOrder } = createOrderEngine(
      { virtualCash: 100000 },
      {
        isAuthenticated: true,
        submitOrderMock: async () => ({
          order_id: 'ord-filled-101',
          symbol: 'TCS',
          side: 'BUY',
          quantity: 5,
          fill_price: 3400.0,
          gross_value: 17000.0,
          cash_balance_after: 83000.0,
          status: 'FILLED',
        }),
      }
    );

    const res = await executeOrder('TCS', 'BUY', 5, 'MARKET');

    assert.equal(res.success, true);
    assert.ok(res.receipt);
    assert.equal(res.receipt.status, 'FILLED');
    assert.equal(res.receipt.fillPrice, 3400.0);
    assert.equal(state.virtualCash, 83000.0);
    assert.equal(state.accountRefreshed, true, 'Backend refreshAccount must be called');
  });

  it('7. Replay trading remains segregated with [REPLAY] notes and notifications', async () => {
    const { state, executeOrder } = createOrderEngine(
      { virtualCash: 50000 },
      { isAuthenticated: true }
    );

    const res = await executeOrder('RELIANCE', 'BUY', 10, 'LIMIT', 2200.0, true, '2024-03-15');

    assert.equal(res.success, true);
    assert.ok(res.receipt);
    assert.equal(res.receipt.isReplay, true);
    assert.match(res.receipt.notes || '', /\[REPLAY - 2024-03-15\]/);
    assert.equal(state.notifications[0].title, 'Replay Order Executed');
    assert.match(state.notifications[0].message, /\[REPLAY\]/);
  });

  it('8. Unauthenticated demo sandbox mode explicitly labels simulated trades with [DEMO]', async () => {
    const { state, executeOrder } = createOrderEngine(
      { virtualCash: 100000 },
      { isAuthenticated: false }
    );

    const res = await executeOrder('INFY', 'BUY', 10, 'MARKET', 1500.0);

    assert.equal(res.success, true);
    assert.ok(res.receipt);
    assert.match(res.receipt.notes || '', /\[DEMO - Unauthenticated Sandbox\]/);
    assert.equal(state.notifications[0].title, 'Demo Order Executed');
    assert.match(state.notifications[0].message, /\[Demo\]/);
  });
});

