import React, { useState } from 'react';
import { useFinancial, LedgerEntry, OrderExecutionType } from '../context/FinancialContext';

export const PracticeScreen: React.FC = () => {
  const { virtualCash, holdings, ledger, marketQuotes, executeOrder } = useFinancial();

  const [selectedSymbol, setSelectedSymbol] = useState('RELIANCE');
  const [orderAction, setOrderAction] = useState<'BUY' | 'SELL'>('BUY');
  const [orderType, setOrderType] = useState<OrderExecutionType>('MARKET');
  const [shares, setShares] = useState(5);
  const [limitPrice, setLimitPrice] = useState<number>(0);
  const [isExecuting, setIsExecuting] = useState(false);
  const [lastReceipt, setLastReceipt] = useState<LedgerEntry | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const currentQuote = marketQuotes[selectedSymbol] || {
    symbol: selectedSymbol,
    name: selectedSymbol,
    price: 2500,
    changeVal: 20,
    changePct: 0.8,
    isPositive: true,
    high: 2520,
    low: 2480,
    volume: '5.2M',
  };

  const effectivePrice = orderType === 'LIMIT' && limitPrice > 0 ? limitPrice : currentQuote.price;
  const orderTotal = shares * effectivePrice;
  const cashAfter = orderAction === 'BUY' ? virtualCash - orderTotal : virtualCash + orderTotal;

  // Owned shares for this symbol
  const targetHolding = holdings.find((h) => h.symbol === selectedSymbol);
  const ownedShares = targetHolding?.shares || 0;

  // Play subtle web audio chime on order fill
  const playTradeChime = () => {
    try {
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, audioCtx.currentTime); // D5
      osc.frequency.exponentialRampToValueAtTime(880, audioCtx.currentTime + 0.15); // A5
      gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.35);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.35);
    } catch {
      // AudioContext unavailable or blocked by browser policy
    }
  };

  const handleExecute = () => {
    setErrorMessage(null);
    setIsExecuting(true);

    setTimeout(() => {
      const result = executeOrder(
        selectedSymbol,
        orderAction,
        shares,
        orderType,
        orderType === 'LIMIT' ? limitPrice : undefined
      );
      setIsExecuting(false);

      if (result.success && result.receipt) {
        setLastReceipt(result.receipt);
        playTradeChime();
      } else if (result.error) {
        setErrorMessage(result.error);
      }
    }, 350);
  };

  // 1-Click Square Off Position
  const handleSquareOff = (symbol: string, qty: number) => {
    const res = executeOrder(symbol, 'SELL', qty, 'MARKET');
    if (res.success && res.receipt) {
      setLastReceipt(res.receipt);
      playTradeChime();
    }
  };

  // 1-Click Add Shares
  const handleAddShares = (symbol: string, qty: number) => {
    const res = executeOrder(symbol, 'BUY', qty, 'MARKET');
    if (res.success && res.receipt) {
      setLastReceipt(res.receipt);
      playTradeChime();
    }
  };

  // Order Book Simulation Data (Dynamic around effective price)
  const orderBookBids = [
    { price: effectivePrice - 0.5, qty: 1420, depth: 85 },
    { price: effectivePrice - 1.0, qty: 2850, depth: 95 },
    { price: effectivePrice - 1.5, qty: 980, depth: 60 },
    { price: effectivePrice - 2.0, qty: 1750, depth: 75 },
    { price: effectivePrice - 2.5, qty: 620, depth: 40 },
  ];

  const orderBookAsks = [
    { price: effectivePrice + 0.5, qty: 1120, depth: 70 },
    { price: effectivePrice + 1.0, qty: 3100, depth: 100 },
    { price: effectivePrice + 1.5, qty: 890, depth: 55 },
    { price: effectivePrice + 2.0, qty: 1430, depth: 68 },
    { price: effectivePrice + 2.5, qty: 540, depth: 35 },
  ];

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* Simulation Ribbon */}
      <div
        className="glass-card"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 24px',
          border: '1px solid var(--color-virtual-border)',
          background: 'linear-gradient(90deg, rgba(245, 158, 11, 0.12) 0%, rgba(245, 158, 11, 0.04) 100%)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span className="badge-virtual">PRO TRADE DESK</span>
          <span style={{ fontSize: '13px', color: '#F3F4F6' }}>
            Simulated institutional terminal matching with real-time NSE observation feeds and atomic virtual ledger.
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Liquid Capital:</span>
          <span className="tabular-nums" style={{ fontSize: '17px', fontWeight: 700, color: '#FFFFFF' }}>
            ₹{virtualCash.toLocaleString('en-IN')}
          </span>
        </div>
      </div>

      {/* Main Trading Floor Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '400px 320px 1fr', gap: '24px', alignItems: 'start' }}>
        {/* Column 1: Pro Order Ticket */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
            <h2 style={{ fontSize: '17px', fontWeight: 700, color: '#FFFFFF', margin: 0 }}>Simulated Order Ticket</h2>
            <span className="badge badge-profit" style={{ fontSize: '10px' }}>Zero Brokerage</span>
          </div>

          {/* Buy / Sell Toggle */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '6px',
              background: 'rgba(0, 0, 0, 0.4)',
              padding: '4px',
              borderRadius: 'var(--radius-sm)',
              marginBottom: '16px',
            }}
          >
            <button
              onClick={() => { setOrderAction('BUY'); setErrorMessage(null); }}
              style={{
                padding: '9px',
                border: 'none',
                borderRadius: 'var(--radius-xs)',
                fontWeight: 700,
                fontSize: '13px',
                cursor: 'pointer',
                background: orderAction === 'BUY' ? 'linear-gradient(135deg, #10B981 0%, #059669 100%)' : 'transparent',
                color: orderAction === 'BUY' ? '#FFFFFF' : 'var(--text-muted)',
                boxShadow: orderAction === 'BUY' ? '0 0 12px rgba(16, 185, 129, 0.3)' : 'none',
              }}
            >
              BUY / LONG
            </button>
            <button
              onClick={() => { setOrderAction('SELL'); setErrorMessage(null); }}
              style={{
                padding: '9px',
                border: 'none',
                borderRadius: 'var(--radius-xs)',
                fontWeight: 700,
                fontSize: '13px',
                cursor: 'pointer',
                background: orderAction === 'SELL' ? 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)' : 'transparent',
                color: orderAction === 'SELL' ? '#FFFFFF' : 'var(--text-muted)',
                boxShadow: orderAction === 'SELL' ? '0 0 12px rgba(239, 68, 68, 0.3)' : 'none',
              }}
            >
              SELL / SHORT
            </button>
          </div>

          {/* Instrument Dropdown */}
          <div style={{ marginBottom: '14px' }}>
            <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 600, textTransform: 'uppercase' }}>
              Instrument
            </label>
            <select
              value={selectedSymbol}
              onChange={(e) => {
                const s = e.target.value;
                setSelectedSymbol(s);
                if (marketQuotes[s]) setLimitPrice(marketQuotes[s].price);
                setErrorMessage(null);
              }}
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-medium)',
                backgroundColor: 'var(--bg-input)',
                color: '#FFFFFF',
                fontSize: '14px',
                fontWeight: 600,
                outline: 'none',
              }}
            >
              {Object.values(marketQuotes).map((item) => (
                <option key={item.symbol} value={item.symbol} style={{ background: '#111827', color: '#FFFFFF' }}>
                  {item.symbol} — ₹{item.price.toLocaleString('en-IN')}
                </option>
              ))}
            </select>
          </div>

          {/* Order Mechanism Tabs */}
          <div style={{ marginBottom: '14px' }}>
            <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 600, textTransform: 'uppercase' }}>
              Order Mechanism
            </label>
            <div style={{ display: 'flex', gap: '6px' }}>
              {(['MARKET', 'LIMIT', 'STOP_LOSS', 'SIP'] as OrderExecutionType[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setOrderType(t)}
                  style={{
                    flex: 1,
                    padding: '7px 4px',
                    fontSize: '11px',
                    fontWeight: 600,
                    borderRadius: 'var(--radius-xs)',
                    cursor: 'pointer',
                    border: orderType === t ? '1px solid var(--color-primary)' : '1px solid var(--border-subtle)',
                    background: orderType === t ? 'rgba(59, 130, 246, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                    color: orderType === t ? '#FFFFFF' : 'var(--text-muted)',
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* Limit Price Input */}
          {(orderType === 'LIMIT' || orderType === 'STOP_LOSS') && (
            <div style={{ marginBottom: '14px' }}>
              <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 600, textTransform: 'uppercase' }}>
                Limit / Trigger Price (₹)
              </label>
              <input
                type="number"
                value={limitPrice || currentQuote.price}
                onChange={(e) => setLimitPrice(Number(e.target.value))}
                step="0.5"
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-medium)',
                  backgroundColor: 'var(--bg-input)',
                  color: '#FFFFFF',
                  fontWeight: 600,
                }}
              />
            </div>
          )}

          {/* Quantity Stepper */}
          <div style={{ marginBottom: '18px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <label style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                Quantity (Shares)
              </label>
              <span style={{ fontSize: '12px', color: 'var(--text-faint)' }}>
                Owned: <strong style={{ color: '#FFFFFF' }}>{ownedShares}</strong>
              </span>
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                type="button"
                onClick={() => setShares((prev) => Math.max(1, prev - 1))}
                className="btn btn-secondary"
                style={{ width: '40px', padding: '0', fontSize: '16px', fontWeight: 700 }}
              >
                -
              </button>
              <input
                type="number"
                min="1"
                value={shares}
                onChange={(e) => setShares(Math.max(1, parseInt(e.target.value) || 1))}
                style={{
                  flex: 1,
                  textAlign: 'center',
                  padding: '9px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-medium)',
                  backgroundColor: 'var(--bg-input)',
                  color: '#FFFFFF',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '15px',
                  fontWeight: 700,
                  outline: 'none',
                }}
              />
              <button
                type="button"
                onClick={() => setShares((prev) => prev + 1)}
                className="btn btn-secondary"
                style={{ width: '40px', padding: '0', fontSize: '16px', fontWeight: 700 }}
              >
                +
              </button>
            </div>
          </div>

          {/* Financial Breakdown */}
          <div
            style={{
              backgroundColor: 'rgba(0, 0, 0, 0.3)',
              borderRadius: 'var(--radius-sm)',
              padding: '12px 14px',
              marginBottom: '18px',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
              fontSize: '12px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
              <span>Reference Fill Price</span>
              <span className="tabular-nums" style={{ color: '#FFFFFF' }}>₹{effectivePrice.toLocaleString('en-IN')}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
              <span>Estimated Order Value</span>
              <span className="tabular-nums" style={{ fontWeight: 700, fontSize: '14px', color: orderAction === 'BUY' ? 'var(--color-primary)' : 'var(--color-profit)' }}>
                ₹{orderTotal.toLocaleString('en-IN')}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
              <span>Brokerage & Regulatory Tax</span>
              <span className="badge badge-profit" style={{ fontSize: '10px' }}>₹0.00 (Paper Simulation)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '6px' }}>
              <span style={{ color: 'var(--text-muted)' }}>Virtual Cash After</span>
              <span className="tabular-nums" style={{ color: cashAfter < 0 ? 'var(--color-loss)' : 'var(--color-virtual)', fontWeight: 700 }}>
                ₹{cashAfter.toLocaleString('en-IN')}
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

          {/* Execute Button */}
          <button
            onClick={handleExecute}
            disabled={isExecuting || (orderAction === 'BUY' && orderTotal > virtualCash) || (orderAction === 'SELL' && ownedShares < shares)}
            className={orderAction === 'BUY' ? 'btn-emerald' : 'btn'}
            style={{
              width: '100%',
              padding: '13px',
              fontSize: '14px',
              fontWeight: 700,
              borderRadius: 'var(--radius-sm)',
              cursor: isExecuting ? 'not-allowed' : 'pointer',
              background: orderAction === 'SELL' ? 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)' : undefined,
              opacity: (orderAction === 'BUY' && orderTotal > virtualCash) || (orderAction === 'SELL' && ownedShares < shares) ? 0.5 : 1,
            }}
          >
            {isExecuting ? 'Routing to Ledger...' : `Execute ${orderAction} (${shares} shares) →`}
          </button>
        </div>

        {/* Column 2: Simulated Level-2 Order Book */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div>
              <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#FFFFFF', margin: 0 }}>Order Book (L2 Depth)</h3>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{selectedSymbol} simulated queue</span>
            </div>
            <span className="badge badge-cyan" style={{ fontSize: '10px' }}>5 Bids / 5 Asks</span>
          </div>

          {/* Asks (Sells in crimson) */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', marginBottom: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-faint)', textTransform: 'uppercase', marginBottom: '4px' }}>
              <span>Price (₹)</span>
              <span>Orders (Qty)</span>
            </div>
            {orderBookAsks.slice().reverse().map((ask, i) => (
              <div
                key={i}
                style={{
                  position: 'relative',
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '3px 6px',
                  fontSize: '12px',
                  borderRadius: '2px',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    position: 'absolute',
                    top: 0,
                    right: 0,
                    bottom: 0,
                    width: `${ask.depth}%`,
                    backgroundColor: 'rgba(239, 68, 68, 0.15)',
                    pointerEvents: 'none',
                  }}
                />
                <span className="tabular-nums" style={{ color: 'var(--color-loss)', fontWeight: 600 }}>
                  ₹{ask.price.toFixed(1)}
                </span>
                <span className="tabular-nums" style={{ color: '#D1D5DB' }}>
                  {ask.qty}
                </span>
              </div>
            ))}
          </div>

          {/* Spread / Mid-Market Price */}
          <div
            style={{
              padding: '8px 12px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'rgba(255, 255, 255, 0.04)',
              borderTop: '1px solid var(--border-subtle)',
              borderBottom: '1px solid var(--border-subtle)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              margin: '8px 0',
            }}
          >
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Market Mid-Spread</span>
            <span className="tabular-nums" style={{ fontSize: '15px', fontWeight: 700, color: '#FFFFFF' }}>
              ₹{effectivePrice.toLocaleString('en-IN')}
            </span>
          </div>

          {/* Bids (Buys in green) */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
            {orderBookBids.map((bid, i) => (
              <div
                key={i}
                style={{
                  position: 'relative',
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '3px 6px',
                  fontSize: '12px',
                  borderRadius: '2px',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    position: 'absolute',
                    top: 0,
                    right: 0,
                    bottom: 0,
                    width: `${bid.depth}%`,
                    backgroundColor: 'rgba(16, 185, 129, 0.15)',
                    pointerEvents: 'none',
                  }}
                />
                <span className="tabular-nums" style={{ color: 'var(--color-profit)', fontWeight: 600 }}>
                  ₹{bid.price.toFixed(1)}
                </span>
                <span className="tabular-nums" style={{ color: '#D1D5DB' }}>
                  {bid.qty}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Column 3: Active Positions & Atomic Ledger */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Active Positions */}
          <div className="glass-card" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#FFFFFF', margin: 0 }}>Active Positions</h3>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{holdings.length} Instruments</span>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-faint)', fontSize: '11px', textTransform: 'uppercase' }}>
                    <th style={{ padding: '8px 10px' }}>Instrument</th>
                    <th style={{ padding: '8px 10px' }}>Shares</th>
                    <th style={{ padding: '8px 10px' }}>Avg Cost</th>
                    <th style={{ padding: '8px 10px' }}>Current</th>
                    <th style={{ padding: '8px 10px' }}>P&L</th>
                    <th style={{ padding: '8px 10px', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {holdings.map((h) => {
                    const posVal = h.shares * h.currentPrice;
                    const posCost = h.shares * h.avgPrice;
                    const pnl = posVal - posCost;
                    const isPos = pnl >= 0;

                    return (
                      <tr key={h.symbol} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                        <td style={{ padding: '10px' }}>
                          <strong style={{ color: '#FFFFFF' }}>{h.symbol}</strong>
                          <div style={{ fontSize: '10px', color: 'var(--text-faint)' }}>{h.assetClass}</div>
                        </td>
                        <td style={{ padding: '10px' }} className="tabular-nums">{h.shares}</td>
                        <td style={{ padding: '10px' }} className="tabular-nums">₹{h.avgPrice.toLocaleString('en-IN')}</td>
                        <td style={{ padding: '10px' }} className="tabular-nums">₹{h.currentPrice.toLocaleString('en-IN')}</td>
                        <td style={{ padding: '10px' }}>
                          <span className={isPos ? 'badge badge-profit' : 'badge badge-loss'} style={{ fontSize: '10px' }}>
                            {isPos ? '+' : ''}₹{pnl.toLocaleString('en-IN')}
                          </span>
                        </td>
                        <td style={{ padding: '10px', textAlign: 'right' }}>
                          <div style={{ display: 'inline-flex', gap: '4px' }}>
                            <button
                              onClick={() => handleAddShares(h.symbol, 5)}
                              className="btn btn-secondary"
                              style={{ padding: '3px 8px', fontSize: '10px' }}
                              title="Buy 5 more shares at market price"
                            >
                              +5
                            </button>
                            <button
                              onClick={() => handleSquareOff(h.symbol, h.shares)}
                              className="btn btn-secondary"
                              style={{ padding: '3px 8px', fontSize: '10px', color: 'var(--color-loss)', borderColor: 'var(--color-loss-border)' }}
                              title="Square off position completely"
                            >
                              Exit All
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Recent Ledger Entries */}
          <div className="glass-card" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#FFFFFF', margin: 0 }}>Execution Ledger</h3>
              <span className="badge badge-cyan" style={{ fontSize: '10px' }}>Atomic Ledger</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {ledger.slice(0, 4).map((l) => (
                <div
                  key={l.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '10px 12px',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: 'rgba(255, 255, 255, 0.02)',
                    border: '1px solid var(--border-subtle)',
                    fontSize: '12px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className={l.type === 'BUY' ? 'badge badge-profit' : l.type === 'SELL' ? 'badge badge-loss' : 'badge badge-virtual'} style={{ fontSize: '9px' }}>
                      {l.type}
                    </span>
                    <strong style={{ color: '#FFFFFF' }}>{l.symbol}</strong>
                    <span style={{ color: 'var(--text-muted)' }}>({l.shares} sh)</span>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div className="tabular-nums" style={{ fontWeight: 600, color: '#FFFFFF' }}>₹{l.total.toLocaleString('en-IN')}</div>
                    <span style={{ fontSize: '10px', color: 'var(--text-faint)' }}>{l.timestamp.slice(0, 11)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Execution Confirmation Receipt Modal */}
      {lastReceipt && (
        <div className="modal-overlay" onClick={() => setLastReceipt(null)}>
          <div className="modal-content contract-note" style={{ maxWidth: '520px', padding: '32px' }} onClick={(e) => e.stopPropagation()}>
            <div className="compliance-watermark">FINEX</div>
            <div style={{ textAlign: 'center', marginBottom: '20px' }}>
              <div
                style={{
                  width: '52px',
                  height: '52px',
                  borderRadius: '50%',
                  background: 'rgba(16, 185, 129, 0.15)',
                  border: '1.5px solid var(--color-profit)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 12px auto',
                  fontSize: '22px',
                  color: 'var(--color-profit)',
                }}
              >
                ✓
              </div>
              <span className="badge badge-profit">{lastReceipt.id} • {lastReceipt.status}</span>
              <h3 style={{ fontSize: '22px', fontWeight: 700, color: '#FFFFFF', marginTop: '6px' }}>
                Order Executed Successfully
              </h3>
            </div>

            <div style={{ backgroundColor: 'rgba(0,0,0,0.4)', padding: '16px', borderRadius: 'var(--radius-sm)', marginBottom: '20px', fontSize: '13px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Security:</span>
                <strong style={{ color: '#FFFFFF' }}>{lastReceipt.symbol}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Action:</span>
                <span style={{ color: '#FFFFFF' }}>{lastReceipt.type} ({lastReceipt.orderType})</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Quantity:</span>
                <span style={{ color: '#FFFFFF' }}>{lastReceipt.shares} shares</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Unit Fill Rate:</span>
                <span style={{ color: '#FFFFFF' }}>₹{lastReceipt.fillPrice.toLocaleString('en-IN')}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Total Consideration:</span>
                <span style={{ color: '#FFFFFF', fontWeight: 700 }}>₹{lastReceipt.total.toLocaleString('en-IN')}</span>
              </div>
              {lastReceipt.realizedPnL !== undefined && (
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Realized Profit / Loss:</span>
                  <span className={lastReceipt.realizedPnL >= 0 ? 'badge badge-profit' : 'badge badge-loss'}>
                    {lastReceipt.realizedPnL >= 0 ? '+' : ''}₹{lastReceipt.realizedPnL.toLocaleString('en-IN')}
                  </span>
                </div>
              )}
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '8px', marginTop: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Paper Cash Balance After:</span>
                <span style={{ color: 'var(--color-virtual)', fontWeight: 700 }}>₹{lastReceipt.cashAfter.toLocaleString('en-IN')}</span>
              </div>
            </div>

            <button onClick={() => setLastReceipt(null)} className="btn btn-primary" style={{ width: '100%' }}>
              Dismiss Receipt
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
