import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  createChart,
  ColorType,
  IChartApi,
  ISeriesApi,
} from 'lightweight-charts';
import { apiClient } from '../../api/client';
import { useFinancial } from '../../context/FinancialContext';

export interface TradeTimeMachineProps {
  initialSymbol?: string;
  onPriceUpdate?: (price: number) => void;
}

interface ReplayCandle {
  time: number; // Unix timestamp in seconds
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
  dateStr?: string;
  timeStr?: string;
}

interface ReplayTradeRecord {
  id: string;
  side: 'BUY' | 'SELL';
  symbol: string;
  shares: number;
  price: number;
  total: number;
  timeIST: string;
  candleIndex: number;
}

// Official NSE Market Holiday Calendar (2026)
const NSE_HOLIDAYS_2026: Record<string, string> = {
  '2026-01-26': 'Republic Day',
  '2026-03-25': 'Holi',
  '2026-04-03': 'Good Friday',
  '2026-04-14': 'Dr. Baba Saheb Ambedkar Jayanti',
  '2026-05-01': 'Maharashtra Day',
  '2026-08-15': 'Independence Day',
  '2026-10-02': 'Mahatma Gandhi Jayanti',
  '2026-10-20': 'Dussehra',
  '2026-11-10': 'Diwali–Balipratipada (Demo Day — Market Closed)',
  '2026-11-24': 'Gurunanak Jayanti',
  '2026-12-25': 'Christmas',
};

const POPULAR_REPLAY_SYMBOLS = [
  'RELIANCE',
  'TCS',
  'INFY',
  'HDFCBANK',
  'ICICIBANK',
  'SBIN',
  'TATAMOTORS',
];

