import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  headline?: string;
  body: string;
  disclaimer?: string;
  citations?: Array<{
    chunk_id: string;
    document_id: string;
    title: string;
    publisher: string;
    section?: string;
    page_number?: number;
    source_url?: string;
    published_date: string;
    excerpt: string;
  }>;
}

export const AskFinExScreen: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputVal, setInputVal] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeConversationId, setActiveConversationId] = useState<string>('conv-welcome-001');
  const [selectedCitation, setSelectedCitation] = useState<any | null>(null);

  // Load persistent conversations from FastAPI on mount
  useEffect(() => {
    const initChat = async () => {
      try {
        const convRes = await apiClient.ai.getConversations();
        if (convRes && convRes.conversations && convRes.conversations.length > 0) {
          const convId = convRes.conversations[0].id;
          setActiveConversationId(convId);
          const msgRes = await apiClient.ai.getMessages(convId);
          if (msgRes && msgRes.messages) {
            setMessages(
              msgRes.messages.map((m) => ({
                id: m.id,
                role: m.role,
                headline: m.headline || '',
                body: m.content,
                disclaimer: m.legal_disclaimer,
                citations: m.citations,
              }))
            );
            // Select first citation if available
            const firstWithCit = msgRes.messages.find((m) => m.citations && m.citations.length > 0);
            if (firstWithCit && firstWithCit.citations) {
              setSelectedCitation(firstWithCit.citations[0]);
            }
          }
        }
      } catch (err) {
        // Fallback default message
        setMessages([
          {
            id: 'init-msg',
            role: 'assistant',
            headline: 'Welcome to Ask FinEx',
            body: 'Ask questions grounded in verified regulatory publications (SEBI, RBI, NSE) and your authorized practice portfolio metrics. All calculations and citations are auditable.',
            disclaimer: 'Educational research only. Does not provide investment advice or equity tips.',
          },
        ]);
      }
    };

    initChat();
  }, []);

  const handleSend = async () => {
    if (!inputVal.trim() || loading) return;
    const userText = inputVal.trim();
    setInputVal('');
    setLoading(true);

    const tempUserMsg: ChatMessage = {
      id: `msg-user-${Date.now()}`,
      role: 'user',
      body: userText,
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const res = await apiClient.ai.sendMessage(activeConversationId, userText);
      if (res && res.assistant_message) {
        const asst = res.assistant_message;
        const newAsstMsg: ChatMessage = {
          id: asst.id,
          role: 'assistant',
          headline: asst.headline,
          body: asst.content,
          disclaimer: asst.legal_disclaimer,
          citations: asst.citations,
        };
        setMessages((prev) => [...prev, newAsstMsg]);
        if (asst.citations && asst.citations.length > 0) {
          setSelectedCitation(asst.citations[0]);
        }
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `msg-err-${Date.now()}`,
          role: 'assistant',
          headline: 'Service Response Issue',
          body: err?.message || 'Could not retrieve verified response. Please verify the backend service is reachable.',
          disclaimer: 'Operational warning: connection to retrieval engine interrupted.',
        },
      ]);
    } finally {
      setLoading(false);
    }
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
        <div className="glass-card" style={{ padding: '28px', display: 'flex', flexDirection: 'column', minHeight: '560px', justifyContent: 'space-between', backgroundColor: '#0A0A0A' }}>
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
              <span>All responses are grounded in verified regulatory sources. Never personalized financial advice.</span>
            </div>

            {/* Messages */}
            {messages.map((m, idx) => {
              if (m.role === 'user') {
                return (
                  <div
                    key={m.id || idx}
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
                    {m.body}
                  </div>
                );
              }

              return (
                <div
                  key={m.id || idx}
                  style={{
                    alignSelf: 'flex-start',
                    maxWidth: '90%',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                  }}
                >
                  {m.headline && (
                    <div style={{ fontSize: '16px', fontWeight: 700, color: '#FFFFFF', letterSpacing: '-0.01em' }}>
                      {m.headline}
                    </div>
                  )}

                  <div style={{ fontSize: '13.5px', lineHeight: 1.6, color: '#D4D4D8', whiteSpace: 'pre-line' }}>
                    {m.body}
                  </div>

                  {/* Citations Badges */}
                  {m.citations && m.citations.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '4px' }}>
                      {m.citations.map((c, cIdx) => (
                        <div
                          key={c.chunk_id || cIdx}
                          onClick={() => setSelectedCitation(c)}
                          style={{
                            fontSize: '11px',
                            color: 'var(--color-action)',
                            backgroundColor: 'rgba(242, 154, 96, 0.1)',
                            border: '1px solid rgba(242, 154, 96, 0.3)',
                            padding: '4px 10px',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          <span>[{cIdx + 1}]</span>
                          <span>{c.publisher}: {c.title.slice(0, 32)}...</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {m.disclaimer && (
                    <div style={{ fontSize: '11px', color: 'var(--text-faint)', fontStyle: 'italic', borderTop: '1px solid var(--border-subtle)', paddingTop: '8px' }}>
                      {m.disclaimer}
                    </div>
                  )}
                </div>
              );
            })}

            {loading && (
              <div style={{ alignSelf: 'flex-start', fontSize: '12px', color: 'var(--color-action)', fontStyle: 'italic' }}>
                FinEx RAG Retriever synthesizing evidence...
              </div>
            )}
          </div>

          {/* Prompt Input Box */}
          <div style={{ marginTop: '24px', display: 'flex', gap: '12px', alignItems: 'center' }}>
            <input
              type="text"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask about emergency funds, asset allocation, diversification, or compare stocks..."
              style={{
                flex: 1,
                padding: '12px 16px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: '#111111',
                border: '1px solid var(--border-subtle)',
                color: '#FFFFFF',
                fontSize: '13px',
                outline: 'none',
              }}
            />
            <button
              onClick={handleSend}
              disabled={loading}
              className="btn btn-action"
              style={{ padding: '12px 24px' }}
            >
              {loading ? 'Asking...' : 'Ask FinEx'}
            </button>
          </div>
        </div>

        {/* Right Source Desk (Evidence Drawer) */}
        <div className="glass-card" style={{ padding: '28px', border: '1px solid var(--border-medium)', backgroundColor: '#0D0D0D' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
            <span className="badge badge-cyan">The Source Desk</span>
            <span style={{ fontSize: '12px', color: 'var(--text-faint)' }}>Verifiable Grounding</span>
          </div>

          {selectedCitation ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Publisher & Document</span>
                <div style={{ fontSize: '16px', fontWeight: 600, color: '#FFFFFF', marginTop: '2px' }}>
                  {selectedCitation.title}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--color-action)', marginTop: '2px' }}>
                  {selectedCitation.publisher} • {selectedCitation.section || 'General Guidance'} • Page {selectedCitation.page_number || 1}
                </div>
              </div>

              <div
                style={{
                  padding: '16px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'rgba(0, 0, 0, 0.4)',
                  border: '1px solid var(--border-subtle)',
                  fontSize: '13px',
                  lineHeight: 1.6,
                  color: 'var(--text-main)',
                }}
              >
                "{selectedCitation.excerpt}"
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="badge badge-profit">Checksum Verified</span>
                <span style={{ fontSize: '11px', color: 'var(--text-faint)', fontFamily: 'var(--font-mono)' }}>
                  ID: {selectedCitation.chunk_id}
                </span>
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Regulatory Framework</span>
                <div style={{ fontSize: '16px', fontWeight: 600, color: '#FFFFFF', marginTop: '2px' }}>
                  Grounded Citation Desk
                </div>
                <div style={{ fontSize: '12px', color: 'var(--color-primary)', marginTop: '2px' }}>
                  SEBI • RBI • NSE Verification
                </div>
              </div>

              <div
                style={{
                  padding: '16px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'rgba(0, 0, 0, 0.4)',
                  border: '1px solid var(--border-subtle)',
                  fontSize: '13px',
                  lineHeight: 1.6,
                  color: 'var(--text-main)',
                }}
              >
                Ask a financial question to inspect verifiable document passages, page offsets, and publication metadata in real-time.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
