import React, { createContext, useContext, useState, useEffect, useRef, ReactNode, useCallback } from 'react';
import { apiClient } from '../api/client';

export interface HoldingItem {
  symbol: string;
  name: string;
  shares: number;
  avgPrice: number;
  currentPrice: number;
  dayChangePct: number;
  assetClass: string;
  color: string;
}

export type OrderExecutionType = 'MARKET' | 'LIMIT' | 'STOP_LOSS' | 'SIP';

export interface LedgerEntry {
  id: string;
  timestamp: string;
  type: 'BUY' | 'SELL' | 'SIP' | 'DEPOSIT';
  orderType: OrderExecutionType;
  symbol: string;
  name?: string;
  shares: number;
  fillPrice: number;
  total: number;
  realizedPnL?: number;
  brokerageFee: number;
  regulatoryFees: number;
  cashAfter: number;
  status: 'FILLED' | 'SETTLED' | 'PENDING' | 'REJECTED';
  notes?: string;
}

export interface AlertNotification {
  id: string;
  time: string;
  title: string;
  message: string;
  type: 'price' | 'allocation' | 'goal' | 'execution';
  read: boolean;
}

export interface SpendingItem {
  id: string;
  date: string;
  merchant: string;
  category: string;
  amount: number;
  isMasked: boolean;
}

export interface MarketQuote {
  symbol: string;
  name: string;
  price: number;
  changeVal: number;
  changePct: number;
  isPositive: boolean;
  high: number;
  low: number;
  volume: string;
  source?: string;
  observedAt?: string;
  isDelayed?: boolean;
  isStale?: boolean;
  lastTick?: 'up' | 'down' | 'none';
}

interface FinancialContextType {
  virtualCash: number;
  holdings: HoldingItem[];
  ledger: LedgerEntry[];
  notifications: AlertNotification[];
  spendingItems: SpendingItem[];
  marketQuotes: Record<string, MarketQuote>;
  isAccountLoading: boolean;
  accountError: string | null;
  totalHoldingsValue: number;
  totalPortfolioValue: number;
  unrealizedPnL: number;
  totalRealizedPnL: number;
  totalTradesCount: number;
  totalTradedVolume: number;
  isQuickTradeOpen: boolean;
  quickTradeSymbol: string;
  openQuickTrade: (symbol?: string) => void;
  closeQuickTrade: () => void;
  executeOrder: (
    symbol: string,
    type: 'BUY' | 'SELL' | 'SIP',
    shares: number,
    orderType?: OrderExecutionType,
    customPrice?: number
  ) => Promise<{ success: boolean; receipt?: LedgerEntry; error?: string }>;
  depositFunds: (amount: number) => Promise<void>;
  resetAccount: () => Promise<void>;
  addSpendingItem: (merchant: string, category: string, amount: number) => Promise<void>;
  markAllNotificationsRead: () => Promise<void>;
  addNotification: (title: string, message: string, type: AlertNotification['type']) => void;
  refreshAccount: () => Promise<void>;
  refreshMarketData: () => Promise<void>;
  clearPrivateState: () => void;
}

const FinancialContext = createContext<FinancialContextType | undefined>(undefined);

// Sector and color taxonomy for UI presentation
const INSTRUMENT_METADATA: Record<string, { name: string; sector: string; color: string }> = {
  RELIANCE: { name: 'Reliance Industries Ltd', sector: 'Energy & Retail', color: '#F29A60' },
  TCS: { name: 'Tata Consultancy Services', sector: 'Technology', color: '#4DD5AD' },
  INFY: { name: 'Infosys Limited', sector: 'Technology', color: '#E0854B' },
  HDFCBANK: { name: 'HDFC Bank Limited', sector: 'Banking & Financials', color: '#A1A1AA' },
  ICICIBANK: { name: 'ICICI Bank Limited', sector: 'Banking & Financials', color: '#8E8E93' },
  TATAMOTORS: { name: 'Tata Motors Limited', sector: 'Automobile', color: '#60A5FA' },
  SBIN: { name: 'State Bank of India', sector: 'Banking & Financials', color: '#34D399' },
  ITC: { name: 'ITC Limited', sector: 'Consumer Goods', color: '#FBBF24' },
};

