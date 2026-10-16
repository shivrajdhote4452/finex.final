import React, { useState } from 'react';

export const PracticeScreen: React.FC = () => {
  const [side, setSide] = useState<'buy' | 'sell'>('buy');
  const [shares, setShares] = useState(2);
  const [stage, setStage] = useState<'create' | 'review' | 'confirmed'>('create');
  const price = 2500;
  const total = shares * price;
  const currentCash = 25000;
  const cashAfter = currentCash - total;

  return (
    <div style={{ maxWidth: '1240px', margin: '0 auto' }}>
      <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-cobalt)', fontWeight: 600 }}>
        Paper Trading {stage === 'review' && '/ Review'}
      </span>

      <div style={{ marginTop: '8px', marginBottom: '32px' }}>
        <h1 style={{ fontSize: '40px', lineHeight: 1.15, margin: 0 }}>
          {stage === 'review' ? 'Check the details. Then confirm.' : 'Make your first considered move.'}
        </h1>
        <p style={{ color: 'var(--color-ink-muted)', fontSize: '14px', marginTop: '4px' }}>
          Virtual funds only. No real-money order will be placed.
        </p>
      </div>

      {stage === 'create' ? (
        /* Screen 09: Order ticket and estimate */
        <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '56px', alignItems: 'start' }}>
          {/* Left Form */}
          <div style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '32px', backgroundColor: 'var(--color-paper-subtle)' }}>
            <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-muted)', display: 'block', marginBottom: '20px' }}>
              New Virtual Order
            </span>

            {/* Instrument */}
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-ink-faint)', letterSpacing: '0.06em', marginBottom: '6px' }}>
                Instrument
              </label>
              <div style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '12px 16px', backgroundColor: '#FFFFFF', fontWeight: 600 }}>
                RELIANCE / NSE
              </div>
            </div>

            {/* Side & Quantity */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-ink-faint)', letterSpacing: '0.06em', marginBottom: '6px' }}>
                  Side
                </label>
                <div style={{ display: 'flex', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
                  <button
                    onClick={() => setSide('buy')}
                    style={{
                      flex: 1,
                      padding: '10px',
                      border: 'none',
                      backgroundColor: side === 'buy' ? 'var(--color-cobalt)' : '#FFFFFF',
                      color: side === 'buy' ? '#FFFFFF' : 'var(--color-ink)',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    Buy
                  </button>
                  <button
                    onClick={() => setSide('sell')}
                    style={{
                      flex: 1,
                      padding: '10px',
                      border: 'none',
                      backgroundColor: side === 'sell' ? 'var(--color-cobalt)' : '#FFFFFF',
                      color: side === 'sell' ? '#FFFFFF' : 'var(--color-ink)',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    Sell
                  </button>
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-ink-faint)', letterSpacing: '0.06em', marginBottom: '6px' }}>
                  Quantity
                </label>
                <input
                  type="number"
                  min="1"
                  value={shares}
                  onChange={(e) => setShares(Math.max(1, parseInt(e.target.value) || 1))}
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: '#FFFFFF',
                    fontFamily: 'var(--font-sans)',
                    fontSize: '14px',
                    fontWeight: 600,
                  }}
                />
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--color-border)', paddingTop: '16px' }}>
              <span style={{ fontSize: '13px', color: 'var(--color-ink-muted)' }}>Estimated reference price</span>
              <span style={{ fontSize: '14px', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>₹2,500.00</span>
            </div>

            <p style={{ fontSize: '12px', color: 'var(--color-ink-faint)', marginTop: '20px', lineHeight: 1.5 }}>
              Reference price is genuine NSE observation. Execution eligibility and atomic ledger updates follow approved backend rules.
            </p>
          </div>

          {/* Right Estimate Card */}
          <div style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '32px', backgroundColor: 'var(--color-paper-subtle)' }}>
            <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>
              Order Estimate
            </span>

            <div style={{ fontFamily: 'var(--font-serif)', fontSize: '48px', color: 'var(--color-ink)', margin: '16px 0 4px 0' }}>
              ₹{total.toLocaleString('en-IN')}
            </div>
            <div style={{ fontSize: '13px', color: 'var(--color-ink-muted)', marginBottom: '28px' }}>
              {shares} shares × ₹2,500.00
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', borderTop: '1px solid var(--color-border)', paddingTop: '20px', marginBottom: '28px', fontSize: '14px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--color-ink-muted)' }}>Virtual cash available</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>₹{currentCash.toLocaleString('en-IN')}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--color-ink-muted)' }}>Cash after estimate</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>₹{cashAfter.toLocaleString('en-IN')}</span>
              </div>
            </div>

            <button onClick={() => setStage('review')} className="button-primary" style={{ width: '100%', padding: '12px 20px', fontSize: '14px' }}>
              Review virtual order →
            </button>
            <span style={{ fontSize: '12px', color: 'var(--color-ink-faint)', display: 'block', textAlign: 'center', marginTop: '10px' }}>
              You will confirm on the next screen.
            </span>
          </div>
        </div>
      ) : (
        /* Screen 10: Confirmation and Order Activity Receipts */
        <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1.2fr', gap: '56px', alignItems: 'start' }}>
          {/* Confirmation Box */}
          <div style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '36px', backgroundColor: 'var(--color-paper-subtle)' }}>
            <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-cobalt)', fontWeight: 600 }}>
              Confirm Virtual Buy
            </span>

            <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '36px', margin: '16px 0 4px 0' }}>RELIANCE</h2>
            <div style={{ fontSize: '13px', color: 'var(--color-ink-muted)', marginBottom: '28px' }}>
              {shares} shares / NSE
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', borderTop: '1px solid var(--color-border)', paddingTop: '20px', marginBottom: '32px', fontSize: '14px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--color-ink-muted)' }}>Reference price</span>
                <span style={{ fontFamily: 'var(--font-mono)' }}>₹2,500.00</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--color-ink-muted)' }}>Estimated value</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>₹{total.toLocaleString('en-IN')}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--color-ink-muted)' }}>Estimated cash after</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>₹{cashAfter.toLocaleString('en-IN')}</span>
              </div>
            </div>

            <button onClick={() => setStage('confirmed')} className="button-primary" style={{ width: '100%', padding: '12px 20px', fontSize: '14px', marginBottom: '16px' }}>
              Confirm virtual buy →
            </button>
            <button onClick={() => setStage('create')} style={{ background: 'none', border: 'none', color: 'var(--color-ink-muted)', cursor: 'pointer', fontSize: '13px' }}>
              ← Edit order
            </button>
          </div>

          {/* After Submission Activity Receipts */}
          <div>
            <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-muted)', display: 'block', marginBottom: '16px' }}>
              After Submission / Order Activity
            </span>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* Receipt 1 */}
              <div style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '16px 20px', backgroundColor: 'var(--color-paper-elevated)' }}>
                <span className="badge-gain" style={{ marginBottom: '8px' }}>Filled</span>
                <div style={{ fontSize: '14px', fontWeight: 600, marginTop: '6px' }}>
                  2 RELIANCE • Filled value ₹5,000.00 →
                </div>
              </div>

              {/* Receipt 2 */}
              <div style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '16px 20px', backgroundColor: 'var(--color-paper-elevated)' }}>
                <span className="badge-virtual" style={{ marginBottom: '8px' }}>Pending</span>
                <div style={{ fontSize: '14px', fontWeight: 500, marginTop: '6px', color: 'var(--color-ink-muted)' }}>
                  Awaiting backend execution result →
                </div>
              </div>

              {/* Receipt 3 */}
              <div style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '16px 20px', backgroundColor: 'var(--color-paper-elevated)' }}>
                <span className="badge-loss" style={{ marginBottom: '8px' }}>Status unknown</span>
                <div style={{ fontSize: '14px', fontWeight: 500, marginTop: '6px', color: 'var(--color-ink-muted)' }}>
                  Check this order before trying again →
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
