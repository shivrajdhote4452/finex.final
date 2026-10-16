import React, { useState } from 'react';
import { useFinancial } from '../context/FinancialContext';

interface SettingsScreenProps {
  onSignOut: () => void;
}

export const SettingsScreen: React.FC<SettingsScreenProps> = ({ onSignOut }) => {
  const { virtualCash, resetAccount } = useFinancial();
  const [resetSuccess, setResetSuccess] = useState(false);
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [activeSubTab, setActiveSubTab] = useState<'profile' | 'sandbox' | 'compliance'>('profile');

  const handleReset = () => {
    resetAccount();
    setResetSuccess(true);
    setTimeout(() => setResetSuccess(false), 2500);
  };

  return (
    <div style={{ maxWidth: '1240px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '32px' }}>
      {/* Header */}
      <div>
        <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-primary)', fontWeight: 600 }}>
          User Preferences & Sandbox Governance
        </span>
        <h1 style={{ fontSize: '36px', fontWeight: 700, color: '#FFFFFF', marginTop: '4px', letterSpacing: '-0.02em' }}>
          Workspace Settings
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
          Manage your investor profile, simulated paper trading account rules, and compliance acknowledgments.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '36px', alignItems: 'start' }}>
        {/* Left Profile Summary Card */}
        <div className="glass-card" style={{ padding: '32px' }}>
          <div
            style={{
              width: '56px',
              height: '56px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--color-action)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 800,
              fontSize: '20px',
              color: '#000000',
              boxShadow: '0 0 16px rgba(242, 154, 96, 0.35)',
              marginBottom: '20px',
            }}
          >
            SD
          </div>

          <h2 style={{ fontSize: '24px', fontWeight: 700, color: '#FFFFFF', margin: '0 0 4px 0' }}>
            Shivraj Dhote
          </h2>
          <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '28px' }}>
            Sole Developer & Admin
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {[
              { id: 'profile', label: 'Investor Profile' },
              { id: 'sandbox', label: 'Sandbox & Trading Rules' },
              { id: 'compliance', label: 'Consent & Regulatory' },
            ].map((tab) => {
              const isActive = activeSubTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveSubTab(tab.id as any)}
                  style={{
                    textAlign: 'left',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-sm)',
                    background: isActive ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
                    border: isActive ? '1px solid var(--color-primary)' : '1px solid transparent',
                    color: isActive ? '#FFFFFF' : 'var(--text-muted)',
                    fontWeight: isActive ? 600 : 500,
                    cursor: 'pointer',
                    fontSize: '13px',
                    transition: 'all 0.15s ease',
                  }}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>

          <div style={{ borderTop: '1px solid var(--border-subtle)', marginTop: '32px', paddingTop: '24px' }}>
            <button
              onClick={onSignOut}
              style={{
                width: '100%',
                padding: '10px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--color-loss-border)',
                background: 'rgba(239, 68, 68, 0.1)',
                color: 'var(--color-loss)',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Sign Out of Session
            </button>
          </div>
        </div>

        {/* Right Tab Content */}
        <div className="glass-card" style={{ padding: '32px' }}>
          {activeSubTab === 'profile' && (
            <div>
              <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#FFFFFF', marginBottom: '20px' }}>
                Investor Profile & Risk Parameters
              </h3>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '16px', borderBottom: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: '#FFFFFF' }}>Display Name</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Shivraj Dhote</div>
                  </div>
                  <span className="badge badge-neutral">Primary Admin</span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '16px', borderBottom: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: '#FFFFFF' }}>Assessed Risk Profile</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Deterministic Score: 68/100 (Balanced Equity-Debt)</div>
                  </div>
                  <span className="badge badge-cyan">Moderate</span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '16px', borderBottom: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: '#FFFFFF' }}>Investment Horizon</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>3 to 5 Years Capital Target</div>
                  </div>
                  <span className="badge badge-profit">3–5 Years</span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '16px', borderBottom: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: '#FFFFFF' }}>In-App Market Alerts</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Push notifications for price thresholds & allocation drift</div>
                  </div>
                  <button
                    onClick={() => setNotificationsEnabled(!notificationsEnabled)}
                    className={notificationsEnabled ? 'btn-emerald' : 'btn btn-secondary'}
                    style={{ padding: '6px 14px', fontSize: '12px', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }}
                  >
                    {notificationsEnabled ? 'Enabled ✓' : 'Disabled'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeSubTab === 'sandbox' && (
            <div>
              <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#FFFFFF', marginBottom: '8px' }}>
                Paper Trading Sandbox Controls
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '24px' }}>
                Manage the isolated virtual cash balance and simulated matching engine rules.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ padding: '20px', borderRadius: 'var(--radius-sm)', backgroundColor: 'rgba(245, 158, 11, 0.08)', border: '1px solid var(--color-virtual-border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontSize: '14px', fontWeight: 700, color: '#FFFFFF' }}>Current Virtual Cash</div>
                      <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Available capital for simulated execution</div>
                    </div>
                    <div className="tabular-nums" style={{ fontSize: '24px', fontWeight: 700, color: 'var(--color-virtual)' }}>
                      ₹{virtualCash.toLocaleString('en-IN')}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: '#FFFFFF' }}>Reset Sandbox Account</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Restores virtual cash to ₹50,000 and resets initial holdings</div>
                  </div>
                  <button
                    onClick={handleReset}
                    className="btn btn-secondary"
                    style={{ color: 'var(--color-virtual)', borderColor: 'var(--color-virtual-border)' }}
                  >
                    {resetSuccess ? 'Account Reset ✓' : 'Reset to ₹50,000'}
                  </button>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: '#FFFFFF' }}>Matching Engine Reference</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>NSE Real-time observation quotes with zero-slippage paper fills</div>
                  </div>
                  <span className="badge badge-profit">Active (Live)</span>
                </div>
              </div>
            </div>
          )}

          {activeSubTab === 'compliance' && (
            <div>
              <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#FFFFFF', marginBottom: '8px' }}>
                Regulatory Consent & Educational Grounding
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '24px' }}>
                FinEx operates strictly within SEBI and RBI educational research frameworks.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ padding: '16px', borderRadius: 'var(--radius-sm)', backgroundColor: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <strong style={{ color: '#FFFFFF' }}>SEBI Paper Trading Risk Disclosure</strong>
                    <span className="badge badge-profit">Accepted v1.0</span>
                  </div>
                  <p style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                    FinEx is an educational platform designed for learning portfolio management, risk evaluation, and asset allocation. All transactions use simulated virtual currency with zero brokerage or financial liability.
                  </p>
                </div>

                <div style={{ padding: '16px', borderRadius: 'var(--radius-sm)', backgroundColor: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <strong style={{ color: '#FFFFFF' }}>AI Answer Grounding Policy</strong>
                    <span className="badge badge-cyan">Active Enforcement</span>
                  </div>
                  <p style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                    FinEx AI strictly cites authentic regulatory corpus documents (SEBI Master Circular, RBI Master Directions, NSE Guidelines). Hallucinated recommendations or speculative stock tips are deterministically rejected.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