export const FinancialProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [virtualCash, setVirtualCash] = useState<number>(0);
  const [holdings, setHoldings] = useState<HoldingItem[]>([]);
  const [ledger, setLedger] = useState<LedgerEntry[]>([]);
  const [notifications, setNotifications] = useState<AlertNotification[]>([]);
  const [spendingItems, setSpendingItems] = useState<SpendingItem[]>([]);
  const [isAccountLoading, setIsAccountLoading] = useState<boolean>(apiClient.isAuthenticated());
  const [accountError, setAccountError] = useState<string | null>(null);

  const sessionGenerationRef = useRef<number>(0);

  // Sourced Market Quotes from verified backend
  const [marketQuotes, setMarketQuotes] = useState<Record<string, MarketQuote>>({});

  const marketQuotesRef = useRef(marketQuotes);
  useEffect(() => {
    marketQuotesRef.current = marketQuotes;
  }, [marketQuotes]);

  // Global Quick Trade Drawer State
  const [isQuickTradeOpen, setIsQuickTradeOpen] = useState(false);
  const [quickTradeSymbol, setQuickTradeSymbol] = useState('RELIANCE');

  const openQuickTrade = (symbol?: string) => {
    if (symbol) setQuickTradeSymbol(symbol);
    setIsQuickTradeOpen(true);
  };

  const closeQuickTrade = () => {
    setIsQuickTradeOpen(false);
  };

  // Clear private client state on logout or session expiration
  const clearPrivateState = useCallback(() => {
    sessionGenerationRef.current += 1;
    setVirtualCash(0);
    setHoldings([]);
    setLedger([]);
    setNotifications([]);
    setSpendingItems([]);
    setAccountError(null);
    setIsAccountLoading(false);
  }, []);

  // --- Real Backend Synchronization with Session Generation Guard ---
  // Decoupled from market quotes to prevent infinite request loops
  const refreshAccount = useCallback(async () => {
    if (!apiClient.isAuthenticated()) {
      clearPrivateState();
      return;
    }
    const thisGen = ++sessionGenerationRef.current;
    setIsAccountLoading(true);
    setAccountError(null);
    try {
      const acct = await apiClient.paperTrading.getAccount();
      if (thisGen !== sessionGenerationRef.current) return;
      if (acct) {
        // Normalize cash_balance and current_cash defensively
        const rawCash = acct.cash_balance ?? acct.current_cash ?? 0;
        const normalizedCash = Number(rawCash);
        setVirtualCash(Number.isFinite(normalizedCash) ? normalizedCash : 0);

        if (acct.positions && Array.isArray(acct.positions)) {
          const mappedHoldings: HoldingItem[] = acct.positions.map((p) => {
            const meta = INSTRUMENT_METADATA[p.symbol] || {
              name: p.symbol,
              sector: 'Equities',
              color: '#F29A60',
            };
            const currentQuote = marketQuotesRef.current[p.symbol];
            const livePrice = currentQuote && Number.isFinite(Number(currentQuote.price))
              ? Number(currentQuote.price)
              : (Number.isFinite(Number(p.current_price)) ? Number(p.current_price) : 0);
            const dayPct = currentQuote && Number.isFinite(Number(currentQuote.changePct))
              ? Number(currentQuote.changePct)
              : 0.0;
            const avgCost = Number(p.average_buy_price ?? p.avg_cost ?? 0);
            const shares = Number(p.quantity ?? 0);
            return {
              symbol: p.symbol,
              name: meta.name,
              shares: Number.isFinite(shares) ? shares : 0,
              avgPrice: Number.isFinite(avgCost) ? avgCost : 0,
              currentPrice: Number.isFinite(livePrice) ? livePrice : 0,
              dayChangePct: Number.isFinite(dayPct) ? dayPct : 0,
              assetClass: meta.sector,
              color: meta.color,
            };
          });
          setHoldings(mappedHoldings);
        } else {
          setHoldings([]);
        }
      }

      // Fetch persistent orders / ledger
      const ordersRes = await apiClient.paperTrading.getOrders(50);
      if (thisGen !== sessionGenerationRef.current) return;
      if (ordersRes && ordersRes.orders) {
        const mappedOrders: LedgerEntry[] = ordersRes.orders.map((o) => {
          const fill = Number(o.fill_price) || 0;
          const gross = Number(o.gross_value) || 0;
          const shares = Number(o.quantity) || 0;
          const cashAfter = o.cash_balance_after !== undefined ? Number(o.cash_balance_after) : 0;
          return {
            id: o.id,
            timestamp: new Date(o.created_at).toLocaleString('en-IN', {
              dateStyle: 'medium',
              timeStyle: 'medium',
            }),
            type: (o.side as 'BUY' | 'SELL') || 'BUY',
            orderType: (o.order_type as OrderExecutionType) || 'MARKET',
            symbol: o.symbol,
            name: INSTRUMENT_METADATA[o.symbol]?.name || o.symbol,
            shares,
            fillPrice: fill,
            total: gross,
            brokerageFee: 0,
            regulatoryFees: 0,
            cashAfter,
            status: (o.status as 'FILLED' | 'SETTLED' | 'PENDING' | 'REJECTED') || 'FILLED',
            notes: `Executed via FinEx Paper Matching Engine at ₹${fill.toLocaleString('en-IN')}`,
          };
        });
        setLedger(mappedOrders);
      }

      // Fetch transactions
      const txRes = await apiClient.spending.getTransactions();
      if (thisGen !== sessionGenerationRef.current) return;
      if (txRes && txRes.transactions) {
        const mappedTx: SpendingItem[] = txRes.transactions.map((t) => ({
          id: t.id,
          date: t.transaction_date,
          merchant: t.masked_description,
          category: t.category_id,
          amount: Number(t.amount) || 0,
          isMasked: true,
        }));
        setSpendingItems(mappedTx);
      }

      // Fetch notifications
      const notifRes = await apiClient.alerts.getNotifications();
      if (thisGen !== sessionGenerationRef.current) return;
      if (notifRes && notifRes.notifications) {
        const mappedNotifs: AlertNotification[] = notifRes.notifications.map((n) => ({
          id: n.id,
          time: new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          title: n.title,
          message: n.body,
          type: n.category === 'PRICE_ALERT' ? 'price' : 'allocation',
          read: n.is_read,
        }));
        setNotifications(mappedNotifs);
      }
    } catch (e: any) {
      if (thisGen === sessionGenerationRef.current) {
        if (e?.status === 401) {
          clearPrivateState();
        } else {
          setAccountError(e?.message || 'Failed to sync with server');
        }
      }
    } finally {
      if (thisGen === sessionGenerationRef.current) {
        setIsAccountLoading(false);
      }
    }
  }, [clearPrivateState]);

  // Market quotes fetcher (decoupled from account synchronization)
  const refreshMarketData = useCallback(async () => {
    try {
      const instRes = await apiClient.market.getInstruments();
      if (instRes && instRes.instruments) {
        for (const inst of instRes.instruments) {
          try {
            const q = await apiClient.market.getQuote(inst.symbol);
            if (q) {
              setMarketQuotes((prev) => {
                const existing = prev[inst.symbol] || {
                  symbol: inst.symbol,
                  name: inst.name,
                  price: Number(q.price),
                  changeVal: 0,
                  changePct: 0,
                  isPositive: true,
                  high: Number(q.price),
                  low: Number(q.price),
                  volume: '10.0M',
                };
                return {
                  ...prev,
                  [inst.symbol]: {
                    ...existing,
                    price: Number(q.price),
                    source: q.source,
                    observedAt: q.observed_at,
                    isDelayed: q.is_delayed,
                    isStale: q.is_stale,
                  },
                };
              });
            }
          } catch {
            // quote unavailable for this instrument
          }
        }
      }
    } catch {
      // offline / fallback
    }
  }, []);

  // Mount effects: fetch market data independently
  useEffect(() => {
    refreshMarketData();
  }, [refreshMarketData]);

  // Reactive subscription to auth state changes (login, logout, expiration)
  useEffect(() => {
    const unsubscribe = apiClient.onAuthStateChange((isAuth) => {
      if (isAuth) {
        refreshAccount();
      } else {
        clearPrivateState();
      }
    });
    return unsubscribe;
  }, [refreshAccount, clearPrivateState]);

  // Derived Financial Metrics normalized against NaN
  const totalHoldingsValue = holdings.reduce((sum, h) => {
    const val = (Number(h.shares) || 0) * (Number(h.currentPrice) || 0);
    return sum + (Number.isFinite(val) ? val : 0);
  }, 0);

  const totalCostBasis = holdings.reduce((sum, h) => {
    const val = (Number(h.shares) || 0) * (Number(h.avgPrice) || 0);
    return sum + (Number.isFinite(val) ? val : 0);
  }, 0);

  const unrealizedPnL = Number.isFinite(totalHoldingsValue - totalCostBasis)
    ? totalHoldingsValue - totalCostBasis
    : 0;

  const safeCash = Number.isFinite(Number(virtualCash)) ? Number(virtualCash) : 0;
  const totalPortfolioValue = safeCash + totalHoldingsValue;

  const totalRealizedPnL = ledger
    .filter((l) => l.realizedPnL !== undefined && Number.isFinite(Number(l.realizedPnL)))
    .reduce((sum, l) => sum + (Number(l.realizedPnL) || 0), 0);

  const totalTradesCount = ledger.filter((l) => l.type === 'BUY' || l.type === 'SELL' || l.type === 'SIP').length;
  const totalTradedVolume = ledger
    .filter((l) => l.type === 'BUY' || l.type === 'SELL' || l.type === 'SIP')
    .reduce((sum, l) => sum + (Number(l.total) || 0), 0);

  const addNotification = (title: string, message: string, type: AlertNotification['type']) => {
    const newAlert: AlertNotification = {
      id: `ALT-${Date.now().toString().slice(-4)}`,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      title,
      message,
      type,
      read: false,
    };
    setNotifications((prev) => [newAlert, ...prev]);
  };

  const markAllNotificationsRead = async () => {
    if (!apiClient.isAuthenticated()) return;
    try {
      await apiClient.alerts.markAllRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    } catch {
      // network failure
    }
  };

  const depositFunds = async (amount: number) => {
    if (!apiClient.isAuthenticated()) {
      addNotification('Deposit Failed', 'Authentication required. Please sign in to deposit funds.', 'execution');
      return;
    }
    if (!amount || amount <= 0) {
      addNotification('Invalid Amount', 'Please specify a positive deposit amount.', 'execution');
      return;
    }
    try {
      await apiClient.paperTrading.deposit(amount);
      await refreshAccount();
      addNotification(
        'Funds Deposited',
        `Credited ₹${amount.toLocaleString('en-IN')} virtual cash to your sandbox account`,
        'execution'
      );
    } catch (e: any) {
      addNotification('Deposit Failed', e?.message || 'Failed to deposit virtual funds.', 'execution');
    }
  };

  const resetAccount = async () => {
    if (!apiClient.isAuthenticated()) {
      addNotification('Reset Failed', 'Authentication required. Please sign in to reset account.', 'execution');
      return;
    }
    try {
      await apiClient.paperTrading.resetAccount();
      await refreshAccount();
      addNotification('Account Reset', 'Restored sandbox balance to ₹1,00,000 virtual cash and reset positions', 'execution');
    } catch (e: any) {
      addNotification('Reset Failed', e?.message || 'Failed to reset account', 'execution');
    }
  };

  const addSpendingItem = async (merchant: string, category: string, amount: number) => {
    if (!apiClient.isAuthenticated()) {
      addNotification('Expense Error', 'Authentication required. Please sign in to record spending.', 'execution');
      return;
    }
    try {
      const todayStr = new Date().toISOString().split('T')[0];
      await apiClient.spending.addManual({
        transaction_date: todayStr,
        amount,
        description: merchant,
        transaction_type: 'DEBIT',
        category_id: category,
      });
      await refreshAccount();
      addNotification('Expense Logged', `Recorded ₹${amount.toLocaleString('en-IN')} for ${merchant} (${category})`, 'execution');
    } catch (e: any) {
      addNotification('Expense Failed', e?.message || 'Failed to record transaction on server.', 'execution');
    }
  };

  // Authoritative Order Execution Engine connected directly to FastAPI Paper Trading Engine
  const executeOrder = async (
    symbol: string,
    type: 'BUY' | 'SELL' | 'SIP',
    shares: number,
    orderType: OrderExecutionType = 'MARKET',
    customPrice?: number
  ): Promise<{ success: boolean; receipt?: LedgerEntry; error?: string }> => {
    if (!apiClient.isAuthenticated()) {
      return {
        success: false,
        error: 'Authentication required. Please sign in to execute paper trades.',
      };
    }

    const side = type === 'BUY' || type === 'SIP' ? 'BUY' : 'SELL';
    const idempotencyKey = `web-ord-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

    try {
      const res = await apiClient.paperTrading.submitOrder(
        {
          symbol,
          side,
          order_type: orderType,
          quantity: shares,
          limit_price: customPrice,
        },
        idempotencyKey
      );

      if (res.status === 'FILLED' || res.status === 'ACCEPTED') {
        const fill = Number(res.fill_price) || 0;
        const gross = Number(res.gross_value) || 0;
        const cashAfter = Number(res.cash_balance_after) || 0;
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
          cashAfter,
          status: 'FILLED',
          notes: `Executed via FinEx Paper Matching Engine at ₹${fill.toLocaleString('en-IN')}`,
        };

        await refreshAccount();

        addNotification(
          'Order Executed',
          `${side === 'BUY' ? 'Bought' : 'Sold'} ${shares} shares of ${symbol} at ₹${fill.toLocaleString('en-IN')}`,
          'execution'
        );
        return { success: true, receipt };
      } else {
        return {
          success: false,
          error: `Order ${res.status}: Order could not be filled at the requested price.`,
        };
      }
    } catch (e: any) {
      return {
        success: false,
        error: e?.message || 'Server error occurred during paper order execution.',
      };
    }
  };

  return (
    <FinancialContext.Provider
      value={{
        virtualCash,
        holdings,
        ledger,
        notifications,
        spendingItems,
        marketQuotes,
        isAccountLoading,
        accountError,
        totalHoldingsValue,
        totalPortfolioValue,
        unrealizedPnL,
        totalRealizedPnL,
        totalTradesCount,
        totalTradedVolume,
        isQuickTradeOpen,
        quickTradeSymbol,
        openQuickTrade,
        closeQuickTrade,
        executeOrder,
        depositFunds,
        resetAccount,
        addSpendingItem,
        markAllNotificationsRead,
        addNotification,
        refreshAccount,
        refreshMarketData,
        clearPrivateState,
      }}
    >
      {children}
    </FinancialContext.Provider>
  );
};

export const useFinancial = () => {
  const context = useContext(FinancialContext);
  if (!context) {
    throw new Error('useFinancial must be used within a FinancialProvider');
  }
  return context;
};
