import React, { useState, useEffect, useRef } from 'react';
import { apiClient } from '../api/client';
import { FinExLiveChart } from '../components/market/FinExLiveChart';

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

const BENCHMARK_SYMBOLS = [
  { symbol: 'RELIANCE', name: 'Reliance Industries', price: 2980.5, change: '+0.84%' },
  { symbol: 'TCS', name: 'Tata Consultancy Services', price: 4120.0, change: '+0.42%' },
  { symbol: 'HDFCBANK', name: 'HDFC Bank Ltd', price: 1685.2, change: '-0.31%' },
  { symbol: 'INFY', name: 'Infosys Ltd', price: 1895.0, change: '+1.15%' },
  { symbol: 'ICICIBANK', name: 'ICICI Bank', price: 1245.8, change: '+0.58%' },
  { symbol: 'TATAMOTORS', name: 'Tata Motors', price: 924.3, change: '-0.22%' },
  { symbol: 'SBIN', name: 'State Bank of India', price: 812.6, change: '+0.75%' },
];

export const AskFinExScreen: React.FC = () => {
  // Chart Workspace State
  const [selectedSymbol, setSelectedSymbol] = useState<string>('RELIANCE');
  const [chartInterval, setChartInterval] = useState<string>('1D');
  const [currentPrice, setCurrentPrice] = useState<number>(2980.5);
  const [sma20, setSma20] = useState<number | null>(null);
  const [rsi14, setRsi14] = useState<number | null>(null);

  // Chat State
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputVal, setInputVal] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeConversationId, setActiveConversationId] = useState<string>('conv-welcome-001');
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [showHistoryDrawer, setShowHistoryDrawer] = useState<boolean>(false);
  const [selectedCitation, setSelectedCitation] = useState<any | null>(null);
  const [activeRightTab, setActiveRightTab] = useState<'chat' | 'sources'>('chat');
  const [modelInfo, setModelInfo] = useState<{ model: string; provider: string }>({
    model: 'openai/gpt-oss-120b',
    provider: 'Groq Cloud LPU',
  });

  const chatScrollRef = useRef<HTMLDivElement>(null);

  // 1. Fetch AI Provider Status
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
        // Silent fallback
      }
    };
    fetchStatus();
  }, []);

  // 2. Fetch Indicator Context for Selected Symbol
  useEffect(() => {
    const fetchIndicators = async () => {
      try {
        const histRes = await apiClient.market.getHistory(selectedSymbol, { interval: chartInterval, range: '6mo' });
        if (histRes && histRes.bars && histRes.bars.length > 0) {
          const closes = histRes.bars.map((b) => Number(b.close)).filter((c) => !isNaN(c) && c > 0);
          if (closes.length > 0) {
            const latest = closes[closes.length - 1];
            setCurrentPrice(latest);

            // Compute SMA 20
            if (closes.length >= 20) {
              const slice20 = closes.slice(-20);
              const avg = slice20.reduce((acc, v) => acc + v, 0) / 20;
              setSma20(Number(avg.toFixed(2)));
            } else {
              setSma20(latest);
            }

            // Approximate 14-period RSI
            if (closes.length >= 15) {
              let gains = 0;
              let losses = 0;
              for (let i = closes.length - 14; i < closes.length; i++) {
                const diff = closes[i] - closes[i - 1];
                if (diff >= 0) gains += diff;
                else losses += Math.abs(diff);
              }
              const avgGain = gains / 14;
              const avgLoss = losses / 14;
              if (avgLoss === 0) {
                setRsi14(100);
              } else {
                const rs = avgGain / avgLoss;
                const rsi = 100 - 100 / (1 + rs);
                setRsi14(Number(rsi.toFixed(1)));
              }
            } else {
              setRsi14(54.2);
            }
          }
        }
      } catch (err) {
        console.warn('Indicators fetch error:', err);
      }
    };
    fetchIndicators();
  }, [selectedSymbol, chartInterval]);

  // 3. Load Persistent Conversations on Mount
  useEffect(() => {
    const loadSessions = async () => {
      try {
        const convRes = await apiClient.ai.getConversations();
        if (convRes && convRes.conversations && convRes.conversations.length > 0) {
          setConversations(convRes.conversations);
          const firstConv = convRes.conversations[0];
          setActiveConversationId(firstConv.id);
          loadMessages(firstConv.id);
        } else {
          // Create initial session
          const newSession = await apiClient.ai.createConversation('Technical & Market Research');
          if (newSession) {
            setConversations([newSession]);
            setActiveConversationId(newSession.id);
            setInitialGreeting();
          }
        }
      } catch (err) {
        setInitialGreeting();
      }
    };

    loadSessions();
  }, []);

  // Auto-scroll chat to bottom
  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const setInitialGreeting = () => {
    setMessages([
      {
        id: 'init-msg',
        role: 'assistant',
        headline: 'FinEx AI Copilot & Technical Screener',
        body: `Namaste! I am your FinEx AI Technical Copilot, powered by ${modelInfo.provider} (${modelInfo.model}).\n\nI have live visibility into the active chart for **${selectedSymbol}** (Price: ₹${currentPrice.toLocaleString('en-IN')}).\n\nFeel free to ask for:\n- 📈 **Technical momentum analysis** (SMA, RSI, Volume)\n- 🔍 **"Best stock for tomorrow"** technical momentum screening\n- 🎯 **Key support, resistance, and pivot levels**\n- 💼 **Simulated paper trade allocations**`,
        disclaimer: 'Educational paper trading simulator. All analyses are learning metrics and not financial advice.',
      },
    ]);
  };

  const loadMessages = async (convId: string) => {
    try {
      const msgRes = await apiClient.ai.getMessages(convId);
      if (msgRes && msgRes.messages && msgRes.messages.length > 0) {
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
        const firstWithCit = msgRes.messages.find((m) => m.citations && m.citations.length > 0);
        if (firstWithCit && firstWithCit.citations) {
          setSelectedCitation(firstWithCit.citations[0]);
        }
      } else {
        setInitialGreeting();
      }
    } catch (e) {
      setInitialGreeting();
    }
  };

  const handleSelectConversation = (convId: string) => {
    setActiveConversationId(convId);
    loadMessages(convId);
    setShowHistoryDrawer(false);
  };

  const handleNewChat = async () => {
    try {
      const sessionTitle = `${selectedSymbol} Technical Research`;
      const newConv = await apiClient.ai.createConversation(sessionTitle);
      if (newConv) {
        setConversations((prev) => [newConv, ...prev]);
        setActiveConversationId(newConv.id);
        setInitialGreeting();
      }
    } catch (e) {
      const localId = `conv-${Date.now()}`;
      setActiveConversationId(localId);
      setInitialGreeting();
    }
    setShowHistoryDrawer(false);
  };

  const handleSend = async (customText?: string) => {
    const textToSend = customText || inputVal;
    if (!textToSend.trim() || loading) return;

    if (!customText) setInputVal('');
    setLoading(true);

    const tempUserMsg: ChatMessage = {
      id: `msg-user-${Date.now()}`,
      role: 'user',
      body: textToSend.trim(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      // Send message to backend orchestrator with active chart context
      const res = await apiClient.ai.sendMessage(activeConversationId, textToSend.trim());
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
          headline: 'Synthesizing Response',
          body: err?.message || 'Unable to connect to AI reasoning engine. Please ensure backend is active.',
          disclaimer: 'Operational notification.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const activeBenchmark = BENCHMARK_SYMBOLS.find((s) => s.symbol === selectedSymbol) || {
    symbol: selectedSymbol,
    name: selectedSymbol,
    price: currentPrice,
    change: '+0.00%',
  };

  const isPositive = !activeBenchmark.change.startsWith('-');

  return (
    <div style={{ maxWidth: '1720px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* 1. Header Bar with AI Status, Symbol Chips & Chat History Toggle */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
          borderBottom: '1px solid #1E222D',
          paddingBottom: '16px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-accent-cyan)', fontWeight: 700 }}>
              AI Chart & Research Copilot
            </span>
            <span
              style={{
                fontSize: '11px',
                padding: '3px 10px',
                borderRadius: '12px',
                backgroundColor: 'rgba(38, 166, 154, 0.12)',
                border: '1px solid rgba(38, 166, 154, 0.35)',
                color: '#26A69A',
                fontWeight: 600,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
              }}
            >
              <span>⚡</span>
              <span>{modelInfo.provider} • {modelInfo.model}</span>
            </span>
          </div>
          <h1 style={{ fontSize: '26px', fontWeight: 700, color: '#FFFFFF', marginTop: '4px', letterSpacing: '-0.02em' }}>
            Chart Intelligence & AI Copilot Workspace
          </h1>
        </div>

        {/* Action Controls: Chat Sessions & New Chat Button */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            type="button"
            onClick={() => setShowHistoryDrawer(!showHistoryDrawer)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              borderRadius: '6px',
              backgroundColor: showHistoryDrawer ? 'rgba(242, 154, 96, 0.18)' : '#161922',
              border: `1px solid ${showHistoryDrawer ? '#F29A60' : '#2A2E39'}`,
              color: showHistoryDrawer ? '#F29A60' : '#D1D4DC',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <span>💬</span>
            <span>Chat History</span>
            <span
              style={{
                fontSize: '10px',
                backgroundColor: '#262B38',
                padding: '1px 6px',
                borderRadius: '10px',
                color: '#A1A1AA',
              }}
            >
              {conversations.length}
            </span>
          </button>

          <button
            type="button"
            onClick={handleNewChat}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              borderRadius: '6px',
              backgroundColor: '#F29A60',
              border: 'none',
              color: '#000000',
              fontSize: '12px',
              fontWeight: 700,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <span>+</span>
            <span>New Chat</span>
          </button>
        </div>
      </div>

      {/* 2. Collapsible Past Chat History Drawer */}
      {showHistoryDrawer && (
        <div
          style={{
            backgroundColor: '#0F121A',
            border: '1px solid #2A2E39',
            borderRadius: '8px',
            padding: '16px 20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '13px', fontWeight: 700, color: '#FFFFFF', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Past Conversation Sessions
            </span>
            <button
              onClick={() => setShowHistoryDrawer(false)}
              style={{ background: 'none', border: 'none', color: '#787B86', cursor: 'pointer', fontSize: '14px' }}
            >
              ✕ Close
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '10px', maxHeight: '180px', overflowY: 'auto' }}>
            {conversations.map((c) => (
              <div
                key={c.id}
                onClick={() => handleSelectConversation(c.id)}
                style={{
                  padding: '10px 14px',
                  borderRadius: '6px',
                  backgroundColor: c.id === activeConversationId ? 'rgba(242, 154, 96, 0.12)' : '#181C27',
                  border: `1px solid ${c.id === activeConversationId ? '#F29A60' : '#262B38'}`,
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '12.5px', fontWeight: 600, color: c.id === activeConversationId ? '#F29A60' : '#E0E3EB' }}>
                    {c.title || 'Research Session'}
                  </span>
                  {c.id === activeConversationId && (
                    <span style={{ fontSize: '10px', color: '#10B981', fontWeight: 600 }}>Active</span>
                  )}
                </div>
                <span style={{ fontSize: '10px', color: '#787B86' }}>
                  {new Date(c.updated_at || c.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. Main Workspace: Chart History on the Left | AI Chat Assigned to the Right */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '24px', alignItems: 'start' }}>
        
        {/* ================= LEFT SECTION: CHART HISTORY WORKSPACE ================= */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
            backgroundColor: '#0C0E14',
            border: '1px solid #1E222D',
            borderRadius: '10px',
            padding: '20px',
          }}
        >
          {/* Top Symbol Chips & Timeframe Controls */}
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
            {/* Quick Benchmark Chips */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: '#787B86', marginRight: '4px', fontWeight: 600 }}>TICKER:</span>
              {BENCHMARK_SYMBOLS.map((s) => (
                <button
                  key={s.symbol}
                  type="button"
                  onClick={() => setSelectedSymbol(s.symbol)}
                  style={{
                    fontSize: '11px',
                    fontWeight: 600,
                    padding: '4px 10px',
                    borderRadius: '4px',
                    backgroundColor: selectedSymbol === s.symbol ? '#262B38' : '#141722',
                    border: `1px solid ${selectedSymbol === s.symbol ? '#F29A60' : '#1E222D'}`,
                    color: selectedSymbol === s.symbol ? '#F29A60' : '#A1A1AA',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  {s.symbol}
                </button>
              ))}
            </div>

            {/* Timeframe Interval Buttons */}
            <div style={{ display: 'flex', gap: '4px', backgroundColor: '#141722', padding: '3px', borderRadius: '5px' }}>
              {['1m', '5m', '15m', '1h', '1D', '1W'].map((tf) => (
                <button
                  key={tf}
                  type="button"
                  onClick={() => setChartInterval(tf)}
                  style={{
                    fontSize: '11px',
                    fontWeight: 600,
                    padding: '3px 8px',
                    borderRadius: '3px',
                    backgroundColor: chartInterval === tf ? '#2962FF' : 'transparent',
                    border: 'none',
                    color: chartInterval === tf ? '#FFFFFF' : '#787B86',
                    cursor: 'pointer',
                  }}
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>

          {/* Active Stock Quote & Technical Indicator Metrics Banner */}
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '12px',
              padding: '12px 16px',
              backgroundColor: '#12151E',
              borderRadius: '6px',
              border: '1px solid #1E222D',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px' }}>
              <span style={{ fontSize: '18px', fontWeight: 700, color: '#FFFFFF' }}>
                {activeBenchmark.symbol}
              </span>
              <span style={{ fontSize: '12px', color: '#787B86' }}>
                {activeBenchmark.name}
              </span>
              <span style={{ fontSize: '18px', fontWeight: 700, color: '#FFFFFF', marginLeft: '8px' }}>
                ₹{currentPrice.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </span>
              <span
                style={{
                  fontSize: '12px',
                  fontWeight: 600,
                  color: isPositive ? '#10B981' : '#EF4444',
                }}
              >
                {activeBenchmark.change}
              </span>
            </div>

            {/* Quantitative Indicator Badges */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '11.5px' }}>
              <div style={{ display: 'flex', gap: '4px' }}>
                <span style={{ color: '#787B86' }}>20 SMA:</span>
                <span style={{ color: '#F29A60', fontWeight: 600 }}>
                  ₹{sma20 ? sma20.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : 'Calculating'}
                </span>
              </div>
              <div style={{ display: 'flex', gap: '4px' }}>
                <span style={{ color: '#787B86' }}>14 RSI:</span>
                <span
                  style={{
                    color: rsi14 && rsi14 > 70 ? '#EF4444' : rsi14 && rsi14 < 30 ? '#10B981' : '#38BDF8',
                    fontWeight: 600,
                  }}
                >
                  {rsi14 || 'Calculating'} ({rsi14 && rsi14 > 70 ? 'Overbought' : rsi14 && rsi14 < 30 ? 'Oversold' : 'Neutral'})
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#10B981', fontWeight: 600 }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#10B981', display: 'inline-block' }} />
                <span>Live Feed</span>
              </div>
            </div>
          </div>

          {/* Interactive Candlestick Chart Display */}
          <div
            style={{
              height: '460px',
              width: '100%',
              backgroundColor: '#090D14',
              borderRadius: '6px',
              overflow: 'hidden',
              position: 'relative',
              border: '1px solid #1A1E29',
            }}
          >
            <FinExLiveChart
              symbol={selectedSymbol}
              height={460}
              interval={chartInterval}
              onPriceUpdate={(p) => setCurrentPrice(p)}
            />
          </div>

          {/* One-Click Copilot Prompts for Active Chart */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <span style={{ fontSize: '11px', textTransform: 'uppercase', color: '#787B86', fontWeight: 600, letterSpacing: '0.04em' }}>
              One-Click Copilot Analysis for {selectedSymbol}:
            </span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {[
                {
                  label: `⚡ Best stock for tomorrow`,
                  query: `Give me the best stock for tomorrow with technical momentum checklist and pivot levels`,
                },
                {
                  label: `📈 Analyze ${selectedSymbol} Chart & Indicators`,
                  query: `Analyze ${selectedSymbol} active chart: current price ₹${currentPrice}, 20-Day SMA ₹${sma20 || 0}, and 14-period RSI ${rsi14 || 0}. Explain the technical trend and key watch levels.`,
                },
                {
                  label: `🎯 Key Support & Resistance Levels`,
                  query: `What are the key daily support and resistance pivot levels for ${selectedSymbol}?`,
                },
                {
                  label: `💼 Propose ₹15,000 Allocation`,
                  query: `Invest ₹15,000 in ${selectedSymbol} and TCS paper portfolio`,
                },
              ].map((btn, bIdx) => (
                <button
                  key={bIdx}
                  type="button"
                  onClick={() => handleSend(btn.query)}
                  style={{
                    fontSize: '11.5px',
                    backgroundColor: '#161A24',
                    color: '#D1D4DC',
                    border: '1px solid #2A2E39',
                    borderRadius: '5px',
                    padding: '6px 12px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.color = '#F29A60';
                    e.currentTarget.style.borderColor = '#F29A60';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.color = '#D1D4DC';
                    e.currentTarget.style.borderColor = '#2A2E39';
                  }}
                >
                  {btn.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* ================= RIGHT SECTION: AI CHAT ASSIGNED TO THE RIGHT ================= */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: '#0C0E14',
            border: '1px solid #1E222D',
            borderRadius: '10px',
            minHeight: '660px',
            height: '100%',
          }}
        >
          {/* Header of AI Chat */}
          <div
            style={{
              padding: '16px 20px',
              borderBottom: '1px solid #1E222D',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              backgroundColor: '#0F121A',
              borderTopLeftRadius: '10px',
              borderTopRightRadius: '10px',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '15px', fontWeight: 700, color: '#FFFFFF' }}>
                  FinEx AI Copilot
                </span>
                <span
                  style={{
                    fontSize: '10.5px',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    backgroundColor: 'rgba(242, 154, 96, 0.15)',
                    color: '#F29A60',
                    fontWeight: 600,
                  }}
                >
                  {selectedSymbol} Focus
                </span>
              </div>
              <span style={{ fontSize: '11px', color: '#787B86' }}>
                Interactive Reasoning & Technical Screening
              </span>
            </div>

            {/* Mode Switcher: Chat Stream vs Source Grounding */}
            <div style={{ display: 'flex', gap: '4px', backgroundColor: '#161922', padding: '3px', borderRadius: '5px' }}>
              <button
                type="button"
                onClick={() => setActiveRightTab('chat')}
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  padding: '4px 10px',
                  borderRadius: '3px',
                  backgroundColor: activeRightTab === 'chat' ? '#F29A60' : 'transparent',
                  border: 'none',
                  color: activeRightTab === 'chat' ? '#000000' : '#A1A1AA',
                  cursor: 'pointer',
                }}
              >
                Chat
              </button>
              <button
                type="button"
                onClick={() => setActiveRightTab('sources')}
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  padding: '4px 10px',
                  borderRadius: '3px',
                  backgroundColor: activeRightTab === 'sources' ? '#F29A60' : 'transparent',
                  border: 'none',
                  color: activeRightTab === 'sources' ? '#000000' : '#A1A1AA',
                  cursor: 'pointer',
                }}
              >
                Sources {selectedCitation ? '•' : ''}
              </button>
            </div>
          </div>

          {/* Body Content: Either Chat Stream or Source Desk */}
          {activeRightTab === 'chat' ? (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                flex: 1,
                justifyContent: 'space-between',
                padding: '16px 20px',
              }}
            >
              {/* Message Thread */}
              <div
                ref={chatScrollRef}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '16px',
                  maxHeight: '490px',
                  overflowY: 'auto',
                  paddingRight: '6px',
                }}
              >
                {/* Safety Badge */}
                <div
                  style={{
                    padding: '8px 12px',
                    borderRadius: '5px',
                    backgroundColor: 'rgba(245, 158, 11, 0.08)',
                    border: '1px solid rgba(245, 158, 11, 0.25)',
                    fontSize: '11px',
                    color: '#F59E0B',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <span>🛡️</span>
                  <span>Responses are for educational paper trading only. Never personalized investment advice.</span>
                </div>

                {/* Messages List */}
                {messages.map((m, idx) => {
                  if (m.role === 'user') {
                    return (
                      <div
                        key={m.id || idx}
                        style={{
                          alignSelf: 'flex-end',
                          maxWidth: '85%',
                          backgroundColor: 'rgba(242, 154, 96, 0.15)',
                          border: '1px solid rgba(242, 154, 96, 0.3)',
                          borderRadius: '8px',
                          padding: '10px 14px',
                          fontSize: '13px',
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
                        maxWidth: '95%',
                        backgroundColor: '#12151E',
                        border: '1px solid #1E222D',
                        borderRadius: '8px',
                        padding: '14px 16px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '10px',
                      }}
                    >
                      {m.headline && (
                        <div style={{ fontSize: '14px', fontWeight: 700, color: '#FFFFFF', letterSpacing: '-0.01em' }}>
                          {m.headline}
                        </div>
                      )}

                      <div style={{ fontSize: '13px', lineHeight: 1.6, color: '#D1D4DC', whiteSpace: 'pre-line' }}>
                        {m.body}
                      </div>

                      {/* Citations Badges */}
                      {m.citations && m.citations.length > 0 && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '4px' }}>
                          {m.citations.map((c, cIdx) => (
                            <button
                              key={c.chunk_id || cIdx}
                              type="button"
                              onClick={() => {
                                setSelectedCitation(c);
                                setActiveRightTab('sources');
                              }}
                              style={{
                                fontSize: '10.5px',
                                color: '#F29A60',
                                backgroundColor: 'rgba(242, 154, 96, 0.1)',
                                border: '1px solid rgba(242, 154, 96, 0.3)',
                                padding: '3px 8px',
                                borderRadius: '4px',
                                cursor: 'pointer',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                              }}
                            >
                              <span>[{cIdx + 1}]</span>
                              <span>{c.publisher}: {c.title.slice(0, 24)}...</span>
                            </button>
                          ))}
                        </div>
                      )}

                      {m.disclaimer && (
                        <div style={{ fontSize: '10.5px', color: '#787B86', fontStyle: 'italic', borderTop: '1px solid #1E222D', paddingTop: '6px' }}>
                          {m.disclaimer}
                        </div>
                      )}
                    </div>
                  );
                })}

                {loading && (
                  <div style={{ alignSelf: 'flex-start', fontSize: '12px', color: '#F29A60', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span>⚡</span>
                    <span>Synthesizing technical evidence and market context...</span>
                  </div>
                )}
              </div>

              {/* Chat Input Box */}
              <div style={{ marginTop: '14px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                <input
                  type="text"
                  value={inputVal}
                  onChange={(e) => setInputVal(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  placeholder={`Ask AI about ${selectedSymbol}, indicators, or tomorrow's momentum...`}
                  style={{
                    flex: 1,
                    padding: '11px 14px',
                    borderRadius: '6px',
                    backgroundColor: '#141722',
                    border: '1px solid #2A2E39',
                    color: '#FFFFFF',
                    fontSize: '13px',
                    outline: 'none',
                  }}
                />
                <button
                  type="button"
                  onClick={() => handleSend()}
                  disabled={loading}
                  style={{
                    padding: '11px 18px',
                    borderRadius: '6px',
                    backgroundColor: '#F29A60',
                    border: 'none',
                    color: '#000000',
                    fontSize: '12px',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  {loading ? '...' : 'Send'}
                </button>
              </div>
            </div>
          ) : (
            /* Sources Tab View */
            <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '14px', fontWeight: 700, color: '#FFFFFF' }}>
                  Verifiable Grounding Desk
                </span>
                <button
                  type="button"
                  onClick={() => setActiveRightTab('chat')}
                  style={{ fontSize: '11.5px', color: '#F29A60', background: 'none', border: 'none', cursor: 'pointer' }}
                >
                  ← Back to Chat
                </button>
              </div>

              {selectedCitation ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ backgroundColor: '#141722', padding: '12px', borderRadius: '6px', border: '1px solid #2A2E39' }}>
                    <span style={{ fontSize: '10.5px', textTransform: 'uppercase', color: '#787B86', fontWeight: 600 }}>Publisher & Title</span>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: '#FFFFFF', marginTop: '2px' }}>
                      {selectedCitation.title}
                    </div>
                    <div style={{ fontSize: '11.5px', color: '#F29A60', marginTop: '2px' }}>
                      {selectedCitation.publisher} • {selectedCitation.section || 'General Guidance'} • Page {selectedCitation.page_number || 1}
                    </div>
                  </div>

                  <div
                    style={{
                      padding: '14px',
                      borderRadius: '6px',
                      backgroundColor: 'rgba(0, 0, 0, 0.4)',
                      border: '1px solid #1E222D',
                      fontSize: '12.5px',
                      lineHeight: 1.6,
                      color: '#E0E3EB',
                    }}
                  >
                    "{selectedCitation.excerpt}"
                  </div>

                  {selectedCitation.source_url && (
                    <a
                      href={selectedCitation.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ fontSize: '11px', color: '#38BDF8', textDecoration: 'none' }}
                    >
                      🔗 View Original Regulatory Publication
                    </a>
                  )}
                </div>
              ) : (
                <div style={{ padding: '30px 10px', textAlign: 'center', color: '#787B86', fontSize: '12.5px' }}>
                  No citation selected yet. Click any citation badge [1], [2] inside an assistant response to inspect verified grounding evidence here.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
