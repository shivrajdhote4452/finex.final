import React from 'react';
import { ThemeToggle } from '../components/common/ThemeToggle';

interface TermsOfServiceScreenProps {
  onBack?: () => void;
}

export const TermsOfServiceScreen: React.FC<TermsOfServiceScreenProps> = ({ onBack }) => {
  const handleBack = () => {
    if (onBack) {
      onBack();
    } else {
      window.location.href = '/';
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: 'var(--bg-app)',
        color: 'var(--text-main)',
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      }}
    >
      {/* Top Navigation Bar */}
      <header
        style={{
          borderBottom: '1px solid var(--border-subtle)',
          backgroundColor: 'var(--bg-sidebar)',
          position: 'sticky',
          top: 0,
          zIndex: 50,
        }}
      >
        <div
          style={{
            maxWidth: '960px',
            margin: '0 auto',
            padding: '16px 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px',
            flexWrap: 'wrap',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
            <span style={{ fontSize: '24px', fontWeight: 900, color: 'var(--text-main)', letterSpacing: '-0.03em' }}>Fin</span>
            <span style={{ fontSize: '24px', fontWeight: 900, color: 'var(--color-action)', letterSpacing: '-0.03em' }}>Ex</span>
            <span
              style={{
                fontSize: '11px',
                color: 'var(--text-muted)',
                fontFamily: "'JetBrains Mono', monospace",
                letterSpacing: '0.05em',
                marginLeft: '8px',
              }}
            >
              TERMS OF SERVICE
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <ThemeToggle variant="segmented" />
            <a
              href="/privacy"
              style={{
                fontSize: '13px',
                color: 'var(--text-muted)',
                textDecoration: 'none',
                padding: '6px 12px',
                borderRadius: '4px',
                border: '1px solid var(--border-subtle)',
                backgroundColor: 'var(--bg-card)',
              }}
            >
              Privacy Policy
            </a>
            <button
              onClick={handleBack}
              style={{
                fontSize: '13px',
                fontWeight: 600,
                color: '#FFFFFF',
                backgroundColor: 'var(--color-action)',
                border: 'none',
                padding: '6px 16px',
                borderRadius: '4px',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              ← Back to FinEx
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main style={{ maxWidth: '960px', margin: '0 auto', padding: '48px 24px 80px' }}>
        {/* Title Header */}
        <div style={{ marginBottom: '36px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '24px' }}>
          <div
            style={{
              fontSize: '12px',
              fontWeight: 700,
              color: 'var(--color-action)',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              fontFamily: "'JetBrains Mono', monospace",
              marginBottom: '8px',
            }}
          >
            User Agreement · Version 1.0
          </div>
          <h1
            style={{
              fontSize: '36px',
              fontWeight: 800,
              letterSpacing: '-0.025em',
              color: 'var(--text-main)',
              margin: '0 0 12px 0',
              lineHeight: 1.2,
            }}
          >
            FinEx Terms of Service
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', margin: 0 }}>
            Effective Date: <strong>November 15, 2026</strong> · Application URL: <strong>https://www.finexai.tech</strong>
          </p>
        </div>

        {/* Core Disclaimer Callout */}
        <div
          style={{
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderLeft: '4px solid var(--color-action)',
            borderRadius: '6px',
            padding: '20px',
            marginBottom: '36px',
          }}
        >
          <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-main)', marginBottom: '6px' }}>
            Important Summary: Zero Financial Risk Educational Platform
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.6, margin: 0 }}>
            FinEx is strictly an educational paper-trading simulator and market analytics learning workspace. All orders, balances, profits, and losses displayed in the terminal use simulated virtual funds (₹1,00,000 virtual balance). FinEx is not a SEBI-registered broker, does not handle real money, does not connect to demat accounts, and does not provide investment advice or recommendations.
          </p>
        </div>

        {/* Section 1: Acceptance of Terms */}
        <section style={{ marginBottom: '32px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-main)', marginBottom: '12px' }}>
            1. Acceptance of Terms
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--text-main)', lineHeight: 1.7, margin: '0 0 12px 0' }}>
            By visiting <strong>https://www.finexai.tech</strong>, creating an account via Google Sign-In, or using any feature of the FinEx Terminal, you agree to comply with and be bound by these Terms of Service ("Terms") and our <a href="/privacy" style={{ color: 'var(--color-action)' }}>Privacy Policy</a>. If you do not agree to these Terms, please do not use the platform.
          </p>
        </section>

        {/* Section 2: Educational Platform Nature & Disclaimers */}
        <section style={{ marginBottom: '32px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-main)', marginBottom: '12px' }}>
            2. Educational Purpose &amp; No-Brokerage Disclaimers
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '16px' }}>
              <strong style={{ fontSize: '13.5px', color: 'var(--color-action)' }}>A. Zero Real Money / Virtual Capital Only</strong>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.6, marginTop: '4px', margin: 0 }}>
                Every FinEx account is initialized with <strong style={{ color: 'var(--text-main)' }}>₹1,00,000 in virtual funds</strong>. This capital is purely simulated and has no real-world cash or monetary value. You cannot deposit real money, withdraw cash, exchange virtual balances, or transfer paper holdings to any real broker or financial institution.
              </p>
            </div>

            <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '16px' }}>
              <strong style={{ fontSize: '13.5px', color: 'var(--color-success)' }}>B. No Brokerage or Clearing Affiliation</strong>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.6, marginTop: '4px', margin: 0 }}>
                FinEx is NOT a registered stockbroker, clearing member, or depository participant under the Securities and Exchange Board of India (SEBI) or any other financial authority. FinEx does not connect to Demat accounts, does not hold investor securities, and does not route orders to live stock exchange order books.
              </p>
            </div>

            <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '16px' }}>
              <strong style={{ fontSize: '13.5px', color: '#6366F1' }}>C. No Investment Advice or Buy/Sell Recommendations</strong>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.6, marginTop: '4px', margin: 0 }}>
                FinEx does NOT provide SEBI-registered Investment Advisory (RIA), Research Analyst, or Portfolio Management services. All interactive charts, behavioral risk scores, educational indicators, and AskFinEx AI responses are provided strictly for general financial education and self-directed study. Nothing on FinEx constitutes an offer, endorsement, or recommendation to buy or sell any financial instrument.
              </p>
            </div>
          </div>
        </section>

        {/* Section 3: User Accounts & Google Authentication */}
        <section style={{ marginBottom: '32px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-main)', marginBottom: '12px' }}>
            3. User Accounts and Authentication
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--text-main)', lineHeight: 1.7, margin: '0 0 12px 0' }}>
            To access the interactive FinEx terminal and save your learning progress, you must authenticate using Google Sign-In. You agree that:
          </p>
          <ul style={{ fontSize: '13.5px', color: 'var(--text-main)', lineHeight: 1.7, paddingLeft: '20px', margin: 0 }}>
            <li>You are responsible for safeguarding your Google account credentials and maintaining security over any device used to access FinEx.</li>
            <li>You must provide accurate profile information and will not impersonate any person or entity.</li>
            <li>You may reset your simulated trading account back to the default ₹50,000 / ₹1,00,000 virtual balance and clear your open positions at any time through the Settings screen.</li>
          </ul>
        </section>

        {/* Section 4: Acceptable Use */}
        <section style={{ marginBottom: '32px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-main)', marginBottom: '12px' }}>
            4. Acceptable Use and Restrictions
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--text-main)', lineHeight: 1.7, margin: '0 0 12px 0' }}>
            You agree to use FinEx solely for lawful educational and simulation purposes. You agree not to:
          </p>
          <ul style={{ fontSize: '13.5px', color: 'var(--text-main)', lineHeight: 1.7, paddingLeft: '20px', margin: 0 }}>
            <li>Interfere with, disrupt, or compromise the integrity, security, or performance of the platform, servers, or database.</li>
            <li>Attempt to bypass authentication, reverse-engineer proprietary algorithms, or circumvent fail-closed security guards.</li>
            <li>Use automated scrapers, crawlers, or high-volume scripts to burden our backend APIs or third-party market data integrations.</li>
            <li>Misrepresent simulated paper trading returns, paper orders, or platform screenshots as real-world financial gains.</li>
          </ul>
        </section>

        {/* Section 5: Market Data Transparency */}
        <section style={{ marginBottom: '32px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-main)', marginBottom: '12px' }}>
            5. Market Data Transparency &amp; Availability
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--text-main)', lineHeight: 1.7, margin: '0 0 12px 0' }}>
            FinEx displays market information for educational demonstration. FinEx explicitly identifies market data freshness across three states:
          </p>
          <ul style={{ fontSize: '13.5px', color: 'var(--text-main)', lineHeight: 1.7, paddingLeft: '20px', margin: 0 }}>
            <li><strong>Live Quotes:</strong> Market updates displayed during official Indian trading hours.</li>
            <li><strong>Cached Snapshots:</strong> Historical or delayed session data displayed off-market, on weekends, or during upstream provider pauses.</li>
            <li><strong>Unavailable Feeds:</strong> Clear offline notifications when exchange connectivity is interrupted.</li>
          </ul>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.6, marginTop: '10px', margin: '10px 0 0 0' }}>
            Market data may be delayed, cached, or simulated. FinEx makes no representation or warranty that market quotes are uninterrupted, accurate, or suitable for real-world trading decisions.
          </p>
        </section>

        {/* Section 6: AskFinEx AI Assistant Disclaimers */}
        <section style={{ marginBottom: '32px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-main)', marginBottom: '12px' }}>
            6. AskFinEx AI Assistant Disclaimers
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--text-main)', lineHeight: 1.7, margin: 0 }}>
            AskFinEx utilizes artificial intelligence and regulatory retrieval systems (grounded in SEBI Master Circulars, RBI Directions, and educational finance materials) to explain concepts in plain English. AI-generated answers are strictly for learning and educational research. They do not constitute formal legal advice, tax advice, or investment recommendations. Users must verify all regulatory circulars directly on the official SEBI website (sebi.gov.in).
          </p>
        </section>

        {/* Section 7: Intellectual Property */}
        <section style={{ marginBottom: '32px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-main)', marginBottom: '12px' }}>
            7. Intellectual Property
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--text-main)', lineHeight: 1.7, margin: 0 }}>
            All rights, title, and interest in and to the FinEx platform, including source code, terminal user interfaces, graphics, brand marks, and educational content, are owned by FinEx and its contributors. All third-party trademarks, exchange symbols, and company names belong to their respective owners.
          </p>
        </section>

        {/* Section 8: Disclaimer of Warranties & Limitation of Liability */}
        <section style={{ marginBottom: '32px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-main)', marginBottom: '12px' }}>
            8. Disclaimer of Warranties &amp; Limitation of Liability
          </h2>
          <div
            style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '6px',
              padding: '18px',
              fontSize: '13px',
              color: 'var(--text-muted)',
              lineHeight: 1.7,
            }}
          >
            <p style={{ margin: '0 0 10px 0' }}>
              THE PLATFORM IS PROVIDED "AS IS" AND "AS AVAILABLE", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
            </p>
            <p style={{ margin: 0 }}>
              IN NO EVENT SHALL FINEX, ITS AUTHORS, OR CONTRIBUTORS BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE, ARISING FROM OR IN CONNECTION WITH THE SOFTWARE, SIMULATED PAPER TRADING, DELAYS IN MARKET FEEDS, OR ANY REAL-MONEY TRADING DECISIONS MADE OUTSIDE THE FINEX PLATFORM.
            </p>
          </div>
        </section>

        {/* Section 9: Modifications & Governing Law */}
        <section style={{ marginBottom: '48px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-main)', marginBottom: '12px' }}>
            9. Governing Law, Modifications &amp; Contact
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--text-main)', lineHeight: 1.7, margin: '0 0 12px 0' }}>
            These Terms are governed by and construed in accordance with the laws of India. We reserve the right to modify these Terms to reflect platform updates or regulatory guidance. Continued use of the platform following any modifications constitutes your acceptance of the updated Terms.
          </p>
          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '16px' }}>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-main)' }}>Questions regarding these Terms?</div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
              Contact: <a href="mailto:shivrajdhote4452@gmail.com" style={{ color: 'var(--color-action)' }}>shivrajdhote4452@gmail.com</a>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-faint)', marginTop: '6px' }}>
              <em>Owner Confirmation Note: Formal legal venue and dispute resolution terms should be confirmed by the platform owner prior to formal publication.</em>
            </div>
          </div>
        </section>

        {/* Bottom Nav Footer */}
        <div
          style={{
            borderTop: '1px solid var(--border-subtle)',
            paddingTop: '24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '13px',
            color: 'var(--text-muted)',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <div>© 2026 FinEx. Educational Simulation Platform.</div>
          <div style={{ display: 'flex', gap: '16px' }}>
            <a href="/privacy" style={{ color: 'var(--text-muted)', textDecoration: 'none' }}>Privacy Policy</a>
            <span>·</span>
            <button
              onClick={handleBack}
              style={{ background: 'none', border: 'none', color: 'var(--color-action)', cursor: 'pointer', padding: 0, font: 'inherit' }}
            >
              Return to FinEx Terminal
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};

export default TermsOfServiceScreen;
