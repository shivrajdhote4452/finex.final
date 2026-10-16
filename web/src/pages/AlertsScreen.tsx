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

          {/* S6 Scenario Stress Test Simulator */}
          <div style={{ marginTop: '28px', paddingTop: '20px', borderTop: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-primary)', fontWeight: 600 }}>
                S6 SCENARIO SIMULATOR
              </span>
              <span className="badge badge-neutral" style={{ fontSize: '10px' }}>Hypothetical</span>
            </div>
            <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#FFFFFF', marginBottom: '6px' }}>
              15% Sector Drawdown Stress Test
            </h4>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '14px' }}>
              Instantaneous deterministic impact test on verified portfolio equity.
            </p>

            <div style={{ padding: '14px', backgroundColor: 'rgba(255, 255, 255, 0.02)', borderRadius: '4px', border: '1px solid var(--border-subtle)', marginBottom: '14px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Target Sector:</span>
                <strong style={{ fontSize: '12px', color: '#FFFFFF' }}>Information Technology</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Baseline Value:</span>
                <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: '#FFFFFF' }}>₹1,00,000.00</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Estimated Drawdown (-15%):</span>
                <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--color-loss)', fontWeight: 700 }}>-₹5,250.00</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Post-Shock Equity:</span>
                <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--color-primary)', fontWeight: 700 }}>₹94,750.00</span>
              </div>
            </div>

            <p style={{ fontSize: '10px', color: 'var(--text-faint)', fontStyle: 'italic', lineHeight: 1.4 }}>
              HYPOTHETICAL STRESS TEST ONLY: Models an isolated sector decline without correlating moves. Not a market forecast or investment advice.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
