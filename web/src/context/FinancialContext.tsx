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
  isReplay?: boolean;
  replayDate?: string;
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
  isPriceUnavailable?: boolean;
  isChangeUnavailable?: boolean;
  isHighLowUnavailable?: boolean;
}

export interface UserProfileData {
  id?: string;
  email?: string;
  full_name?: string;
  display_name?: string;
  is_owner?: boolean;
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
  isOwner: boolean;
  userProfile: UserProfileData | null;
  displayName: string;
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
    customPrice?: number,
    isReplay?: boolean,
    replayDate?: string
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
  const getCashStorageKey = useCallback(() => {
    try {
      const payload = apiClient.getTokenPayload();
      const uid = payload?.sub || payload?.user_id;
      return uid ? `finex_virtual_cash_${uid}` : 'finex_virtual_cash_guest';
    } catch {
      return 'finex_virtual_cash_guest';
    }
  }, []);

  const [virtualCash, setVirtualCash] = useState<number>(() => {
    try {
      const payload = apiClient.getTokenPayload();
      const uid = payload?.sub || payload?.user_id;
      const key = uid ? `finex_virtual_cash_${uid}` : 'finex_virtual_cash_guest';
      const saved = localStorage.getItem(key);
      if (saved !== null && saved !== undefined && saved !== '') {
        const val = Number(saved);
        if (Number.isFinite(val) && val >= 0) return val;
      }
      return 100000;
    } catch {
      return 100000;
    }
  });

  const updateVirtualCash = useCallback((updater: number | ((prev: number) => number)) => {
    setVirtualCash((prev) => {
      const next = typeof updater === 'function' ? updater(prev) : updater;
      const safeNext = Number.isFinite(next) && next >= 0 ? next : 0;
      try {
        const key = getCashStorageKey();
        localStorage.setItem(key, String(safeNext));
      } catch {}
      return safeNext;
    });
  }, [getCashStorageKey]);

  const [holdings, setHoldings] = useState<HoldingItem[]>([]);
  const [ledger, setLedger] = useState<LedgerEntry[]>([]);
  const [notifications, setNotifications] = useState<AlertNotification[]>([]);
  const [spendingItems, setSpendingItems] = useState<SpendingItem[]>([]);
  const [isAccountLoading, setIsAccountLoading] = useState<boolean>(apiClient.isAuthenticated());
  const [accountError, setAccountError] = useState<string | null>(null);
  const [isOwner, setIsOwner] = useState<boolean>(false);
  const [userProfile, setUserProfile] = useState<UserProfileData | null>(null);

  const displayName = userProfile?.display_name || userProfile?.full_name?.split(' ')[0] || '';

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
    setVirtualCash(100000);
    setHoldings([]);
    setLedger([]);
    setNotifications([]);
    setSpendingItems([]);
    setAccountError(null);
    setIsOwner(false);
    setUserProfile(null);
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
      try {
        const me = await apiClient.auth.getMe();
        if (thisGen === sessionGenerationRef.current && me) {
          setIsOwner(Boolean(me.is_owner));
          setUserProfile({
            id: me.user_id,
            email: me.email,
            full_name: me.full_name,
            display_name: me.display_name,
            is_owner: Boolean(me.is_owner),
          });
        }
      } catch {
        // In local offline mode or unauthenticated fallback, fail closed (isOwner remains false)
      }

