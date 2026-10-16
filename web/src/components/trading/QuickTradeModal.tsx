import React, { useState } from 'react';
import { useFinancial, OrderExecutionType, LedgerEntry } from '../../context/FinancialContext';

export const QuickTradeModal: React.FC = () => {
  const {
    isQuickTradeOpen,
    quickTradeSymbol,
    closeQuickTrade,
    marketQuotes,
    virtualCash,
    holdings,
    executeOrder,
  } = useFinancial();

  const [symbol, setSymbol] = useState(quickTradeSymbol || 'RELIANCE');
  const [tradeType, setTradeType] = useState<'BUY' | 'SELL'>('BUY');
  const [orderType, setOrderType] = useState<OrderExecutionType>('MARKET');
  const [shares, setShares] = useState(5);
  const [limitPrice, setLimitPrice] = useState<number>(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [receipt, setReceipt] = useState<LedgerEntry | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Sync symbol when opened
  React.useEffect(() => {
    if (quickTradeSymbol) {
      setSymbol(quickTradeSymbol);
      const quote = marketQuotes[quickTradeSymbol];
      if (quote) setLimitPrice(quote.price);
    }
  }, [quickTradeSymbol, marketQuotes]);

  if (!isQuickTradeOpen) return null;

  const currentQuote = marketQuotes[symbol] || {
    symbol,
    name: symbol,
    price: 2500,
    changePct: 1.0,
    isPositive: true,
  };

  const effectivePrice = orderType === 'LIMIT' && limitPrice > 0 ? limitPrice : currentQuote.price;
  const totalAmount = shares * effectivePrice;
  const ownedHolding = holdings.find((h) => h.symbol === symbol);
  const ownedShares = ownedHolding ? ownedHolding.shares : 0;

  const handlePercentageClick = (pct: number) => {
    if (tradeType === 'BUY') {
      const maxCash = virtualCash * pct;
      const calculatedShares = Math.max(1, Math.floor(maxCash / effectivePrice));
      setShares(calculatedShares);
    } else {
      const calculatedShares = Math.max(1, Math.floor(ownedShares * pct));
      setShares(calculatedShares);
    }
  };

  const handleSubmit = () => {
    setErrorMessage(null);
    setIsSubmitting(true);

    setTimeout(() => {
      const res = executeOrder(
        symbol,
        tradeType,
        shares,
        orderType,
        orderType === 'LIMIT' ? limitPrice : undefined
      );
      setIsSubmitting(false);

      if (res.success && res.receipt) {
        setReceipt(res.receipt);
      } else if (res.error) {
        setErrorMessage(res.error);
      }
    }, 350);
  };

  const handleClose = () => {
    setReceipt(null);
    setErrorMessage(null);
    closeQuickTrade();
  };

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div
        className="modal-content"
        style={{ maxWidth: '540px', padding: '32px' }}
        onClick={(e) => e.stopPropagation()}
      >
        {receipt ? (
          /* Execution Success Contract Note */
          <div style={{ textAlign: 'center' }}>
            <div
              style={{
                width: '56px',
                height: '56px',
                borderRadius: '50%',
                backgroundColor: 'rgba(16, 185, 129, 0.15)',
                border: '2px solid var(--color-profit)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px auto',
                fontSize: '24px',
                color: 'var(--color-profit)',
              }}
            >
              ✓
            </div>

            <span className="badge badge-profit" style={{ marginBottom: '8px' }}>
              ORDER EXECUTED • {receipt.id}
            </span>
            <h3 style={{ fontSize: '24px', fontWeight: 700, color: '#FFFFFF', marginTop: '4px' }}>
              {receipt.type === 'BUY' ? 'Purchase Successful' : 'Sale Executed'}
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '24px' }}>
              Simulated fill settled instantly on FinEx Paper Matching Engine.
            </p>

            <div
              style={{
                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '20px',
                textAlign: 'left',
                marginBottom: '24px',
                fontSize: '13px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Instrument</span>
                <strong style={{ color: '#FFFFFF' }}>{receipt.symbol} ({receipt.shares} shares)</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Fill Price</span>
                <span className="tabular-nums" style={{ color: '#FFFFFF' }}>₹{receipt.fillPrice.toLocaleString('en-IN')}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Gross Consideration</span>
                <span className="tabular-nums" style={{ color: '#FFFFFF', fontWeight: 600 }}>₹{receipt.total.toLocaleString('en-IN')}</span>
              </div>
              {receipt.realizedPnL !== undefined && (
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Realized Profit / Loss</span>
                  <span className={receipt.realizedPnL >= 0 ? 'badge badge-profit' : 'badge badge-loss'}>
                    {receipt.realizedPnL >= 0 ? '+' : ''}₹{receipt.realizedPnL.toLocaleString('en-IN')}
                  </span>
                </div>
              )}
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '10px', marginTop: '10px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Paper Virtual Cash Balance</span>
                <span className="tabular-nums" style={{ color: 'var(--color-virtual)', fontWeight: 700 }}>
                  ₹{receipt.cashAfter.toLocaleString('en-IN')}
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px' }}>
              <button onClick={() => setReceipt(null)} className="btn btn-secondary" style={{ flex: 1 }}>
                Place Another Trade
              </button>
              <button onClick={handleClose} className="btn btn-primary" style={{ flex: 1 }}>
                Done
              </button>
            </div>
          </div>
        ) : (
          /* Order Entry Ticket Form */
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: 'var(--radius-sm)',
                    background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 800,
                    fontSize: '16px',
                    color: '#FFFFFF',
                  }}
                >
                  ⚡
                </div>
                <div>
                  <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#FFFFFF', margin: 0 }}>
                    Quick Order Execution
                  </h3>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Instant simulated paper trading
                  </span>
                </div>
              </div>

              <button
                onClick={handleClose}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  fontSize: '20px',
                  cursor: 'pointer',
                  padding: '4px 8px',
                }}
              >
                ✕
              </button>
            </div>

            {/* Buy / Sell Selector */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '8px',
                background: 'rgba(0, 0, 0, 0.4)',
                padding: '4px',
                borderRadius: 'var(--radius-sm)',
                marginBottom: '20px',
              }}
            >
              <button
                onClick={() => { setTradeType('BUY'); setErrorMessage(null); }}
                style={{
                  padding: '10px',
                  border: 'none',
                  borderRadius: 'var(--radius-xs)',
                  fontWeight: 700,
                  fontSize: '13px',
                  cursor: 'pointer',
                  background: tradeType === 'BUY' ? 'linear-gradient(135deg, #10B981 0%, #059669 100%)' : 'transparent',
                  color: tradeType === 'BUY' ? '#FFFFFF' : 'var(--text-muted)',
                  boxShadow: tradeType === 'BUY' ? '0 0 14px rgba(16, 185, 129, 0.35)' : 'none',
                  transition: 'all 0.15s ease',
                }}
              >
                BUY / LONG
              </button>
              <button
                onClick={() => { setTradeType('SELL'); setErrorMessage(null); }}
                style={{
                  padding: '10px',
                  border: 'none',
                  borderRadius: 'var(--radius-xs)',
                  fontWeight: 700,
                  fontSize: '13px',
                  cursor: 'pointer',
                  background: tradeType === 'SELL' ? 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)' : 'transparent',
                  color: tradeType === 'SELL' ? '#FFFFFF' : 'var(--text-muted)',
                  boxShadow: tradeType === 'SELL' ? '0 0 14px rgba(239, 68, 68, 0.35)' : 'none',
                  transition: 'all 0.15s ease',
                }}
              >
                SELL / SHORT
              </button>
            </div>

            {/* Instrument Dropdown & Current Price */}
            <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '16px', marginBottom: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase', fontWeight: 600 }}>
                  Instrument
                </label>
                <select
                  value={symbol}
                  onChange={(e) => {
                    const next = e.target.value;
                    setSymbol(next);
                    if (marketQuotes[next]) setLimitPrice(marketQuotes[next].price);
                    setErrorMessage(null);
                  }}
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-medium)',
                    backgroundColor: 'var(--bg-input)',
                    color: '#FFFFFF',
                    fontWeight: 600,
                    outline: 'none',
                  }}
                >
                  {Object.values(marketQuotes).map((q) => (
                    <option key={q.symbol} value={q.symbol} style={{ backgroundColor: '#111827', color: '#FFFFFF' }}>
                      {q.symbol} — {q.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase', fontWeight: 600 }}>
                  Market Quote
                </label>
                <div
                  style={{
                    padding: '9px 12px',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: 'rgba(255, 255, 255, 0.04)',
                    border: '1px solid var(--border-subtle)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <span className="tabular-nums" style={{ fontSize: '15px', fontWeight: 700, color: '#FFFFFF' }}>
                    ₹{currentQuote.price.toLocaleString('en-IN')}
                  </span>
                  <span className={currentQuote.isPositive ? 'badge badge-profit' : 'badge badge-loss'} style={{ fontSize: '10px' }}>
                    {currentQuote.isPositive ? '+' : ''}{currentQuote.changePct}%
                  </span>
                </div>
              </div>
            </div>

            {/* Order Type Tabs */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase', fontWeight: 600 }}>
                Execution Mechanism
              </label>
              <div style={{ display: 'flex', gap: '8px' }}>
                {(['MARKET', 'LIMIT', 'STOP_LOSS', 'SIP'] as OrderExecutionType[]).map((type) => (
                  <button
                    key={type}
                    onClick={() => setOrderType(type)}
                    style={{
                      flex: 1,
                      padding: '8px 4px',
                      fontSize: '11px',
                      fontWeight: 600,
                      borderRadius: 'var(--radius-xs)',
                      cursor: 'pointer',
                      border: orderType === type ? '1px solid var(--color-primary)' : '1px solid var(--border-subtle)',
                      background: orderType === type ? 'rgba(59, 130, 246, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                      color: orderType === type ? '#FFFFFF' : 'var(--text-muted)',
                    }}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>

            {/* Limit Price Input if LIMIT or STOP_LOSS */}
            {(orderType === 'LIMIT' || orderType === 'STOP_LOSS') && (
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase', fontWeight: 600 }}>
                  Target Limit / Stop Price (₹)
                </label>
                <input
                  type="number"
                  value={limitPrice || currentQuote.price}
                  onChange={(e) => setLimitPrice(Number(e.target.value))}
                  step="0.5"
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-medium)',
                    backgroundColor: 'var(--bg-input)',
                    color: '#FFFFFF',
                    fontWeight: 600,
                  }}
                />
              </div>
            )}

            {/* Shares Quantity Input & Percentage Helpers */}
            <div style={{ marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <label style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                  Quantity (Shares)
                </label>
                <span style={{ fontSize: '12px', color: 'var(--text-faint)' }}>
                  Owned: <strong style={{ color: '#FFFFFF' }}>{ownedShares}</strong>
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '8px', marginBottom: '8px' }}>
                <input
                  type="number"
                  min="1"
                  value={shares}
                  onChange={(e) => setShares(Math.max(1, parseInt(e.target.value) || 1))}
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-medium)',
                    backgroundColor: 'var(--bg-input)',
                    color: '#FFFFFF',
                    fontWeight: 700,
                    fontSize: '16px',
                  }}
                />
                <div style={{ display: 'flex', gap: '4px' }}>
                  <button
                    onClick={() => setShares((prev) => Math.max(1, prev - 1))}
                    className="btn btn-secondary"
                    style={{ padding: '0 14px', fontSize: '16px' }}
                  >
                    -
                  </button>
                  <button
                    onClick={() => setShares((prev) => prev + 1)}
                    className="btn btn-secondary"
                    style={{ padding: '0 14px', fontSize: '16px' }}
                  >
                    +
                  </button>
                </div>
              </div>

              {/* Quick % Helpers */}
              <div style={{ display: 'flex', gap: '6px' }}>
                {[0.25, 0.5, 0.75, 1.0].map((pct) => (
                  <button
                    key={pct}
                    onClick={() => handlePercentageClick(pct)}
                    style={{
                      flex: 1,
                      padding: '4px',
                      fontSize: '11px',
                      borderRadius: 'var(--radius-xs)',
                      background: 'rgba(255, 255, 255, 0.04)',
                      border: '1px solid var(--border-subtle)',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                    }}
                  >
                    {pct * 100}%
                  </button>
                ))}
              </div>
            </div>

            {/* Financial Consideration & Ledger Impact */}
            <div
              style={{
                backgroundColor: 'rgba(0, 0, 0, 0.25)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '14px',
                marginBottom: '20px',
                fontSize: '12px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Estimated Consideration</span>
                <span className="tabular-nums" style={{ color: '#FFFFFF', fontWeight: 600 }}>
                  ₹{totalAmount.toLocaleString('en-IN')}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Brokerage & Taxes</span>
                <span className="badge badge-profit" style={{ fontSize: '10px' }}>
                  ₹0.00 (Paper Simulation)
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '6px', marginTop: '6px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Virtual Balance After</span>
                <span className="tabular-nums" style={{ color: 'var(--color-virtual)', fontWeight: 600 }}>
                  ₹{tradeType === 'BUY' ? (virtualCash - totalAmount).toLocaleString('en-IN') : (virtualCash + totalAmount).toLocaleString('en-IN')}
                </span>
              </div>
            </div>

            {errorMessage && (
              <div
                style={{
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'var(--color-loss-bg)',
                  border: '1px solid var(--color-loss-border)',
                  color: 'var(--color-loss)',
                  fontSize: '12px',
                  marginBottom: '16px',
                }}
              >
                ⚠️ {errorMessage}
              </div>
            )}

            <button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className={tradeType === 'BUY' ? 'btn-emerald' : 'btn'}
              style={{
                width: '100%',
                padding: '14px',
                fontSize: '14px',
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
                background: tradeType === 'SELL' ? 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)' : undefined,
              }}
            >
              {isSubmitting
                ? 'Routing to Paper Matching Engine...'
                : tradeType === 'BUY'
                ? `Execute Buy • ₹${totalAmount.toLocaleString('en-IN')}`
                : `Execute Sell • ₹${totalAmount.toLocaleString('en-IN')}`}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
