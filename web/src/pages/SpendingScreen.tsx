import React, { useState } from 'react';

export const SpendingScreen: React.FC = () => {
  const [view, setView] = useState<'monthly' | 'csv-preview'>('monthly');

  if (view === 'csv-preview') {
    // Screen 14 / 16: CSV Import Preview & Validation Table
    return (
      <div style={{ maxWidth: '1240px', margin: '0 auto' }}>
        <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-cobalt)', fontWeight: 600 }}>
          CSV Import / Review
        </span>

        <div style={{ marginTop: '8px', marginBottom: '32px' }}>
          <h1 style={{ fontSize: '40px', lineHeight: 1.15, margin: 0 }}>Check before adding.</h1>
          <p style={{ color: 'var(--color-ink-muted)', fontSize: '14px', marginTop: '4px' }}>
            october-transactions.csv • Nothing has been imported yet.
          </p>
        </div>

        {/* Audit Metrics Bar */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '24px', borderBottom: '1px solid var(--color-border)', paddingBottom: '24px', marginBottom: '32px' }}>
          <div>
            <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>Rows Found</span>
            <div style={{ fontFamily: 'var(--font-serif)', fontSize: '42px', marginTop: '4px' }}>128</div>
          </div>
          <div>
            <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>Valid Rows</span>
            <div style={{ fontFamily: 'var(--font-serif)', fontSize: '42px', color: 'var(--color-gain)', marginTop: '4px' }}>120</div>
          </div>
          <div>
            <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>Duplicates</span>
            <div style={{ fontFamily: 'var(--font-serif)', fontSize: '42px', color: 'var(--color-virtual-text)', marginTop: '4px' }}>5</div>
          </div>
          <div>
            <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>Need Correction</span>
            <div style={{ fontFamily: 'var(--font-serif)', fontSize: '42px', color: 'var(--color-loss)', marginTop: '4px' }}>3</div>
          </div>
        </div>

        {/* Validation Table */}
        <div style={{ width: '100%', overflowX: 'auto', marginBottom: '24px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--color-border)', fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>
                <th style={{ padding: '12px 16px', fontWeight: 500 }}>Date</th>
                <th style={{ padding: '12px 16px', fontWeight: 500 }}>Description</th>
                <th style={{ padding: '12px 16px', fontWeight: 500 }}>Amount / INR</th>
                <th style={{ padding: '12px 16px', fontWeight: 500 }}>Category</th>
                <th style={{ padding: '12px 16px', fontWeight: 500, textAlign: 'right' }}>Validation</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                <td style={{ padding: '16px 16px', fontSize: '14px' }}>05 Oct 2026</td>
                <td style={{ padding: '16px 16px', fontSize: '14px' }}>Merchant ••42</td>
                <td style={{ padding: '16px 16px', fontFamily: 'var(--font-mono)' }}>₹1,200</td>
                <td style={{ padding: '16px 16px', fontSize: '14px' }}>Shopping</td>
                <td style={{ padding: '16px 16px', textAlign: 'right' }}>
                  <span className="badge-gain">Valid</span>
                </td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                <td style={{ padding: '16px 16px', fontSize: '14px' }}>06 Oct 2026</td>
                <td style={{ padding: '16px 16px', fontSize: '14px' }}>Merchant ••86</td>
                <td style={{ padding: '16px 16px', fontFamily: 'var(--font-mono)' }}>₹650</td>
                <td style={{ padding: '16px 16px', fontSize: '14px' }}>Transport</td>
                <td style={{ padding: '16px 16px', textAlign: 'right' }}>
                  <span className="badge-virtual">Duplicate</span>
                </td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--color-border-subtle)', backgroundColor: '#FDF7F5' }}>
                <td style={{ padding: '16px 16px', fontSize: '14px', color: 'var(--color-loss)' }}>Invalid date</td>
                <td style={{ padding: '16px 16px', fontSize: '14px' }}>Merchant ••19</td>
                <td style={{ padding: '16px 16px', fontFamily: 'var(--font-mono)' }}>₹2,100</td>
                <td style={{ padding: '16px 16px', fontSize: '14px', color: 'var(--color-ink-muted)' }}>Unassigned</td>
                <td style={{ padding: '16px 16px', textAlign: 'right' }}>
                  <span className="badge-loss" style={{ cursor: 'pointer' }}>Fix date</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <p style={{ fontSize: '13px', color: 'var(--color-ink-muted)', marginBottom: '32px' }}>
          Duplicates stay excluded. Correct invalid rows or explicitly leave them out before importing the valid selection.
        </p>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button onClick={() => setView('monthly')} className="button-secondary">
            ← Back to mapping
          </button>
          <button onClick={() => setView('monthly')} className="button-primary" style={{ padding: '12px 24px' }}>
            Import 120 valid rows →
          </button>
        </div>
      </div>
    );
  }

  // Screen 13 / 15: Monthly Breakdown & Review Queue
  return (
    <div style={{ maxWidth: '1240px', margin: '0 auto' }}>
      <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-cobalt)', fontWeight: 600 }}>
        Spending / October
      </span>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginTop: '8px', marginBottom: '32px' }}>
        <div>
          <h1 style={{ fontSize: '40px', lineHeight: 1.15, margin: 0 }}>A closer look at this month.</h1>
          <p style={{ color: 'var(--color-ink-muted)', fontSize: '14px', marginTop: '4px' }}>
            Illustrative transactions in INR. Transfers and refunds are excluded from outflow.
          </p>
        </div>
        <button onClick={() => setView('csv-preview')} className="button-primary" style={{ padding: '10px 20px', fontSize: '13px' }}>
          Import CSV →
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '56px', alignItems: 'start' }}>
        {/* Left Outflow & Categories */}
        <div>
          <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>
            Total Outflow
          </span>
          <div style={{ fontFamily: 'var(--font-serif)', fontSize: '52px', color: 'var(--color-ink)', margin: '8px 0 4px 0' }}>
            ₹24,800
          </div>
          <div style={{ fontSize: '13px', color: 'var(--color-gain)', marginBottom: '28px' }}>
            ₹1,400 less than September
          </div>

          {/* Category Proportion Strip (Screen 13 of PDF) */}
          <div style={{ display: 'flex', width: '100%', height: '14px', borderRadius: '2px', overflow: 'hidden', marginBottom: '24px' }}>
            <div style={{ width: '32%', backgroundColor: '#234BC0' }} title="Food & dining ₹8,000" />
            <div style={{ width: '26%', backgroundColor: '#5E7A6E' }} title="Shopping ₹6,500" />
            <div style={{ width: '17%', backgroundColor: '#C08D50' }} title="Transport ₹4,300" />
            <div style={{ width: '25%', backgroundColor: '#9C584E' }} title="Other ₹6,000" />
          </div>

          {/* Category List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '14px' }}>
                <span style={{ color: '#234BC0' }}>●</span> Food & dining
              </div>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>₹8,000</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '14px' }}>
                <span style={{ color: '#5E7A6E' }}>●</span> Shopping
              </div>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>₹6,500</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '14px' }}>
                <span style={{ color: '#C08D50' }}>●</span> Transport
              </div>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>₹4,300</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '14px' }}>
                <span style={{ color: '#9C584E' }}>●</span> Other
              </div>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>₹6,000</span>
            </div>
          </div>
        </div>

        {/* Right Review Before Accepting Box */}
        <div style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '32px', backgroundColor: 'var(--color-paper-subtle)' }}>
          <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-loss)', fontWeight: 600 }}>
            Review Before Accepting
          </span>

          <h3 style={{ fontFamily: 'var(--font-serif)', fontSize: '32px', margin: '12px 0 20px 0' }}>
            4 transactions<br />
            <em style={{ fontStyle: 'italic', fontSize: '24px' }}>need a category check.</em>
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', borderTop: '1px solid var(--color-border)', paddingTop: '16px', marginBottom: '28px', fontSize: '14px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Merchant ••42</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>₹1,200</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Merchant ••86</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>₹650</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Merchant ••19</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>₹2,100</span>
            </div>
          </div>

          <button onClick={() => setView('csv-preview')} className="button-primary" style={{ width: '100%', padding: '12px 20px', fontSize: '14px' }}>
            Review categories →
          </button>
        </div>
      </div>
    </div>
  );
};
