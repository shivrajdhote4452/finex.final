import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

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
  lastTick?: 'up' | 'down' | 'none';
}

interface FinancialContextType {
  virtualCash: number;
  holdings: HoldingItem[];
  ledger: LedgerEntry[];
  notifications: AlertNotification[];
  spendingItems: SpendingItem[];
  marketQuotes: Record<string, MarketQuote>;
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
  ) => { success: boolean; receipt?: LedgerEntry; error?: string };
  depositFunds: (amount: number) => void;
  resetAccount: () => void;
  addSpendingItem: (merchant: string, category: string, amount: number) => void;
  markAllNotificationsRead: () => void;
  addNotification: (title: string, message: string, type: AlertNotification['type']) => void;
}

const FinancialContext = createContext<FinancialContextType | undefined>(undefined);

export const FinancialProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [virtualCash, setVirtualCash] = useState<number>(35000);

  // Initial Real Market Quotes
  const [marketQuotes, setMarketQuotes] = useState<Record<string, MarketQuote>>({
    RELIANCE: { symbol: 'RELIANCE', name: 'Reliance Industries Ltd', price: 2500.0, changeVal: 30.0, changePct: 1.21, isPositive: true, high: 2515.0, low: 2468.0, volume: '8.4M', lastTick: 'none' },
    TCS: { symbol: 'TCS', name: 'Tata Consultancy Services', price: 3600.0, changeVal: -29.0, changePct: -0.80, isPositive: false, high: 3645.0, low: 3590.0, volume: '3.1M', lastTick: 'none' },
    INFY: { symbol: 'INFY', name: 'Infosys Ltd', price: 1450.0, changeVal: 7.9, changePct: 0.55, isPositive: true, high: 1458.0, low: 1438.0, volume: '5.2M', lastTick: 'none' },
    HDFCBANK: { symbol: 'HDFCBANK', name: 'HDFC Bank Ltd', price: 1600.0, changeVal: 5.1, changePct: 0.32, isPositive: true, high: 1612.0, low: 1590.0, volume: '9.8M', lastTick: 'none' },
    ICICIBANK: { symbol: 'ICICIBANK', name: 'ICICI Bank Ltd', price: 1240.0, changeVal: 18.6, changePct: 1.52, isPositive: true, high: 1248.0, low: 1222.0, volume: '11.5M', lastTick: 'none' },
    TATAMOTORS: { symbol: 'TATAMOTORS', name: 'Tata Motors Ltd', price: 924.5, changeVal: 19.2, changePct: 2.12, isPositive: true, high: 932.0, low: 908.0, volume: '14.2M', lastTick: 'none' },
    ITC: { symbol: 'ITC', name: 'ITC Ltd', price: 495.2, changeVal: 1.95, changePct: 0.40, isPositive: true, high: 498.0, low: 492.5, volume: '7.6M', lastTick: 'none' },
    SBIN: { symbol: 'SBIN', name: 'State Bank of India', price: 815.0, changeVal: -4.2, changePct: -0.51, isPositive: false, high: 824.0, low: 811.0, volume: '12.8M', lastTick: 'none' },
  });

  const [holdings, setHoldings] = useState<HoldingItem[]>([
    { symbol: 'RELIANCE', name: 'Reliance Industries', shares: 10, avgPrice: 2300, currentPrice: 2500, dayChangePct: 1.21, assetClass: 'Energy', color: '#3B82F6' },
    { symbol: 'TCS', name: 'Tata Consultancy Services', shares: 10, avgPrice: 3450, currentPrice: 3600, dayChangePct: -0.80, assetClass: 'IT', color: '#10B981' },
    { symbol: 'INFY', name: 'Infosys', shares: 10, avgPrice: 1350, currentPrice: 1450, dayChangePct: 0.55, assetClass: 'IT', color: '#F59E0B' },
    { symbol: 'HDFCBANK', name: 'HDFC Bank', shares: 15, avgPrice: 1533, currentPrice: 1600, dayChangePct: 0.32, assetClass: 'Banking', color: '#8B5CF6' },
  ]);

  const [ledger, setLedger] = useState<LedgerEntry[]>([
    {
      id: 'ORD-7712',
      timestamp: '16 Oct 2026, 10:15:32',
      type: 'BUY',
      orderType: 'MARKET',
      symbol: 'RELIANCE',
      name: 'Reliance Industries Ltd',
      shares: 5,
      fillPrice: 2500,
      total: 12500,
      brokerageFee: 0,
      regulatoryFees: 0,
      cashAfter: 35000,
      status: 'FILLED',
      notes: 'Executed via FinEx Paper Matching Engine (NSE Reference)',
    },
    {
      id: 'ORD-7690',
      timestamp: '15 Oct 2026, 14:20:10',
      type: 'SELL',
      orderType: 'LIMIT',
      symbol: 'TCS',
      name: 'Tata Consultancy Services',
      shares: 2,
      fillPrice: 3580,
      total: 7160,
      realizedPnL: 260,
      brokerageFee: 0,
      regulatoryFees: 0,
      cashAfter: 47500,
      status: 'FILLED',
      notes: 'Target limit price ₹3,580 met during post-lunch session',
    },
    {
      id: 'ORD-7651',
      timestamp: '14 Oct 2026, 11:05:44',
      type: 'BUY',
      orderType: 'SIP',
      symbol: 'HDFCBANK',
      name: 'HDFC Bank Ltd',
      shares: 15,
      fillPrice: 1533,
      total: 22995,
      brokerageFee: 0,
      regulatoryFees: 0,
      cashAfter: 40340,
      status: 'FILLED',
      notes: 'Automated monthly recurring equity SIP execution',
    },
    {
      id: 'DEP-1001',
      timestamp: '14 Oct 2026, 09:00:00',
      type: 'DEPOSIT',
      orderType: 'MARKET',
      symbol: 'INR_CASH',
      name: 'Virtual Sandbox Allocation',
      shares: 1,
      fillPrice: 50000,
      total: 50000,
      brokerageFee: 0,
      regulatoryFees: 0,
      cashAfter: 63335,
      status: 'SETTLED',
      notes: 'Sandbox initial virtual capital credit',
    },
  ]);

  const [notifications, setNotifications] = useState<AlertNotification[]>([
    { id: 'ALT-1', time: '09:40 AM', title: 'Price threshold reached', message: 'RELIANCE crossed your threshold of ₹2,500.00', type: 'price', read: false },
    { id: 'ALT-2', time: '09:15 AM', title: 'Allocation alert', message: 'TCS accounts for 36.2% of your equity portfolio.', type: 'allocation', read: false },
    { id: 'ALT-3', time: '08:00 AM', title: 'Goal check-in', message: 'Emergency fund contribution of ₹5,000 scheduled for Oct.', type: 'goal', read: true },
  ]);

  const [spendingItems, setSpendingItems] = useState<SpendingItem[]>([
    { id: 'TX-101', date: '05 Oct 2026', merchant: 'Merchant ••42', category: 'Food & Dining', amount: 1200, isMasked: true },
    { id: 'TX-102', date: '06 Oct 2026', merchant: 'Merchant ••86', category: 'Transport', amount: 650, isMasked: true },
    { id: 'TX-103', date: '08 Oct 2026', merchant: 'Merchant ••19', category: 'Shopping', amount: 2100, isMasked: true },
    { id: 'TX-104', date: '11 Oct 2026', merchant: 'Merchant ••77', category: 'Bills & Utilities', amount: 3500, isMasked: true },
    { id: 'TX-105', date: '14 Oct 2026', merchant: 'Merchant ••04', category: 'Food & Dining', amount: 1850, isMasked: true },
  ]);

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

  // Live Market Pulse (Subtle Micro-Tick Simulation)
  useEffect(() => {
    const symbols = Object.keys(marketQuotes);
    const interval = setInterval(() => {
      const targetSymbol = symbols[Math.floor(Math.random() * symbols.length)];
      const current = marketQuotes[targetSymbol];
      if (!current) return;

      // ±0.1% to ±0.25% micro-variation
      const deltaPercent = (Math.random() * 0.4 - 0.18) / 100;
      const rawNewPrice = current.price * (1 + deltaPercent);
      const newPrice = Math.round(rawNewPrice * 10) / 10;
      const priceDiff = newPrice - current.price;
      const newChangeVal = Math.round((current.changeVal + priceDiff) * 10) / 10;
      const newChangePct = Math.round(((newChangeVal / (newPrice - newChangeVal)) * 100) * 100) / 100;
      const tick = priceDiff >= 0 ? 'up' : 'down';

      setMarketQuotes((prev) => ({
        ...prev,
        [targetSymbol]: {
          ...current,
          price: newPrice,
          changeVal: newChangeVal,
          changePct: newChangePct,
          isPositive: newChangeVal >= 0,
          high: Math.max(current.high, newPrice),
          low: Math.min(current.low, newPrice),
          lastTick: tick,
        },
      }));

      // Synchronize in-flight holdings current price
      setHoldings((prev) =>
        prev.map((h) =>
          h.symbol === targetSymbol
            ? { ...h, currentPrice: newPrice, dayChangePct: newChangePct }
            : h
        )
      );
    }, 4500);

    return () => clearInterval(interval);
  }, [marketQuotes]);

  // Derived Financial Metrics
  const totalHoldingsValue = holdings.reduce((sum, h) => sum + h.shares * h.currentPrice, 0);
  const totalCostBasis = holdings.reduce((sum, h) => sum + h.shares * h.avgPrice, 0);
  const unrealizedPnL = totalHoldingsValue - totalCostBasis;
  const totalPortfolioValue = totalHoldingsValue + virtualCash;

  const totalRealizedPnL = ledger
    .filter((l) => l.realizedPnL !== undefined)
    .reduce((sum, l) => sum + (l.realizedPnL || 0), 0);

  const totalTradesCount = ledger.filter((l) => l.type === 'BUY' || l.type === 'SELL' || l.type === 'SIP').length;
  const totalTradedVolume = ledger
    .filter((l) => l.type === 'BUY' || l.type === 'SELL' || l.type === 'SIP')
    .reduce((sum, l) => sum + l.total, 0);

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

  const markAllNotificationsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const depositFunds = (amount: number) => {
    const nextCash = virtualCash + amount;
    setVirtualCash(nextCash);

    const receipt: LedgerEntry = {
      id: `DEP-${Date.now().toString().slice(-4)}`,
      timestamp: new Date().toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'medium' }),
      type: 'DEPOSIT',
      orderType: 'MARKET',
      symbol: 'INR_CASH',
      name: 'Virtual Sandbox Allocation',
      shares: 1,
      fillPrice: amount,
      total: amount,
      brokerageFee: 0,
      regulatoryFees: 0,
      cashAfter: nextCash,
      status: 'SETTLED',
      notes: `Injected ₹${amount.toLocaleString('en-IN')} simulated paper funds`,
    };

    setLedger((prev) => [receipt, ...prev]);
    addNotification('Funds Deposited', `Credited ₹${amount.toLocaleString('en-IN')} virtual cash to your sandbox account`, 'execution');
  };

  const resetAccount = () => {
    setVirtualCash(50000);
    setHoldings([
      { symbol: 'RELIANCE', name: 'Reliance Industries', shares: 10, avgPrice: 2300, currentPrice: 2500, dayChangePct: 1.21, assetClass: 'Energy', color: '#3B82F6' },
      { symbol: 'TCS', name: 'Tata Consultancy Services', shares: 10, avgPrice: 3450, currentPrice: 3600, dayChangePct: -0.80, assetClass: 'IT', color: '#10B981' },
      { symbol: 'INFY', name: 'Infosys', shares: 10, avgPrice: 1350, currentPrice: 1450, dayChangePct: 0.55, assetClass: 'IT', color: '#F59E0B' },
      { symbol: 'HDFCBANK', name: 'HDFC Bank', shares: 15, avgPrice: 1533, currentPrice: 1600, dayChangePct: 0.32, assetClass: 'Banking', color: '#8B5CF6' },
    ]);
    addNotification('Account Reset', 'Restored sandbox balance to ₹50,000 virtual cash and baseline portfolio', 'execution');
  };

  const addSpendingItem = (merchant: string, category: string, amount: number) => {
    const newItem: SpendingItem = {
      id: `TX-${Date.now().toString().slice(-4)}`,
      date: new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }),
      merchant,
      category,
      amount,
      isMasked: true,
    };
    setSpendingItems((prev) => [newItem, ...prev]);
    addNotification('Expense Logged', `Recorded ₹${amount.toLocaleString('en-IN')} for ${merchant} (${category})`, 'execution');
  };

  // Atomic Simulated Order Execution Engine
  const executeOrder = (
    symbol: string,
    type: 'BUY' | 'SELL' | 'SIP',
    shares: number,
    orderType: OrderExecutionType = 'MARKET',
    customPrice?: number
  ) => {
    const targetQuote = marketQuotes[symbol];
    const unitPrice = customPrice && customPrice > 0 ? customPrice : (targetQuote ? targetQuote.price : 2500);
    const orderCost = shares * unitPrice;

    if (type === 'BUY' || type === 'SIP') {
      if (orderCost > virtualCash) {
        return {
          success: false,
          error: `Insufficient virtual cash. Required ₹${orderCost.toLocaleString('en-IN')}, available ₹${virtualCash.toLocaleString('en-IN')}.`,
        };
      }

      const nextCash = virtualCash - orderCost;
      setVirtualCash(nextCash);

      setHoldings((prev) => {
        const existing = prev.find((h) => h.symbol === symbol);
        if (existing) {
          const totalShares = existing.shares + shares;
          const newAvgPrice = (existing.shares * existing.avgPrice + orderCost) / totalShares;
          return prev.map((h) =>
            h.symbol === symbol
              ? { ...h, shares: totalShares, avgPrice: Math.round(newAvgPrice) }
              : h
          );
        } else {
          return [
            ...prev,
            {
              symbol,
              name: targetQuote?.name || symbol,
              shares,
              avgPrice: unitPrice,
              currentPrice: unitPrice,
              dayChangePct: targetQuote?.changePct || 0.0,
              assetClass: 'Equity',
              color: '#3B82F6',
            },
          ];
        }
      });

      const receipt: LedgerEntry = {
        id: `ORD-${Date.now().toString().slice(-4)}`,
        timestamp: new Date().toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'medium' }),
        type,
        orderType,
        symbol,
        name: targetQuote?.name || symbol,
        shares,
        fillPrice: unitPrice,
        total: orderCost,
        brokerageFee: 0,
        regulatoryFees: 0,
        cashAfter: nextCash,
        status: 'FILLED',
        notes: `Executed via FinEx Paper Matching Engine at ₹${unitPrice.toLocaleString('en-IN')}`,
      };

      setLedger((prev) => [receipt, ...prev]);
      addNotification('Order Executed', `Bought ${shares} shares of ${symbol} at ₹${unitPrice.toLocaleString('en-IN')}`, 'execution');
      return { success: true, receipt };
    } else {
      // SELL
      const targetHolding = holdings.find((h) => h.symbol === symbol);
      if (!targetHolding || targetHolding.shares < shares) {
        return {
          success: false,
          error: `Insufficient shares to sell. You own ${targetHolding ? targetHolding.shares : 0} shares of ${symbol}.`,
        };
      }

      const costBasis = shares * targetHolding.avgPrice;
      const realizedGain = orderCost - costBasis;
      const nextCash = virtualCash + orderCost;
      setVirtualCash(nextCash);

      setHoldings((prev) =>
        prev
          .map((h) => (h.symbol === symbol ? { ...h, shares: h.shares - shares } : h))
          .filter((h) => h.shares > 0)
      );

      const receipt: LedgerEntry = {
        id: `ORD-${Date.now().toString().slice(-4)}`,
        timestamp: new Date().toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'medium' }),
        type: 'SELL',
        orderType,
        symbol,
        name: targetQuote?.name || symbol,
        shares,
        fillPrice: unitPrice,
        total: orderCost,
        realizedPnL: realizedGain,
        brokerageFee: 0,
        regulatoryFees: 0,
        cashAfter: nextCash,
        status: 'FILLED',
        notes: `Realized P&L: ${realizedGain >= 0 ? '+' : ''}₹${realizedGain.toLocaleString('en-IN')}`,
      };

      setLedger((prev) => [receipt, ...prev]);
      addNotification(
        'Order Executed',
        `Sold ${shares} shares of ${symbol} at ₹${unitPrice.toLocaleString('en-IN')} (P&L: ${realizedGain >= 0 ? '+' : ''}₹${realizedGain.toLocaleString('en-IN')})`,
        'execution'
      );
      return { success: true, receipt };
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
      }}
    >
      {children}
    </FinancialContext.Provider>
  );
};

export const useFinancial = () => {
  const context = useContext(FinancialContext);
  if (!context) throw new Error('useFinancial must be used within FinancialProvider');
  return context;
};
