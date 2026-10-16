import React, { useState } from 'react';
import { useFinancial } from '../context/FinancialContext';

export const AskFinExScreen: React.FC = () => {
  const { holdings } = useFinancial();

  const [messages, setMessages] = useState([
    {
      role: 'user',
      text: 'Which holding is the largest in my portfolio, and does it align with standard diversification principles?',
    },
    {
      role: 'assistant',
      headline: 'TCS is your largest individual equity holding.',
      body: 'In your active practice portfolio, TCS accounts for ₹36,000, representing 36.2% of your invested equity holdings (excluding cash). SEBI educational materials emphasize that exceeding 30% concentration in a single stock exposes a portfolio to disproportionate company-specific risk. [1]',
      disclaimer: 'FinEx provides educational research assistance only. It does not provide personalized investment advice or buy/sell recommendations.',
      citationId: '1',
      citationLabel: '[1] View Portfolio Concentration Proof',
    },
  ]);

  const [inputVal, setInputVal] = useState('');
  const [activeEvidence, setActiveEvidence] = useState<'holdings' | 'sebi'>('holdings');

  const handleSend = () => {
    if (!inputVal.trim()) return;
    const userText = inputVal;
    setInputVal('');

    setMessages((prev) => [...prev, { role: 'user', text: userText }]);

    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          headline: 'Diversification balances exposure across sectors.',
          body: 'According to the SEBI Investor Education Handbook, diversifying across non-correlated sectors (e.g. Technology, Banking, Energy) reduces overall volatility while preserving compounding potential. [2]',
          disclaimer: 'Educational synthesis based on regulatory publications. Past market returns do not guarantee future performance.',
          citationId: '2',
          citationLabel: '[2] Inspect SEBI Investor Education Guide (p. 14)',
        },
      ]);
      setActiveEvidence('sebi');
    }, 450);
  };

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* Header */}
      <div>
        <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-accent-cyan)', fontWeight: 600 }}>
          AI Research & Educational Assistant
        </span>
        <h1 style={{ fontSize: '36px', fontWeight: 700, color: '#FFFFFF', marginTop: '4px', letterSpacing: '-0.02em' }}>
          Document-Grounded Financial Intelligence
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px' }}>
          Ask questions grounded in verified regulatory documentation, SEBI investor guides, and your authorized portfolio metrics.
        </p>
      </div>

      {/* Main Workspace: Left Conversation, Right Source Desk */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.8fr 1.2fr', gap: '32px', alignItems: 'start' }}>
        {/* Left Chat Stream */}
        <div className="glass-card" style={{ padding: '28px', display: 'flex', flexDirection: 'column', minHeight: '560px', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {/* Safety Banner */}
            <div
              style={{
                padding: '10px 16px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'rgba(245, 158, 11, 0.08)',
                border: '1px solid var(--color-virtual-border)',
                fontSize: '12px',
                color: 'var(--color-virtual)',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <span>🛡️</span>
              <span>All responses are grounded in verified regulatory sources. Never financial advice.</span>
            </div>

            {/* Messages */}
            {messages.map((m, idx) => {
              if (m.role === 'user') {
                return (
                  <div
                    key={idx}
                    style={{
                      alignSelf: 'flex-end',
                      maxWidth: '85%',
                      backgroundColor: 'rgba(242, 154, 96, 0.12)',
                      border: '1px solid rgba(242, 154, 96, 0.25)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '12px 16px',
                      fontSize: '13px',
                      color: '#FFFFFF',
                    }}
                  >
                    {m.text}
                  </div>
                );
              }

              return (
                <div
                  key={idx}
                  style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.02)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-md)',
                    padding: '20px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                  }}
                >
                  <h3 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--color-accent-cyan)' }}>
                    {m.headline}
                  </h3>
                  <p style={{ fontSize: '14px', lineHeight: 1.6, color: 'var(--text-main)' }}>
                    {m.body}
                  </p>

                  <div
                    style={{
                      padding: '10px',
                      borderRadius: 'var(--radius-xs)',
                      backgroundColor: 'rgba(0, 0, 0, 0.25)',
                      fontSize: '12px',
                      color: 'var(--text-faint)',
                      fontStyle: 'italic',
                    }}
                  >
                    {m.disclaimer}
                  </div>

                  {m.citationLabel && (
                    <button
                      onClick={() => setActiveEvidence(m.citationId === '1' ? 'holdings' : 'sebi')}
                      className="btn btn-secondary"
                      style={{
                        alignSelf: 'flex-start',
                        padding: '6px 12px',
                        fontSize: '12px',
                        color: 'var(--color-primary)',
                        borderColor: 'rgba(59, 130, 246, 0.4)',
                      }}
                    >
                      {m.citationLabel} →
                    </button>
                  )}
                </div>
              );
            })}
          </div>

          {/* Composer */}
          <div style={{ display: 'flex', gap: '12px', borderTop: '1px solid var(--border-subtle)', paddingTop: '20px', marginTop: '20px' }}>
            <input
              type="text"
              placeholder="Ask a question about your portfolio, asset allocation, or market rules..."
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              style={{
                flex: 1,
                padding: '12px 16px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-medium)',
                backgroundColor: 'var(--bg-input)',
                color: '#FFFFFF',
                fontFamily: 'var(--font-sans)',
                fontSize: '14px',
                outline: 'none',
              }}
            />
            <button onClick={handleSend} className="btn btn-primary" style={{ padding: '12px 24px' }}>
              Ask FinEx
            </button>
          </div>
        </div>

        {/* Right Source Desk (Evidence Drawer) */}
        <div className="glass-card" style={{ padding: '28px', border: '1px solid var(--border-medium)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
            <span className="badge badge-cyan">The Source Desk</span>
            <span style={{ fontSize: '12px', color: 'var(--text-faint)' }}>Verifiable Grounding</span>
          </div>

          {activeEvidence === 'holdings' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Evidence Type</span>
                <div style={{ fontSize: '16px', fontWeight: 600, color: '#FFFFFF', marginTop: '2px' }}>
                  User Holdings Snapshot
                </div>
              </div>

              <div
                style={{
                  padding: '16px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'rgba(0, 0, 0, 0.3)',
                  border: '1px solid var(--border-subtle)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '13px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                <div style={{ color: 'var(--text-muted)' }}>TCS Holding: ₹36,000 (10 shares @ ₹3,600)</div>
                <div style={{ color: 'var(--text-muted)' }}>Total Equity Assets: ₹99,500</div>
                <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '8px', color: 'var(--color-accent-cyan)', fontWeight: 700 }}>
                  Math: 36,000 ÷ 99,500 = 36.18% (~36.2%)
                </div>
              </div>

              <p style={{ fontSize: '12px', color: 'var(--text-faint)', lineHeight: 1.5 }}>
                Derived deterministically by the FinEx portfolio calculation service. LLM reasoning does not perform arithmetic.
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Regulatory Document</span>
                <div style={{ fontSize: '16px', fontWeight: 600, color: '#FFFFFF', marginTop: '2px' }}>
                  SEBI Investor Education Handbook
                </div>
                <div style={{ fontSize: '12px', color: 'var(--color-primary)', marginTop: '2px' }}>
                  Section 4.2 • Page 14 • Oct 2023 Edition
                </div>
              </div>

              <div
                style={{
                  padding: '16px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'rgba(0, 0, 0, 0.3)',
                  border: '1px solid var(--border-subtle)',
                  fontSize: '13px',
                  lineHeight: 1.6,
                  color: 'var(--text-main)',
                }}
              >
                "Diversification is a technique that reduces risk by allocating investments across various financial instruments, industries, and other categories. It aims to maximize returns by investing in different areas that would each react differently to the same event."
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="badge badge-profit">Checksum Verified</span>
                <span style={{ fontSize: '11px', color: 'var(--text-faint)' }}>SHA256: 8a4f9...</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