export const TradeTimeMachine: React.FC<TradeTimeMachineProps> = ({
  initialSymbol = 'RELIANCE',
  onPriceUpdate,
}) => {
  const { virtualCash, executeOrder } = useFinancial();

  // Configuration State
  const [symbol, setSymbol] = useState<string>(initialSymbol);
  // Default to Friday 16 Oct 2026 — the most recent verified trading day with cached candles
  const [selectedDate, setSelectedDate] = useState<string>('2026-10-16');

  // Playback Engine State
  const [allCandles, setAllCandles] = useState<ReplayCandle[]>([]);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [speed, setSpeed] = useState<1 | 4 | 16>(1);

  // Status & Data States
  const [loading, setLoading] = useState<boolean>(false);
  const [emptyState, setEmptyState] = useState<{
    type: 'holiday' | 'no_data';
    holidayName?: string;
    message: string;
  } | null>(null);

  // Paper Trading State within Replay
  const [orderQty, setOrderQty] = useState<number>(5);
  const [isExecutingTrade, setIsExecutingTrade] = useState<boolean>(false);
  const [tradeConfirmation, setTradeConfirmation] = useState<{
    type: 'success' | 'error';
    message: string;
    timestamp: string;
  } | null>(null);
  const [sessionTrades, setSessionTrades] = useState<ReplayTradeRecord[]>([]);

  // Chart Container Refs
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const timerRef = useRef<any>(null);

  // Helper: check if a date is weekend or holiday
  const checkDateStatus = (dateStr: string) => {
    const parts = dateStr.split('-');
    if (parts.length !== 3) return null;
    const y = parseInt(parts[0], 10);
    const m = parseInt(parts[1], 10) - 1;
    const d = parseInt(parts[2], 10);
    const dateObj = new Date(Date.UTC(y, m, d));

    const dayOfWeek = dateObj.getUTCDay(); // 0 = Sun, 6 = Sat
    if (dayOfWeek === 0 || dayOfWeek === 6) {
      return {
        type: 'holiday' as const,
        holidayName: dayOfWeek === 0 ? 'Sunday (Weekend)' : 'Saturday (Weekend)',
        message: `NSE was closed on this date (${dayOfWeek === 0 ? 'Sunday' : 'Saturday'}). Indian equities markets do not operate on weekends. No bars are synthesized. Please select an active NSE trading day (e.g., Friday 16 Oct 2026).`,
      };
    }

    if (NSE_HOLIDAYS_2026[dateStr]) {
      return {
        type: 'holiday' as const,
        holidayName: NSE_HOLIDAYS_2026[dateStr],
        message: `NSE was closed on this date (${NSE_HOLIDAYS_2026[dateStr]}). Indian equities markets observe official exchange holidays. No bars are synthesized. Please select an active NSE trading day (e.g., Friday 16 Oct 2026).`,
      };
    }

    return null;
  };

  // 1. Fetch Real Historical Candles for Date & Symbol
  const loadDayCandles = useCallback(async (sym: string, dateStr: string) => {
    setIsPlaying(false);
    if (timerRef.current) clearInterval(timerRef.current);
    setLoading(true);
    setEmptyState(null);
    setTradeConfirmation(null);
    setAllCandles([]);
    setCurrentStep(0);

    // Step A: Check market holiday / weekend first
    const holidayCheck = checkDateStatus(dateStr);
    if (holidayCheck) {
      setLoading(false);
      setEmptyState(holidayCheck);
      return;
    }

    try {
      // Step B: Fetch genuine historical 5-min bars via apiClient
      const cleanSym = sym.replace('.NS', '').replace('NSE:', '').trim().toUpperCase();
      const res = await apiClient.market.getHistory(cleanSym, {
        interval: '5m',
        start_date: dateStr,
        end_date: dateStr,
      } as any);

      const payload = (res as any)?.data || res;
      const rawCandles = payload?.candles || payload?.bars || [];

      // Step C: Filter strictly to bars belonging to the selected date
      // This guarantees no cross-day fallback bars are displayed
      const targetDatePrefix = dateStr;
      const formatted: ReplayCandle[] = rawCandles
        .map((c: any) => {
          const unixTime = typeof c.time === 'number' ? c.time : Math.floor(new Date(c.time || c.date).getTime() / 1000);
          const candleDate = new Date(unixTime * 1000);
          const istDateStr = candleDate.toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' });
          const istTimeStr = candleDate.toLocaleTimeString('en-IN', {
            timeZone: 'Asia/Kolkata',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false,
          });

          return {
            time: unixTime,
            open: Number(c.open),
            high: Number(c.high),
            low: Number(c.low),
            close: Number(c.close),
            volume: Number(c.volume || 0),
            dateStr: istDateStr,
            timeStr: istTimeStr,
          };
        })
        .filter((c: ReplayCandle) => {
          return !isNaN(c.time) && c.open > 0 && c.dateStr === targetDatePrefix;
        })
        .sort((a: ReplayCandle, b: ReplayCandle) => a.time - b.time);

      // Deduplicate by timestamp
      const seen = new Set<number>();
      const deduplicated = formatted.filter((c) => {
        if (seen.has(c.time)) return false;
        seen.add(c.time);
        return true;
      });

      if (deduplicated.length === 0) {
        setEmptyState({
          type: 'no_data',
          message: `No historical candles available for ${cleanSym} on ${dateStr}. FinEx does not fabricate synthetic candles in Replay mode. Please select another symbol (e.g. RELIANCE, TCS, INFY) or pick another trading date.`,
        });
      } else {
        setAllCandles(deduplicated);
        setCurrentStep(0);
        if (onPriceUpdate && deduplicated[0]) {
          onPriceUpdate(deduplicated[0].close);
        }
      }
    } catch (err: any) {
      console.error('Time Machine load failed:', err);
      setEmptyState({
        type: 'no_data',
        message: `Unable to retrieve verified historical candles for ${sym} on ${dateStr}: ${err?.message || 'Network error'}. FinEx never invents fake prices.`,
      });
    } finally {
      setLoading(false);
    }
  }, [onPriceUpdate]);

  // Load when symbol or date changes
  useEffect(() => {
    loadDayCandles(symbol, selectedDate);
  }, [symbol, selectedDate, loadDayCandles]);

  // 2. Initialize Lightweight Chart
  useEffect(() => {
    if (!chartContainerRef.current) return;
    const container = chartContainerRef.current;
    container.innerHTML = '';

    const chart = createChart(container, {
      layout: {
        background: { type: ColorType.Solid, color: '#090D14' },
        textColor: '#94A3B8',
        fontSize: 12,
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
      },
      crosshair: {
        vertLine: { color: '#F59E0B', width: 1, style: 2 },
        horzLine: { color: '#F59E0B', width: 1, style: 2 },
      },
      localization: {
        locale: 'en-IN',
        timeFormatter: (time: number) => {
          const d = new Date(time * 1000);
          return d.toLocaleTimeString('en-IN', {
            timeZone: 'Asia/Kolkata',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false,
          });
        },
      },
      timeScale: {
        borderColor: 'rgba(245, 158, 11, 0.25)',
        timeVisible: true,
        secondsVisible: false,
        barSpacing: 9,
        minBarSpacing: 4,
        rightOffset: 5,
        tickMarkFormatter: (time: any) => {
          if (typeof time === 'number') {
            const d = new Date(time * 1000);
            return d.toLocaleTimeString('en-IN', {
              timeZone: 'Asia/Kolkata',
              hour: '2-digit',
              minute: '2-digit',
              hour12: false,
            });
          }
          return null;
        },
      },
      rightPriceScale: {
        borderColor: 'rgba(245, 158, 11, 0.25)',
        scaleMargins: { top: 0.1, bottom: 0.15 },
        autoScale: true,
      },
      width: container.clientWidth || 800,
      height: container.clientHeight || 420,
    });

    chartInstanceRef.current = chart;

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#10B981',
      downColor: '#EF4444',
      borderVisible: false,
      wickUpColor: '#10B981',
      wickDownColor: '#EF4444',
      priceLineVisible: true,
      priceLineColor: '#F59E0B',
      lastValueVisible: true,
    });
    seriesRef.current = candleSeries;

    const resizeObserver = new ResizeObserver((entries) => {
      if (entries[0] && chartInstanceRef.current) {
        const { width: w, height: h } = entries[0].contentRect;
        if (w > 0 && h > 0) {
          chartInstanceRef.current.applyOptions({
            width: Math.floor(w),
            height: Math.floor(h),
          });
        }
      }
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      if (timerRef.current) clearInterval(timerRef.current);
      chart.remove();
    };
  }, []);

  // 3. Update Chart on step change
  useEffect(() => {
    if (!seriesRef.current || allCandles.length === 0) return;

    const slice = allCandles.slice(0, currentStep + 1);
    seriesRef.current.setData(
      slice.map((c) => ({
        time: c.time as any,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }))
    );

    if (chartInstanceRef.current && currentStep <= 5) {
      chartInstanceRef.current.timeScale().fitContent();
    }

    const currentCandle = allCandles[currentStep];
    if (currentCandle && onPriceUpdate) {
      onPriceUpdate(currentCandle.close);
    }
  }, [currentStep, allCandles, onPriceUpdate]);

  // 4. Playback Timer Engine
  useEffect(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    if (!isPlaying || allCandles.length === 0) return;

    const intervalMs = speed === 1 ? 1200 : speed === 4 ? 350 : 80;

    timerRef.current = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev >= allCandles.length - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, intervalMs);

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [isPlaying, speed, allCandles.length]);

  // Playback Control Handlers
  const handlePlayPause = () => {
    if (allCandles.length === 0) return;
    if (currentStep >= allCandles.length - 1) {
      // Loop or restart if at end
      setCurrentStep(0);
      setIsPlaying(true);
    } else {
      setIsPlaying(!isPlaying);
    }
  };

  const handleStepForward = () => {
    setIsPlaying(false);
    if (currentStep < allCandles.length - 1) {
      setCurrentStep((prev) => prev + 1);
    }
  };

  const handleStepBackward = () => {
    setIsPlaying(false);
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1);
    }
  };

  const handleRestart = () => {
    setIsPlaying(false);
    setCurrentStep(0);
    if (chartInstanceRef.current) {
      chartInstanceRef.current.timeScale().fitContent();
    }
  };

  // Paper Trade Execution Handler against current replay candle
  const handleExecuteReplayTrade = async (side: 'BUY' | 'SELL') => {
    if (allCandles.length === 0 || isExecutingTrade) return;
    const candle = allCandles[currentStep];
    if (!candle) return;

    setIsExecutingTrade(true);
    setTradeConfirmation(null);

    try {
      const fillPrice = candle.close;
      const totalAmount = fillPrice * orderQty;

      if (side === 'BUY' && totalAmount > virtualCash) {
        setTradeConfirmation({
          type: 'error',
          message: `Insufficient virtual cash (₹${virtualCash.toLocaleString('en-IN')}) for replay buy of ₹${totalAmount.toLocaleString('en-IN')}.`,
          timestamp: candle.timeStr || '',
        });
        setIsExecutingTrade(false);
        return;
      }

      const res = await executeOrder(
        symbol,
        side,
        orderQty,
        'MARKET',
        fillPrice,
        true, // isReplay
        selectedDate // replayDate
      );

      if (res.success) {
        const newTrade: ReplayTradeRecord = {
          id: res.receipt?.id || `rep-${Date.now()}`,
          side,
          symbol,
          shares: orderQty,
          price: fillPrice,
          total: totalAmount,
          timeIST: candle.timeStr || '09:15',
          candleIndex: currentStep,
        };
        setSessionTrades((prev) => [newTrade, ...prev]);

        setTradeConfirmation({
          type: 'success',
          message: `REPLAY — ${symbol} — ${selectedDate} — past NSE data, not live: ${side} ${orderQty} shares @ ₹${fillPrice.toFixed(2)} (Total: ₹${totalAmount.toLocaleString('en-IN')}). Virtual cash updated!`,
          timestamp: candle.timeStr || '',
        });
      } else {
        setTradeConfirmation({
          type: 'error',
          message: res.error || 'Failed to execute replay order.',
          timestamp: candle.timeStr || '',
        });
      }
    } catch (err: any) {
      setTradeConfirmation({
        type: 'error',
        message: err?.message || 'Error routing replay trade to virtual ledger.',
        timestamp: candle.timeStr || '',
      });
    } finally {
      setIsExecutingTrade(false);
    }
  };

  const currentCandle = allCandles[currentStep];
  const firstCandle = allCandles[0];
  const dayChange = currentCandle && firstCandle ? currentCandle.close - firstCandle.open : 0;
  const dayChangePct = currentCandle && firstCandle && firstCandle.open > 0 ? (dayChange / firstCandle.open) * 100 : 0;
  const isPositiveDay = dayChange >= 0;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        width: '100%',
        backgroundColor: '#090D14',
        color: '#E2E8F0',
        fontFamily: 'Inter, system-ui, sans-serif',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {/* 1. MANDATORY PERSISTENT REPLAY BADGE (Top Ribbon — Always Visible in Every State) */}
      <div
        id="time-machine-persistent-badge"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 16px',
          backgroundColor: '#171206',
          borderBottom: '1px solid rgba(245, 158, 11, 0.4)',
          color: '#FBBF24',
          fontSize: '11px',
          fontWeight: 700,
          flexShrink: 0,
          zIndex: 10,
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, flexWrap: 'wrap' }}>
          <span
            style={{
              display: 'inline-block',
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: isPlaying ? '#10B981' : '#F59E0B',
              boxShadow: isPlaying ? '0 0 10px #10B981' : '0 0 8px #F59E0B',
              animation: isPlaying ? 'pulse 1.5s infinite' : 'none',
            }}
          />
          <span
            style={{
              backgroundColor: '#B45309',
              color: '#FFFFFF',
              padding: '2px 8px',
              borderRadius: '4px',
              fontSize: '10px',
              letterSpacing: '0.6px',
              fontWeight: 800,
            }}
          >
            TRADE TIME MACHINE
          </span>
          <span style={{ color: '#FCD34D', letterSpacing: '0.3px', fontWeight: 700 }}>
            REPLAY — {symbol} — {selectedDate} — past NSE data, not live
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
          {allCandles.length > 0 && currentCandle && (
            <>
              <span
                style={{
                  backgroundColor: '#0F172A',
                  border: '1px solid rgba(245, 158, 11, 0.3)',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontSize: '11px',
                  color: '#94A3B8',
                }}
              >
                🕐 <strong style={{ color: '#FFFFFF' }}>{currentCandle.timeStr || '09:15'} IST</strong>
                {' '}(Bar {currentStep + 1}/{allCandles.length})
              </span>
              <span
                style={{
                  backgroundColor: '#0F172A',
                  border: '1px solid rgba(245, 158, 11, 0.3)',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontSize: '11px',
                }}
              >
                LTP: <strong style={{ color: '#FFFFFF' }}>₹{currentCandle.close.toFixed(2)}</strong>
                {' '}
                <span style={{ color: isPositiveDay ? '#10B981' : '#EF4444', fontWeight: 600 }}>
                  ({isPositiveDay ? '+' : ''}{dayChangePct.toFixed(2)}%)
                </span>
              </span>
            </>
          )}

          <span
            style={{
              backgroundColor: isPlaying ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)',
              color: isPlaying ? '#34D399' : '#FBBF24',
              border: `1px solid ${isPlaying ? 'rgba(16, 185, 129, 0.4)' : 'rgba(245, 158, 11, 0.4)'}`,
              padding: '2px 8px',
              borderRadius: '4px',
              fontSize: '10px',
              fontWeight: 700,
            }}
          >
            {isPlaying ? `PLAYING (${speed}x)` : 'PAUSED'}
          </span>
        </div>
      </div>

      {/* 2. REPLAY CONTROLS & DATE/SYMBOL SELECTOR BAR */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 16px',
          backgroundColor: '#0D1117',
          borderBottom: '1px solid #1E293B',
          fontSize: '12px',
          gap: '12px',
          flexWrap: 'wrap',
          flexShrink: 0,
        }}
      >
        {/* Symbol & Date Pickers */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <label style={{ color: '#94A3B8', fontSize: '11px', fontWeight: 600 }}>Symbol:</label>
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            style={{
              backgroundColor: '#1E293B',
              color: '#FFFFFF',
              border: '1px solid #334155',
              borderRadius: '4px',
              padding: '4px 8px',
              fontSize: '11px',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            {POPULAR_REPLAY_SYMBOLS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>

          <label style={{ color: '#94A3B8', fontSize: '11px', fontWeight: 600, marginLeft: '6px' }}>
            Trading Date:
          </label>
          <input
            type="date"
            value={selectedDate}
            max="2026-11-10"
            onChange={(e) => setSelectedDate(e.target.value)}
            style={{
              backgroundColor: '#1E293B',
              color: '#FFFFFF',
              border: '1px solid #334155',
              borderRadius: '4px',
              padding: '3px 8px',
              fontSize: '11px',
              cursor: 'pointer',
            }}
          />

          {/* Quick Date Chips for Demo Script */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginLeft: '4px' }}>
            <button
              onClick={() => setSelectedDate('2026-10-16')}
              style={{
                backgroundColor: selectedDate === '2026-10-16' ? '#2563EB' : 'rgba(255, 255, 255, 0.05)',
                color: selectedDate === '2026-10-16' ? '#FFFFFF' : '#94A3B8',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '4px',
                padding: '2px 8px',
                fontSize: '10px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
              title="Verified NSE Equities Trading Day (Friday 16 Oct 2026)"
            >
              16 Oct (Fri)
            </button>
            <button
              onClick={() => setSelectedDate('2026-10-15')}
              style={{
                backgroundColor: selectedDate === '2026-10-15' ? '#2563EB' : 'rgba(255, 255, 255, 0.05)',
                color: selectedDate === '2026-10-15' ? '#FFFFFF' : '#94A3B8',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '4px',
                padding: '2px 8px',
                fontSize: '10px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
              title="Verified NSE Equities Trading Day (Thursday 15 Oct 2026)"
            >
              15 Oct (Thu)
            </button>
            <button
              onClick={() => setSelectedDate('2026-11-10')}
              style={{
                backgroundColor: selectedDate === '2026-11-10' ? '#DC2626' : 'rgba(239, 68, 68, 0.1)',
                color: selectedDate === '2026-11-10' ? '#FFFFFF' : '#F87171',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '4px',
                padding: '2px 8px',
                fontSize: '10px',
                fontWeight: 700,
                cursor: 'pointer',
              }}
              title="Demo Day Check: Diwali Market Closed Holiday State"
            >
              10 Nov (Diwali — Closed)
            </button>
          </div>
        </div>

        {/* Playback Controls (Play / Pause / Step / Speed) */}
        {allCandles.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={handleRestart}
              style={{
                backgroundColor: '#1E293B',
                color: '#E2E8F0',
                border: '1px solid #334155',
                borderRadius: '4px',
                padding: '4px 8px',
                fontSize: '11px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
              title="Rewind to Market Open (09:15 IST)"
            >
              ↺ Restart
            </button>
            <button
              onClick={handleStepBackward}
              disabled={currentStep === 0}
              style={{
                backgroundColor: '#1E293B',
                color: currentStep === 0 ? '#64748B' : '#E2E8F0',
                border: '1px solid #334155',
                borderRadius: '4px',
                padding: '4px 8px',
                fontSize: '11px',
                fontWeight: 600,
                cursor: currentStep === 0 ? 'not-allowed' : 'pointer',
              }}
              title="Step Back 1 Candle"
            >
              ⏮
            </button>
            <button
              onClick={handlePlayPause}
              style={{
                backgroundColor: isPlaying ? '#EF4444' : '#10B981',
                color: '#FFFFFF',
                border: 'none',
                borderRadius: '4px',
                padding: '4px 14px',
                fontSize: '12px',
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                boxShadow: isPlaying ? '0 0 8px rgba(239, 68, 68, 0.4)' : '0 0 8px rgba(16, 185, 129, 0.4)',
              }}
            >
              {isPlaying ? '⏸ Pause' : '▶ Play'}
            </button>
            <button
              onClick={handleStepForward}
              disabled={currentStep >= allCandles.length - 1}
              style={{
                backgroundColor: '#1E293B',
                color: currentStep >= allCandles.length - 1 ? '#64748B' : '#E2E8F0',
                border: '1px solid #334155',
                borderRadius: '4px',
                padding: '4px 8px',
                fontSize: '11px',
                fontWeight: 600,
                cursor: currentStep >= allCandles.length - 1 ? 'not-allowed' : 'pointer',
              }}
              title="Step Forward 1 Candle"
            >
              ⏭
            </button>

            {/* Speed Selector */}
            <div style={{ display: 'flex', backgroundColor: '#1E293B', borderRadius: '4px', padding: '1px' }}>
              {([1, 4, 16] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => setSpeed(s)}
                  style={{
                    backgroundColor: speed === s ? '#F59E0B' : 'transparent',
                    color: speed === s ? '#000000' : '#94A3B8',
                    border: 'none',
                    borderRadius: '3px',
                    padding: '2px 7px',
                    fontSize: '10px',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  {s}x
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 3. TIMELINE SCRUBBER (When candles are loaded) */}
      {allCandles.length > 0 && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            padding: '4px 16px',
            backgroundColor: '#090D14',
            borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
            gap: '12px',
            flexShrink: 0,
            fontSize: '11px',
          }}
        >
          <span style={{ color: '#64748B', flexShrink: 0 }}>09:15 IST</span>
          <input
            type="range"
            min={0}
            max={allCandles.length - 1}
            value={currentStep}
            onChange={(e) => {
              setIsPlaying(false);
              setCurrentStep(parseInt(e.target.value, 10));
            }}
            style={{
              flex: 1,
              accentColor: '#F59E0B',
              cursor: 'pointer',
              height: '4px',
            }}
          />
          <span style={{ color: '#64748B', flexShrink: 0 }}>15:30 IST</span>
        </div>
      )}

      {/* 4. MAIN CHART & INTERACTIVE TRADING DESK */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0, position: 'relative', overflow: 'hidden' }}>
        {/* Center: Lightweight Candlestick Chart */}
        <div style={{ flex: 1, minWidth: 0, minHeight: 0, position: 'relative', display: 'flex', overflow: 'hidden' }}>
          {/* Chart Canvas Container */}
          <div
            ref={chartContainerRef}
            style={{
              width: '100%',
              height: '100%',
              visibility: emptyState || loading ? 'hidden' : 'visible',
            }}
          />

          {/* Loading Indicator */}
          {loading && (
            <div
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: '#090D14',
                zIndex: 20,
                gap: '12px',
              }}
            >
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  border: '3px solid rgba(245, 158, 11, 0.2)',
                  borderTopColor: '#F59E0B',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite',
                }}
              />
              <span style={{ color: '#FCD34D', fontSize: '13px', fontWeight: 600 }}>
                Loading verified historical candles for {symbol} ({selectedDate})...
              </span>
            </div>
          )}

          {/* HONEST EMPTY STATES (No Fabrication) */}
          {emptyState && !loading && (
            <div
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: '#090D14',
                zIndex: 20,
                padding: '32px',
                textAlign: 'center',
              }}
            >
              <div
                style={{
                  maxWidth: '560px',
                  backgroundColor: '#0F172A',
                  border: `1px solid ${emptyState.type === 'holiday' ? 'rgba(239, 68, 68, 0.4)' : 'rgba(148, 163, 184, 0.2)'}`,
                  borderRadius: '12px',
                  padding: '28px',
                  boxShadow: '0 12px 32px rgba(0, 0, 0, 0.6)',
                }}
              >
                <div style={{ fontSize: '36px', marginBottom: '12px' }}>
                  {emptyState.type === 'holiday' ? '🏛️' : '📊'}
                </div>
                <h3
                  style={{
                    fontSize: '17px',
                    fontWeight: 700,
                    color: emptyState.type === 'holiday' ? '#F87171' : '#E2E8F0',
                    margin: '0 0 8px 0',
                  }}
                >
                  {emptyState.type === 'holiday'
                    ? `NSE Closed — ${emptyState.holidayName || 'Market Holiday'}`
                    : `No Historical Candles for ${symbol}`}
                </h3>
                <p style={{ fontSize: '13px', color: '#94A3B8', lineHeight: '1.6', margin: '0 0 20px 0' }}>
                  {emptyState.message}
                </p>

                <div style={{ display: 'flex', justifyContent: 'center', gap: '8px' }}>
                  <button
                    onClick={() => {
                      setSelectedDate('2026-10-16');
                      setSymbol('RELIANCE');
                    }}
                    style={{
                      backgroundColor: '#10B981',
                      color: '#FFFFFF',
                      border: 'none',
                      borderRadius: '6px',
                      padding: '8px 16px',
                      fontSize: '12px',
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    Load Friday 16 Oct 2026 (RELIANCE) →
                  </button>
                  <button
                    onClick={() => {
                      setSelectedDate('2026-10-15');
                      setSymbol('TCS');
                    }}
                    style={{
                      backgroundColor: '#1E293B',
                      color: '#94A3B8',
                      border: '1px solid #334155',
                      borderRadius: '6px',
                      padding: '8px 16px',
                      fontSize: '12px',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    Load Thursday 15 Oct (TCS)
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Side: Replay Paper Trading Desk */}
        {allCandles.length > 0 && currentCandle && (
          <div
            style={{
              width: '280px',
              backgroundColor: '#0B0F19',
              borderLeft: '1px solid #1E293B',
              display: 'flex',
              flexDirection: 'column',
              padding: '16px',
              gap: '14px',
              flexShrink: 0,
              overflowY: 'auto',
            }}
          >
            <div>
              <div style={{ fontSize: '10px', color: '#F59E0B', fontWeight: 800, letterSpacing: '0.5px' }}>
                REPLAY PAPER TRADE
              </div>
              <h4 style={{ margin: '2px 0 0 0', fontSize: '15px', color: '#FFFFFF', fontWeight: 700 }}>
                {symbol} Order Ticket
              </h4>
            </div>

            {/* Price Card */}
            <div
              style={{
                backgroundColor: '#111827',
                border: '1px solid #1F2937',
                borderRadius: '6px',
                padding: '10px 12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
              }}
            >
              <span style={{ fontSize: '10px', color: '#94A3B8' }}>Replay Close Price:</span>
              <div style={{ fontSize: '20px', fontWeight: 800, color: '#FFFFFF' }}>
                ₹{currentCandle.close.toFixed(2)}
              </div>
              <span style={{ fontSize: '10px', color: '#64748B' }}>
                Open: ₹{currentCandle.open.toFixed(2)} | High: ₹{currentCandle.high.toFixed(2)} | Low: ₹{currentCandle.low.toFixed(2)}
              </span>
            </div>

            {/* Shares Quantity Selector */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#94A3B8', marginBottom: '6px' }}>
                <span>Shares:</span>
                <span style={{ color: '#FFFFFF', fontWeight: 700 }}>{orderQty} shares</span>
              </div>
              <div style={{ display: 'flex', gap: '4px' }}>
                {[1, 5, 10, 25].map((q) => (
                  <button
                    key={q}
                    onClick={() => setOrderQty(q)}
                    style={{
                      flex: 1,
                      backgroundColor: orderQty === q ? '#F59E0B' : '#1E293B',
                      color: orderQty === q ? '#000000' : '#E2E8F0',
                      border: 'none',
                      borderRadius: '4px',
                      padding: '5px 0',
                      fontSize: '11px',
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>

            {/* Order Value & Available Cash */}
            <div style={{ fontSize: '11px', display: 'flex', flexDirection: 'column', gap: '4px', color: '#94A3B8' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Estimated Total:</span>
                <strong style={{ color: '#FCD34D' }}>₹{(currentCandle.close * orderQty).toFixed(2)}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Paper Cash:</span>
                <strong style={{ color: '#FFFFFF' }}>₹{virtualCash.toLocaleString('en-IN')}</strong>
              </div>
            </div>

            {/* Buy / Sell Buttons */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <button
                onClick={() => handleExecuteReplayTrade('BUY')}
                disabled={isExecutingTrade || currentCandle.close * orderQty > virtualCash}
                style={{
                  backgroundColor: '#10B981',
                  color: '#FFFFFF',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '10px 0',
                  fontSize: '12px',
                  fontWeight: 700,
                  cursor: isExecutingTrade || currentCandle.close * orderQty > virtualCash ? 'not-allowed' : 'pointer',
                  opacity: currentCandle.close * orderQty > virtualCash ? 0.5 : 1,
                }}
              >
                Buy {orderQty}
              </button>
              <button
                onClick={() => handleExecuteReplayTrade('SELL')}
                disabled={isExecutingTrade}
                style={{
                  backgroundColor: '#EF4444',
                  color: '#FFFFFF',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '10px 0',
                  fontSize: '12px',
                  fontWeight: 700,
                  cursor: isExecutingTrade ? 'not-allowed' : 'pointer',
                }}
              >
                Sell {orderQty}
              </button>
            </div>

            {/* Trade Confirmation Notice */}
            {tradeConfirmation && (
              <div
                style={{
                  backgroundColor: tradeConfirmation.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                  border: `1px solid ${tradeConfirmation.type === 'success' ? '#10B981' : '#EF4444'}`,
                  borderRadius: '6px',
                  padding: '8px 10px',
                  fontSize: '11px',
                  color: tradeConfirmation.type === 'success' ? '#34D399' : '#F87171',
                  lineHeight: '1.4',
                }}
              >
                {tradeConfirmation.message}
              </div>
            )}

            {/* Session Replay Trade History */}
            {sessionTrades.length > 0 && (
              <div style={{ marginTop: 'auto', borderTop: '1px solid #1E293B', paddingTop: '10px' }}>
                <div style={{ fontSize: '10px', color: '#94A3B8', fontWeight: 700, marginBottom: '6px' }}>
                  SESSION REPLAY TRADES ({sessionTrades.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '120px', overflowY: 'auto' }}>
                  {sessionTrades.map((t) => (
                    <div
                      key={t.id}
                      style={{
                        backgroundColor: '#1E293B',
                        borderRadius: '4px',
                        padding: '4px 6px',
                        fontSize: '10px',
                        display: 'flex',
                        justifyContent: 'space-between',
                      }}
                    >
                      <span style={{ color: t.side === 'BUY' ? '#10B981' : '#EF4444', fontWeight: 700 }}>
                        {t.side} {t.shares} @ ₹{t.price.toFixed(2)}
                      </span>
                      <span style={{ color: '#64748B' }}>{t.timeIST}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
