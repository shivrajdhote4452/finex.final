import React, { useState } from 'react';
import { useFinancial } from '../context/FinancialContext';

export const AlertsScreen: React.FC = () => {
  const { notifications, markAllNotificationsRead, addNotification } = useFinancial();

  const [instrument, setInstrument] = useState('RELIANCE');
  const [threshold, setThreshold] = useState('2600.00');
  const [ruleAdded, setRuleAdded] = useState(false);

  const handleSaveAlert = (e: React.FormEvent) => {
    e.preventDefault();
    addNotification('Price Rule Created', `Active monitoring: Trigger alert when ${instrument} crosses ₹${threshold}`, 'price');
    setRuleAdded(true);
    setTimeout(() => setRuleAdded(false), 2500);
  };

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-primary)', fontWeight: 600 }}>
            Automated Monitoring
          </span>
          <h1 style={{ fontSize: '36px', fontWeight: 700, color: '#FFFFFF', marginTop: '4px', letterSpacing: '-0.02em' }}>
            Smart Alerts & Trigger Rules
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
            Deterministic rule evaluation with deduplication and cooldown controls.
          </p>
        </div>

        <button onClick={markAllNotificationsRead} className="btn btn-secondary">
          ✓ Mark All as Read
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: '28px', alignItems: 'start' }}>
        {/* Left Column: Notification Feed */}
        <div className="glass-card" style={{ padding: '28px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#FFFFFF' }}>Recent In-App Notifications</h3>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{notifications.length} Total Alerts</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {notifications.map((n) => (
              <div
                key={n.id}
                style={{
                  padding: '16px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: n.read ? 'rgba(255, 255, 255, 0.02)' : 'rgba(59, 130, 246, 0.08)',
                  border: n.read ? '1px solid var(--border-subtle)' : '1px solid rgba(59, 130, 246, 0.3)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    {!n.read && <div className="pulse-dot" />}
                    <strong style={{ fontSize: '14px', color: '#FFFFFF' }}>{n.title}</strong>
                    <span className="badge badge-neutral" style={{ fontSize: '10px' }}>{n.type}</span>
                  </div>
                  <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                    {n.message}
                  </p>
                </div>
                <span className="tabular-nums" style={{ fontSize: '11px', color: 'var(--text-faint)' }}>
                  {n.time}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Rule Creator */}
        <div className="glass-card" style={{ padding: '28px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#FFFFFF', marginBottom: '6px' }}>
            Create Price Alert Rule
          </h3>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '20px' }}>
            Evaluated at end-of-day close. Suppresses duplicate firings within 24h.
          </p>

          <form onSubmit={handleSaveAlert} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                Instrument
              </label>
              <select
                value={instrument}
                onChange={(e) => setInstrument(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-medium)',
                  backgroundColor: 'var(--bg-input)',
                  color: '#FFFFFF',
                  fontFamily: 'var(--font-sans)',
                  fontSize: '13px',
                }}
              >
                <option value="RELIANCE">RELIANCE (Reliance Industries)</option>
                <option value="TCS">TCS (Tata Consultancy Services)</option>
                <option value="INFY">INFY (Infosys)</option>
                <option value="HDFCBANK">HDFCBANK (HDFC Bank)</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                Price Threshold (INR)
              </label>
              <input
                type="number"
                step="0.01"
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-medium)',
                  backgroundColor: 'var(--bg-input)',
                  color: '#FFFFFF',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '13px',
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                Delivery Channel
              </label>
              <div style={{ fontSize: '13px', color: 'var(--color-accent-cyan)' }}>
                ✓ In-App Feed + FCM Mobile Push (When connected)
              </div>
            </div>

            {ruleAdded && (
              <div style={{ color: 'var(--color-profit)', fontSize: '12px' }}>
                ✓ Price rule registered in operational database!
              </div>
            )}

            <button type="submit" className="btn btn-primary" style={{ marginTop: '8px' }}>
              Save Alert Rule →
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
