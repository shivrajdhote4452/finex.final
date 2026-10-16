import React, { useState } from 'react';
import { useFinancial, LedgerEntry } from '../context/FinancialContext';

export const TransactionsScreen: React.FC = () => {
  const {
    ledger,
    totalTradesCount,
    totalTradedVolume,
    totalRealizedPnL,
    openQuickTrade,
    depositFunds,
  } = useFinancial();


  const [activeFilter, setActiveFilter] = useState<'ALL' | 'BUY' | 'SELL' | 'SIP' | 'DEPOSIT'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNote, setSelectedNote] = useState<LedgerEntry | null>(null);
  const [showDepositModal, setShowDepositModal] = useState(false);
  const [depositAmount, setDepositAmount] = useState<number>(50000);

  // Filtered transactions
  const filteredLedger = ledger.filter((entry) => {
    const matchesFilter = activeFilter === 'ALL' || entry.type === activeFilter;
    const matchesSearch =
      entry.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      entry.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (entry.name && entry.name.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesFilter && matchesSearch;
  });

  // Calculate stats
  const buyCount = ledger.filter((l) => l.type === 'BUY').length;
  const sellOrders = ledger.filter((l) => l.type === 'SELL' && l.realizedPnL !== undefined);
  const winningTrades = sellOrders.filter((l) => (l.realizedPnL || 0) > 0).length;
  const winRate = sellOrders.length > 0 ? Math.round((winningTrades / sellOrders.length) * 100) : 100;
  const simulatedBrokerageSaved = totalTradesCount * 20; // ₹20 flat discount broker fee saved

  // Export to CSV function
  const handleExportCSV = () => {
    const headers = ['Order ID', 'Timestamp', 'Type', 'Order Mechanism', 'Symbol', 'Shares', 'Fill Price', 'Total (INR)', 'Realized PnL (INR)', 'Cash After', 'Status'];
    const rows = ledger.map((l) => [
      l.id,
      `"${l.timestamp}"`,
      l.type,
      l.orderType,
      l.symbol,
      l.shares,
      l.fillPrice,
      l.total,
      l.realizedPnL ?? 0,
      l.cashAfter,
      l.status,
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `finex_transactions_ledger_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDepositSubmit = () => {
    depositFunds(depositAmount);
    setShowDepositModal(false);
  };

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '32px' }}>
      {/* Top Header & Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-primary)', fontWeight: 600 }}>
            Audit & Execution Desk
          </span>
          <h1 style={{ fontSize: '36px', fontWeight: 700, color: '#FFFFFF', marginTop: '4px', letterSpacing: '-0.02em' }}>
            Transaction Ledger & Trade History
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
            Every simulated order execution is immutably recorded with real-time balance reconciliation.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button onClick={() => setShowDepositModal(true)} className="btn btn-secondary">
            💰 Add Paper Cash
          </button>
          <button onClick={handleExportCSV} className="btn btn-secondary">
            📥 Export to CSV
          </button>
          <button onClick={() => openQuickTrade()} className="btn-emerald" style={{ padding: '10px 20px', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }}>
            ⚡ Place New Trade
          </button>
        </div>
      </div>

      {/* KPI Highlights Ribbon */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '16px' }}>
        <div className="glass-card" style={{ padding: '20px' }}>
          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>
            Traded Volume
          </span>
          <div className="tabular-nums" style={{ fontSize: '28px', fontWeight: 700, color: '#FFFFFF', marginTop: '6px' }}>
            ₹{totalTradedVolume.toLocaleString('en-IN')}
          </div>
          <span style={{ fontSize: '12px', color: 'var(--text-faint)' }}>Gross cumulative turnover</span>
        </div>

        <div className="glass-card" style={{ padding: '20px' }}>
          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>
            Realized P&L
          </span>
          <div className="tabular-nums" style={{ fontSize: '28px', fontWeight: 700, color: totalRealizedPnL >= 0 ? 'var(--color-profit)' : 'var(--color-loss)', marginTop: '6px' }}>
            {totalRealizedPnL >= 0 ? '+' : ''}₹{totalRealizedPnL.toLocaleString('en-IN')}
          </div>
          <span className={totalRealizedPnL >= 0 ? 'badge badge-profit' : 'badge badge-loss'} style={{ fontSize: '10px', marginTop: '4px' }}>
            Closed positions return
          </span>
        </div>

        <div className="glass-card" style={{ padding: '20px' }}>
          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>
            Total Executed
          </span>
          <div className="tabular-nums" style={{ fontSize: '28px', fontWeight: 700, color: '#FFFFFF', marginTop: '6px' }}>
            {totalTradesCount} Orders
          </div>
          <span style={{ fontSize: '12px', color: 'var(--text-faint)' }}>{buyCount} Buys • {sellOrders.length} Sells</span>
        </div>

        <div className="glass-card" style={{ padding: '20px' }}>
          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>
            Trade Win Rate
          </span>
          <div className="tabular-nums" style={{ fontSize: '28px', fontWeight: 700, color: 'var(--color-accent-cyan)', marginTop: '6px' }}>
            {winRate}%
          </div>
          <span style={{ fontSize: '12px', color: 'var(--text-faint)' }}>Profitable closed sells</span>
        </div>

        <div className="glass-card" style={{ padding: '20px', border: '1px solid var(--color-virtual-border)' }}>
          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-virtual)', fontWeight: 600 }}>
            Simulated Fees Saved
          </span>
          <div className="tabular-nums" style={{ fontSize: '28px', fontWeight: 700, color: 'var(--color-virtual)', marginTop: '6px' }}>
            ₹{simulatedBrokerageSaved.toLocaleString('en-IN')}
          </div>
          <span style={{ fontSize: '12px', color: 'var(--text-faint)' }}>Zero broker commission</span>
        </div>
      </div>

      {/* Filter Tabs & Search Bar */}
      <div className="glass-card" style={{ padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          {[
            { id: 'ALL', label: 'All Operations' },
            { id: 'BUY', label: 'Buy Orders' },
            { id: 'SELL', label: 'Sell Orders' },
            { id: 'SIP', label: 'Recurring SIP' },
            { id: 'DEPOSIT', label: 'Cash Injections' },
          ].map((tab) => {
            const isActive = activeFilter === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveFilter(tab.id as any)}
                style={{
                  background: isActive ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
                  border: isActive ? '1px solid var(--color-primary)' : '1px solid transparent',
                  borderRadius: 'var(--radius-sm)',
                  color: isActive ? '#FFFFFF' : 'var(--text-muted)',
                  fontSize: '13px',
                  fontWeight: isActive ? 600 : 500,
                  padding: '8px 16px',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Search Input */}
        <div style={{ width: '300px' }}>
          <input
            type="text"
            placeholder="Search order ID or symbol..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '8px 14px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-medium)',
              backgroundColor: 'var(--bg-input)',
              color: '#FFFFFF',
              fontSize: '13px',
            }}
          />
        </div>
      </div>

      {/* Transaction Ledger Table */}
      <div className="glass-card" style={{ padding: '24px' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-faint)', fontSize: '11px', textTransform: 'uppercase' }}>
                <th style={{ padding: '12px 14px' }}>Order ID & Time</th>
                <th style={{ padding: '12px 14px' }}>Action</th>
                <th style={{ padding: '12px 14px' }}>Instrument</th>
                <th style={{ padding: '12px 14px' }}>Quantity</th>
                <th style={{ padding: '12px 14px' }}>Execution Price</th>
                <th style={{ padding: '12px 14px' }}>Total Consideration</th>
                <th style={{ padding: '12px 14px' }}>Realized Gain</th>
                <th style={{ padding: '12px 14px' }}>Cash Balance</th>
                <th style={{ padding: '12px 14px', textAlign: 'right' }}>Slip</th>
              </tr>
            </thead>
            <tbody>
              {filteredLedger.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    No transactions match the selected criteria.
                  </td>
                </tr>
              ) : (
                filteredLedger.map((entry) => {
                  const isBuy = entry.type === 'BUY';
                  const isSell = entry.type === 'SELL';
                  const isDeposit = entry.type === 'DEPOSIT';

                  return (

                    <tr
                      key={entry.id}
                      style={{
                        borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                        transition: 'background 0.15s ease',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.02)')}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                    >
                      {/* ID & Timestamp */}
                      <td style={{ padding: '14px' }}>
                        <strong style={{ color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>{entry.id}</strong>
                        <div style={{ fontSize: '11px', color: 'var(--text-faint)' }}>{entry.timestamp}</div>
                      </td>

                      {/* Action Pill */}
                      <td style={{ padding: '14px' }}>
                        <span
                          className={
                            isBuy
                              ? 'badge badge-profit'
                              : isSell
                              ? 'badge badge-loss'
                              : isDeposit
                              ? 'badge badge-virtual'
                              : 'badge badge-cyan'
                          }
                          style={{ fontSize: '11px', fontWeight: 700 }}
                        >
                          {entry.type} • {entry.orderType}
                        </span>
                      </td>

                      {/* Instrument */}
                      <td style={{ padding: '14px' }}>
                        <strong style={{ color: '#FFFFFF' }}>{entry.symbol}</strong>
                        {entry.name && <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{entry.name}</div>}
                      </td>

                      {/* Shares */}
                      <td style={{ padding: '14px' }} className="tabular-nums">
                        {isDeposit ? '1 Unit' : `${entry.shares} sh`}
                      </td>

                      {/* Fill Price */}
                      <td style={{ padding: '14px' }} className="tabular-nums">
                        ₹{entry.fillPrice.toLocaleString('en-IN')}
                      </td>

                      {/* Total */}
                      <td style={{ padding: '14px', fontWeight: 600 }} className="tabular-nums">
                        ₹{entry.total.toLocaleString('en-IN')}
                      </td>

                      {/* Realized PnL */}
                      <td style={{ padding: '14px' }}>
                        {entry.realizedPnL !== undefined ? (
                          <span className={entry.realizedPnL >= 0 ? 'badge badge-profit' : 'badge badge-loss'}>
                            {entry.realizedPnL >= 0 ? '+' : ''}₹{entry.realizedPnL.toLocaleString('en-IN')}
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-faint)' }}>—</span>
                        )}
                      </td>

                      {/* Cash After */}
                      <td style={{ padding: '14px', color: 'var(--color-virtual)' }} className="tabular-nums">
                        ₹{entry.cashAfter.toLocaleString('en-IN')}
                      </td>

                      {/* Contract Slip Button */}
                      <td style={{ padding: '14px', textAlign: 'right' }}>
                        <button
                          onClick={() => setSelectedNote(entry)}
                          className="btn btn-secondary"
                          style={{ padding: '4px 10px', fontSize: '11px' }}
                        >
                          Contract Note →
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Contract Note Modal */}
      {selectedNote && (
        <div className="modal-overlay" onClick={() => setSelectedNote(null)}>
          <div
            className="modal-content contract-note"
            style={{ maxWidth: '640px', padding: '36px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="compliance-watermark">FINEX SIMULATION</div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '20px', marginBottom: '24px' }}>
              <div>
                <span className="badge badge-cyan" style={{ marginBottom: '8px' }}>
                  Electronic Contract Note
                </span>
                <h2 style={{ fontSize: '22px', fontWeight: 700, color: '#FFFFFF', margin: 0 }}>
                  Order Fill Confirmation
                </h2>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Reference No: {selectedNote.id} • Settlement Route: NSE-SIM
                </span>
              </div>

              <button
                onClick={() => setSelectedNote(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  fontSize: '20px',
                  cursor: 'pointer',
                }}
              >
                ✕
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px', fontSize: '13px' }}>
              <div>
                <span style={{ color: 'var(--text-faint)', fontSize: '11px', textTransform: 'uppercase' }}>Client Identifier</span>
                <div style={{ color: '#FFFFFF', fontWeight: 600 }}>Shivraj Dhote (FINEX-SD-01)</div>
              </div>
              <div>
                <span style={{ color: 'var(--text-faint)', fontSize: '11px', textTransform: 'uppercase' }}>Execution Timestamp</span>
                <div style={{ color: '#FFFFFF' }}>{selectedNote.timestamp}</div>
              </div>
              <div>
                <span style={{ color: 'var(--text-faint)', fontSize: '11px', textTransform: 'uppercase' }}>Order Mechanism</span>
                <div style={{ color: '#FFFFFF' }}>{selectedNote.orderType} • Cash Delivery (Paper)</div>
              </div>
              <div>
                <span style={{ color: 'var(--text-faint)', fontSize: '11px', textTransform: 'uppercase' }}>Execution Status</span>
                <div style={{ color: 'var(--color-profit)', fontWeight: 600 }}>{selectedNote.status} (Immediate Match)</div>
              </div>
            </div>

            {/* Financial Consideration Breakdown Table */}
            <div style={{ backgroundColor: 'rgba(0, 0, 0, 0.4)', borderRadius: 'var(--radius-sm)', padding: '16px', marginBottom: '20px', fontSize: '13px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Security / Symbol:</span>
                <strong style={{ color: '#FFFFFF' }}>{selectedNote.symbol} — {selectedNote.name || selectedNote.symbol}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Quantity Executed:</span>
                <span className="tabular-nums" style={{ color: '#FFFFFF' }}>{selectedNote.shares} shares</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Unit Execution Price:</span>
                <span className="tabular-nums" style={{ color: '#FFFFFF' }}>₹{selectedNote.fillPrice.toLocaleString('en-IN')}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Gross Consideration:</span>
                <span className="tabular-nums" style={{ color: '#FFFFFF', fontWeight: 700 }}>₹{selectedNote.total.toLocaleString('en-IN')}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Brokerage (Educational Sandbox):</span>
                <span style={{ color: 'var(--color-profit)' }}>₹0.00 (Free)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>STT / Exchange Charges:</span>
                <span style={{ color: 'var(--color-profit)' }}>₹0.00 (Simulated)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '8px', marginTop: '8px' }}>
                <span style={{ color: '#FFFFFF', fontWeight: 600 }}>Net Virtual Cash Impact:</span>
                <span className="tabular-nums" style={{ color: 'var(--color-virtual)', fontWeight: 700, fontSize: '15px' }}>
                  {selectedNote.type === 'BUY' ? '-' : '+'}₹{selectedNote.total.toLocaleString('en-IN')}
                </span>
              </div>
            </div>

            <div style={{ fontSize: '11px', color: 'var(--text-faint)', lineHeight: 1.5, marginBottom: '24px' }}>
              Note: This electronic contract note is issued strictly for educational simulation purposes on the FinEx platform. No real security was transferred, and no brokerage liability was incurred. Grounded in SEBI guidelines on simulated paper trading risk disclosure.
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button onClick={() => setSelectedNote(null)} className="btn btn-primary" style={{ padding: '10px 24px' }}>
                Close Contract Note
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Paper Cash Modal */}
      {showDepositModal && (
        <div className="modal-overlay" onClick={() => setShowDepositModal(false)}>
          <div
            className="modal-content"
            style={{ maxWidth: '440px', padding: '32px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ fontSize: '20px', fontWeight: 700, color: '#FFFFFF', marginBottom: '8px' }}>
              Inject Virtual Paper Capital
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '20px' }}>
              Add simulated funds to your paper trading ledger to practice larger portfolio allocations.
            </p>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', fontWeight: 600 }}>
                Select Allocation Amount
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', marginBottom: '16px' }}>
                {[25000, 50000, 100000].map((amt) => (
                  <button
                    key={amt}
                    onClick={() => setDepositAmount(amt)}
                    style={{
                      padding: '12px 6px',
                      borderRadius: 'var(--radius-sm)',
                      border: depositAmount === amt ? '1px solid var(--color-virtual)' : '1px solid var(--border-subtle)',
                      background: depositAmount === amt ? 'rgba(245, 158, 11, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                      color: depositAmount === amt ? 'var(--color-virtual)' : 'var(--text-muted)',
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    +₹{(amt / 1000).toFixed(0)}k
                  </button>
                ))}
              </div>

              <input
                type="number"
                value={depositAmount}
                onChange={(e) => setDepositAmount(Math.max(1000, Number(e.target.value)))}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-medium)',
                  backgroundColor: 'var(--bg-input)',
                  color: '#FFFFFF',
                  fontWeight: 700,
                  fontSize: '18px',
                }}
              />
            </div>

            <div style={{ display: 'flex', gap: '12px' }}>
              <button onClick={() => setShowDepositModal(false)} className="btn btn-secondary" style={{ flex: 1 }}>
                Cancel
              </button>
              <button
                onClick={handleDepositSubmit}
                className="btn btn-primary"
                style={{ flex: 1 }}
              >
                Confirm Injection →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
