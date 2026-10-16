import React from 'react';

interface SettingsScreenProps {
  onSignOut: () => void;
}

export const SettingsScreen: React.FC<SettingsScreenProps> = ({ onSignOut }) => {
  return (
    <div style={{ maxWidth: '1240px', margin: '0 auto' }}>
      <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-cobalt)', fontWeight: 600 }}>
        Your Workspace
      </span>

      <div style={{ marginTop: '8px', marginBottom: '40px' }}>
        <h1 style={{ fontSize: '40px', lineHeight: 1.15, margin: 0 }}>The details that make it yours.</h1>
        <p style={{ color: 'var(--color-ink-muted)', fontSize: '14px', marginTop: '4px' }}>
          Profile, preferences and privacy in one predictable place.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '56px', alignItems: 'start' }}>
        {/* Left Navy Profile Summary Card */}
        <div style={{ backgroundColor: '#162032', color: '#FFFFFF', borderRadius: 'var(--radius-sm)', padding: '36px' }}>
          <div
            style={{
              width: '48px',
              height: '48px',
              borderRadius: '50%',
              backgroundColor: 'rgba(255, 255, 255, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 600,
              fontSize: '16px',
              marginBottom: '20px',
            }}
          >
            SD
          </div>

          <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '28px', color: '#FFFFFF', margin: '0 0 4px 0' }}>
            Shivraj Dhote
          </h2>
          <div style={{ fontSize: '13px', opacity: 0.7, marginBottom: '36px' }}>
            Personal workspace
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', fontSize: '14px' }}>
            <span style={{ color: '#FFFFFF', fontWeight: 600, cursor: 'pointer', borderBottom: '1px solid rgba(255, 255, 255, 0.3)', paddingBottom: '8px' }}>
              Profile
            </span>
            <span style={{ opacity: 0.7, cursor: 'pointer' }}>
              Notifications
            </span>
            <span style={{ opacity: 0.7, cursor: 'pointer' }}>
              Privacy & consent
            </span>
          </div>
        </div>

        {/* Right Settings Rows */}
        <div>
          <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-cobalt)', fontWeight: 600 }}>
            Profile & Preferences
          </span>

          <div style={{ marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '0' }}>
            {/* Row 1 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '24px 0', borderBottom: '1px solid var(--color-border)' }}>
              <div>
                <strong style={{ fontSize: '15px' }}>Display name</strong>
                <div style={{ fontSize: '14px', color: 'var(--color-ink-muted)', marginTop: '2px' }}>Shivraj Dhote</div>
              </div>
              <span style={{ fontSize: '13px', color: 'var(--color-cobalt)', fontWeight: 500, cursor: 'pointer' }}>Edit →</span>
            </div>

            {/* Row 2 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '24px 0', borderBottom: '1px solid var(--color-border)' }}>
              <div>
                <strong style={{ fontSize: '15px' }}>Risk profile</strong>
                <div style={{ fontSize: '14px', color: 'var(--color-ink-muted)', marginTop: '2px' }}>Review the latest assessment and your answers</div>
              </div>
              <span style={{ fontSize: '13px', color: 'var(--color-cobalt)', fontWeight: 500, cursor: 'pointer' }}>View →</span>
            </div>

            {/* Row 3 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '24px 0', borderBottom: '1px solid var(--color-border)' }}>
              <div>
                <strong style={{ fontSize: '15px' }}>Consent history</strong>
                <div style={{ fontSize: '14px', color: 'var(--color-ink-muted)', marginTop: '2px' }}>See the policy version you accepted (v1.0)</div>
              </div>
              <span style={{ fontSize: '13px', color: 'var(--color-cobalt)', fontWeight: 500, cursor: 'pointer' }}>View →</span>
            </div>

            {/* Row 4 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '24px 0', borderBottom: '1px solid var(--color-border)' }}>
              <div>
                <strong style={{ fontSize: '15px' }}>Push notifications</strong>
                <div style={{ fontSize: '14px', color: 'var(--color-ink-muted)', marginTop: '2px' }}>Device permission must be verified in the live app</div>
              </div>
              <span style={{ fontSize: '13px', color: 'var(--color-cobalt)', fontWeight: 500, cursor: 'pointer' }}>Manage →</span>
            </div>

            {/* Sign Out Row */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '32px 0' }}>
              <button
                onClick={onSignOut}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--color-loss)',
                  fontSize: '14px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  padding: 0,
                }}
              >
                Sign out
              </button>
              <span style={{ fontSize: '13px', color: 'var(--color-ink-faint)' }}>
                Signed in with Google
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
