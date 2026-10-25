import React, { useState } from 'react';
import { useFinancial, LedgerEntry } from '../../context/FinancialContext';
import { NavigationTab } from '../layout/AppShell';

interface RecentTransactionsProps {
  title?: string;
  maxItems?: number;
  showFilters?: boolean;
  onNavigate?: (tab: NavigationTab) => void;
  className?: string;
}

export const RecentTransactions: React.FC<RecentTransactionsProps> = ({
  title = 'Recent Transactions & Execution Activity',
  maxItems,
  showFilters = true,
  onNavigate,
  className = '',
}) => {
  const { ledger } = useFinancial();
  const [sideFilter, setSideFilter] = useState<'ALL' | 'BUY' | 'SELL'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEntry, setSelectedEntry] = useState<LedgerEntry | null>(null);

  // Filter transactions: newest-first is default
  const filteredLedger = ledger.filter((entry) => {
    const matchesSide = sideFilter === 'ALL' || entry.type === sideFilter;
    const matchesSearch =
      searchQuery.trim() === '' ||
      entry.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      entry.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (entry.name && entry.name.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesSide && matchesSearch;
  });

  const displayedEntries = maxItems ? filteredLedger.slice(0, maxItems) : filteredLedger;

  return (
    <div
      className={`glass-card ${className}`}
      style={{
        padding: '24px',
        width: '100%',
        minWidth: 0,
        boxSizing: 'border-box',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
      }}
    >
      {/* Header & Controls */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '14px',
          width: '100%',
          minWidth: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#FFFFFF', margin: 0 }}>
            {title}
          </h3>
          <span className="badge badge-neutral" style={{ fontSize: '11px' }}>
            {ledger.length} {ledger.length === 1 ? 'Trade' : 'Trades'}
          </span>
        </div>

        {onNavigate && (
          <button
            type="button"
            onClick={() => onNavigate('transactions')}
            className="btn btn-secondary"
            style={{ padding: '4px 10px', fontSize: '11px', cursor: 'pointer' }}
          >
            Audit Ledger →
          </button>
        )}
      </div>

      {/* Filter Ribbon: Search + Buy/Sell Filters */}
      {showFilters && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '12px',
            padding: '10px 14px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          {/* Side Filter Pills */}
          <div style={{ display: 'flex', gap: '6px' }}>
            {(['ALL', 'BUY', 'SELL'] as const).map((side) => {
              const isActive = sideFilter === side;
              return (
                <button
                  key={side}
                  type="button"
                  onClick={() => setSideFilter(side)}
                  style={{
                    padding: '5px 12px',
                    borderRadius: 'var(--radius-xs)',
                    border: isActive ? '1px solid var(--color-action)' : '1px solid transparent',
                    background: isActive ? 'var(--color-action-bg)' : 'transparent',
                    color: isActive ? 'var(--color-action)' : 'var(--text-muted)',
                    fontSize: '11.5px',
                    fontWeight: isActive ? 600 : 500,
                    cursor: 'pointer',
                    transition: 'all var(--transition-fast)',
                  }}
                >
                  {side === 'ALL' ? 'All Sides' : side === 'BUY' ? 'Buys' : 'Sells'}
                </button>
              );
            })}
          </div>

          {/* Search Box */}
          <div style={{ flex: '0 1 240px', minWidth: '160px' }}>
            <input
              type="text"
              placeholder="Search symbol or order ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '6px 12px',
                borderRadius: 'var(--radius-xs)',
                border: '1px solid var(--border-medium)',
                backgroundColor: 'var(--bg-input)',
                color: '#FFFFFF',
                fontSize: '12px',
                outline: 'none',
                boxSizing: 'border-box',
              }}
            />
          </div>
        </div>
      )}

      {/* Transactions Feed / Table */}
      {displayedEntries.length === 0 ? (
        /* Honest Empty State — No mock or placeholder data */
        <div
          style={{
            textAlign: 'center',
            padding: '48px 20px',
            backgroundColor: 'rgba(255, 255, 255, 0.01)',
            borderRadius: 'var(--radius-sm)',
            border: '1px dashed var(--border-subtle)',
          }}
        >
          <div style={{ fontSize: '28px', marginBottom: '8px' }}>📜</div>
          <div style={{ fontSize: '14px', fontWeight: 600, color: '#FFFFFF', marginBottom: '4px' }}>
            {ledger.length === 0
              ? 'No trades yet — your paper trades will appear here'
              : 'No transactions match the selected filter'}
          </div>
          <p
            style={{
              fontSize: '12px',
              color: 'var(--text-muted)',
              maxWidth: '380px',
              margin: '0 auto 16px auto',
              lineHeight: 1.5,
            }}
          >
            {ledger.length === 0
              ? 'Simulate your first buy or sell order on the Practice desk or test historical strategies with Trade Time Machine.'
              : 'Try clearing your search query or selecting a different filter.'}
          </p>
          {ledger.length === 0 && onNavigate && (
            <button
              type="button"
              onClick={() => onNavigate('practice')}
              className="btn-emerald"
              style={{
                padding: '8px 18px',
                fontSize: '12px',
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
              }}
            >
              Open Practice Desk →
            </button>
          )}
        </div>
      ) : (
        <div className="table-scroll-wrapper" style={{ maxHeight: '480px', overflowY: 'auto' }}>
          <table
            style={{
              width: '100%',
              minWidth: '640px',
              borderCollapse: 'collapse',
              textAlign: 'left',
              fontSize: '13px',
            }}
          >
            <thead>
              <tr
                style={{
                  borderBottom: '1px solid var(--border-subtle)',
                  color: 'var(--text-faint)',
                  fontSize: '11px',
                  textTransform: 'uppercase',
                }}
              >
                <th style={{ padding: '10px 14px' }}>Side / Status</th>
                <th style={{ padding: '10px 14px' }}>Symbol</th>
                <th style={{ padding: '10px 14px' }}>Quantity</th>
                <th style={{ padding: '10px 14px' }}>Exec Price</th>
                <th style={{ padding: '10px 14px' }}>Total Value</th>
                <th style={{ padding: '10px 14px' }}>Realized P&L</th>
                <th style={{ padding: '10px 14px' }}>Time</th>
                <th style={{ padding: '10px 14px', textAlign: 'right' }}>Slip</th>
              </tr>
            </thead>
            <tbody>
              {displayedEntries.map((entry) => {
                const isBuy = entry.type === 'BUY';
                const isSell = entry.type === 'SELL';
                const isReplay = Boolean(entry.isReplay || entry.notes?.includes('REPLAY'));

                return (
                  <tr
                    key={entry.id}
                    onClick={() => setSelectedEntry(entry)}
                    style={{
                      borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                      cursor: 'pointer',
                      transition: 'background-color var(--transition-fast)',
                    }}
                    onMouseEnter={(e) =>
                      (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.02)')
                    }
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.backgroundColor = 'transparent')
                    }
                  >
                    {/* Side & Status */}
                    <td style={{ padding: '12px 14px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span
                          className={
                            isBuy
                              ? 'badge badge-profit'
                              : isSell
                              ? 'badge badge-loss'
                              : 'badge badge-virtual'
                          }
                          style={{ fontSize: '10px', fontWeight: 700 }}
                        >
                          {entry.type}
                        </span>
                        {isReplay && (
                          <span
                            style={{
                              backgroundColor: 'rgba(245, 158, 11, 0.2)',
                              color: '#FBBF24',
                              border: '1px solid rgba(245, 158, 11, 0.4)',
                              borderRadius: '3px',
                              padding: '1px 5px',
                              fontSize: '9px',
                              fontWeight: 800,
                            }}
                          >
                            REPLAY
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Symbol */}
                    <td style={{ padding: '12px 14px' }}>
                      <div className="truncate-text" style={{ maxWidth: '140px' }}>
                        <strong style={{ color: '#FFFFFF', fontSize: '13px' }}>
                          {entry.symbol}
                        </strong>
                        {entry.name && (
                          <div style={{ fontSize: '11px', color: 'var(--text-faint)' }}>
                            {entry.name}
                          </div>
                        )}
                      </div>
                    </td>

                    {/* Quantity */}
                    <td style={{ padding: '12px 14px' }} className="tabular-nums">
                      {entry.type === 'DEPOSIT' ? '1 Unit' : `${entry.shares} sh`}
                    </td>

                    {/* Price */}
                    <td style={{ padding: '12px 14px' }} className="tabular-nums">
                      ₹{entry.fillPrice.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>

                    {/* Total Value */}
                    <td
                      style={{ padding: '12px 14px', fontWeight: 600, color: '#FFFFFF' }}
                      className="tabular-nums"
                    >
                      ₹{entry.total.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>

                    {/* Realized P&L on Sells */}
                    <td style={{ padding: '12px 14px' }}>
                      {isSell && entry.realizedPnL !== undefined ? (
                        <span
                          className={
                            entry.realizedPnL >= 0 ? 'badge badge-profit' : 'badge badge-loss'
                          }
                          style={{ fontSize: '10.5px' }}
                        >
                          {entry.realizedPnL >= 0 ? '+' : ''}₹
                          {entry.realizedPnL.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-faint)' }}>—</span>
                      )}
                    </td>

                    {/* Timestamp */}
                    <td style={{ padding: '12px 14px', fontSize: '11.5px', color: 'var(--text-muted)' }}>
                      {entry.timestamp}
                    </td>

                    {/* Detail Slip CTA */}
                    <td style={{ padding: '12px 14px', textAlign: 'right' }}>
                      <span
                        style={{
                          fontSize: '11px',
                          color: 'var(--color-action)',
                          fontWeight: 500,
                        }}
                      >
                        Receipt →
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Execution Contract Slip Detail Modal */}
      {selectedEntry && (
        <div className="modal-overlay" onClick={() => setSelectedEntry(null)}>
          <div
            className="modal-content contract-note"
            style={{ maxWidth: '520px', padding: '32px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="compliance-watermark">FINEX</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <span className="badge badge-neutral" style={{ fontSize: '10px', marginBottom: '6px' }}>
                  TRADE CONFIRMATION • {selectedEntry.id}
                </span>
                <h3 style={{ fontSize: '20px', fontWeight: 700, color: '#FFFFFF', margin: 0 }}>
                  Electronic Contract Note
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedEntry(null)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-muted)',
                  fontSize: '20px',
                  cursor: 'pointer',
                  padding: '2px 6px',
                }}
              >
                ×
              </button>
            </div>

            <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '8px 0 20px 0' }}>
              Execution confirmed on FinEx simulated matching engine.
            </p>

            <div
              style={{
                backgroundColor: 'rgba(0,0,0,0.4)',
                padding: '16px',
                borderRadius: 'var(--radius-sm)',
                marginBottom: '20px',
                fontSize: '13px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Security Symbol:</span>
                <strong style={{ color: '#FFFFFF' }}>{selectedEntry.symbol}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Side & Type:</span>
                <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                  <span
                    className={
                      selectedEntry.type === 'BUY'
                        ? 'badge badge-profit'
                        : selectedEntry.type === 'SELL'
                        ? 'badge badge-loss'
                        : 'badge badge-virtual'
                    }
                  >
                    {selectedEntry.type} ({selectedEntry.orderType})
                  </span>
                  {(selectedEntry.isReplay || selectedEntry.notes?.includes('REPLAY')) && (
                    <span
                      style={{
                        backgroundColor: 'rgba(245, 158, 11, 0.2)',
                        color: '#FBBF24',
                        border: '1px solid rgba(245, 158, 11, 0.4)',
                        borderRadius: '3px',
                        padding: '1px 5px',
                        fontSize: '9px',
                        fontWeight: 800,
                      }}
                    >
                      REPLAY
                    </span>
                  )}
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Quantity Executed:</span>
                <span style={{ color: '#FFFFFF' }}>{selectedEntry.shares} shares</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Execution Price:</span>
                <span style={{ color: '#FFFFFF' }}>
                  ₹{selectedEntry.fillPrice.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Gross Consideration:</span>
                <span style={{ color: '#FFFFFF', fontWeight: 700 }}>
                  ₹{selectedEntry.total.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
              {selectedEntry.type === 'SELL' && selectedEntry.realizedPnL !== undefined && (
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Realized Profit / Loss:</span>
                  <span
                    className={
                      selectedEntry.realizedPnL >= 0 ? 'badge badge-profit' : 'badge badge-loss'
                    }
                  >
                    {selectedEntry.realizedPnL >= 0 ? '+' : ''}₹
                    {selectedEntry.realizedPnL.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </span>
                </div>
              )}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  borderTop: '1px solid var(--border-subtle)',
                  paddingTop: '10px',
                  marginTop: '4px',
                }}
              >
                <span style={{ color: 'var(--text-muted)' }}>Virtual Cash After:</span>
                <span style={{ color: 'var(--color-virtual)', fontWeight: 700 }}>
                  ₹{selectedEntry.cashAfter.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Execution Timestamp:</span>
                <span style={{ color: 'var(--text-primary)', fontSize: '12px' }}>
                  {selectedEntry.timestamp}
                </span>
              </div>
            </div>

            {selectedEntry.notes && (
              <div
                style={{
                  fontSize: '11.5px',
                  color: 'var(--text-muted)',
                  backgroundColor: 'rgba(255, 255, 255, 0.02)',
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-xs)',
                  border: '1px solid var(--border-subtle)',
                  marginBottom: '20px',
                }}
              >
                {selectedEntry.notes}
              </div>
            )}

            <button
              type="button"
              onClick={() => setSelectedEntry(null)}
              className="btn btn-secondary"
              style={{ width: '100%', cursor: 'pointer' }}
            >
              Close Receipt
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default RecentTransactions;
