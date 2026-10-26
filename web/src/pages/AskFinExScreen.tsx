import React, { useState, useEffect, useRef } from 'react';
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

interface ConversationItem {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

import { CleanFormattedText } from '../components/common/CleanFormattedText';
import { useFinancial } from '../context/FinancialContext';

export const AskFinExScreen: React.FC = () => {
  const { displayName } = useFinancial();
  const trimmedName = displayName?.trim();
  const greeting = trimmedName ? `Namaste, ${trimmedName}` : 'Namaste';

  // Conversation Sessions (Chat History) State
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState<string>('');
  const [loadingHistory, setLoadingHistory] = useState<boolean>(true);
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(() => {
    if (typeof window !== 'undefined' && window.innerWidth < 768) {
      return false;
    }
    return true;
  });

  // Active Chat State
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputVal, setInputVal] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<any | null>(null);
  const [showSourcesPanel, setShowSourcesPanel] = useState<boolean>(false);

  // Model & Provider Info
  const [modelInfo, setModelInfo] = useState<{ model: string; provider: string }>({
    model: 'openai/gpt-oss-120b',
    provider: 'Groq Cloud LPU',
  });

  const chatScrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // 1. Fetch AI Provider Status on Mount
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const statusRes = await apiClient.ai.getAssistantStatus();
        if (statusRes) {
          setModelInfo({
            model: statusRes.model || 'openai/gpt-oss-120b',
            provider: statusRes.provider === 'groq-live' ? 'Groq LPU (120B Flagship)' : statusRes.provider,
          });
        }
      } catch (e) {
        // Fallback default
      }
    };
    fetchStatus();
  }, []);

  // 2. Load Previous Chat History on mount
  // Gemini Behavior: Always start in a fresh NEW CHAT state on open!
  useEffect(() => {
    const loadChatHistory = async () => {
      setLoadingHistory(true);
      try {
        const convRes = await apiClient.ai.getConversations();
        if (convRes && convRes.conversations) {
          setConversations(convRes.conversations);
        }
      } catch (err) {
        console.warn('Could not load chat history:', err);
      } finally {
        setLoadingHistory(false);
      }

      // Explicit Gemini Behavior: Show new chat when website/app opens
      setActiveConversationId(null);
      setMessages([]);
    };

    loadChatHistory();
  }, []);

  // Auto-scroll chat to bottom
  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  // Load a specific historical conversation
  const handleSelectConversation = async (convId: string) => {
    if (typeof window !== 'undefined' && window.innerWidth < 768) {
      setIsHistoryOpen(false);
    }
    if (convId === activeConversationId) return;
    setActiveConversationId(convId);
    setLoading(true);
    try {
      const msgRes = await apiClient.ai.getMessages(convId);
      if (msgRes && msgRes.messages) {
        setMessages(
          msgRes.messages.map((m: any) => ({
            id: m.id,
            role: m.role,
            headline: m.headline || '',
            body: m.content,
            disclaimer: m.legal_disclaimer,
            citations: m.citations,
          }))
        );
        const firstWithCit = msgRes.messages.find((m: any) => m.citations && m.citations.length > 0);
        if (firstWithCit && firstWithCit.citations) {
          setSelectedCitation(firstWithCit.citations[0]);
        }
      } else {
        setMessages([]);
      }
    } catch (err) {
      console.warn('Failed to load conversation messages:', err);
      setMessages([]);
    } finally {
      setLoading(false);
    }
  };

  // Start a fresh New Chat (Gemini behavior)
  const handleStartNewChat = () => {
    setActiveConversationId(null);
    setMessages([]);
    setInputVal('');
    setSelectedCitation(null);
    setShowSourcesPanel(false);
    if (typeof window !== 'undefined' && window.innerWidth < 768) {
      setIsHistoryOpen(false);
    }
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  // Delete a conversation from history
  const handleDeleteConversation = async (e: React.MouseEvent, convId: string) => {
    e.stopPropagation();
    try {
      await apiClient.ai.deleteConversation(convId);
      setConversations((prev) => prev.filter((c) => c.id !== convId));
      if (activeConversationId === convId) {
        handleStartNewChat();
      }
    } catch (err) {
      console.warn('Failed to delete conversation:', err);
    }
  };

  // Send message
  const handleSend = async (presetText?: string) => {
    const textToSend = presetText || inputVal;
    if (!textToSend.trim() || loading) return;

    if (!presetText) setInputVal('');
    setLoading(true);

    const tempUserMsg: ChatMessage = {
      id: `msg-user-${Date.now()}`,
      role: 'user',
      body: textToSend.trim(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      let targetConvId = activeConversationId;

      // If in New Chat mode, create persistent session dynamically
      if (!targetConvId) {
        const rawTitle = textToSend.trim();
        const sessionTitle = rawTitle.length > 38 ? `${rawTitle.slice(0, 35)}...` : rawTitle;
        try {
          const newConv = await apiClient.ai.createConversation(sessionTitle);
          if (newConv && newConv.id) {
            targetConvId = newConv.id;
            setActiveConversationId(newConv.id);
            setConversations((prev) => [newConv, ...prev]);
          }
        } catch (e) {
          targetConvId = `conv-${Date.now()}`;
          setActiveConversationId(targetConvId);
        }
      }

      // Send to backend orchestrator (connected to Groq 120B / Gemini)
      const res = await apiClient.ai.sendMessage(targetConvId || 'conv-default', textToSend.trim());
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
          body: err?.message || 'Could not retrieve AI response. Please ensure backend is running.',
          disclaimer: 'Operational notification.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Filter conversations for search box
  const filteredConversations = conversations.filter((c) =>
    (c.title || 'Research Session').toLowerCase().includes(searchFilter.toLowerCase())
  );

  // Clean Structured Formatter Helper
  const renderFormattedText = (text: string) => {
    return <CleanFormattedText text={text} />;
  };

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        flex: 1,
        minHeight: 0,
        display: 'flex',
        overflow: 'hidden',
        backgroundColor: '#07090E',
      }}
    >
      {/* ============================================================== */}
      {/* 1. LEFT SIDEBAR: CHAT HISTORY (Previous Chats + New Chat)      */}
      {/* ============================================================== */}
      {isHistoryOpen && (
        <div
          className="ask-finex-history-pane"
          style={{
            width: '280px',
            minWidth: '280px',
            maxWidth: '320px',
            backgroundColor: '#090B10',
            borderRight: '1px solid #1A1E29',
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            overflow: 'hidden',
            flexShrink: 0,
          }}
        >
        {/* Top Header & + New Chat Button */}
        <div style={{ padding: '16px', borderBottom: '1px solid #1A1E29', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '14px', fontWeight: 700, color: '#FFFFFF', letterSpacing: '0.02em' }}>
                Chat History
              </span>
              <span
                style={{
                  fontSize: '11px',
                  backgroundColor: '#1E2330',
                  color: '#A1A1AA',
                  padding: '2px 7px',
                  borderRadius: '10px',
                  fontWeight: 600,
                }}
              >
                {conversations.length}
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '11px', color: '#10B981', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#10B981', display: 'inline-block' }} />
                Connected
              </span>
              <button
                type="button"
                className="mobile-only"
                onClick={() => setIsHistoryOpen(false)}
                style={{
                  background: '#161922',
                  border: '1px solid #2A2E39',
                  borderRadius: '4px',
                  color: '#FFFFFF',
                  padding: '3px 8px',
                  fontSize: '11px',
                  cursor: 'pointer',
                }}
              >
                ✕ Close
              </button>
            </div>
          </div>

          {/* + New Chat Button (Prominent, Gemini/ChatGPT Style) */}
          <button
            type="button"
            onClick={handleStartNewChat}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              padding: '11px 16px',
              borderRadius: '8px',
              backgroundColor: '#F29A60',
              border: 'none',
              color: '#000000',
              fontSize: '13px',
              fontWeight: 700,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
              boxShadow: '0 2px 8px rgba(242, 154, 96, 0.25)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#FFA76E';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#F29A60';
            }}
          >
            <span style={{ fontSize: '16px', lineHeight: 1 }}>+</span>
            <span>New Chat</span>
          </button>

          {/* Search Box */}
          <input
            type="text"
            placeholder="Search previous chats..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            style={{
              width: '100%',
              padding: '8px 12px',
              borderRadius: '6px',
              backgroundColor: '#11141C',
              border: '1px solid #242938',
              color: '#FFFFFF',
              fontSize: '12px',
              outline: 'none',
              boxSizing: 'border-box',
            }}
          />
        </div>

        {/* Previous Chats List */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '10px',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
          }}
        >
          {loadingHistory ? (
            <div style={{ textAlign: 'center', padding: '24px 0', color: '#787B86', fontSize: '12px' }}>
              Loading past chats...
            </div>
          ) : filteredConversations.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '28px 12px', color: '#787B86', fontSize: '12px', lineHeight: 1.5 }}>
              {searchFilter ? 'No matching chats found.' : 'No previous chats yet.\nStart a new chat to begin!'}
            </div>
          ) : (
            filteredConversations.map((c) => {
              const isSelected = c.id === activeConversationId;
              const formattedDate = new Date(c.updated_at || c.created_at).toLocaleDateString('en-IN', {
                month: 'short',
                day: 'numeric',
              });

              return (
                <div
                  key={c.id}
                  onClick={() => handleSelectConversation(c.id)}
                  style={{
                    padding: '10px 12px',
                    borderRadius: '7px',
                    backgroundColor: isSelected ? 'rgba(242, 154, 96, 0.14)' : '#11141C',
                    border: `1px solid ${isSelected ? '#F29A60' : '#1C202C'}`,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '8px',
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={(e) => {
                    if (!isSelected) {
                      e.currentTarget.style.backgroundColor = '#171B26';
                      e.currentTarget.style.borderColor = '#2B3142';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected) {
                      e.currentTarget.style.backgroundColor = '#11141C';
                      e.currentTarget.style.borderColor = '#1C202C';
                    }
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                    <span style={{ fontSize: '13px', color: isSelected ? '#F29A60' : '#787B86' }}>💬</span>
                    <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                      <span
                        style={{
                          fontSize: '12.5px',
                          fontWeight: isSelected ? 600 : 500,
                          color: isSelected ? '#FFFFFF' : '#D1D4DC',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          maxWidth: '180px',
                        }}
                      >
                        {c.title || 'Research Session'}
                      </span>
                      <span style={{ fontSize: '10px', color: '#787B86' }}>{formattedDate}</span>
                    </div>
                  </div>

                  {/* Delete Conversation Button */}
                  <button
                    type="button"
                    title="Delete Chat"
                    onClick={(e) => handleDeleteConversation(e, c.id)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#787B86',
                      fontSize: '13px',
                      cursor: 'pointer',
                      padding: '4px',
                      borderRadius: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      opacity: isSelected ? 0.9 : 0.6,
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.color = '#EF4444';
                      e.currentTarget.style.opacity = '1';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.color = '#787B86';
                      e.currentTarget.style.opacity = isSelected ? '0.9' : '0.6';
                    }}
                  >
                    🗑️
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>
      )}

      {/* ============================================================== */}
      {/* 2. RIGHT MAIN WORKSPACE: AI CHAT (Full Right Area)            */}
      {/* ============================================================== */}
      <div
        style={{
          flex: 1,
          backgroundColor: '#07090E',
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          minHeight: 0,
          minWidth: 0,
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        {/* Top Header of Chat Area */}
        <div
          style={{
            padding: '10px 16px',
            borderBottom: '1px solid #1A1E29',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: '#090B10',
            flexShrink: 0,
            flexWrap: 'wrap',
            gap: '8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0, flex: '1 1 auto' }}>
            {/* Toggle History Sidebar button */}
            <button
              type="button"
              onClick={() => setIsHistoryOpen(!isHistoryOpen)}
              title={isHistoryOpen ? 'Collapse Chat History' : 'Expand Chat History'}
              style={{
                background: '#161922',
                border: '1px solid #2A2E39',
                borderRadius: '6px',
                color: isHistoryOpen ? '#D1D4DC' : '#F29A60',
                padding: '6px 10px',
                fontSize: '12px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontWeight: 600,
                flexShrink: 0,
              }}
            >
              <span>{isHistoryOpen ? '✕' : '💬'}</span>
              <span>{isHistoryOpen ? 'Hide' : `History (${conversations.length})`}</span>
            </button>

            <div style={{ minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ fontSize: '15px', fontWeight: 700, color: '#FFFFFF', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {activeConversationId
                    ? conversations.find((c) => c.id === activeConversationId)?.title || 'FinEx AI Assistant'
                    : 'New Chat'}
                </h2>
                <span
                  style={{
                    fontSize: '11px',
                    padding: '2px 8px',
                    borderRadius: '10px',
                    backgroundColor: 'rgba(38, 166, 154, 0.12)',
                    border: '1px solid rgba(38, 166, 154, 0.3)',
                    color: '#26A69A',
                    fontWeight: 600,
                    whiteSpace: 'nowrap',
                  }}
                >
                  ✨ {modelInfo.model}
                </span>
              </div>
              <p style={{ margin: '2px 0 0 0', fontSize: '11.5px', color: '#787B86', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                Document-grounded market intelligence, technical momentum screening & regulatory citations.
              </p>
            </div>
          </div>

          {/* Quick Actions Header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
            {selectedCitation && (
              <button
                type="button"
                onClick={() => setShowSourcesPanel(!showSourcesPanel)}
                style={{
                  fontSize: '11.5px',
                  padding: '5px 12px',
                  borderRadius: '6px',
                  backgroundColor: showSourcesPanel ? 'rgba(242, 154, 96, 0.18)' : '#161922',
                  border: `1px solid ${showSourcesPanel ? '#F29A60' : '#2A2E39'}`,
                  color: showSourcesPanel ? '#F29A60' : '#D1D4DC',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
              >
                📑 Regulatory Source Desk {showSourcesPanel ? '▲' : '▼'}
              </button>
            )}

            <button
              type="button"
              onClick={handleStartNewChat}
              style={{
                fontSize: '11.5px',
                padding: '5px 12px',
                borderRadius: '6px',
                backgroundColor: '#161922',
                border: '1px solid #2A2E39',
                color: '#D1D4DC',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              + New Chat
            </button>
          </div>
        </div>

        {/* Source Desk Citations Drawer (if opened) */}
        {showSourcesPanel && selectedCitation && (
          <div
            style={{
              padding: '16px 20px',
              backgroundColor: '#0F121C',
              borderBottom: '1px solid #242938',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', fontWeight: 700, color: '#F29A60', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Verified Regulatory Grounding Excerpt
              </span>
              <button
                onClick={() => setShowSourcesPanel(false)}
                style={{ background: 'none', border: 'none', color: '#787B86', cursor: 'pointer', fontSize: '13px' }}
              >
                ✕ Close
              </button>
            </div>
            <div style={{ fontSize: '13px', fontWeight: 600, color: '#FFFFFF' }}>
              {selectedCitation.title} ({selectedCitation.publisher})
            </div>
            <div
              style={{
                padding: '10px 14px',
                backgroundColor: 'rgba(0, 0, 0, 0.35)',
                border: '1px solid #1E222D',
                borderRadius: '6px',
                fontSize: '12.5px',
                lineHeight: 1.6,
                color: '#D1D4DC',
                fontStyle: 'italic',
              }}
            >
              "{selectedCitation.excerpt}"
            </div>
            {selectedCitation.source_url && (
              <a
                href={selectedCitation.source_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ fontSize: '11.5px', color: '#38BDF8', textDecoration: 'none' }}
              >
                🔗 Read full regulatory publication
              </a>
            )}
          </div>
        )}

        {/* Chat Thread Messages Stream */}
        <div
          ref={chatScrollRef}
          style={{
            flex: 1,
            minHeight: 0,
            overflowY: 'auto',
            padding: '24px 24px 16px 24px',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div
            style={{
              maxWidth: '960px',
              width: '100%',
              margin: '0 auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '20px',
              flex: messages.length === 0 ? 1 : undefined,
              justifyContent: messages.length === 0 ? 'center' : undefined,
            }}
          >
          {/* Welcome Screen / Gemini-Style Starter Grid if Messages is Empty */}
          {messages.length === 0 ? (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                margin: 'auto 0',
                gap: '24px',
                maxWidth: '720px',
                alignSelf: 'center',
                textAlign: 'center',
              }}
            >
              <div>
                <span style={{ fontSize: '13px', color: '#F29A60', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                  FinEx Financial Intelligence
                </span>
                <h1 style={{ fontSize: '32px', fontWeight: 700, color: '#FFFFFF', marginTop: '6px', letterSpacing: '-0.02em' }}>
                  {greeting}
                </h1>
                <p style={{ color: '#A1A1AA', fontSize: '14px', marginTop: '6px', lineHeight: 1.5 }}>
                  Ask questions grounded in live NSE market quotes, verified technical momentum indicators, and SEBI regulatory publications.
                </p>
              </div>

              {/* Starter Question Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', width: '100%', textAlign: 'left' }}>
                {[
                  {
                    title: '⚡ Best stock for tomorrow',
                    subtitle: 'Screen top liquid NSE equities for momentum, 20-Day SMA, and pivot watch levels',
                    prompt: 'Give me best stock for tomorrow with technical momentum checklist and pivot levels',
                  },
                  {
                    title: '📈 Technical Momentum Analysis',
                    subtitle: 'Explain how to combine 14-period RSI and 20-day SMA for paper trade setups',
                    prompt: 'How to combine 14-period RSI and 20-day SMA to identify swing paper trade setups in Indian markets?',
                  },
                  {
                    title: '💼 Propose Virtual Portfolio',
                    subtitle: 'Simulate a ₹1,00,000 diversified allocation across RELIANCE, TCS, and HDFCBANK',
                    prompt: 'Invest ₹1,00,000 across RELIANCE, TCS, and HDFCBANK in virtual paper trading',
                  },
                  {
                    title: '🛡️ SEBI Risk Management Rules',
                    subtitle: 'Review essential investor safety guidelines and emergency fund allocation',
                    prompt: "What is SEBI's rule on emergency funds and portfolio risk management?",
                  },
                ].map((card, cIdx) => (
                  <div
                    key={cIdx}
                    onClick={() => handleSend(card.prompt)}
                    style={{
                      padding: '16px',
                      backgroundColor: '#11141D',
                      border: '1px solid #1F2433',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px',
                      transition: 'all 0.15s ease',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = '#181C28';
                      e.currentTarget.style.borderColor = '#F29A60';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = '#11141D';
                      e.currentTarget.style.borderColor = '#1F2433';
                    }}
                  >
                    <span style={{ fontSize: '13.5px', fontWeight: 600, color: '#FFFFFF' }}>{card.title}</span>
                    <span style={{ fontSize: '11.5px', color: '#787B86', lineHeight: 1.4 }}>{card.subtitle}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            // Message List
            messages.map((m, idx) => {
              if (m.role === 'user') {
                return (
                  <div
                    key={m.id || idx}
                    style={{
                      alignSelf: 'flex-end',
                      maxWidth: '80%',
                      backgroundColor: 'rgba(242, 154, 96, 0.14)',
                      border: '1px solid rgba(242, 154, 96, 0.3)',
                      borderRadius: '10px',
                      padding: '12px 18px',
                      fontSize: '13.5px',
                      color: '#FFFFFF',
                      lineHeight: 1.5,
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
                    maxWidth: '92%',
                    backgroundColor: '#10131B',
                    border: '1px solid #1E2330',
                    borderRadius: '10px',
                    padding: '18px 22px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                  }}
                >
                  {m.headline && (
                    <div style={{ fontSize: '15px', fontWeight: 700, color: '#FFFFFF', letterSpacing: '-0.01em' }}>
                      {m.headline}
                    </div>
                  )}

                  <div style={{ fontSize: '13.5px', lineHeight: 1.65, color: '#D4D8E2' }}>
                    {renderFormattedText(m.body)}
                  </div>

                  {/* Citations Badges */}
                  {m.citations && m.citations.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
                      {m.citations.map((c, cIdx) => (
                        <button
                          key={c.chunk_id || cIdx}
                          type="button"
                          onClick={() => {
                            setSelectedCitation(c);
                            setShowSourcesPanel(true);
                          }}
                          style={{
                            fontSize: '11px',
                            color: '#F29A60',
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
                          <span>{c.publisher}: {c.title.slice(0, 28)}...</span>
                        </button>
                      ))}
                    </div>
                  )}

                  {m.disclaimer && (
                    <div
                      style={{
                        fontSize: '11px',
                        color: '#787B86',
                        fontStyle: 'italic',
                        borderTop: '1px solid #1A1E29',
                        paddingTop: '8px',
                      }}
                    >
                      {m.disclaimer}
                    </div>
                  )}
                </div>
              );
            })
          )}

          {loading && (
            <div
              style={{
                alignSelf: 'flex-start',
                fontSize: '13px',
                color: '#F29A60',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '12px 18px',
                backgroundColor: '#10131B',
                borderRadius: '8px',
                border: '1px solid #1E2330',
              }}
            >
              <span>⚡</span>
              <span>FinEx AI is analyzing live quotes & technical data...</span>
            </div>
          )}
          </div>
        </div>

        {/* Input Bar at Bottom */}
        <div
          style={{
            padding: '14px 24px 16px 24px',
            borderTop: '1px solid #1A1E29',
            backgroundColor: '#090B10',
            flexShrink: 0,
          }}
        >
          <div
            style={{
              maxWidth: '960px',
              width: '100%',
              margin: '0 auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
            }}
          >
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <input
                ref={inputRef}
                type="text"
                value={inputVal}
                onChange={(e) => setInputVal(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Ask about stocks for tomorrow, technical indicators (SMA, RSI), paper trade proposals..."
                style={{
                  flex: 1,
                  padding: '13px 18px',
                  borderRadius: '8px',
                  backgroundColor: '#12151F',
                  border: '1px solid #242938',
                  color: '#FFFFFF',
                  fontSize: '13.5px',
                  outline: 'none',
                }}
              />
              <button
                type="button"
                onClick={() => handleSend()}
                disabled={loading || !inputVal.trim()}
                style={{
                  padding: '13px 24px',
                  borderRadius: '8px',
                  backgroundColor: inputVal.trim() && !loading ? '#F29A60' : '#2A2E39',
                  border: 'none',
                  color: inputVal.trim() && !loading ? '#000000' : '#787B86',
                  fontSize: '13px',
                  fontWeight: 700,
                  cursor: inputVal.trim() && !loading ? 'pointer' : 'not-allowed',
                  transition: 'all 0.15s ease',
                  flexShrink: 0,
                }}
              >
                {loading ? 'Thinking...' : 'Send'}
              </button>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px', color: '#656A76', padding: '0 4px' }}>
              <span>Virtual paper trading simulator. Educational metrics only. Not financial advice.</span>
              <span>Press Enter ↵ to send</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
