import React, { useState } from 'react';
import { useFinancial } from '../context/FinancialContext';

export const SpendingScreen: React.FC = () => {
  const { spendingItems, addSpendingItem } = useFinancial();
  const [activeCategory, setActiveCategory] = useState<string>('All');
  const [searchTerm, setSearchTerm] = useState('');
  const [view, setView] = useState<'transactions' | 'csv-import'>('transactions');
  const [showAddModal, setShowAddModal] = useState(false);
  const [newMerchant, setNewMerchant] = useState('');
  const [newCategory, setNewCategory] = useState('Food & Dining');
  const [newAmount, setNewAmount] = useState<number>(500);

  const categories = ['All', 'Food & Dining', 'Shopping', 'Transport', 'Bills & Utilities', 'Healthcare', 'Entertainment'];

  const filtered = spendingItems.filter((tx) => {
    const matchesCat = activeCategory === 'All' || tx.category === activeCategory;
    const matchesSearch = tx.merchant.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesCat && matchesSearch;
  });

  const totalSpent = spendingItems.reduce((sum, item) => sum + item.amount, 0);

  const handleAddSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMerchant || newAmount <= 0) return;
    addSpendingItem(newMerchant, newCategory, newAmount);
    setNewMerchant('');
    setNewAmount(500);
    setShowAddModal(false);
  };

  if (view === 'csv-import') {
    return (
      <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '28px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-primary)', fontWeight: 600 }}>
              Privacy-Preserving Ingestion
            </span>
            <h1 style={{ fontSize: '32px', fontWeight: 700, color: '#FFFFFF', marginTop: '4px' }}>
              CSV Audit & Staging Preview
            </h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
              Raw merchant descriptions are masked server-side before category enrichment.
            </p>
          </div>
          <button onClick={() => setView('transactions')} className="btn btn-secondary">
            ← Back to Transactions
          </button>
        </div>

        {/* Audit Metrics */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px' }}>
          <div className="glass-card" style={{ padding: '20px' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Rows Parsed</span>
            <div className="tabular-nums" style={{ fontSize: '32px', fontWeight: 700, color: '#FFFFFF', marginTop: '6px' }}>128</div>
          </div>
          <div className="glass-card" style={{ padding: '20px' }}>
            <span style={{ fontSize: '11px', color: 'var(--color-profit)', textTransform: 'uppercase' }}>Valid Staged</span>
            <div className="tabular-nums" style={{ fontSize: '32px', fontWeight: 700, color: 'var(--color-profit)', marginTop: '6px' }}>120</div>
          </div>
          <div className="glass-card" style={{ padding: '20px' }}>
            <span style={{ fontSize: '11px', color: 'var(--color-virtual)', textTransform: 'uppercase' }}>Duplicates</span>
            <div className="tabular-nums" style={{ fontSize: '32px', fontWeight: 700, color: 'var(--color-virtual)', marginTop: '6px' }}>5</div>
          </div>
          <div className="glass-card" style={{ padding: '20px' }}>
            <span style={{ fontSize: '11px', color: 'var(--color-loss)', textTransform: 'uppercase' }}>Requires Fix</span>
            <div className="tabular-nums" style={{ fontSize: '32px', fontWeight: 700, color: 'var(--color-loss)', marginTop: '6px' }}>3</div>
          </div>
        </div>

        {/* Preview Table */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-faint)', fontSize: '11px', textTransform: 'uppercase' }}>
                <th style={{ padding: '10px 14px' }}>Date</th>
                <th style={{ padding: '10px 14px' }}>Masked Merchant</th>
                <th style={{ padding: '10px 14px' }}>Amount</th>
                <th style={{ padding: '10px 14px' }}>Inferred Category</th>
                <th style={{ padding: '10px 14px', textAlign: 'right' }}>Audit Status</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                <td style={{ padding: '12px 14px' }}>05 Oct 2026</td>
                <td style={{ padding: '12px 14px' }}>Merchant ••42</td>
                <td style={{ padding: '12px 14px' }} className="tabular-nums">₹1,200.00</td>
                <td style={{ padding: '12px 14px' }}>Shopping</td>
                <td style={{ padding: '12px 14px', textAlign: 'right' }}>
                  <span className="badge badge-profit">Valid</span>
                </td>
              </tr>
              <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                <td style={{ padding: '12px 14px' }}>06 Oct 2026</td>
                <td style={{ padding: '12px 14px' }}>Merchant ••86</td>
                <td style={{ padding: '12px 14px' }} className="tabular-nums">₹650.00</td>
                <td style={{ padding: '12px 14px' }}>Transport</td>
                <td style={{ padding: '12px 14px', textAlign: 'right' }}>
                  <span className="badge badge-virtual">Duplicate Ignored</span>
                </td>
              </tr>
              <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)', background: 'rgba(239, 68, 68, 0.05)' }}>
                <td style={{ padding: '12px 14px', color: 'var(--color-loss)' }}>Invalid date format</td>
                <td style={{ padding: '12px 14px' }}>Merchant ••19</td>
                <td style={{ padding: '12px 14px' }} className="tabular-nums">₹2,100.00</td>
                <td style={{ padding: '12px 14px' }}>Unassigned</td>
                <td style={{ padding: '12px 14px', textAlign: 'right' }}>
                  <span className="badge badge-loss">Fix Required</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-primary)', fontWeight: 600 }}>
            Cashflow & Ledger Tracking
          </span>
          <h1 style={{ fontSize: '36px', fontWeight: 700, color: '#FFFFFF', marginTop: '4px', letterSpacing: '-0.02em' }}>
            Spending & Expense Analytics
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
            Deterministic category classification with privacy masking for merchant descriptions.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button onClick={() => setShowAddModal(true)} className="btn-emerald" style={{ padding: '10px 18px', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }}>
            + Log Transaction
          </button>
          <button onClick={() => setView('csv-import')} className="btn btn-secondary">
            CSV Staging Audit
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px' }}>
        <div className="glass-card" style={{ padding: '24px' }}>
          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>
            October Total Outflow
          </span>
          <div className="tabular-nums" style={{ fontSize: '32px', fontWeight: 700, color: '#FFFFFF', marginTop: '8px' }}>
            ₹{totalSpent.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          <span style={{ fontSize: '12px', color: 'var(--text-faint)' }}>{spendingItems.length} Logged Transactions</span>
        </div>

        <div className="glass-card" style={{ padding: '24px' }}>
          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>
            Top Category
          </span>
          <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--color-primary)', marginTop: '12px' }}>
            Bills & Utilities
          </div>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>₹3,500.00 (37.6% of spend)</span>
        </div>

        <div className="glass-card" style={{ padding: '24px' }}>
          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>
            Privacy Masking
          </span>
          <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--color-profit)', marginTop: '12px' }}>
            100% Active
          </div>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Account identifiers masked</span>
        </div>

        <div className="glass-card" style={{ padding: '24px' }}>
          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>
            Monthly Budget Cap
          </span>
          <div className="tabular-nums" style={{ fontSize: '32px', fontWeight: 700, color: '#FFFFFF', marginTop: '8px' }}>
            ₹25,000.00
          </div>
          <span style={{ fontSize: '12px', color: 'var(--color-profit)' }}>
            ₹{(25000 - totalSpent).toLocaleString('en-IN')} remaining buffer
          </span>
        </div>
      </div>

      {/* Category Pills */}
      <div className="glass-card" style={{ padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {categories.map((c) => (
            <button
              key={c}
              onClick={() => setActiveCategory(c)}
              style={{
                padding: '7px 14px',
                borderRadius: 'var(--radius-sm)',
                border: activeCategory === c ? '1px solid var(--color-primary)' : '1px solid transparent',
                background: activeCategory === c ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
                color: activeCategory === c ? '#FFFFFF' : 'var(--text-muted)',
                fontSize: '12px',
                fontWeight: activeCategory === c ? 600 : 500,
                cursor: 'pointer',
              }}
            >
              {c}
            </button>
          ))}
        </div>

        <input
          type="text"
          placeholder="Search merchant name..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{
            padding: '8px 14px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-medium)',
            backgroundColor: 'var(--bg-input)',
            color: '#FFFFFF',
            fontSize: '12px',
            width: '240px',
            outline: 'none',
          }}
        />
      </div>

      {/* Transactions Table Card */}
      <div className="glass-card" style={{ padding: '24px' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-faint)', fontSize: '11px', textTransform: 'uppercase' }}>
                <th style={{ padding: '12px 14px' }}>Transaction ID</th>
                <th style={{ padding: '12px 14px' }}>Date</th>
                <th style={{ padding: '12px 14px' }}>Merchant Description</th>
                <th style={{ padding: '12px 14px' }}>Category</th>
                <th style={{ padding: '12px 14px', textAlign: 'right' }}>Amount / INR</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((tx) => (
                <tr key={tx.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                  <td style={{ padding: '14px', color: 'var(--text-faint)' }} className="tabular-nums">{tx.id}</td>
                  <td style={{ padding: '14px', color: 'var(--text-muted)' }}>{tx.date}</td>
                  <td style={{ padding: '14px', color: '#FFFFFF', fontWeight: 500 }}>
                    <span className="badge badge-neutral" style={{ marginRight: '8px', fontSize: '10px' }}>Masked</span>
                    {tx.merchant}
                  </td>
                  <td style={{ padding: '14px' }}>
                    <span className="badge badge-cyan">{tx.category}</span>
                  </td>
                  <td style={{ padding: '14px', textAlign: 'right', fontWeight: 700 }} className="tabular-nums">
                    ₹{tx.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Expense Modal */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-content" style={{ maxWidth: '440px', padding: '32px' }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontSize: '20px', fontWeight: 700, color: '#FFFFFF', marginBottom: '8px' }}>
              Log New Transaction
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '20px' }}>
              Record an outflow in your personal finance tracking ledger.
            </p>

            <form onSubmit={handleAddSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase', fontWeight: 600 }}>
                  Merchant / Payee Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Swiggy, Amazon, Metro, Electricity"
                  value={newMerchant}
                  onChange={(e) => setNewMerchant(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-medium)',
                    backgroundColor: 'var(--bg-input)',
                    color: '#FFFFFF',
                    fontSize: '13px',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase', fontWeight: 600 }}>
                  Expense Category
                </label>
                <select
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-medium)',
                    backgroundColor: 'var(--bg-input)',
                    color: '#FFFFFF',
                    fontSize: '13px',
                  }}
                >
                  {categories.filter((c) => c !== 'All').map((c) => (
                    <option key={c} value={c} style={{ backgroundColor: '#111827', color: '#FFFFFF' }}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase', fontWeight: 600 }}>
                  Amount (₹)
                </label>
                <input
                  type="number"
                  min="1"
                  required
                  value={newAmount}
                  onChange={(e) => setNewAmount(Number(e.target.value))}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-medium)',
                    backgroundColor: 'var(--bg-input)',
                    color: '#FFFFFF',
                    fontWeight: 700,
                    fontSize: '16px',
                  }}
                />
              </div>

              <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
                <button type="button" onClick={() => setShowAddModal(false)} className="btn btn-secondary" style={{ flex: 1 }}>
                  Cancel
                </button>
                <button type="submit" className="btn-emerald" style={{ flex: 1, padding: '12px', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }}>
                  Save Transaction →
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