      const acct = await apiClient.paperTrading.getAccount();
      if (thisGen !== sessionGenerationRef.current) return;
      if (acct) {
        // Normalize cash_balance and current_cash defensively
        // Authoritative backend cash balance (including legitimate ₹0.00) is preserved
        const rawCash = acct.cash_balance ?? acct.current_cash;
        const normalizedCash = Number(rawCash);
        if (Number.isFinite(normalizedCash) && normalizedCash >= 0) {
          updateVirtualCash(normalizedCash);
        } else {
          // Fallback only if backend returned null, undefined, or NaN
          updateVirtualCash(100000);
        }

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
          const isNetwork = e?.code === 'TIMEOUT' || e?.code === 'NETWORK_ERROR' || e?.message?.includes('Failed to fetch') || e?.message?.includes('waking up');
          setAccountError(
            isNetwork
              ? 'Unable to connect to FinEx server. The service may be waking up.'
              : e?.message || 'Failed to sync portfolio with server.'
          );
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
    if (!amount || amount <= 0) {
      addNotification('Invalid Amount', 'Please specify a positive deposit amount.', 'execution');
      return;
    }
    if (!isOwner) {
      addNotification('Action Denied', 'Paper trading sandbox controls are restricted to the platform owner.', 'execution');
      return;
    }
    try {
      if (apiClient.isAuthenticated()) {
        await apiClient.paperTrading.deposit(amount);
      }
    } catch (e: any) {
      console.warn('Backend deposit failed or offline:', e);
    }
    updateVirtualCash((prev) => prev + amount);
    const depositEntry: LedgerEntry = {
      id: `DEP-${Date.now()}`,
      timestamp: new Date().toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'medium' }),
      type: 'DEPOSIT',
      orderType: 'MARKET',
      symbol: 'INR',
      name: 'Virtual Paper Cash Deposit',
      shares: 1,
      fillPrice: amount,
      total: amount,
      brokerageFee: 0,
      regulatoryFees: 0,
      cashAfter: virtualCash + amount,
      status: 'FILLED',
      notes: `Paper wallet funded with ₹${amount.toLocaleString('en-IN')}`,
    };
    setLedger((prev) => [depositEntry, ...prev]);
    addNotification(
      'Funds Deposited',
      `Credited ₹${amount.toLocaleString('en-IN')} virtual cash to your ${isOwner ? 'sandbox' : 'paper'} account`,
      'execution'
    );
  };

  const resetAccount = async () => {
    if (!apiClient.isAuthenticated()) {
      addNotification('Reset Failed', 'Authentication required. Please sign in to reset account.', 'execution');
      return;
    }
    if (!isOwner) {
      addNotification('Action Denied', 'Paper trading sandbox controls are restricted to the platform owner.', 'execution');
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
    customPrice?: number,
    isReplay?: boolean,
    replayDate?: string
  ): Promise<{ success: boolean; receipt?: LedgerEntry; error?: string }> => {
    const side = type === 'BUY' || type === 'SIP' ? 'BUY' : 'SELL';
    const idempotencyKey = `web-ord-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

    if (isReplay && customPrice !== undefined && customPrice > 0) {
      const fill = customPrice;
      const gross = fill * shares;
      if (side === 'BUY' && gross > virtualCash) {
        return {
          success: false,
          error: `Insufficient virtual cash balance (₹${virtualCash.toLocaleString('en-IN')}) for replay trade of ₹${gross.toLocaleString('en-IN')}.`,
        };
      }
      const cashAfter = side === 'BUY' ? Math.max(0, virtualCash - gross) : virtualCash + gross;
      updateVirtualCash(cashAfter);

      setHoldings((prev) => {
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
      });

      const existingHolding = holdings.find((h) => h.symbol === symbol);
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

      setLedger((prev) => [receipt, ...prev]);

      addNotification(
        'Replay Order Executed',
        `[REPLAY] ${side === 'BUY' ? 'Bought' : 'Sold'} ${shares} shares of ${symbol} at ₹${fill.toLocaleString('en-IN')} (${replayDate || 'Past NSE'})`,
        'execution'
      );

      return { success: true, receipt };
    }

    if (apiClient.isAuthenticated()) {
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

        if (res.status === 'FILLED') {
          const fill = Number(res.fill_price) || 0;
          const gross = Number(res.gross_value) || (fill * shares);
          const cashAfter = Number(res.cash_balance_after);
          if (!isNaN(cashAfter) && res.cash_balance_after !== undefined) {
            updateVirtualCash(cashAfter);
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
            cashAfter: !isNaN(cashAfter) ? cashAfter : virtualCash,
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
            cashAfter: virtualCash,
            status: 'PENDING',
            notes: `Order placed and pending fill in FinEx Order Book. Limit: ₹${Number(customPrice || 0).toLocaleString('en-IN')}`,
          };

          setLedger((prev) => [receipt, ...prev]);
          await refreshAccount();

          addNotification(
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
        // Handle network disconnection, timeouts and unknown execution outcomes explicitly
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
          // Attempt account and order reconciliation before reporting outcome to avoid duplicate retries
          try {
            await refreshAccount();
            const orderList = await apiClient.paperTrading.getOrders(10);
            const matchedOrder = orderList?.orders?.find((o: any) => o.idempotency_key === idempotencyKey);
            if (matchedOrder) {
              if (matchedOrder.status === 'FILLED') {
                const fill = Number(matchedOrder.fill_price) || 0;
                const gross = Number(matchedOrder.gross_value) || (fill * shares);
                const cashAfter = Number(matchedOrder.cash_balance_after);
                if (!isNaN(cashAfter)) {
                  updateVirtualCash(cashAfter);
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
                  cashAfter: !isNaN(cashAfter) ? cashAfter : virtualCash,
                  status: 'FILLED',
                  notes: `Reconciled order via FinEx Paper Matching Engine at ₹${fill.toLocaleString('en-IN')}`,
                };
                setLedger((prev) => [receipt, ...prev]);
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
                  cashAfter: virtualCash,
                  status: 'PENDING',
                  notes: 'Reconciled pending order in FinEx Order Book.',
                };
                setLedger((prev) => [receipt, ...prev]);
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

        // Backend HTTP error (e.g. 400 Bad Request, 422 Unprocessable Entity, 500)
        return {
          success: false,
          error: err?.message || 'Order failed on the server.',
        };
      }
    }

    // Local fallback exclusively for unauthenticated preview/demo environments
    const currentQuote = marketQuotesRef.current[symbol];
    const fill = customPrice || (currentQuote && currentQuote.price ? currentQuote.price : 1000);
    const gross = fill * shares;
    if (side === 'BUY' && gross > virtualCash) {
      return {
        success: false,
        error: `Insufficient virtual cash balance (₹${virtualCash.toLocaleString('en-IN')}) for trade of ₹${gross.toLocaleString('en-IN')}.`,
      };
    }
    const cashAfter = side === 'BUY' ? Math.max(0, virtualCash - gross) : virtualCash + gross;
    updateVirtualCash(cashAfter);

    setHoldings((prev) => {
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
    });

    const existingHolding = holdings.find((h) => h.symbol === symbol);
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

    setLedger((prev) => [receipt, ...prev]);

    addNotification(
      'Demo Order Executed',
      `[Demo] ${side === 'BUY' ? 'Bought' : 'Sold'} ${shares} shares of ${symbol} at ₹${fill.toLocaleString('en-IN')}`,
      'execution'
    );
    return { success: true, receipt };
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
        isOwner,
        userProfile,
        displayName,
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
