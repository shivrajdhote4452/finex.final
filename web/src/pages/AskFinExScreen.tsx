import React, { useState } from 'react';

export const AskFinExScreen: React.FC = () => {
  const [messages, setMessages] = useState([
    {
      role: 'user',
      text: 'Which holding is the largest in my portfolio?',
    },
    {
      role: 'assistant',
      headline: 'TCS is your largest holding.',
      body: 'It represents ₹36,000, or 36.2% of your invested holdings in this illustrated snapshot. Cash is excluded from this allocation. [1]',
      disclaimer: 'That is a description of concentration, not a recommendation to buy or sell.',
      citationId: '1',
      citationLabel: '[1] Inspect the holdings used in this answer',
    },
  ]);

  const [inputVal, setInputVal] = useState('');
  const [activeEvidence, setActiveEvidence] = useState<'holdings' | 'sebi'>('holdings');

  const handleSend = () => {
    if (!inputVal.trim()) return;
    const newMsg = { role: 'user', text: inputVal };
    setMessages((prev) => [...prev, newMsg]);
    setInputVal('');

    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          headline: 'Diversification balances exposure across sectors.',
          body: 'According to SEBI educational guidance, spreading capital reduces the impact of a single stock decline on your overall wealth. [2]',
          disclaimer: 'Educational information only. Consult a registered financial advisor for personal advice.',
          citationId: '2',
          citationLabel: '[2] Inspect SEBI Investor Guide, Section 4',
        },
      ]);
      setActiveEvidence('sebi');
    }, 400);
  };

  return (
    <div style={{ maxWidth: '1240px', margin: '0 auto' }}>
      <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-cobalt)', fontWeight: 600 }}>
        Ask FinEx
      </span>

      <div style={{ marginTop: '8px', marginBottom: '32px' }}>
        <h1 style={{ fontSize: '40px', lineHeight: 1.15, margin: 0 }}>Let’s look a little closer.</h1>
        <p style={{ color: 'var(--color-ink-muted)', fontSize: '14px', marginTop: '4px' }}>
          Portfolio context attached • Educational explanation
        </p>
      </div>

      {/* Reading-Room Layout: Left Conversation, Right Source Desk */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.8fr 1.2fr', gap: '56px', alignItems: 'start' }}>
        {/* Left Conversation Stream */}
        <div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '28px', marginBottom: '32px' }}>
            {messages.map((m, idx) => {
              if (m.role === 'user') {
                return (
                  <div
                    key={idx}
                    style={{
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '16px 20px',
                      backgroundColor: 'var(--color-paper-subtle)',
                      fontSize: '15px',
                      fontWeight: 500,
                    }}
                  >
                    {m.text}
                  </div>
                );
              }

              return (
                <div key={idx} style={{ padding: '8px 0' }}>
                  <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '28px', color: 'var(--color-ink)', marginBottom: '12px' }}>
                    {m.headline}
                  </h2>
                  <p style={{ fontSize: '15px', lineHeight: 1.6, color: 'var(--color-ink)', marginBottom: '16px' }}>
                    {m.body}
                  </p>
                  <p style={{ fontFamily: 'var(--font-serif)', fontStyle: 'italic', fontSize: '14px', color: 'var(--color-ink-muted)', marginBottom: '16px' }}>
                    {m.disclaimer}
                  </p>
                  {m.citationLabel && (
                    <button
                      onClick={() => setActiveEvidence(m.citationId === '1' ? 'holdings' : 'sebi')}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: 'var(--color-cobalt)',
                        fontSize: '13px',
                        fontWeight: 500,
                        cursor: 'pointer',
                        textDecoration: 'underline',
                        padding: 0,
                      }}
                    >
                      {m.citationLabel}
                    </button>
                  )}
                </div>
              );
            })}
          </div>

          {/* Composer */}
          <div style={{ display: 'flex', gap: '12px', borderTop: '1px solid var(--color-border)', paddingTop: '20px' }}>
            <input
              type="text"
              placeholder="Ask a follow-up question…"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              style={{
                flex: 1,
                padding: '12px 16px',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'transparent',
                fontFamily: 'var(--font-sans)',
                fontSize: '14px',
                color: 'var(--color-ink)',
              }}
            />
            <button onClick={handleSend} className="button-primary" style={{ padding: '12px 24px' }}>
              Send →
            </button>
          </div>
        </div>

        {/* Right Source Desk (Evidence Alongside the Answer) */}
        <div style={{ borderLeft: '1px solid var(--color-border-subtle)', paddingLeft: '40px' }}>
          <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-cobalt)', fontWeight: 600 }}>
            The Source Desk
          </span>
          <h3 style={{ fontFamily: 'var(--font-serif)', fontSize: '26px', lineHeight: 1.25, margin: '12px 0 24px 0' }}>
            Evidence, alongside<br />
            <em style={{ fontStyle: 'italic' }}>the answer.</em>
          </h3>

          {activeEvidence === 'holdings' ? (
            <div style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '24px', backgroundColor: 'var(--color-paper-subtle)' }}>
              <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>
                01 / Your Paper Portfolio
              </span>
              <div style={{ fontWeight: 600, fontSize: '16px', margin: '8px 0 16px 0' }}>
                Holdings snapshot
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '14px', fontFamily: 'var(--font-mono)' }}>
                <div>TCS · ₹36,000</div>
                <div>Invested holdings · ₹99,500</div>
                <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '8px', color: 'var(--color-cobalt)', fontWeight: 600 }}>
                  36,000 ÷ 99,500 = 36.2%
                </div>
              </div>
            </div>
          ) : (
            <div style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '24px', backgroundColor: 'var(--color-paper-subtle)' }}>
              <span style={{ fontSize: '11px', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-ink-muted)' }}>
                02 / Regulatory Guide
              </span>
              <div style={{ fontWeight: 600, fontSize: '16px', margin: '8px 0 12px 0' }}>
                SEBI Investor Guide (p. 14)
              </div>
              <p style={{ fontSize: '13px', lineHeight: 1.5, color: 'var(--color-ink-muted)' }}>
                "Portfolio diversification involves spreading your investments among different financial instruments, industries, and other categories to maximize return by investing in different areas that would each react differently to the same event."
              </p>
            </div>
          )}

          <div style={{ marginTop: '24px', fontSize: '12px', color: 'var(--color-ink-faint)' }}>
            Data status: verified genuine observation
          </div>
        </div>
      </div>
    </div>
  );
};
