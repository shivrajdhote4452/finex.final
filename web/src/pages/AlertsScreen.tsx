import React, { useState } from 'react';

export const AlertsScreen: React.FC = () => {
  const [instrument, setInstrument] = useState('RELIANCE');
  const [condition, setCondition] = useState('Price above ₹2,600.00');

  const alerts = [
    { time: '09:40', title: 'Price threshold reached', text: 'RELIANCE crossed your illustrated threshold.', color: 'var(--color-gain)' },
    { time: '09:15', title: 'Allocation changed', text: 'Review concentration in your practice portfolio.', color: 'var(--color-cobalt)' },
    { time: '08:00', title: 'Monthly goal check-in', text: 'Your emergency fund contribution is due.', color: 'var(--color-loss)' },
  ];

  return (
    <div style={{ maxWidth: '1240px', margin: '0 auto' }}>
      <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-cobalt)', fontWeight: 600 }}>
        Alerts
      </span>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginTop: '8px', marginBottom: '32px' }}>
        <div>
          <h1 style={{ fontSize: '40px', lineHeight: 1.15, margin: 0 }}>Only what needs your attention.</h1>
          <p style={{ color: 'var(--color-ink-muted)', fontSize: '14px', marginTop: '4px' }}>
            A durable in-app history, even when a push notification fails.
          </p>
        </div>
        <button className="button-primary" style={{ padding: '10px 20px', fontSize: '13px' }}>
          Create alert →
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: '56px', alignItems: 'start' }}>
        {/* Timeline Notifications Column */}
        <div>
          <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-faint)', display: 'block', marginBottom: '20px' }}>
            Today
          </span>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '28px', borderLeft: '1px solid var(--color-border)', paddingLeft: '24px', marginLeft: '6px' }}>
            {alerts.map((a, i) => (
              <div key={i} style={{ position: 'relative' }}>
                {/* Dot marker */}
                <div
                  style={{
                    position: 'absolute',
                    left: '-29px',
                    top: '4px',
                    width: '10px',
                    height: '10px',
                    borderRadius: '50%',
                    backgroundColor: a.color,
                  }}
                />
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', marginBottom: '4px' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--color-ink-muted)' }}>
                    {a.time}
                  </span>
                  <span style={{ fontWeight: 600, fontSize: '16px' }}>{a.title}</span>
                </div>
                <p style={{ fontSize: '14px', color: 'var(--color-ink-muted)', marginBottom: '8px' }}>
                  {a.text}
                </p>
                <span style={{ fontSize: '13px', color: 'var(--color-cobalt)', fontWeight: 500, cursor: 'pointer' }}>
                  View details →
                </span>
              </div>
            ))}
          </div>

          <div style={{ marginTop: '40px', fontSize: '12px', color: 'var(--color-ink-faint)' }}>
            Earlier notifications remain available in history.
          </div>
        </div>

        {/* Right Rule Creator Form */}
        <div style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '32px', backgroundColor: 'var(--color-paper-subtle)' }}>
          <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-cobalt)', fontWeight: 600 }}>
            Price Alert Rule
          </span>

          <div style={{ marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-ink-faint)', letterSpacing: '0.06em', marginBottom: '6px' }}>
                Instrument
              </label>
              <input
                type="text"
                value={instrument}
                onChange={(e) => setInstrument(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: '#FFFFFF',
                  fontFamily: 'var(--font-sans)',
                  fontSize: '14px',
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-ink-faint)', letterSpacing: '0.06em', marginBottom: '6px' }}>
                Condition
              </label>
              <input
                type="text"
                value={condition}
                onChange={(e) => setCondition(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: '#FFFFFF',
                  fontFamily: 'var(--font-sans)',
                  fontSize: '14px',
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', color: 'var(--color-ink-faint)', letterSpacing: '0.06em', marginBottom: '6px' }}>
                Delivery
              </label>
              <div style={{ fontSize: '13px', color: 'var(--color-ink-muted)', padding: '6px 0' }}>
                In-app + push when available
              </div>
            </div>

            <button className="button-primary" style={{ width: '100%', padding: '12px 20px', fontSize: '14px', marginTop: '12px' }}>
              Save alert →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
