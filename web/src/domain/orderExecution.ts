import type { HoldingItem, LedgerEntry, OrderExecutionType } from '../context/FinancialContext.ts';

export interface OrderExecutionParams {
  symbol: string;
  type: 'BUY' | 'SELL' | 'SIP';
  shares: number;
  orderType?: OrderExecutionType;
  customPrice?: number;
  isReplay?: boolean;
  replayDate?: string;
  idempotencyKey?: string;
}

export interface OrderExecutionResult {
  success: boolean;
  receipt?: LedgerEntry;
  error?: string;
}

export interface OrderExecutionContext {
  virtualCash: number;
  updateVirtualCash: (cash: number) => void;
  getHoldings: () => HoldingItem[];
  setHoldings: (updater: (prev: HoldingItem[]) => HoldingItem[]) => void;
  setLedger: (updater: (prev: LedgerEntry[]) => LedgerEntry[]) => void;
  addNotification?: (title: string, message: string, type: 'price' | 'allocation' | 'goal' | 'execution') => void;
  refreshAccount: () => Promise<void>;
  apiClient: {
    isAuthenticated: () => boolean;
    paperTrading: {
      submitOrder: (
        order: { symbol: string; side: 'BUY' | 'SELL'; order_type: OrderExecutionType; quantity: number; limit_price?: number },
        idempotencyKey?: string
      ) => Promise<any>;
      getOrders: (limit?: number) => Promise<{ orders: any[]; total: number }>;
    };
  };
  getQuotePrice?: (symbol: string) => number | undefined;
}

export const INSTRUMENT_METADATA: Record<string, { name: string; sector: string; color: string }> = {
  RELIANCE: { name: 'Reliance Industries Ltd', sector: 'Energy & Retail', color: '#F29A60' },
  TCS: { name: 'Tata Consultancy Services', sector: 'Technology', color: '#4DD5AD' },
  INFY: { name: 'Infosys Limited', sector: 'Technology', color: '#E0854B' },
  HDFCBANK: { name: 'HDFC Bank Limited', sector: 'Banking & Financials', color: '#A1A1AA' },
  ICICIBANK: { name: 'ICICI Bank Limited', sector: 'Banking & Financials', color: '#8E8E93' },
  TATAMOTORS: { name: 'Tata Motors Limited', sector: 'Automobile', color: '#60A5FA' },
  SBIN: { name: 'State Bank of India', sector: 'Banking & Financials', color: '#34D399' },
  ITC: { name: 'ITC Limited', sector: 'Consumer Goods', color: '#FBBF24' },
};

