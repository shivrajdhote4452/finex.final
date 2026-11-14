import React from 'react';

interface PrivacyPolicyScreenProps {
  onBack?: () => void;
}

export const PrivacyPolicyScreen: React.FC<PrivacyPolicyScreenProps> = ({ onBack }) => {
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
        backgroundColor: '#000000',
        color: '#FFFFFF',
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      }}
    >
      {/* Top Navigation Bar */}
      <header
        style={{
          borderBottom: '1px solid #1F1F1F',
          backgroundColor: '#080808',
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
            <span style={{ fontSize: '24px', fontWeight: 900, color: '#FFFFFF', letterSpacing: '-0.03em' }}>Fin</span>
            <span style={{ fontSize: '24px', fontWeight: 900, color: 'var(--color-action, #F29A60)', letterSpacing: '-0.03em' }}>Ex</span>
            <span
              style={{
                fontSize: '11px',
                color: '#71717A',
                fontFamily: "'JetBrains Mono', monospace",
                letterSpacing: '0.05em',
                marginLeft: '8px',
              }}
            >
              LEGAL &amp; PRIVACY
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <a
              href="/terms"
              style={{
                fontSize: '13px',
                color: '#A1A1AA',
                textDecoration: 'none',
                padding: '6px 12px',
                borderRadius: '4px',
                border: '1px solid #27272A',
                backgroundColor: '#121214',
              }}
            >
              Terms of Service
            </a>
            <button
              onClick={handleBack}
              style={{
                fontSize: '13px',
                fontWeight: 600,
                color: '#000000',
                backgroundColor: 'var(--color-action, #F29A60)',
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
        <div style={{ marginBottom: '36px', borderBottom: '1px solid #1F1F1F', paddingBottom: '24px' }}>
          <div
            style={{
              fontSize: '12px',
              fontWeight: 700,
              color: 'var(--color-action, #F29A60)',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              fontFamily: "'JetBrains Mono', monospace",
              marginBottom: '8px',
            }}
          >
            Compliance &amp; Data Governance · Version 1.0
          </div>
          <h1
            style={{
              fontSize: '36px',
              fontWeight: 800,
              letterSpacing: '-0.025em',
              color: '#FFFFFF',
              margin: '0 0 12px 0',
              lineHeight: 1.2,
            }}
          >
            FinEx Privacy Policy
          </h1>
          <p style={{ fontSize: '14px', color: '#8E8E93', margin: 0 }}>
            Effective Date: <strong>November 15, 2026</strong> · Application URL: <strong>https://www.finexai.tech</strong>
          </p>
        </div>

        {/* Educational Platform Callout Banner */}
        <div
          style={{
            backgroundColor: '#0A0A0C',
            border: '1px solid #27272A',
            borderLeft: '4px solid var(--color-action, #F29A60)',
            borderRadius: '6px',
            padding: '20px',
            marginBottom: '36px',
          }}
        >
          <div style={{ fontSize: '14px', fontWeight: 700, color: '#FFFFFF', marginBottom: '6px' }}>
            Educational Platform &amp; Paper-Trading Notice
          </div>
          <p style={{ fontSize: '13px', color: '#A1A1AA', lineHeight: 1.6, margin: 0 }}>
            FinEx is strictly an educational financial simulation and learning platform designed to teach market mechanics, order types, risk profiling, and regulatory awareness. All trading on FinEx uses simulated virtual capital (₹1,00,000 virtual balance). FinEx is not a broker, does not connect to real demat accounts, does not hold customer funds or securities, and does not provide investment advisory services.
          </p>
        </div>

        {/* Section 1: Overview */}
        <section style={{ marginBottom: '32px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: '#FFFFFF', marginBottom: '12px' }}>
            1. Overview and Scope
          </h2>
          <p style={{ fontSize: '14px', color: '#D4D4D8', lineHeight: 1.7, margin: '0 0 12px 0' }}>
            This Privacy Policy describes how FinEx ("we", "us", or "our") collects, uses, stores, and discloses information when you visit <strong>https://www.finexai.tech</strong> (the "Site") or access the FinEx Terminal application.
          </p>
          <p style={{ fontSize: '14px', color: '#D4D4D8', lineHeight: 1.7, margin: 0 }}>
            We are committed to transparent data practices and data minimization. We only collect information that is strictly necessary to authenticate your access, deliver educational paper trading, maintain compliance records, and provide AI-assisted financial explanations.
          </p>
        </section>

        {/* Section 2: Information We Collect */}
        <section style={{ marginBottom: '32px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: '#FFFFFF', marginBottom: '12px' }}>
            2. Information We Collect and Process
          </h2>
          <p style={{ fontSize: '14px', color: '#D4D4D8', lineHeight: 1.7, margin: '0 0 16px 0' }}>
            Based on the actual technical implementation of FinEx, the platform processes the following categories of information:
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Google OAuth Data */}
            <div style={{ backgroundColor: '#0A0A0C', border: '1px solid #1F1F1F', borderRadius: '6px', padding: '18px' }}>
              <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-action, #F29A60)', marginBottom: '6px' }}>
                A. Google Account Information (Google Sign-In / OAuth 2.0)
              </div>
              <p style={{ fontSize: '13px', color: '#A1A1AA', lineHeight: 1.6, margin: '0 0 8px 0' }}>
                When you sign in using Google OAuth, Google Identity Services issues a cryptographically signed OpenID Connect ID token. Our backend verifies this token with Google's servers. From this token, we extract and store:
              </p>
              <ul style={{ fontSize: '13px', color: '#D4D4D8', lineHeight: 1.6, paddingLeft: '20px', margin: 0 }}>
                <li><strong>Unique Google Subject Identifier (sub):</strong> A persistent numeric identifier used to securely map your account across logins.</li>
                <li><strong>Email Address:</strong> Your primary Google account email, used as your unique login handle and for essential administrative notices.</li>
                <li><strong>Full Name:</strong> Your display name as provided by Google, used to personalize your workspace interface.</li>
                <li><strong>Profile Picture URL:</strong> If provided by your Google profile, used solely for displaying your avatar inside the terminal.</li>
              </ul>
              <p style={{ fontSize: '12px', color: '#71717A', marginTop: '10px', margin: '10px 0 0 0' }}>
                <em>Note: We never receive, request, or store your Google account password, Google Drive files, contacts, or any other unrelated Google account data.</em>
              </p>
            </div>

            {/* Paper Trading & Simulation Data */}
            <div style={{ backgroundColor: '#0A0A0C', border: '1px solid #1F1F1F', borderRadius: '6px', padding: '18px' }}>
              <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-positive, #4DD5AD)', marginBottom: '6px' }}>
                B. Simulated Paper Trading &amp; Portfolio Data
              </div>
              <p style={{ fontSize: '13px', color: '#A1A1AA', lineHeight: 1.6, margin: '0 0 8px 0' }}>
                To simulate order execution and portfolio management without financial risk, we store:
              </p>
              <ul style={{ fontSize: '13px', color: '#D4D4D8', lineHeight: 1.6, paddingLeft: '20px', margin: 0 }}>
                <li>Your virtual cash balance (initialized at ₹1,00,000 virtual funds, with user-initiated resets supported).</li>
                <li>Simulated orders placed (stock symbol, order side, quantity, order type, simulated price, fill status).</li>
                <li>Paper portfolio holdings, average cost basis, realized/unrealized profit-and-loss calculations, and cash ledger records.</li>
              </ul>
            </div>

            {/* Behavioral Risk Assessment & Learning Preferences */}
            <div style={{ backgroundColor: '#0A0A0C', border: '1px solid #1F1F1F', borderRadius: '6px', padding: '18px' }}>
              <div style={{ fontSize: '14px', fontWeight: 700, color: '#A5B4FC', marginBottom: '6px' }}>
                C. Educational Questionnaire &amp; Preference Data
              </div>
              <p style={{ fontSize: '13px', color: '#A1A1AA', lineHeight: 1.6, margin: '0 0 8px 0' }}>
                To illustrate how personal risk appetite shapes asset allocation:
              </p>
              <ul style={{ fontSize: '13px', color: '#D4D4D8', lineHeight: 1.6, paddingLeft: '20px', margin: 0 }}>
                <li>Responses to our 4-question behavioral risk questionnaire and investment horizon selections, which compute an educational risk tier (Conservative, Moderate, or Aggressive).</li>
                <li>User-created market price alerts and watchlist selections.</li>
                <li>Simulated goal targets and spending category summaries (processed if you choose to test the budgeting CSV upload feature).</li>
              </ul>
            </div>

            {/* AskFinEx Assistant Interactions */}
            <div style={{ backgroundColor: '#0A0A0C', border: '1px solid #1F1F1F', borderRadius: '6px', padding: '18px' }}>
              <div style={{ fontSize: '14px', fontWeight: 700, color: '#38BDF8', marginBottom: '6px' }}>
                D. AskFinEx AI Assistant Queries
              </div>
              <p style={{ fontSize: '13px', color: '#A1A1AA', lineHeight: 1.6, margin: 0 }}>
                Text prompts entered into the AskFinEx search and chat interface are processed to retrieve citations from official public regulatory corpora (SEBI Master Circulars, RBI Directions). Prompts are used exclusively to generate real-time educational responses and are not used to train proprietary public models.
              </p>
            </div>

            {/* Compliance, Consent & Session Logs */}
            <div style={{ backgroundColor: '#0A0A0C', border: '1px solid #1F1F1F', borderRadius: '6px', padding: '18px' }}>
              <div style={{ fontSize: '14px', fontWeight: 700, color: '#E0E0E0', marginBottom: '6px' }}>
                E. Technical, Audit &amp; Consent Records
              </div>
              <p style={{ fontSize: '13px', color: '#A1A1AA', lineHeight: 1.6, margin: '0 0 8px 0' }}>
                To maintain operational security and compliance auditability:
              </p>
              <ul style={{ fontSize: '13px', color: '#D4D4D8', lineHeight: 1.6, paddingLeft: '20px', margin: 0 }}>
                <li><strong>Consent Records:</strong> Policy version acknowledged (e.g., v1.0), timestamp of consent, and client IP/user agent.</li>
                <li><strong>Session Management:</strong> Signed JSON Web Tokens (JWT) with 60-minute expiration, and a server-side revoked token blacklist to ensure instant revocation upon sign-out.</li>
                <li><strong>Error &amp; Diagnostic Logs:</strong> Anonymized HTTP status codes, correlation IDs, and application events to maintain platform reliability.</li>
              </ul>
            </div>
          </div>
        </section>

        {/* Section 3: Google API Services User Data Policy Compliance */}
        <section style={{ marginBottom: '32px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: '#FFFFFF', marginBottom: '12px' }}>
            3. Google API Services User Data Policy &amp; Limited Use Disclosure
          </h2>
          <div
            style={{
              backgroundColor: '#0F172A',
              border: '1px solid #1E293B',
              borderRadius: '6px',
              padding: '20px',
            }}
          >
            <p style={{ fontSize: '13.5px', color: '#E2E8F0', lineHeight: 1.7, margin: '0 0 12px 0' }}>
              FinEx's use and transfer to any other app of information received from Google APIs adheres to the{' '}
              <a
                href="https://developers.google.com/terms/api-services-user-data-policy"
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: '#38BDF8', textDecoration: 'underline' }}
              >
                Google API Services User Data Policy
              </a>
              , including the <strong>Limited Use</strong> requirements.
            </p>
            <p style={{ fontSize: '13px', color: '#94A3B8', lineHeight: 1.6, margin: 0 }}>
              Specifically, Google user data is accessed solely to establish user identity for educational paper trading. We do not transfer, sell, or disclose Google user data to third parties, advertising brokers, data resellers, or information brokers. We do not use Google user data for advertising, marketing campaigns, or credit scoring.
            </p>
          </div>
        </section>

        {/* Section 4: Third-Party Service Providers */}
        <section style={{ marginBottom: '32px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: '#FFFFFF', marginBottom: '12px' }}>
            4. Third-Party Service Providers
          </h2>
          <p style={{ fontSize: '14px', color: '#D4D4D8', lineHeight: 1.7, margin: '0 0 16px 0' }}>
            We partner with reliable cloud and service providers to operate FinEx securely:
          </p>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #27272A', color: '#8E8E93' }}>
                  <th style={{ padding: '10px 12px' }}>Provider</th>
                  <th style={{ padding: '10px 12px' }}>Purpose</th>
                  <th style={{ padding: '10px 12px' }}>Data Handled</th>
                </tr>
              </thead>
              <tbody style={{ color: '#D4D4D8' }}>
                <tr style={{ borderBottom: '1px solid #1F1F1F' }}>
                  <td style={{ padding: '12px', fontWeight: 600, color: '#FFFFFF' }}>Google Identity Services</td>
                  <td style={{ padding: '12px' }}>OAuth 2.0 Identity Authentication</td>
                  <td style={{ padding: '12px' }}>ID token verification (email, name, sub)</td>
                </tr>
                <tr style={{ borderBottom: '1px solid #1F1F1F' }}>
                  <td style={{ padding: '12px', fontWeight: 600, color: '#FFFFFF' }}>Neon (PostgreSQL on AWS)</td>
                  <td style={{ padding: '12px' }}>Operational Cloud Database</td>
                  <td style={{ padding: '12px' }}>Encrypted user profiles, orders, paper positions</td>
                </tr>
                <tr style={{ borderBottom: '1px solid #1F1F1F' }}>
                  <td style={{ padding: '12px', fontWeight: 600, color: '#FFFFFF' }}>Render</td>
                  <td style={{ padding: '12px' }}>Backend API Web Service</td>
                  <td style={{ padding: '12px' }}>FastAPI endpoints, simulated order matching</td>
                </tr>
                <tr style={{ borderBottom: '1px solid #1F1F1F' }}>
                  <td style={{ padding: '12px', fontWeight: 600, color: '#FFFFFF' }}>Vercel</td>
                  <td style={{ padding: '12px' }}>Frontend Static Hosting &amp; CDN</td>
                  <td style={{ padding: '12px' }}>Web application distribution (https://www.finexai.tech)</td>
                </tr>
                <tr style={{ borderBottom: '1px solid #1F1F1F' }}>
                  <td style={{ padding: '12px', fontWeight: 600, color: '#FFFFFF' }}>Yahoo Finance / Angel SmartAPI</td>
                  <td style={{ padding: '12px' }}>Market Observation Feeds</td>
                  <td style={{ padding: '12px' }}>Public Indian market symbols &amp; candles (no user data)</td>
                </tr>
                <tr style={{ borderBottom: '1px solid #1F1F1F' }}>
                  <td style={{ padding: '12px', fontWeight: 600, color: '#FFFFFF' }}>Groq API / Google Gemini</td>
                  <td style={{ padding: '12px' }}>Educational AI Question Answering</td>
                  <td style={{ padding: '12px' }}>User text queries on financial concepts &amp; regulations</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* Section 5: Security & Session Protection */}
        <section style={{ marginBottom: '32px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: '#FFFFFF', marginBottom: '12px' }}>
            5. Security &amp; Session Protection
          </h2>
          <p style={{ fontSize: '14px', color: '#D4D4D8', lineHeight: 1.7, margin: '0 0 12px 0' }}>
            We implement strict security measures to protect user data and maintain service integrity:
          </p>
          <ul style={{ fontSize: '13.5px', color: '#D4D4D8', lineHeight: 1.7, paddingLeft: '20px', margin: 0 }}>
            <li><strong>Fail-Closed Authentication:</strong> All protected API endpoints verify cryptographic JWT tokens. Missing, malformed, expired, or revoked tokens return HTTP 401.</li>
            <li><strong>Session Expiration &amp; Immediate Revocation:</strong> Access tokens expire after 60 minutes. When a user clicks Sign Out, the token is recorded in the server-side revocation list to prevent replay attacks.</li>
            <li><strong>Transport Encryption:</strong> All communications between the browser, Vercel frontend, Render backend, and database use TLS/HTTPS encryption.</li>
            <li><strong>No Financial Asset Exposure:</strong> Because FinEx operates strictly with virtual funds and has no access to real bank or brokerage accounts, users face zero financial asset exposure.</li>
          </ul>
        </section>

        {/* Section 6: Data Retention & User Rights */}
        <section style={{ marginBottom: '32px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: '#FFFFFF', marginBottom: '12px' }}>
            6. Data Retention, Deletion &amp; User Inquiries
          </h2>
          <p style={{ fontSize: '14px', color: '#D4D4D8', lineHeight: 1.7, margin: '0 0 12px 0' }}>
            Your account profile and virtual trading records remain stored in our database while your account is active, enabling you to resume your learning and review order histories across browser sessions.
          </p>
          <div
            style={{
              backgroundColor: '#0A0A0C',
              border: '1px solid #1F1F1F',
              borderRadius: '6px',
              padding: '16px',
              marginBottom: '14px',
            }}
          >
            <strong style={{ fontSize: '13.5px', color: '#FFFFFF' }}>Account Deletion and Data Purge Requests</strong>
            <p style={{ fontSize: '13px', color: '#A1A1AA', lineHeight: 1.6, marginTop: '4px', margin: 0 }}>
              If you wish to delete your account, remove your Google identity mapping, or wipe your paper-trading history from our database, you may submit a request to the platform administrator at{' '}
              <a href="mailto:shivrajdhote4452@gmail.com" style={{ color: 'var(--color-action, #F29A60)' }}>
                shivrajdhote4452@gmail.com
              </a>
              . Requests are verified and processed manually by the administrator.
            </p>
          </div>
          <p style={{ fontSize: '13px', color: '#8E8E93', lineHeight: 1.6, margin: 0 }}>
            <em>Owner Confirmation Note:</em> Specific automated data retention schedules and self-service account deletion workflows are subject to administrative confirmation prior to official store or marketplace publication.
          </p>
        </section>

        {/* Section 7: Children's Privacy */}
        <section style={{ marginBottom: '32px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: '#FFFFFF', marginBottom: '12px' }}>
            7. Children's Privacy
          </h2>
          <p style={{ fontSize: '14px', color: '#D4D4D8', lineHeight: 1.7, margin: 0 }}>
            FinEx is designed for university students, educators, and adult retail learners. We do not knowingly collect personal information from individuals under 13 years of age. If we learn that personal data of a minor has been collected without verifiable parental consent, we will promptly delete that information.
          </p>
        </section>

        {/* Section 8: Contact Information */}
        <section style={{ marginBottom: '48px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: '#FFFFFF', marginBottom: '12px' }}>
            8. Contact Information
          </h2>
          <p style={{ fontSize: '14px', color: '#D4D4D8', lineHeight: 1.7, margin: '0 0 12px 0' }}>
            If you have questions, feedback, or data requests regarding this Privacy Policy or FinEx's educational workspace, please contact:
          </p>
          <div style={{ backgroundColor: '#0A0A0C', border: '1px solid #1F1F1F', borderRadius: '6px', padding: '18px' }}>
            <div style={{ fontSize: '14px', fontWeight: 700, color: '#FFFFFF' }}>FinEx Platform Team</div>
            <div style={{ fontSize: '13px', color: '#A1A1AA', marginTop: '4px' }}>Lead Developer &amp; Administrator: Shivraj Dhote</div>
            <div style={{ fontSize: '13px', color: '#A1A1AA', marginTop: '2px' }}>
              Inquiries &amp; Privacy: <a href="mailto:shivrajdhote4452@gmail.com" style={{ color: 'var(--color-action, #F29A60)' }}>shivrajdhote4452@gmail.com</a>
            </div>
            <div style={{ fontSize: '13px', color: '#71717A', marginTop: '4px' }}>Website: https://www.finexai.tech</div>
          </div>
        </section>

        {/* Bottom Nav Footer */}
        <div
          style={{
            borderTop: '1px solid #1F1F1F',
            paddingTop: '24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '13px',
            color: '#71717A',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <div>© 2026 FinEx. Educational Simulation Platform.</div>
          <div style={{ display: 'flex', gap: '16px' }}>
            <a href="/terms" style={{ color: '#A1A1AA', textDecoration: 'none' }}>Terms of Service</a>
            <span>·</span>
            <button
              onClick={handleBack}
              style={{ background: 'none', border: 'none', color: 'var(--color-action, #F29A60)', cursor: 'pointer', padding: 0, font: 'inherit' }}
            >
              Return to FinEx Terminal
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};

export default PrivacyPolicyScreen;
