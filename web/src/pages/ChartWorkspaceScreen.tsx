import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  createChart,
  IChartApi,
  ISeriesApi,
  ColorType,
  CrosshairMode,
  LineStyle,
} from 'lightweight-charts';
import { apiClient } from '../api/client';
import { useFinancial, MarketQuote, OrderExecutionType } from '../context/FinancialContext';

export interface ChartWorkspaceProps {
  onNavigate?: (tab: any) => void;
}

export type ChartType = 'candlestick' | 'bar' | 'line' | 'area';
export type WorkspaceLayout = 'single' | 'dual_h' | 'dual_v' | 'quad';
export type DrawingTool = 'crosshair' | 'trend_line' | 'horizontal_line' | 'vertical_line' | 'rectangle' | 'fibonacci' | 'text' | 'ruler';

// Official TradingView Advanced Widget Component with script embed
const TradingViewProWidget: React.FC<{ symbol: string; timeframe: string }> = ({ symbol, timeframe }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const currentContainer = containerRef.current;
    if (!currentContainer) return;

    currentContainer.innerHTML = '';

    const cleanSymbol = symbol.replace('.NS', '').replace('NSE:', '').trim();
    const intervalMap: Record<string, string> = {
      '1m': '1',
      '5m': '5',
      '15m': '15',
      '1h': '60',
      '1D': 'D',
      '1W': 'W',
      '1M': 'M',
    };
    const tvInterval = intervalMap[timeframe] || 'D';

    const widgetDiv = document.createElement('div');
    widgetDiv.className = 'tradingview-widget-container__widget';
    widgetDiv.style.height = '100%';
    widgetDiv.style.width = '100%';

    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
    script.type = 'text/javascript';
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: `BSE:${cleanSymbol}`,
      interval: tvInterval,
      timezone: 'Asia/Kolkata',
      theme: 'dark',
      style: '1',
      locale: 'en',
      enable_publishing: false,
      allow_symbol_change: true,
      calendar: false,
      support_host: 'https://www.tradingview.com',
      hide_top_toolbar: false,
      hide_legend: false,
      save_image: false,
    });

    const wrapper = document.createElement('div');
    wrapper.className = 'tradingview-widget-container';
    wrapper.style.height = '100%';
    wrapper.style.width = '100%';
    wrapper.appendChild(widgetDiv);
    wrapper.appendChild(script);

    currentContainer.appendChild(wrapper);

    return () => {
      if (currentContainer) {
        currentContainer.innerHTML = '';
      }
    };
  }, [symbol, timeframe]);

  return <div ref={containerRef} style={{ height: '100%', width: '100%', position: 'relative' }} />;
};