export function generateIdempotencyKey(): string {
  return `web-ord-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

export function isNetworkOrTimeoutError(err: any): boolean {
  return (
    err?.code === 'TIMEOUT' ||
    err?.code === 'NETWORK_ERROR' ||
    err?.status === 408 ||
    err?.status === 0 ||
    err?.name === 'TypeError' ||
    Boolean(err?.message?.includes('fetch')) ||
    Boolean(err?.message?.includes('timeout')) ||
    Boolean(err?.message?.includes('NetworkError'))
  );
}

export function calculateNewHoldings(
  prev: HoldingItem[],
  symbol: string,
  side: 'BUY' | 'SELL',
  shares: number,
  fill: number,
  gross: number
): HoldingItem[] {
  const existing = prev.find((h) => h.symbol === symbol);
  if (side === 'BUY') {
    if (existing) {
      const totalShares = existing.shares + shares;
      const avgCost = (existing.shares * existing.avgPrice + gross) / totalShares;
      return prev.map((h) => (h.symbol === symbol ? { ...h, shares: totalShares, avgPrice: avgCost } : h));
    } else {
      const meta = INSTRUMENT_METADATA[symbol] || { name: symbol, sector: 'Equities', color: '#F29A60' };
      return [
        ...prev,
        {
          symbol,
          name: meta.name,
          shares,
          avgPrice: fill,
          currentPrice: fill,
          dayChangePct: 0,
          assetClass: meta.sector,
          color: meta.color,
        },
      ];
    }
  } else {
    if (!existing) return prev;
    if (existing.shares <= shares) return prev.filter((h) => h.symbol !== symbol);
    return prev.map((h) => (h.symbol === symbol ? { ...h, shares: h.shares - shares } : h));
  }
}

/**
 * Authoritative Paper Order Execution Engine.
 * Executed in production by FinancialContext.tsx and tested by order_flow.test.ts.
 */
export async function processOrderExecution(
  params: OrderExecutionParams,
  context: OrderExecutionContext
): Promise<OrderExecutionResult> {
  const {
    symbol,
    type,
    shares,
    orderType = 'MARKET',
    customPrice,
    isReplay,
    replayDate,
  } = params;

  const side: 'BUY' | 'SELL' = type === 'BUY' || type === 'SIP' ? 'BUY' : 'SELL';
  const idempotencyKey = params.idempotencyKey || generateIdempotencyKey();

  // 1. Historical Replay Execution (Time Machine)
  if (isReplay && customPrice !== undefined && customPrice > 0) {
    const fill = customPrice;
    const gross = fill * shares;
    if (side === 'BUY' && gross > context.virtualCash) {
      return {
        success: false,
        error: `Insufficient virtual cash balance (₹${context.virtualCash.toLocaleString('en-IN')}) for replay trade of ₹${gross.toLocaleString('en-IN')}.`,
      };
    }
    const cashAfter = side === 'BUY' ? Math.max(0, context.virtualCash - gross) : context.virtualCash + gross;
    context.updateVirtualCash(cashAfter);

    context.setHoldings((prev) => calculateNewHoldings(prev, symbol, side, shares, fill, gross));

    const existingHolding = context.getHoldings().find((h) => h.symbol === symbol);
    const replayRealizedPnL =
      side === 'SELL' && existingHolding
        ? (fill - existingHolding.avgPrice) * shares
        : undefined;

    const receipt: LedgerEntry = {
      id: `ord-rep-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      timestamp: new Date().toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'medium' }),
      type: side,
      orderType,
      symbol,
      name: INSTRUMENT_METADATA[symbol]?.name || symbol,
      shares,
      fillPrice: fill,
      total: gross,
      realizedPnL: replayRealizedPnL,
      brokerageFee: 0,
      regulatoryFees: 0,
      cashAfter,
      status: 'FILLED',
      notes: `[REPLAY - ${replayDate || 'Past NSE'}] Executed via Trade Time Machine at ₹${fill.toLocaleString('en-IN')}`,
      isReplay: true,
      replayDate: replayDate || 'Past NSE',
    };

    context.setLedger((prev) => [receipt, ...prev]);

    context.addNotification?.(
      'Replay Order Executed',
      `[REPLAY] ${side === 'BUY' ? 'Bought' : 'Sold'} ${shares} shares of ${symbol} at ₹${fill.toLocaleString('en-IN')} (${replayDate || 'Past NSE'})`,
      'execution'
    );

    return { success: true, receipt };
  }

  // 2. Authenticated Paper Trading (Authoritative PostgreSQL Backend)
  if (context.apiClient.isAuthenticated()) {
    try {
      const res = await context.apiClient.paperTrading.submitOrder(
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
        const gross = Number(res.gross_value) || (fill * shares);
        const cashAfter = Number(res.cash_balance_after);
        if (!isNaN(cashAfter) && res.cash_balance_after !== undefined) {
          context.updateVirtualCash(cashAfter);
        }

        const receipt: LedgerEntry = {
          id: res.order_id,
          timestamp: new Date().toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'medium' }),
          type: side,
          orderType,
          symbol: res.symbol,
          name: INSTRUMENT_METADATA[res.symbol]?.name || res.symbol,
          shares: Number(res.quantity) || shares,
          fillPrice: fill,
          total: gross,
          brokerageFee: 0,
          regulatoryFees: 0,
          cashAfter: !isNaN(cashAfter) ? cashAfter : context.virtualCash,
          status: 'FILLED',
          notes: `Executed via FinEx Paper Matching Engine at ₹${fill.toLocaleString('en-IN')}`,
        };

        await context.refreshAccount();

        context.addNotification?.(
          'Order Executed',
          `${side === 'BUY' ? 'Bought' : 'Sold'} ${shares} shares of ${symbol} at ₹${fill.toLocaleString('en-IN')}`,
          'execution'
        );
        return { success: true, receipt };
      } else if (res.status === 'ACCEPTED' || res.status === 'PENDING') {
        // Order accepted by matching engine (e.g. limit order awaiting fill price).
        // Do NOT mutate cash or holdings until fill confirmation is received.
        const receipt: LedgerEntry = {
          id: res.order_id,
          timestamp: new Date().toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'medium' }),
          type: side,
          orderType,
          symbol: res.symbol,
          name: INSTRUMENT_METADATA[res.symbol]?.name || res.symbol,
          shares: Number(res.quantity) || shares,
          fillPrice: 0,
          total: (customPrice || 0) * (Number(res.quantity) || shares),
          brokerageFee: 0,
          regulatoryFees: 0,
          cashAfter: context.virtualCash,
          status: 'PENDING',
          notes: `Order placed and pending fill in FinEx Order Book. Limit: ₹${Number(customPrice || 0).toLocaleString('en-IN')}`,
        };

        context.setLedger((prev) => [receipt, ...prev]);
        await context.refreshAccount();

        context.addNotification?.(
          'Order Placed (Pending)',
          `${side === 'BUY' ? 'Buy' : 'Sell'} order for ${shares} shares of ${symbol} placed (Pending execution).`,
          'execution'
        );
        return { success: true, receipt };
      } else {
        // Server rejected the order (e.g. risk check, insufficient balance, stale quote)
        const rejectionReason = (res as any).rejection_reason || (res as any).error || `Order ${res.status}: Order could not be filled.`;
        return {
          success: false,
          error: rejectionReason,
        };
      }
    } catch (err: any) {
      if (isNetworkOrTimeoutError(err)) {
        // Attempt account and order reconciliation before reporting outcome to avoid duplicate retries
        try {
          await context.refreshAccount();
          const orderList = await context.apiClient.paperTrading.getOrders(10);
          const matchedOrder = orderList?.orders?.find((o: any) => o.idempotency_key === idempotencyKey);
          if (matchedOrder) {
            if (matchedOrder.status === 'FILLED') {
              const fill = Number(matchedOrder.fill_price) || 0;
              const gross = Number(matchedOrder.gross_value) || (fill * shares);
              const cashAfter = Number(matchedOrder.cash_balance_after);
              if (!isNaN(cashAfter)) {
                context.updateVirtualCash(cashAfter);
              }
              const receipt: LedgerEntry = {
                id: matchedOrder.id,
                timestamp: new Date().toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'medium' }),
                type: side,
                orderType,
                symbol: matchedOrder.symbol,
                name: INSTRUMENT_METADATA[matchedOrder.symbol]?.name || matchedOrder.symbol,
                shares: Number(matchedOrder.quantity) || shares,
                fillPrice: fill,
                total: gross,
                brokerageFee: 0,
                regulatoryFees: 0,
                cashAfter: !isNaN(cashAfter) ? cashAfter : context.virtualCash,
                status: 'FILLED',
                notes: `Reconciled order via FinEx Paper Matching Engine at ₹${fill.toLocaleString('en-IN')}`,
              };
              context.setLedger((prev) => [receipt, ...prev]);
              return { success: true, receipt };
            } else if (matchedOrder.status === 'ACCEPTED' || matchedOrder.status === 'PENDING') {
              const receipt: LedgerEntry = {
                id: matchedOrder.id,
                timestamp: new Date().toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'medium' }),
                type: side,
                orderType,
                symbol: matchedOrder.symbol,
                name: INSTRUMENT_METADATA[matchedOrder.symbol]?.name || matchedOrder.symbol,
                shares: Number(matchedOrder.quantity) || shares,
                fillPrice: 0,
                total: (customPrice || 0) * (Number(matchedOrder.quantity) || shares),
                brokerageFee: 0,
                regulatoryFees: 0,
                cashAfter: context.virtualCash,
                status: 'PENDING',
                notes: 'Reconciled pending order in FinEx Order Book.',
              };
              context.setLedger((prev) => [receipt, ...prev]);
              return { success: true, receipt };
            }
          }
        } catch (reconcileErr) {
          console.warn('Order reconciliation attempt encountered an error:', reconcileErr);
        }

        return {
          success: false,
          error: 'Order status uncertain due to network timeout. FinEx is reconciling your account. Please check your order activity before retrying to prevent duplicate trades.',
        };
      }

      // Backend HTTP error (e.g. 400 Bad Request, 422 Unprocessable Entity, 500 Internal Server Error)
      return {
        success: false,
        error: err?.message || 'Order failed on the server.',
      };
    }
  }

  // 3. Local Fallback Exclusively for Unauthenticated Preview/Demo Sandboxes
  const currentPrice = context.getQuotePrice?.(symbol) || 1000;
  const fill = customPrice || currentPrice;
  const gross = fill * shares;
  if (side === 'BUY' && gross > context.virtualCash) {
    return {
      success: false,
      error: `Insufficient virtual cash balance (₹${context.virtualCash.toLocaleString('en-IN')}) for trade of ₹${gross.toLocaleString('en-IN')}.`,
    };
  }
  const cashAfter = side === 'BUY' ? Math.max(0, context.virtualCash - gross) : context.virtualCash + gross;
  context.updateVirtualCash(cashAfter);

  context.setHoldings((prev) => calculateNewHoldings(prev, symbol, side, shares, fill, gross));

  const existingHolding = context.getHoldings().find((h) => h.symbol === symbol);
  const fallbackRealizedPnL =
    side === 'SELL' && existingHolding
      ? (fill - existingHolding.avgPrice) * shares
      : undefined;

  const receipt: LedgerEntry = {
    id: `ord-demo-${Date.now()}`,
    timestamp: new Date().toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'medium' }),
    type: side,
    orderType,
    symbol,
    name: INSTRUMENT_METADATA[symbol]?.name || symbol,
    shares,
    fillPrice: fill,
    total: gross,
    realizedPnL: fallbackRealizedPnL,
    brokerageFee: 0,
    regulatoryFees: 0,
    cashAfter,
    status: 'FILLED',
    notes: `[DEMO - Unauthenticated Sandbox] Simulated locally at ₹${fill.toLocaleString('en-IN')}. Log in for persistent paper trading.`,
  };

  context.setLedger((prev) => [receipt, ...prev]);

  context.addNotification?.(
    'Demo Order Executed',
    `[Demo] ${side === 'BUY' ? 'Bought' : 'Sold'} ${shares} shares of ${symbol} at ₹${fill.toLocaleString('en-IN')}`,
    'execution'
  );
  return { success: true, receipt };
}