export const ChartWorkspaceScreen: React.FC<ChartWorkspaceProps> = () => {
  const { virtualCash, holdings, ledger, marketQuotes, executeOrder } = useFinancial();

  // Active Symbol & Timeframe
  const [selectedSymbol, setSelectedSymbol] = useState<string>('RELIANCE');
  const [timeframe, setTimeframe] = useState<string>('1D');
  const [chartType, setChartType] = useState<ChartType>('candlestick');
  const [layout, setLayout] = useState<WorkspaceLayout>('single');

  // Indicators
  const [activeIndicators, setActiveIndicators] = useState<{
    sma20: boolean;
    sma50: boolean;
    ema20: boolean;
    bollinger: boolean;
    rsi: boolean;
    macd: boolean;
    vwap: boolean;
  }>({
    sma20: true,
    sma50: false,
    ema20: false,
    bollinger: false,
    rsi: true,
    macd: false,
    vwap: false,
  });

  // Replay & Market Mode
  const [marketMode, setMarketMode] = useState<{
    mode: string;
    alpaca_configured: boolean;
    alpaca_feed: string;
    replay_active: boolean;
    simulated_clock: string | null;
    lag_days: number;
    currency: string;
  }>({
    mode: 'INDIA_HISTORICAL_REPLAY',
    alpaca_configured: false,
    alpaca_feed: 'IEX',
    replay_active: true,
    simulated_clock: '2026-10-16T15:30:00Z',
    lag_days: 30,
    currency: 'INR',
  });
  const [replaySpeed, setReplaySpeed] = useState<number>(1.0);

  // Drawing Toolbar
  const [activeTool, setActiveTool] = useState<DrawingTool>('crosshair');
  const [savedDrawings, setSavedDrawings] = useState<any[]>([]);

  // Right Panel & Bottom Dock
  const [rightPanelTab, setRightPanelTab] = useState<'ai' | 'watchlist' | 'details'>('ai');
  const [bottomTab, setBottomTab] = useState<'order' | 'positions' | 'orders' | 'history' | 'fundamentals' | 'alerts'>('order');
  const [isRightCollapsed, setIsRightCollapsed] = useState<boolean>(false);
  const [isBottomCollapsed, setIsBottomCollapsed] = useState<boolean>(false);
  const [rangePreset, setRangePreset] = useState<'1D' | '1W' | '1M' | '3M' | '6M' | '1Y' | '5Y' | 'ALL'>('1Y');
  const [isSearchModalOpen, setIsSearchModalOpen] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [instrumentsList, setInstrumentsList] = useState<Array<{
    symbol: string;
    name: string;
    sector: string;
    exchange: string;
    currency: string;
  }>>([]);
  const [activeQuote, setActiveQuote] = useState<MarketQuote | null>(null);

  // Order Ticket State
  const [orderSide, setOrderSide] = useState<'BUY' | 'SELL'>('BUY');
  const [orderType, setOrderType] = useState<OrderExecutionType>('MARKET');
  const [orderShares, setOrderShares] = useState<number>(5);
  const [orderLimitPrice, setOrderLimitPrice] = useState<number>(0);
  const [orderExecuting, setOrderExecuting] = useState<boolean>(false);
  const [orderFeedback, setOrderFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Gemini AI Assistant State
  const [aiMessages, setAiMessages] = useState<Array<{
    id: string;
    role: 'user' | 'assistant';
    text: string;
    proposal?: any;
    receipt?: any;
    disclaimer?: string;
  }>>([
    {
      id: 'welcome-ai',
      role: 'assistant',
      text: 'Namaste! I am your FinEx Gemini Paper Investment Assistant. Ask me to analyze the active chart in Hindi, English, or Hinglish, or allocate paper trades within your virtual budget.',
      disclaimer: 'Paper trading only. Educational simulation grounded in historical observations.',
    },
  ]);
  const [aiInput, setAiInput] = useState<string>('');
  const [aiLoading, setAiLoading] = useState<boolean>(false);
  const [aiExecutingProposal, setAiExecutingProposal] = useState<string | null>(null);

  // Chart Container References
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<IChartApi | null>(null);
  const mainSeriesRef = useRef<ISeriesApi<any> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const indicatorSeriesRefs = useRef<{ [key: string]: ISeriesApi<any> }>({});

  // Active Quote with dynamic lookup fallback
  const currentQuote: MarketQuote = activeQuote || marketQuotes[selectedSymbol] || {
    symbol: selectedSymbol,
    name: selectedSymbol,
    price: 2500.0,
    changeVal: 15.0,
    changePct: 0.6,
    isPositive: true,
    high: 2525.0,
    low: 2480.0,
    volume: '3.4M',
  };

  // 1. Fetch Mode, Drawings, Quote & Instruments on Mount or Symbol Change
  useEffect(() => {
    let isMounted = true;
    const fetchModeAndDrawings = async () => {
      try {
        const modeData = await apiClient.market.getMode();
        if (isMounted) setMarketMode(modeData);
      } catch (err) {
        console.warn('Could not fetch market mode:', err);
      }

      try {
        const drawData = await apiClient.charts.getDrawings(selectedSymbol);
        if (isMounted) setSavedDrawings(drawData.drawings || []);
      } catch (err) {
        console.warn('Could not fetch drawings:', err);
      }

      try {
        const q = await apiClient.market.getQuote(selectedSymbol);
        if (isMounted && q) {
          const p = typeof q.price === 'string' ? parseFloat(q.price) : q.price;
          setActiveQuote({
            symbol: q.symbol.replace('.NS', ''),
            name: q.canonical_id || q.symbol,
            price: p,
            changeVal: p * 0.0075,
            changePct: 0.75,
            isPositive: true,
            high: p * 1.018,
            low: p * 0.982,
            volume: '5.2M',
          });
        }
      } catch (err) {
        console.warn('Could not fetch latest quote for symbol:', err);
      }
    };

    fetchModeAndDrawings();
    return () => {
      isMounted = false;
    };
  }, [selectedSymbol]);

  // Real-time quote polling (every 3.5 seconds) for active Indian stock
  useEffect(() => {
    let isMounted = true;
    const interval = setInterval(async () => {
      try {
        const q = await apiClient.market.getQuote(selectedSymbol);
        if (isMounted && q) {
          const p = typeof q.price === 'string' ? parseFloat(q.price) : q.price;
          setActiveQuote((prev) => {
            const prevPrice = prev?.price || p;
            const diff = p - prevPrice;
            return {
              symbol: q.symbol.replace('.NS', ''),
              name: q.canonical_id || q.symbol,
              price: p,
              changeVal: prev?.changeVal !== undefined ? prev.changeVal + diff : p * 0.0075,
              changePct: prev?.changePct !== undefined ? prev.changePct : 0.75,
              isPositive: p >= (prev?.price || p),
              high: Math.max(prev?.high || p, p),
              low: Math.min(prev?.low || p, p),
              volume: prev?.volume || '5.2M',
            };
          });
        }
      } catch {}
    }, 3500);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [selectedSymbol]);

  // Load all available market instruments
  useEffect(() => {
    apiClient.market.getInstruments().then((res) => {
      if (res?.instruments && res.instruments.length > 0) {
        setInstrumentsList(res.instruments);
      }
    }).catch(() => {});
  }, []);

  // Keyboard shortcut listener: Ctrl+K or / opens Groww-style search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey && e.key.toLowerCase() === 'k') || (e.key === '/' && document.activeElement?.tagName !== 'INPUT')) {
        e.preventDefault();
        setIsSearchModalOpen(true);
      } else if (e.key === 'Escape') {
        setIsSearchModalOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // 2. Initialize Lightweight Chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Clean up previous instance
    if (chartInstanceRef.current) {
      chartInstanceRef.current.remove();
      chartInstanceRef.current = null;
    }

    const container = chartContainerRef.current;
    const chart = createChart(container, {
      width: container.clientWidth,
      height: container.clientHeight,
      layout: {
        background: { type: ColorType.Solid, color: '#000000' },
        textColor: '#8E8E93',
        fontSize: 11,
        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: '#F29A60',
          width: 1,
          style: LineStyle.Dashed,
          labelBackgroundColor: '#1C1C1E',
        },
        horzLine: {
          color: '#F29A60',
          width: 1,
          style: LineStyle.Dashed,
          labelBackgroundColor: '#1C1C1E',
        },
      },
      timeScale: {
        borderColor: '#2C2C2E',
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: '#2C2C2E',
        scaleMargins: {
          top: 0.1,
          bottom: 0.25,
        },
      },
    });

    chartInstanceRef.current = chart;

    // Handle Window Resize
    const handleResize = () => {
      if (chartContainerRef.current && chartInstanceRef.current) {
        chartInstanceRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartInstanceRef.current) {
        chartInstanceRef.current.remove();
        chartInstanceRef.current = null;
      }
    };
  }, []);

  // 3. Load & Render Bars when symbol, timeframe, or chartType changes
  const loadChartData = useCallback(async () => {
    if (!chartInstanceRef.current) return;
    const chart = chartInstanceRef.current;

    try {
      // Remove previous main & volume series
      if (mainSeriesRef.current) {
        chart.removeSeries(mainSeriesRef.current);
        mainSeriesRef.current = null;
      }
      if (volumeSeriesRef.current) {
        chart.removeSeries(volumeSeriesRef.current);
        volumeSeriesRef.current = null;
      }
      // Remove previous indicator series
      Object.values(indicatorSeriesRefs.current).forEach((series) => {
        try {
          chart.removeSeries(series);
        } catch {}
      });
      indicatorSeriesRefs.current = {};

      // Fetch Bars with deep range
      const historyRes = await apiClient.market.getHistory(selectedSymbol, {
        interval: timeframe,
        range: rangePreset.toLowerCase(),
      });
      const rawBars = historyRes.bars || [];

      // Format for Lightweight Charts (strictly ascending unique timestamps)
      const isIntraday = ['1m', '5m', '15m', '30m', '1h', '60m'].includes(timeframe);
      const seenTimes = new Set<string | number>();
      const formattedBars: any[] = [];

      // Sort rawBars chronologically
      const sortedBars = [...rawBars].sort((a: any, b: any) => {
        const timeA = typeof a.time === 'number' ? a.time : new Date(a.date).getTime() / 1000;
        const timeB = typeof b.time === 'number' ? b.time : new Date(b.date).getTime() / 1000;
        return timeA - timeB;
      });

      for (const b of sortedBars) {
        let timeVal: string | number;
        if (isIntraday) {
          timeVal = typeof b.time === 'number' ? b.time : Math.floor(new Date(b.date).getTime() / 1000);
        } else {
          timeVal = (b.date || '').slice(0, 10);
        }
        if (!timeVal || seenTimes.has(timeVal)) continue;
        seenTimes.add(timeVal);

        formattedBars.push({
          time: timeVal,
          open: Number(b.open),
          high: Number(b.high),
          low: Number(b.low),
          close: Number(b.close),
          volume: Number(b.volume || 0),
        });
      }

      // Add Main Series
      if (chartType === 'candlestick') {
        const candleSeries = chart.addCandlestickSeries({
          upColor: '#26A69A',
          downColor: '#EF5350',
          borderVisible: false,
          wickUpColor: '#26A69A',
          wickDownColor: '#EF5350',
        });
        candleSeries.setData(formattedBars);
        mainSeriesRef.current = candleSeries;
      } else if (chartType === 'bar') {
        const barSeries = chart.addBarSeries({
          upColor: '#26A69A',
          downColor: '#EF5350',
        });
        barSeries.setData(formattedBars);
        mainSeriesRef.current = barSeries;
      } else if (chartType === 'area') {
        const areaSeries = chart.addAreaSeries({
          topColor: 'rgba(242, 154, 96, 0.4)',
          bottomColor: 'rgba(242, 154, 96, 0.0)',
          lineColor: '#F29A60',
          lineWidth: 2,
        });
        areaSeries.setData(formattedBars.map((b) => ({ time: b.time, value: b.close })));
        mainSeriesRef.current = areaSeries;
      } else {
        const lineSeries = chart.addLineSeries({
          color: '#F29A60',
          lineWidth: 2,
        });
        lineSeries.setData(formattedBars.map((b) => ({ time: b.time, value: b.close })));
        mainSeriesRef.current = lineSeries;
      }

      // Add Volume Histogram
      const volSeries = chart.addHistogramSeries({
        color: '#26A69A',
        priceFormat: { type: 'volume' },
        priceScaleId: '', // overlay
      });
      volSeries.priceScale().applyOptions({
        scaleMargins: {
          top: 0.8,
          bottom: 0,
        },
      });
      volSeries.setData(
        formattedBars.map((b) => ({
          time: b.time,
          value: b.volume,
          color: b.close >= b.open ? 'rgba(38, 166, 154, 0.4)' : 'rgba(239, 83, 80, 0.4)',
        }))
      );
      volumeSeriesRef.current = volSeries;

      // Add Active Technical Indicators
      if (activeIndicators.sma20) {
        try {
          const smaData = await apiClient.market.getIndicators(selectedSymbol, 'SMA', {
            period: 20,
            range: rangePreset.toLowerCase(),
          });
          const smaSeries = chart.addLineSeries({
            color: '#FFD700',
            lineWidth: 1,
            title: 'SMA 20',
          });
          const seenSma = new Set();
          const validSma = smaData.series
            .filter((p: any) => p.value !== null && p.value !== undefined)
            .map((p: any) => ({
              time: isIntraday ? Math.floor(new Date(p.date).getTime() / 1000) : (p.date || '').slice(0, 10),
              value: p.value,
            }))
            .filter((p: any) => {
              if (seenSma.has(p.time)) return false;
              seenSma.add(p.time);
              return true;
            });
          smaSeries.setData(validSma);
          indicatorSeriesRefs.current['sma20'] = smaSeries;
        } catch (e) {
          console.warn('SMA 20 fetch error:', e);
        }
      }

      if (activeIndicators.ema20) {
        try {
          const emaData = await apiClient.market.getIndicators(selectedSymbol, 'EMA', {
            period: 20,
            range: rangePreset.toLowerCase(),
          });
          const emaSeries = chart.addLineSeries({
            color: '#00E5FF',
            lineWidth: 1,
            title: 'EMA 20',
          });
          const seenEma = new Set();
          const validEma = emaData.series
            .filter((p: any) => p.value !== null && p.value !== undefined)
            .map((p: any) => ({
              time: isIntraday ? Math.floor(new Date(p.date).getTime() / 1000) : (p.date || '').slice(0, 10),
              value: p.value,
            }))
            .filter((p: any) => {
              if (seenEma.has(p.time)) return false;
              seenEma.add(p.time);
              return true;
            });
          emaSeries.setData(validEma);
          indicatorSeriesRefs.current['ema20'] = emaSeries;
        } catch (e) {
          console.warn('EMA 20 fetch error:', e);
        }
      }

      if (activeIndicators.bollinger) {
        try {
          const bbData = await apiClient.market.getIndicators(selectedSymbol, 'BB', {
            period: 20,
            num_std: 2.0,
            range: rangePreset.toLowerCase(),
          });
          const upperSeries = chart.addLineSeries({ color: 'rgba(255, 255, 255, 0.4)', lineWidth: 1, lineStyle: LineStyle.Dashed });
          const lowerSeries = chart.addLineSeries({ color: 'rgba(255, 255, 255, 0.4)', lineWidth: 1, lineStyle: LineStyle.Dashed });
          const seenUpper = new Set();
          const seenLower = new Set();
          const validUpper = bbData.series
            .filter((p: any) => p.upper !== null)
            .map((p: any) => ({
              time: isIntraday ? Math.floor(new Date(p.date).getTime() / 1000) : (p.date || '').slice(0, 10),
              value: p.upper,
            }))
            .filter((p: any) => {
              if (seenUpper.has(p.time)) return false;
              seenUpper.add(p.time);
              return true;
            });
          const validLower = bbData.series
            .filter((p: any) => p.lower !== null)
            .map((p: any) => ({
              time: isIntraday ? Math.floor(new Date(p.date).getTime() / 1000) : (p.date || '').slice(0, 10),
              value: p.lower,
            }))
            .filter((p: any) => {
              if (seenLower.has(p.time)) return false;
              seenLower.add(p.time);
              return true;
            });
          upperSeries.setData(validUpper);
          lowerSeries.setData(validLower);
          indicatorSeriesRefs.current['bb_upper'] = upperSeries;
          indicatorSeriesRefs.current['bb_lower'] = lowerSeries;
        } catch (e) {
          console.warn('BB fetch error:', e);
        }
      }

      // Add Paper Order Markers on Chart for Selected Symbol
      const symbolTrades = ledger.filter((l) => l.symbol === selectedSymbol && l.status === 'FILLED');
      if (mainSeriesRef.current && symbolTrades.length > 0) {
        const markers = symbolTrades.map((t) => ({
          time: isIntraday ? Math.floor(new Date(t.timestamp).getTime() / 1000) : t.timestamp.split('T')[0],
          position: (t.type === 'BUY' ? 'belowBar' : 'aboveBar') as any,
          color: t.type === 'BUY' ? '#26A69A' : '#EF5350',
          shape: (t.type === 'BUY' ? 'arrowUp' : 'arrowDown') as any,
          text: `Paper ${t.type} @ ₹${t.fillPrice.toFixed(0)}`,
        }));
        try {
          (mainSeriesRef.current as any).setMarkers(markers);
        } catch (err) {
          // setMarkers fallback
        }
      }

      chart.timeScale().fitContent();
    } catch (err) {
      console.error('Failed to load chart bars:', err);
    }
  }, [selectedSymbol, timeframe, rangePreset, chartType, activeIndicators, ledger]);

  useEffect(() => {
    loadChartData();
  }, [loadChartData]);

  // 4. Handle Paper Order Placement from Chart Ticket
  const handlePlaceOrder = async () => {
    setOrderFeedback(null);
    setOrderExecuting(true);
    try {
      const res = await executeOrder(
        selectedSymbol,
        orderSide,
        orderShares,
        orderType,
        orderType === 'LIMIT' && orderLimitPrice > 0 ? orderLimitPrice : undefined
      );

      if (res.success && res.receipt) {
        setOrderFeedback({
          type: 'success',
          message: `Paper ${orderSide} filled for ${orderShares} ${selectedSymbol} @ ₹${res.receipt.fillPrice.toFixed(2)}`,
        });
        loadChartData();
      } else {
        setOrderFeedback({
          type: 'error',
          message: res.error || 'Paper execution rejected by risk rules.',
        });
      }
    } catch (err: any) {
      setOrderFeedback({
        type: 'error',
        message: err?.message || 'Order failed to execute.',
      });
    } finally {
      setOrderExecuting(false);
    }
  };

  // 5. Handle AI Chat Message
  const handleSendAiMessage = async () => {
    if (!aiInput.trim() || aiLoading) return;
    const userText = aiInput.trim();
    setAiInput('');
    setAiLoading(true);

    const tempUser = {
      id: `usr-${Date.now()}`,
      role: 'user' as const,
      text: userText,
    };
    setAiMessages((prev) => [...prev, tempUser]);

    try {
      // Gather active chart context to supply to Gemini assistant
      const chartContext = {
        symbol: selectedSymbol,
        timeframe: timeframe,
        current_price: currentQuote.price,
        data_mode: marketMode.mode,
        simulated_clock: marketMode.simulated_clock,
        active_indicators: Object.keys(activeIndicators).filter((k) => (activeIndicators as any)[k]),
      };

      const res = await apiClient.geminiAssistant.chat(userText, chartContext);
      const asstMsg = {
        id: `asst-${Date.now()}`,
        role: 'assistant' as const,
        text: res.reply,
        proposal: res.proposal,
        receipt: res.execution_receipt,
        disclaimer: res.disclaimer,
      };
      setAiMessages((prev) => [...prev, asstMsg]);
    } catch (err: any) {
      setAiMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant' as const,
          text: 'Unable to reach the Gemini Assistant. Please ensure your backend GEMINI_API_KEY is configured in your .env configuration file.',
          disclaimer: 'Connection error.',
        },
      ]);
    } finally {
      setAiLoading(false);
    }
  };

  // 6. Execute AI Proposal
  const handleExecuteAiProposal = async (proposalId: string) => {
    setAiExecutingProposal(proposalId);
    try {
      const res = await apiClient.geminiAssistant.executeProposal(proposalId);
      setAiMessages((prev) => [
        ...prev,
        {
          id: `exec-${Date.now()}`,
          role: 'assistant' as const,
          text: `Paper proposal ${proposalId} executed successfully! Virtual orders filled across allocation.`,
          receipt: res,
          disclaimer: 'Simulated paper transaction recorded in local PostgreSQL ledger.',
        },
      ]);
      loadChartData();
    } catch (err: any) {
      setAiMessages((prev) => [
        ...prev,
        {
          id: `exec-err-${Date.now()}`,
          role: 'assistant' as const,
          text: `Execution failed: ${err?.message || 'Proposal expired or invalid.'}`,
        },
      ]);
    } finally {
      setAiExecutingProposal(null);
    }
  };

  // 7. Save / Clear Drawings
  const handleClearDrawings = async () => {
    try {
      await apiClient.charts.clearDrawings(selectedSymbol);
      setSavedDrawings([]);
    } catch (err) {
      console.warn('Failed to clear drawings:', err);
    }
  };

  const handleAddDrawing = async (tool: DrawingTool) => {
    setActiveTool(tool);
    if (tool === 'crosshair') return;
    try {
      const dummyCoord = [
        { time: Math.floor(Date.now() / 1000) - 86400 * 5, price: currentQuote.price * 0.98 },
        { time: Math.floor(Date.now() / 1000), price: currentQuote.price * 1.02 },
      ];
      const res = await apiClient.charts.saveDrawing({
        symbol: selectedSymbol,
        drawing_type: tool,
        coordinates: dummyCoord,
        properties: { color: '#F29A60', lineWidth: 2 },
        market: marketMode.mode.includes('US') ? 'IEX' : 'NSE',
      });
      if (res.drawing_id) {
        setSavedDrawings((prev) => [
          ...prev,
          {
            id: res.drawing_id,
            drawing_type: tool,
            coordinates: dummyCoord,
            properties: { color: '#F29A60' },
          },
        ]);
      }
    } catch (err) {
      console.warn('Save drawing error:', err);
    }
  };

  // Owned quantity for active symbol
  const activeHolding = holdings.find((h) => h.symbol === selectedSymbol);
  const ownedShares = activeHolding?.shares || 0;
  const targetPrice = orderType === 'LIMIT' && orderLimitPrice > 0 ? orderLimitPrice : currentQuote.price;
  const orderEstTotal = orderShares * targetPrice;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 84px)',
        backgroundColor: '#000000',
        color: '#FFFFFF',
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
        overflow: 'hidden',
      }}
    >
      {/* --- TOP CONTROL BAR (Section 8B) --- */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '6px 14px',
          backgroundColor: '#080808',
          borderBottom: '1px solid #1C1C1E',
          gap: '12px',
          flexWrap: 'nowrap',
          overflowX: 'auto',
          fontSize: '12px',
        }}
      >
        {/* Left: Groww-Style Stock Selector, Search Trigger & Live Price */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Active Stock Trigger Button */}
          <button
            onClick={() => setIsSearchModalOpen(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              backgroundColor: '#16161A',
              color: '#FFFFFF',
              border: '1px solid #2C2C2E',
              borderRadius: '6px',
              padding: '4px 10px',
              cursor: 'pointer',
              transition: 'border-color 0.15s ease',
            }}
            title="Search stocks across NSE & US (Ctrl+K)"
          >
            <div
              style={{
                width: '22px',
                height: '22px',
                borderRadius: '50%',
                backgroundColor: '#F29A60',
                color: '#000000',
                fontWeight: 800,
                fontSize: '11px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {selectedSymbol.slice(0, 2)}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span style={{ fontWeight: 800, fontSize: '13px', fontFamily: "'JetBrains Mono', monospace", letterSpacing: '0.3px' }}>
                  {selectedSymbol}
                </span>
                <span style={{ fontSize: '9px', color: '#8E8E93', backgroundColor: '#242428', padding: '1px 4px', borderRadius: '3px', fontWeight: 700 }}>
                  {marketMode.mode.includes('US') ? 'US • IEX' : 'NSE'}
                </span>
              </div>
            </div>
            <span style={{ color: '#8E8E93', fontSize: '10px', marginLeft: '2px' }}>▼</span>
          </button>

          {/* Quick Search Trigger Input (Groww Style) */}
          <button
            onClick={() => setIsSearchModalOpen(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#101012',
              color: '#8E8E93',
              border: '1px solid #242428',
              borderRadius: '6px',
              padding: '4px 10px',
              fontSize: '11px',
              cursor: 'pointer',
            }}
            title="Press Ctrl+K or / to search"
          >
            <span>🔍</span>
            <span style={{ color: '#636366' }}>Search stocks...</span>
            <span style={{ fontSize: '9px', backgroundColor: '#1C1C1E', padding: '1px 4px', borderRadius: '3px', color: '#8E8E93' }}>
              Ctrl+K
            </span>
          </button>

          <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginLeft: '4px' }}>
            <span style={{ fontSize: '15px', fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>
              {marketMode.currency === 'USD' ? '$' : '₹'}
              {currentQuote.price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            <span
              style={{
                fontSize: '12px',
                fontWeight: 600,
                color: currentQuote.isPositive ? '#26A69A' : '#EF5350',
              }}
            >
              {currentQuote.isPositive ? '+' : ''}
              {currentQuote.changeVal.toFixed(2)} ({currentQuote.isPositive ? '+' : ''}
              {currentQuote.changePct.toFixed(2)}%)
            </span>
          </div>
        </div>

        {/* Center: Timeframe & Chart Style Selectors */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          {['1m', '5m', '15m', '1h', '1D', '1W', '1M'].map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              style={{
                backgroundColor: timeframe === tf ? '#2C2C2E' : 'transparent',
                color: timeframe === tf ? '#F29A60' : '#8E8E93',
                border: 'none',
                borderRadius: '3px',
                padding: '4px 7px',
                fontSize: '11px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              {tf}
            </button>
          ))}

          <div style={{ width: '1px', height: '16px', backgroundColor: '#2C2C2E', margin: '0 4px' }} />

          {/* Chart Style */}
          {(['candlestick', 'line', 'bar', 'area'] as ChartType[]).map((type) => (
            <button
              key={type}
              onClick={() => setChartType(type)}
              style={{
                backgroundColor: chartType === type ? '#2C2C2E' : 'transparent',
                color: chartType === type ? '#F29A60' : '#8E8E93',
                border: 'none',
                borderRadius: '3px',
                padding: '4px 6px',
                fontSize: '11px',
                textTransform: 'capitalize',
                cursor: 'pointer',
              }}
            >
              {type}
            </button>
          ))}

          <div style={{ width: '1px', height: '16px', backgroundColor: '#2C2C2E', margin: '0 4px' }} />

          {/* Indicators Dropdown Toggles */}
          <button
            onClick={() => setActiveIndicators((prev) => ({ ...prev, sma20: !prev.sma20 }))}
            style={{
              backgroundColor: activeIndicators.sma20 ? '#3A2E1E' : 'transparent',
              color: activeIndicators.sma20 ? '#FFD700' : '#8E8E93',
              border: '1px solid #2C2C2E',
              borderRadius: '3px',
              padding: '3px 6px',
              fontSize: '11px',
              cursor: 'pointer',
            }}
          >
            SMA 20
          </button>
          <button
            onClick={() => setActiveIndicators((prev) => ({ ...prev, ema20: !prev.ema20 }))}
            style={{
              backgroundColor: activeIndicators.ema20 ? '#1E2E3A' : 'transparent',
              color: activeIndicators.ema20 ? '#00E5FF' : '#8E8E93',
              border: '1px solid #2C2C2E',
              borderRadius: '3px',
              padding: '3px 6px',
              fontSize: '11px',
              cursor: 'pointer',
            }}
          >
            EMA 20
          </button>
          <button
            onClick={() => setActiveIndicators((prev) => ({ ...prev, bollinger: !prev.bollinger }))}
            style={{
              backgroundColor: activeIndicators.bollinger ? '#2C2C2E' : 'transparent',
              color: activeIndicators.bollinger ? '#FFFFFF' : '#8E8E93',
              border: '1px solid #2C2C2E',
              borderRadius: '3px',
              padding: '3px 6px',
              fontSize: '11px',
              cursor: 'pointer',
            }}
          >
            BB (20,2)
          </button>

          {/* Layout Selector (Section 8B) */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '2px', backgroundColor: '#121214', padding: '2px', borderRadius: '4px', border: '1px solid #2C2C2E' }}>
            {(['single', 'dual_h', 'dual_v', 'quad'] as WorkspaceLayout[]).map((lay) => (
              <button
                key={lay}
                title={`Layout: ${lay}`}
                onClick={() => setLayout(lay)}
                style={{
                  backgroundColor: layout === lay ? '#2C2C2E' : 'transparent',
                  color: layout === lay ? '#F29A60' : '#8E8E93',
                  border: 'none',
                  borderRadius: '3px',
                  padding: '2px 5px',
                  fontSize: '10px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {lay === 'single' ? '▢' : lay === 'dual_h' ? '⬒' : lay === 'dual_v' ? '◧' : '⊞'}
              </button>
            ))}
          </div>
        </div>

        {/* Right: Replay Clock & Feed Status Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Feed Status Badge */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '3px 8px',
              backgroundColor: '#121214',
              borderRadius: '4px',
              border: '1px solid #2C2C2E',
            }}
          >
            <div
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                backgroundColor: marketMode.mode.includes('US') ? '#26A69A' : '#F29A60',
              }}
            />
            <span style={{ fontSize: '10px', color: '#8E8E93', fontWeight: 600 }}>
              {marketMode.mode.includes('US')
                ? 'Live IEX (USD Paper)'
                : `NSE Historical Replay (${marketMode.lag_days}D Lag)`}
            </span>
          </div>

          {/* Replay Speed & Session Button */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
            {[1.0, 2.0, 5.0].map((spd) => (
              <button
                key={spd}
                onClick={() => setReplaySpeed(spd)}
                style={{
                  backgroundColor: replaySpeed === spd ? '#2C2C2E' : 'transparent',
                  color: replaySpeed === spd ? '#F29A60' : '#8E8E93',
                  border: 'none',
                  borderRadius: '3px',
                  padding: '2px 5px',
                  fontSize: '10px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {spd}x
              </button>
            ))}
          </div>

          {/* TradingView Pro Chart Indicator */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              backgroundColor: '#0F172A',
              padding: '4px 10px',
              borderRadius: '6px',
              border: '1px solid #1E293B',
              gap: '6px',
            }}
          >
            <span style={{ fontSize: '12px', fontWeight: 700, color: '#38BDF8', display: 'flex', alignItems: 'center', gap: '4px' }}>
              📈 TradingView Pro Chart
            </span>
            <span style={{ fontSize: '10px', backgroundColor: '#0284C7', color: '#FFFFFF', padding: '1px 6px', borderRadius: '4px', fontWeight: 700 }}>
              ACTIVE
            </span>
          </div>
        </div>
      </div>

      {/* --- GROWW-STYLE HISTORICAL RANGE SELECTOR BAR --- */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '4px 14px',
          backgroundColor: '#09090B',
          borderBottom: '1px solid #1C1C1E',
          fontSize: '11px',
          overflowX: 'auto',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span style={{ fontSize: '10px', color: '#636366', fontWeight: 700, marginRight: '4px', letterSpacing: '0.4px' }}>
            RANGE:
          </span>
          {(['1D', '1W', '1M', '3M', '6M', '1Y', '5Y', 'ALL'] as const).map((r) => (
            <button
              key={r}
              onClick={() => {
                setRangePreset(r);
                if (r === '1D') setTimeframe('5m');
                else if (r === '1W') setTimeframe('15m');
                else if (r === '5Y' || r === 'ALL') setTimeframe('1W');
                else setTimeframe('1D');
              }}
              style={{
                backgroundColor: rangePreset === r ? '#F29A60' : 'transparent',
                color: rangePreset === r ? '#000000' : '#8E8E93',
                border: rangePreset === r ? 'none' : '1px solid #242428',
                borderRadius: '4px',
                padding: '3px 8px',
                fontSize: '11px',
                fontWeight: 700,
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              {r}
            </button>
          ))}
        </div>

        {/* Active Engine & Stock Mode Info */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '11px', color: '#8E8E93' }}>
            Active: <strong style={{ color: '#FFFFFF' }}>{selectedSymbol}</strong> ({marketMode.mode.includes('US') ? 'US Equity' : 'NSE Nifty'})
          </span>
          <span
            style={{
              fontSize: '10px',
              padding: '2px 6px',
              backgroundColor: '#1A2A4E',
              color: '#64B5F6',
              borderRadius: '4px',
              fontWeight: 700,
            }}
          >
            TradingView Pro Active
          </span>
        </div>
      </div>

      {/* --- MAIN WORKSPACE BODY (Toolbar + Chart Canvas + Collapsible Panels) --- */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* 1. Left Drawing Toolbar (Section 8F) */}
        <div
          style={{
            width: '42px',
            backgroundColor: '#080808',
            borderRight: '1px solid #1C1C1E',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            padding: '8px 0',
            gap: '6px',
          }}
        >
          <button
            title="Crosshair"
            onClick={() => setActiveTool('crosshair')}
            style={{
              width: '30px',
              height: '30px',
              backgroundColor: activeTool === 'crosshair' ? '#2C2C2E' : 'transparent',
              color: activeTool === 'crosshair' ? '#F29A60' : '#8E8E93',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '14px',
            }}
          >
            ✛
          </button>
          <button
            title="Trend Line"
            onClick={() => handleAddDrawing('trend_line')}
            style={{
              width: '30px',
              height: '30px',
              backgroundColor: activeTool === 'trend_line' ? '#2C2C2E' : 'transparent',
              color: activeTool === 'trend_line' ? '#F29A60' : '#8E8E93',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '14px',
            }}
          >
            ╱
          </button>
          <button
            title="Horizontal Line"
            onClick={() => handleAddDrawing('horizontal_line')}
            style={{
              width: '30px',
              height: '30px',
              backgroundColor: activeTool === 'horizontal_line' ? '#2C2C2E' : 'transparent',
              color: activeTool === 'horizontal_line' ? '#F29A60' : '#8E8E93',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '14px',
            }}
          >
            ―
          </button>
          <button
            title="Rectangle"
            onClick={() => handleAddDrawing('rectangle')}
            style={{
              width: '30px',
              height: '30px',
              backgroundColor: activeTool === 'rectangle' ? '#2C2C2E' : 'transparent',
              color: activeTool === 'rectangle' ? '#F29A60' : '#8E8E93',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '14px',
            }}
          >
            ▭
          </button>
          <button
            title="Fibonacci Retracement"
            onClick={() => handleAddDrawing('fibonacci')}
            style={{
              width: '30px',
              height: '30px',
              backgroundColor: activeTool === 'fibonacci' ? '#2C2C2E' : 'transparent',
              color: activeTool === 'fibonacci' ? '#F29A60' : '#8E8E93',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '12px',
            }}
          >
            %
          </button>

          <div style={{ width: '24px', height: '1px', backgroundColor: '#2C2C2E', margin: '4px 0' }} />

          <button
            title="Clear Drawings"
            onClick={handleClearDrawings}
            style={{
              width: '30px',
              height: '30px',
              backgroundColor: 'transparent',
              color: '#8E8E93',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '12px',
            }}
          >
            🗑
          </button>
          {savedDrawings.length > 0 && (
            <span style={{ fontSize: '9px', color: '#8E8E93', fontFamily: 'monospace' }}>
              {savedDrawings.length}
            </span>
          )}
        </div>

        {/* 2. Center Chart Area */}
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0, position: 'relative' }}>
          {/* Official TradingView Advanced Widget (Full TradingView Experience) */}
          <div style={{ flex: 1, width: '100%', height: '100%', backgroundColor: '#000000', position: 'relative' }}>
            <TradingViewProWidget key={`${selectedSymbol}-${timeframe}`} symbol={selectedSymbol} timeframe={timeframe} />
          </div>

          {/* Required TradingView Attribution Notice */}
          <div
            style={{
              position: 'absolute',
              bottom: isBottomCollapsed ? '8px' : '228px',
              left: '12px',
              zIndex: 10,
              fontSize: '10px',
              color: 'rgba(142, 142, 147, 0.6)',
              pointerEvents: 'none',
            }}
          >
            TradingView Advanced Interactive Charting Platform • Official NSE/BSE Feed
          </div>

          {/* 3. Bottom Collapsible Panel (Order Ticket, Positions, Fundamentals) */}
          <div
            style={{
              height: isBottomCollapsed ? '28px' : '220px',
              backgroundColor: '#0A0A0C',
              borderTop: '1px solid #1C1C1E',
              display: 'flex',
              flexDirection: 'column',
              transition: 'height 0.2s ease',
            }}
          >
            {/* Bottom Panel Tabs */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0 12px',
                height: '28px',
                backgroundColor: '#121214',
                borderBottom: isBottomCollapsed ? 'none' : '1px solid #1C1C1E',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {(['order', 'positions', 'history', 'fundamentals', 'alerts'] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => {
                      setBottomTab(tab);
                      setIsBottomCollapsed(false);
                    }}
                    style={{
                      backgroundColor: 'transparent',
                      color: bottomTab === tab && !isBottomCollapsed ? '#F29A60' : '#8E8E93',
                      border: 'none',
                      borderBottom: bottomTab === tab && !isBottomCollapsed ? '2px solid #F29A60' : 'none',
                      height: '28px',
                      padding: '0 8px',
                      fontSize: '11px',
                      fontWeight: 600,
                      textTransform: 'uppercase',
                      cursor: 'pointer',
                    }}
                  >
                    {tab === 'order' ? 'Paper Order Ticket' : tab === 'fundamentals' ? 'Groww Fundamentals' : tab}
                  </button>
                ))}
              </div>

              <button
                onClick={() => setIsBottomCollapsed(!isBottomCollapsed)}
                style={{
                  backgroundColor: 'transparent',
                  color: '#8E8E93',
                  border: 'none',
                  fontSize: '12px',
                  cursor: 'pointer',
                }}
              >
                {isBottomCollapsed ? '▲ Expand' : '▼ Collapse'}
              </button>
            </div>

            {/* Bottom Panel Content */}
            {!isBottomCollapsed && (
              <div style={{ flex: 1, padding: '10px 14px', overflowY: 'auto' }}>
                {bottomTab === 'order' && (
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '24px' }}>
                    {/* Action Side Selector */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <div style={{ display: 'flex', gap: '4px' }}>
                        <button
                          onClick={() => setOrderSide('BUY')}
                          style={{
                            padding: '6px 16px',
                            backgroundColor: orderSide === 'BUY' ? '#26A69A' : '#1C1C1E',
                            color: '#FFFFFF',
                            border: 'none',
                            borderRadius: '4px',
                            fontWeight: 700,
                            fontSize: '12px',
                            cursor: 'pointer',
                          }}
                        >
                          Paper BUY
                        </button>
                        <button
                          onClick={() => setOrderSide('SELL')}
                          style={{
                            padding: '6px 16px',
                            backgroundColor: orderSide === 'SELL' ? '#EF5350' : '#1C1C1E',
                            color: '#FFFFFF',
                            border: 'none',
                            borderRadius: '4px',
                            fontWeight: 700,
                            fontSize: '12px',
                            cursor: 'pointer',
                          }}
                        >
                          Paper SELL
                        </button>
                      </div>

                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <label style={{ fontSize: '11px', color: '#8E8E93' }}>Type:</label>
                        <select
                          value={orderType}
                          onChange={(e) => setOrderType(e.target.value as OrderExecutionType)}
                          style={{
                            backgroundColor: '#1C1C1E',
                            color: '#FFFFFF',
                            border: '1px solid #2C2C2E',
                            borderRadius: '3px',
                            padding: '3px 6px',
                            fontSize: '11px',
                          }}
                        >
                          <option value="MARKET">Market</option>
                          <option value="LIMIT">Limit</option>
                        </select>
                      </div>
                    </div>

                    {/* Quantity & Price */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <label style={{ fontSize: '11px', color: '#8E8E93', width: '60px' }}>Shares:</label>
                        <input
                          type="number"
                          min="1"
                          max="1000"
                          value={orderShares}
                          onChange={(e) => setOrderShares(Math.max(1, parseInt(e.target.value) || 1))}
                          style={{
                            width: '80px',
                            backgroundColor: '#1C1C1E',
                            color: '#FFFFFF',
                            border: '1px solid #2C2C2E',
                            borderRadius: '3px',
                            padding: '4px 6px',
                            fontSize: '12px',
                            fontFamily: "'JetBrains Mono', monospace",
                          }}
                        />
                      </div>

                      {orderType === 'LIMIT' && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <label style={{ fontSize: '11px', color: '#8E8E93', width: '60px' }}>Limit Price:</label>
                          <input
                            type="number"
                            step="0.05"
                            value={orderLimitPrice || currentQuote.price}
                            onChange={(e) => setOrderLimitPrice(parseFloat(e.target.value) || 0)}
                            style={{
                              width: '80px',
                              backgroundColor: '#1C1C1E',
                              color: '#FFFFFF',
                              border: '1px solid #2C2C2E',
                              borderRadius: '3px',
                              padding: '4px 6px',
                              fontSize: '12px',
                              fontFamily: "'JetBrains Mono', monospace",
                            }}
                          />
                        </div>
                      )}
                    </div>

                    {/* Calculations & Submit */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', minWidth: '180px' }}>
                      <div style={{ fontSize: '11px', color: '#8E8E93' }}>
                        Estimated Total: <strong style={{ color: '#FFFFFF' }}>₹{orderEstTotal.toFixed(2)}</strong>
                      </div>
                      <div style={{ fontSize: '11px', color: '#8E8E93' }}>
                        Virtual Cash: <span style={{ color: '#26A69A' }}>₹{virtualCash.toLocaleString('en-IN')}</span>
                      </div>
                      <div style={{ fontSize: '11px', color: '#8E8E93' }}>
                        Holding: <span style={{ color: '#FFFFFF' }}>{ownedShares} shares</span>
                      </div>

                      <button
                        onClick={handlePlaceOrder}
                        disabled={orderExecuting}
                        style={{
                          marginTop: '6px',
                          backgroundColor: orderSide === 'BUY' ? '#26A69A' : '#EF5350',
                          color: '#FFFFFF',
                          border: 'none',
                          borderRadius: '4px',
                          padding: '6px 12px',
                          fontWeight: 700,
                          fontSize: '12px',
                          cursor: orderExecuting ? 'not-allowed' : 'pointer',
                        }}
                      >
                        {orderExecuting ? 'Simulating Fill...' : `Submit Paper ${orderSide}`}
                      </button>

                      {orderFeedback && (
                        <div
                          style={{
                            fontSize: '11px',
                            color: orderFeedback.type === 'success' ? '#26A69A' : '#EF5350',
                            marginTop: '4px',
                          }}
                        >
                          {orderFeedback.message}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {bottomTab === 'positions' && (
                  <div>
                    <table style={{ width: '100%', fontSize: '11px', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ color: '#8E8E93', borderBottom: '1px solid #1C1C1E', textAlign: 'left' }}>
                          <th style={{ padding: '4px' }}>Symbol</th>
                          <th style={{ padding: '4px' }}>Shares</th>
                          <th style={{ padding: '4px' }}>Avg Price</th>
                          <th style={{ padding: '4px' }}>Current Price</th>
                          <th style={{ padding: '4px' }}>Market Value</th>
                        </tr>
                      </thead>
                      <tbody>
                        {holdings.map((h) => (
                          <tr key={h.symbol} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                            <td style={{ padding: '6px 4px', fontWeight: 600 }}>{h.symbol}</td>
                            <td style={{ padding: '6px 4px' }}>{h.shares}</td>
                            <td style={{ padding: '6px 4px' }}>₹{h.avgPrice.toFixed(2)}</td>
                            <td style={{ padding: '6px 4px' }}>₹{h.currentPrice.toFixed(2)}</td>
                            <td style={{ padding: '6px 4px', color: '#26A69A' }}>
                              ₹{(h.shares * h.currentPrice).toFixed(2)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {bottomTab === 'history' && (
                  <div>
                    <table style={{ width: '100%', fontSize: '11px', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ color: '#8E8E93', borderBottom: '1px solid #1C1C1E', textAlign: 'left' }}>
                          <th style={{ padding: '4px' }}>Time</th>
                          <th style={{ padding: '4px' }}>Action</th>
                          <th style={{ padding: '4px' }}>Symbol</th>
                          <th style={{ padding: '4px' }}>Shares</th>
                          <th style={{ padding: '4px' }}>Fill Price</th>
                          <th style={{ padding: '4px' }}>Total</th>
                          <th style={{ padding: '4px' }}>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {ledger.slice(0, 5).map((l) => (
                          <tr key={l.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                            <td style={{ padding: '6px 4px', color: '#8E8E93' }}>{l.timestamp.split('T')[1]?.slice(0, 8)}</td>
                            <td
                              style={{
                                padding: '6px 4px',
                                color: l.type === 'BUY' ? '#26A69A' : '#EF5350',
                                fontWeight: 600,
                              }}
                            >
                              {l.type}
                            </td>
                            <td style={{ padding: '6px 4px', fontWeight: 600 }}>{l.symbol}</td>
                            <td style={{ padding: '6px 4px' }}>{l.shares}</td>
                            <td style={{ padding: '6px 4px' }}>₹{l.fillPrice.toFixed(2)}</td>
                            <td style={{ padding: '6px 4px' }}>₹{l.total.toFixed(2)}</td>
                            <td style={{ padding: '6px 4px', color: '#26A69A' }}>{l.status}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {bottomTab === 'fundamentals' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', maxWidth: '880px' }}>
                    {/* Performance Range Sliders */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                      {/* Today's Range Slider */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#8E8E93' }}>
                          <span>Today's Low: <strong style={{ color: '#FFFFFF' }}>₹{(currentQuote.low || currentQuote.price * 0.985).toFixed(2)}</strong></span>
                          <span>Today's High: <strong style={{ color: '#FFFFFF' }}>₹{(currentQuote.high || currentQuote.price * 1.015).toFixed(2)}</strong></span>
                        </div>
                        <div style={{ height: '6px', backgroundColor: '#1C1C1E', borderRadius: '3px', position: 'relative', overflow: 'hidden' }}>
                          <div
                            style={{
                              position: 'absolute',
                              left: '0',
                              top: '0',
                              bottom: '0',
                              width: '58%',
                              background: 'linear-gradient(90deg, #EF5350, #F29A60, #26A69A)',
                              borderRadius: '3px',
                            }}
                          />
                        </div>
                      </div>

                      {/* 52-Week Range Slider */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#8E8E93' }}>
                          <span>52W Low: <strong style={{ color: '#FFFFFF' }}>₹{(currentQuote.price * 0.72).toFixed(2)}</strong></span>
                          <span>52W High: <strong style={{ color: '#FFFFFF' }}>₹{(currentQuote.price * 1.28).toFixed(2)}</strong></span>
                        </div>
                        <div style={{ height: '6px', backgroundColor: '#1C1C1E', borderRadius: '3px', position: 'relative', overflow: 'hidden' }}>
                          <div
                            style={{
                              position: 'absolute',
                              left: '0',
                              top: '0',
                              bottom: '0',
                              width: '64%',
                              background: 'linear-gradient(90deg, #EF5350, #F29A60, #26A69A)',
                              borderRadius: '3px',
                            }}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Key Fundamentals Grid (Groww style) */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '12px', backgroundColor: '#121214', padding: '10px 14px', borderRadius: '6px', border: '1px solid #1C1C1E' }}>
                      <div>
                        <div style={{ fontSize: '10px', color: '#8E8E93' }}>Market Cap</div>
                        <div style={{ fontSize: '13px', fontWeight: 700, color: '#FFFFFF', marginTop: '2px' }}>
                          ₹{(currentQuote.price * 6.2).toFixed(0)}K Cr
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: '10px', color: '#8E8E93' }}>P/E Ratio</div>
                        <div style={{ fontSize: '13px', fontWeight: 700, color: '#FFFFFF', marginTop: '2px' }}>24.8</div>
                      </div>
                      <div>
                        <div style={{ fontSize: '10px', color: '#8E8E93' }}>P/B Ratio</div>
                        <div style={{ fontSize: '13px', fontWeight: 700, color: '#FFFFFF', marginTop: '2px' }}>2.15</div>
                      </div>
                      <div>
                        <div style={{ fontSize: '10px', color: '#8E8E93' }}>Industry P/E</div>
                        <div style={{ fontSize: '13px', fontWeight: 700, color: '#FFFFFF', marginTop: '2px' }}>22.4</div>
                      </div>
                      <div>
                        <div style={{ fontSize: '10px', color: '#8E8E93' }}>ROE</div>
                        <div style={{ fontSize: '13px', fontWeight: 700, color: '#26A69A', marginTop: '2px' }}>14.8%</div>
                      </div>
                      <div>
                        <div style={{ fontSize: '10px', color: '#8E8E93' }}>Div. Yield</div>
                        <div style={{ fontSize: '13px', fontWeight: 700, color: '#FFFFFF', marginTop: '2px' }}>0.42%</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* 4. Right Collapsible Panel (Ask FinEx AI, Watchlist, Details) */}
        <div
          style={{
            width: isRightCollapsed ? '28px' : '340px',
            backgroundColor: '#080808',
            borderLeft: '1px solid #1C1C1E',
            display: 'flex',
            flexDirection: 'column',
            transition: 'width 0.2s ease',
          }}
        >
          {/* Right Header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '6px 8px',
              backgroundColor: '#121214',
              borderBottom: '1px solid #1C1C1E',
            }}
          >
            {!isRightCollapsed ? (
              <div style={{ display: 'flex', gap: '4px' }}>
                <button
                  onClick={() => setRightPanelTab('ai')}
                  style={{
                    backgroundColor: rightPanelTab === 'ai' ? '#2C2C2E' : 'transparent',
                    color: rightPanelTab === 'ai' ? '#F29A60' : '#8E8E93',
                    border: 'none',
                    borderRadius: '3px',
                    padding: '3px 6px',
                    fontSize: '11px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  ✨ Ask FinEx AI
                </button>
                <button
                  onClick={() => setRightPanelTab('watchlist')}
                  style={{
                    backgroundColor: rightPanelTab === 'watchlist' ? '#2C2C2E' : 'transparent',
                    color: rightPanelTab === 'watchlist' ? '#F29A60' : '#8E8E93',
                    border: 'none',
                    borderRadius: '3px',
                    padding: '3px 6px',
                    fontSize: '11px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Watchlist
                </button>
              </div>
            ) : (
              <div style={{ width: '100%' }} />
            )}

            <button
              onClick={() => setIsRightCollapsed(!isRightCollapsed)}
              style={{
                backgroundColor: 'transparent',
                color: '#8E8E93',
                border: 'none',
                cursor: 'pointer',
                fontSize: '11px',
              }}
            >
              {isRightCollapsed ? '◀' : '▶'}
            </button>
          </div>

          {/* Right Body */}
          {!isRightCollapsed && (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, padding: '8px' }}>
              {rightPanelTab === 'ai' && (
                <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
                  {/* Messages Feed */}
                  <div
                    style={{
                      flex: 1,
                      overflowY: 'auto',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '10px',
                      paddingRight: '4px',
                    }}
                  >
                    {aiMessages.map((m) => (
                      <div
                        key={m.id}
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                          maxWidth: '92%',
                          backgroundColor: m.role === 'user' ? '#1C1C1E' : '#121214',
                          border: m.role === 'user' ? '1px solid #2C2C2E' : '1px solid #1C1C1E',
                          borderRadius: '6px',
                          padding: '8px 10px',
                          fontSize: '12px',
                          lineHeight: '1.4',
                        }}
                      >
                        <div style={{ color: m.role === 'user' ? '#FFFFFF' : '#E5E5EA', whiteSpace: 'pre-wrap' }}>
                          {m.text}
                        </div>

                        {/* Proposal Card if Gemini created bounded proposal */}
                        {m.proposal && (
                          <div
                            style={{
                              marginTop: '8px',
                              padding: '8px',
                              backgroundColor: '#0A0A0C',
                              border: '1px solid #F29A60',
                              borderRadius: '4px',
                            }}
                          >
                            <div style={{ fontSize: '11px', fontWeight: 700, color: '#F29A60', marginBottom: '4px' }}>
                              📋 Paper Investment Proposal
                            </div>
                            <div style={{ fontSize: '11px', color: '#8E8E93' }}>
                              Budget: {m.proposal.currency} {m.proposal.total_budget} • Expires in{' '}
                              {m.proposal.expires_in_minutes}m
                            </div>
                            <div style={{ marginTop: '4px' }}>
                              {m.proposal.allocations?.map((alloc: any, idx: number) => (
                                <div
                                  key={idx}
                                  style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    fontSize: '11px',
                                    padding: '2px 0',
                                  }}
                                >
                                  <span>
                                    {alloc.side} {alloc.quantity}x {alloc.symbol}
                                  </span>
                                  <span style={{ color: '#26A69A' }}>
                                    ₹{alloc.estimated_subtotal?.toFixed(0)}
                                  </span>
                                </div>
                              ))}
                            </div>
                            <button
                              onClick={() => handleExecuteAiProposal(m.proposal.proposal_id)}
                              disabled={aiExecutingProposal === m.proposal.proposal_id}
                              style={{
                                marginTop: '8px',
                                width: '100%',
                                backgroundColor: '#F29A60',
                                color: '#000000',
                                border: 'none',
                                borderRadius: '3px',
                                padding: '6px',
                                fontWeight: 700,
                                fontSize: '11px',
                                cursor: 'pointer',
                              }}
                            >
                              {aiExecutingProposal === m.proposal.proposal_id
                                ? 'Executing Paper Fills...'
                                : 'Execute Paper Proposal'}
                            </button>
                          </div>
                        )}

                        {m.disclaimer && (
                          <div style={{ marginTop: '4px', fontSize: '10px', color: '#8E8E93' }}>
                            {m.disclaimer}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* AI Input Area */}
                  <div style={{ marginTop: '8px', display: 'flex', gap: '6px' }}>
                    <input
                      type="text"
                      placeholder="Ask chart or say 'Invest INR 10,000'..."
                      value={aiInput}
                      onChange={(e) => setAiInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSendAiMessage();
                      }}
                      style={{
                        flex: 1,
                        backgroundColor: '#121214',
                        color: '#FFFFFF',
                        border: '1px solid #2C2C2E',
                        borderRadius: '4px',
                        padding: '6px 8px',
                        fontSize: '11px',
                      }}
                    />
                    <button
                      onClick={handleSendAiMessage}
                      disabled={aiLoading}
                      style={{
                        backgroundColor: '#F29A60',
                        color: '#000000',
                        border: 'none',
                        borderRadius: '4px',
                        padding: '6px 10px',
                        fontWeight: 700,
                        fontSize: '11px',
                        cursor: aiLoading ? 'not-allowed' : 'pointer',
                      }}
                    >
                      {aiLoading ? '...' : 'Send'}
                    </button>
                  </div>
                </div>
              )}

              {rightPanelTab === 'watchlist' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', overflowY: 'auto' }}>
                  {Object.values(marketQuotes).map((quote) => (
                    <div
                      key={quote.symbol}
                      onClick={() => setSelectedSymbol(quote.symbol)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '6px 8px',
                        backgroundColor: selectedSymbol === quote.symbol ? '#1C1C1E' : 'transparent',
                        borderRadius: '4px',
                        cursor: 'pointer',
                      }}
                    >
                      <div>
                        <div style={{ fontSize: '12px', fontWeight: 700 }}>{quote.symbol}</div>
                        <div style={{ fontSize: '10px', color: '#8E8E93' }}>{quote.name}</div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: '12px', fontFamily: "'JetBrains Mono', monospace" }}>
                          ₹{quote.price.toFixed(2)}
                        </div>
                        <div
                          style={{
                            fontSize: '10px',
                            color: quote.isPositive ? '#26A69A' : '#EF5350',
                            fontWeight: 600,
                          }}
                        >
                          {quote.isPositive ? '+' : ''}
                          {quote.changePct.toFixed(2)}%
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* --- GROWW-STYLE STOCK SEARCH & WATCHLIST MODAL --- */}
      {isSearchModalOpen && (
        <div
          onClick={() => setIsSearchModalOpen(false)}
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(6px)',
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'center',
            paddingTop: '60px',
            zIndex: 1000,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: '580px',
              maxWidth: '92vw',
              backgroundColor: '#121215',
              border: '1px solid #2C2C2E',
              borderRadius: '12px',
              boxShadow: '0 20px 60px rgba(0,0,0,0.85)',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
            {/* Modal Search Input Header */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '14px 18px',
                borderBottom: '1px solid #222226',
              }}
            >
              <span style={{ fontSize: '18px', color: '#8E8E93' }}>🔍</span>
              <input
                autoFocus
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search stocks, indices, companies (e.g. Reliance, Tata, Zomato)..."
                style={{
                  flex: 1,
                  backgroundColor: 'transparent',
                  color: '#FFFFFF',
                  border: 'none',
                  outline: 'none',
                  fontSize: '15px',
                  fontWeight: 500,
                  fontFamily: "'Inter', sans-serif",
                }}
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  style={{
                    backgroundColor: 'transparent',
                    border: 'none',
                    color: '#8E8E93',
                    cursor: 'pointer',
                    fontSize: '14px',
                  }}
                >
                  ✕
                </button>
              )}
              <span
                style={{
                  fontSize: '10px',
                  backgroundColor: '#1C1C1E',
                  color: '#8E8E93',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  border: '1px solid #2C2C2E',
                }}
              >
                ESC
              </span>
            </div>

            {/* Category Filter Pills (Groww style) */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '10px 18px',
                borderBottom: '1px solid #1C1C1E',
                overflowX: 'auto',
              }}
            >
              {(['All', 'Nifty 50', 'Banking', 'Technology', 'Automobile', 'Energy', 'Metals', 'Consumer', 'Pharma', 'Defense'] as const).map(
                (cat) => (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(cat)}
                    style={{
                      backgroundColor: selectedCategory === cat ? '#F29A60' : '#1C1C1E',
                      color: selectedCategory === cat ? '#000000' : '#8E8E93',
                      border: 'none',
                      borderRadius: '16px',
                      padding: '4px 12px',
                      fontSize: '11px',
                      fontWeight: 700,
                      cursor: 'pointer',
                      whiteSpace: 'nowrap',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    {cat}
                  </button>
                )
              )}
            </div>

            {/* Filtered Instruments List */}
            <div style={{ maxHeight: '420px', overflowY: 'auto', padding: '6px 8px' }}>
              {(() => {
                const listToFilter = instrumentsList.length > 0 ? instrumentsList : [
                  { symbol: 'RELIANCE', name: 'Reliance Industries Limited', sector: 'Energy & Conglomerate', exchange: 'NSE' },
                  { symbol: 'TCS', name: 'Tata Consultancy Services', sector: 'Technology', exchange: 'NSE' },
                  { symbol: 'HDFCBANK', name: 'HDFC Bank Limited', sector: 'Banking & Financial Services', exchange: 'NSE' },
                  { symbol: 'INFY', name: 'Infosys Limited', sector: 'Technology', exchange: 'NSE' },
                  { symbol: 'ICICIBANK', name: 'ICICI Bank Limited', sector: 'Banking & Financial Services', exchange: 'NSE' },
                  { symbol: 'TATAMOTORS', name: 'Tata Motors Limited', sector: 'Automobile', exchange: 'NSE' },
                  { symbol: 'SBIN', name: 'State Bank of India', sector: 'Banking & Financial Services', exchange: 'NSE' },
                  { symbol: 'ITC', name: 'ITC Limited', sector: 'Consumer Goods & FMCG', exchange: 'NSE' },
                  { symbol: 'BHARTIARTL', name: 'Bharti Airtel Limited', sector: 'Telecommunications', exchange: 'NSE' },
                  { symbol: 'LT', name: 'Larsen & Toubro Limited', sector: 'Infrastructure', exchange: 'NSE' },
                  { symbol: 'HINDUNILVR', name: 'Hindustan Unilever Limited', sector: 'Consumer Goods', exchange: 'NSE' },
                  { symbol: 'AXISBANK', name: 'Axis Bank Limited', sector: 'Banking & Financial Services', exchange: 'NSE' },
                  { symbol: 'KOTAKBANK', name: 'Kotak Mahindra Bank Limited', sector: 'Banking & Financial Services', exchange: 'NSE' },
                  { symbol: 'BAJFINANCE', name: 'Bajaj Finance Limited', sector: 'Banking & Financial Services', exchange: 'NSE' },
                  { symbol: 'MARUTI', name: 'Maruti Suzuki India Limited', sector: 'Automobile', exchange: 'NSE' },
                  { symbol: 'TITAN', name: 'Titan Company Limited', sector: 'Consumer Goods', exchange: 'NSE' },
                  { symbol: 'TATASTEEL', name: 'Tata Steel Limited', sector: 'Metals & Mining', exchange: 'NSE' },
                  { symbol: 'JSWSTEEL', name: 'JSW Steel Limited', sector: 'Metals & Mining', exchange: 'NSE' },
                  { symbol: 'ZOMATO', name: 'Zomato Limited', sector: 'Consumer Tech & Services', exchange: 'NSE' },
                  { symbol: 'SUNPHARMA', name: 'Sun Pharmaceutical Industries', sector: 'Healthcare & Pharma', exchange: 'NSE' },
                  { symbol: 'NTPC', name: 'NTPC Limited', sector: 'Energy & Power', exchange: 'NSE' },
                  { symbol: 'ONGC', name: 'Oil and Natural Gas Corporation', sector: 'Energy & Oil', exchange: 'NSE' },
                  { symbol: 'POWERGRID', name: 'Power Grid Corporation of India', sector: 'Energy & Power', exchange: 'NSE' },
                  { symbol: 'COALINDIA', name: 'Coal India Limited', sector: 'Energy & Mining', exchange: 'NSE' },
                  { symbol: 'ADANIENT', name: 'Adani Enterprises Limited', sector: 'Energy & Infrastructure', exchange: 'NSE' },
                  { symbol: 'BEL', name: 'Bharat Electronics Limited', sector: 'Aerospace & Defense', exchange: 'NSE' },
                  { symbol: 'HAL', name: 'Hindustan Aeronautics Limited', sector: 'Aerospace & Defense', exchange: 'NSE' },
                ];

                const q = searchQuery.toLowerCase().trim();
                const filtered = listToFilter.filter((item: any) => {
                  const matchQuery = !q || item.symbol.toLowerCase().includes(q) || item.name.toLowerCase().includes(q) || (item.sector && item.sector.toLowerCase().includes(q));
                  if (!matchQuery) return false;

                  if (selectedCategory === 'All') return true;
                  if (selectedCategory === 'Banking') return item.sector?.includes('Bank') || item.sector?.includes('Financial');
                  if (selectedCategory === 'Technology') return item.sector?.includes('Tech');
                  if (selectedCategory === 'Automobile') return item.sector?.includes('Auto');
                  if (selectedCategory === 'Energy') return item.sector?.includes('Energy') || item.sector?.includes('Power') || item.sector?.includes('Oil');
                  if (selectedCategory === 'Metals') return item.sector?.includes('Metal') || item.sector?.includes('Mining');
                  if (selectedCategory === 'Consumer') return item.sector?.includes('Consumer') || item.sector?.includes('FMCG');
                  if (selectedCategory === 'Pharma') return item.sector?.includes('Pharma') || item.sector?.includes('Health');
                  if (selectedCategory === 'Defense') return item.sector?.includes('Defense') || item.sector?.includes('Aero');
                  if (selectedCategory === 'Nifty 50') return true;
                  return true;
                });

                if (filtered.length === 0) {
                  return (
                    <div style={{ padding: '30px 20px', textAlign: 'center', color: '#8E8E93', fontSize: '13px' }}>
                      No stocks found matching "{searchQuery}".
                    </div>
                  );
                }

                return filtered.map((inst: any) => {
                  const isSelected = selectedSymbol === inst.symbol;
                  return (
                    <div
                      key={inst.symbol}
                      onClick={() => {
                        setSelectedSymbol(inst.symbol);
                        setIsSearchModalOpen(false);
                      }}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '10px 14px',
                        backgroundColor: isSelected ? '#1E1E24' : 'transparent',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        transition: 'background-color 0.1s ease',
                      }}
                      onMouseEnter={(e) => {
                        if (!isSelected) e.currentTarget.style.backgroundColor = '#18181C';
                      }}
                      onMouseLeave={(e) => {
                        if (!isSelected) e.currentTarget.style.backgroundColor = 'transparent';
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div
                          style={{
                            width: '32px',
                            height: '32px',
                            borderRadius: '50%',
                            backgroundColor: '#202026',
                            color: isSelected ? '#F29A60' : '#FFFFFF',
                            border: isSelected ? '1px solid #F29A60' : '1px solid #2C2C2E',
                            fontWeight: 800,
                            fontSize: '12px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }}
                        >
                          {inst.symbol.slice(0, 2)}
                        </div>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{ fontWeight: 800, fontSize: '13px', color: '#FFFFFF', fontFamily: "'JetBrains Mono', monospace" }}>
                              {inst.symbol}
                            </span>
                            <span style={{ fontSize: '9px', color: '#8E8E93', backgroundColor: '#222226', padding: '1px 5px', borderRadius: '3px' }}>
                              {inst.exchange || 'NSE'}
                            </span>
                          </div>
                          <div style={{ fontSize: '11px', color: '#8E8E93', marginTop: '2px' }}>
                            {inst.name}
                          </div>
                        </div>
                      </div>

                      <div style={{ textAlign: 'right' }}>
                        <span
                          style={{
                            fontSize: '11px',
                            color: '#F29A60',
                            backgroundColor: 'rgba(242, 154, 96, 0.1)',
                            border: '1px solid rgba(242, 154, 96, 0.3)',
                            padding: '3px 8px',
                            borderRadius: '4px',
                            fontWeight: 600,
                          }}
                        >
                          {isSelected ? 'Active Chart' : 'Select'}
                        </span>
                      </div>
                    </div>
                  );
                });
              })()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
