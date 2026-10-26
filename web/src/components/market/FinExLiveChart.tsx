import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi } from 'lightweight-charts';
import { apiClient } from '../../api/client';

interface FinExLiveChartProps {
  symbol: string;
  height?: number;
  interval?: string;
  rangePreset?: string;
  onPriceUpdate?: (price: number) => void;
}

const SYMBOL_BASE_PRICES: Record<string, number> = {
  RELIANCE: 2520,
  TCS: 3550,
  INFY: 1510,
  HDFCBANK: 1680,
  ICICIBANK: 1120,
  TATAMOTORS: 940,
  SBIN: 810,
  BHARTIARTL: 1450,
  ITC: 480,
  LT: 3600,
  NTPC: 303,
  ONGC: 225,
  POWERGRID: 252,
  ADANIENT: 2594,
  WIPRO: 495,
  KOTAKBANK: 1780,
  AXISBANK: 1150,
  MARUTI: 11800,
  SUNPHARMA: 1620,
  BAJFINANCE: 7200,
};

interface CachedCandleData {
  candles: Array<{ time: number; open: number; high: number; low: number; close: number }>;
  observedAt: string;
}

const memoryCandleCache = new Map<string, CachedCandleData>();

function getCachedCandles(cleanSymbol: string): CachedCandleData | null {
  if (memoryCandleCache.has(cleanSymbol)) {
    return memoryCandleCache.get(cleanSymbol)!;
  }
  try {
    const raw = localStorage.getItem(`finex_candles_cache_${cleanSymbol}`);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && Array.isArray(parsed.candles) && parsed.candles.length > 0) {
        memoryCandleCache.set(cleanSymbol, parsed);
        return parsed;
      }
    }
  } catch {}
  return null;
}

function setCachedCandles(cleanSymbol: string, data: CachedCandleData) {
  memoryCandleCache.set(cleanSymbol, data);
  try {
    localStorage.setItem(`finex_candles_cache_${cleanSymbol}`, JSON.stringify(data));
  } catch {}
}

function generateFallbackCandles(cleanSymbol: string, rangePreset: string, interval: string) {
  const basePrice = SYMBOL_BASE_PRICES[cleanSymbol] || 1500;
  const isIntraday = ['1m', '5m', '15m', '30m', '1h', 'ONE_MINUTE', 'FIVE_MINUTE', 'FIFTEEN_MINUTE'].includes(interval) || rangePreset === '1D';

  const candles: Array<{ time: number; open: number; high: number; low: number; close: number }> = [];
  const nowSec = Math.floor(Date.now() / 1000);

  if (isIntraday) {
    const stepSec = 300; // 5 min
    const totalBars = 78;
    let currPrice = basePrice * 0.985;
    const startSec = nowSec - (totalBars * stepSec);

    for (let i = 0; i < totalBars; i++) {
      const barTime = startSec + (i * stepSec);
      const change = (Math.random() - 0.485) * (basePrice * 0.004);
      const open = Math.round(currPrice * 100) / 100;
      const close = Math.round((currPrice + change) * 100) / 100;
      const high = Math.round((Math.max(open, close) + Math.random() * (basePrice * 0.003)) * 100) / 100;
      const low = Math.round((Math.min(open, close) - Math.random() * (basePrice * 0.003)) * 100) / 100;
      currPrice = close;
      candles.push({ time: barTime, open, high, low, close });
    }
  } else {
    const daysMap: Record<string, number> = {
      '1W': 7,
      '1M': 30,
      '3M': 90,
      '6M': 180,
      '1Y': 252,
      '5Y': 1260,
      'ALL': 1800,
    };
    const totalBars = daysMap[rangePreset] || 252;
    const daySec = 86400;
    let currPrice = basePrice * 0.85;
    const startSec = nowSec - (totalBars * daySec);

    for (let i = 0; i < totalBars; i++) {
      const barTime = startSec + (i * daySec);
      const change = (Math.random() - 0.48) * (currPrice * 0.016);
      const open = Math.round(currPrice * 100) / 100;
      const close = Math.round((currPrice + change) * 100) / 100;
      const high = Math.round((Math.max(open, close) + Math.random() * (currPrice * 0.011)) * 100) / 100;
      const low = Math.round((Math.min(open, close) - Math.random() * (currPrice * 0.011)) * 100) / 100;
      currPrice = close;
      candles.push({ time: barTime, open, high, low, close });
    }
  }

  return candles;
}

export const FinExLiveChart: React.FC<FinExLiveChartProps> = ({
  symbol,
  height = 400,
  interval = 'ONE_MINUTE',
  rangePreset = '1Y',
  onPriceUpdate,
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const lastBarRef = useRef<{ time: number; open: number; high: number; low: number; close: number } | null>(null);
  const simTimerRef = useRef<any>(null);

  const [freshness, setFreshness] = useState<{
    status: string;
    source: string;
    asOf: string;
    lastPrice: number | null;
  }>({
    status: 'CONNECTING',
    source: 'ANGEL_ONE_SMARTAPI',
    asOf: '',
    lastPrice: null,
  });

  const isDemoSimEnabled = (import.meta as any).env?.VITE_DEMO_SIMULATION === 'true';
  const [isSimulated, setIsSimulated] = useState<boolean>(false);
  const isSimulatedRef = useRef<boolean>(false);
  const [cachedLabel, setCachedLabel] = useState<string | null>(null);
  const [noDataAvailable, setNoDataAvailable] = useState<boolean>(false);

  const cleanSymbol = symbol.replace('.NS', '').replace('NSE:', '').trim().toUpperCase();

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // 1. Initialize Lightweight Chart
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
        vertLine: { color: '#6366F1', width: 1, style: 2 },
        horzLine: { color: '#6366F1', width: 1, style: 2 },
      },
      localization: {
        locale: 'en-IN',
        timeFormatter: (time: number) => {
          const d = new Date(time * 1000);
          if (interval === 'ONE_DAY' || interval === '1d' || interval === '1D') {
            return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
          }
          return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false });
        },
      },
      timeScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
        timeVisible: true,
        secondsVisible: false,
        barSpacing: 8,
        minBarSpacing: 4,
        rightOffset: 5,
        tickMarkFormatter: (time: any) => {
          if (typeof time === 'number') {
            const d = new Date(time * 1000);
            if (interval === 'ONE_DAY' || interval === '1d' || interval === '1D') {
              return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
            }
            const hours = String(d.getHours()).padStart(2, '0');
            const mins = String(d.getMinutes()).padStart(2, '0');
            return `${hours}:${mins}`;
          }
          return null;
        },
      },
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
        scaleMargins: { top: 0.08, bottom: 0.12 },
        autoScale: true,
      },
      width: container.clientWidth || 800,
      height: container.clientHeight || 400,
    });

    chartInstanceRef.current = chart;

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#10B981',
      downColor: '#EF4444',
      borderVisible: false,
      wickUpColor: '#10B981',
      wickDownColor: '#EF4444',
      priceLineVisible: false,
      lastValueVisible: true,
    });
    seriesRef.current = candleSeries;

    // Handle Resize to exact pixel dimensions of container
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

    // Helper to start realistic simulated micro-ticks (ONLY when explicit demo simulation is enabled)
    const startSimulatedTicks = (baseLastBar: { time: number; open: number; high: number; low: number; close: number }) => {
      if (!isDemoSimEnabled) return;
      if (simTimerRef.current) clearInterval(simTimerRef.current);
      lastBarRef.current = { ...baseLastBar };

      simTimerRef.current = setInterval(() => {
        if (!seriesRef.current || !lastBarRef.current) return;
        const prev = lastBarRef.current;
        const tickDelta = (Math.random() - 0.49) * (prev.close * 0.001);
        const newClose = Math.round((prev.close + tickDelta) * 100) / 100;
        const updated = {
          time: prev.time,
          open: prev.open,
          high: Math.max(prev.high, newClose),
          low: Math.min(prev.low, newClose),
          close: newClose,
        };
        lastBarRef.current = updated;
        try {
          seriesRef.current.update(updated as any);
        } catch {}
        if (onPriceUpdate) onPriceUpdate(newClose);
        setFreshness((f) => ({
          ...f,
          lastPrice: newClose,
          asOf: new Date().toLocaleTimeString(),
        }));
      }, 3000);
    };

    // 2. Fetch Historical Candles (Option B: Cached-First, Synthesizer behind explicit demo flag)
    const fetchHistory = async () => {
      try {
        const RANGE_DAYS: Record<string, number> = {
          '1D': 2,
          '1W': 7,
          '1M': 30,
          '3M': 90,
          '6M': 180,
          '1Y': 365,
          '5Y': 1825,
          'ALL': 3650,
        };
        const fetchDays = RANGE_DAYS[rangePreset] ?? 365;
        let res: any;
        const isIndex = cleanSymbol.startsWith('NIFTY') || cleanSymbol === 'SENSEX' || cleanSymbol.includes('INDEX');
        if (isIndex) {
          try {
            res = await apiClient.market.getIndexHistory(cleanSymbol, {
              interval: interval,
              days: fetchDays,
            });
          } catch {
            res = await apiClient.market.getHistory(cleanSymbol, {
              interval: interval,
              days: fetchDays,
            } as any);
          }
        } else {
          res = await apiClient.market.getHistory(cleanSymbol, {
            interval: interval,
            days: fetchDays,
          } as any);
        }
        const payload = (res as any)?.data || res;
        const candles = payload?.candles || payload?.bars || [];

        if (candles.length > 0 && seriesRef.current) {
          const seen = new Set<number>();
          const formatted = candles
            .map((c: any) => ({
              time: typeof c.time === 'number' ? c.time : Math.floor(new Date(c.time || c.date).getTime() / 1000),
              open: Number(c.open),
              high: Number(c.high),
              low: Number(c.low),
              close: Number(c.close),
            }))
            .filter((c: any) => !isNaN(c.time) && c.open > 0)
            .sort((a: any, b: any) => a.time - b.time)
            .filter((c: any) => {
              if (seen.has(c.time)) return false;
              seen.add(c.time);
              return true;
            });

          if (formatted.length > 0) {
            seriesRef.current.setData(formatted);
            chart.timeScale().fitContent();

            const last = formatted[formatted.length - 1];
            if (last) {
              lastBarRef.current = { ...last };
            }

            const observedAtStr = payload.observed_at || new Date().toLocaleString('en-IN');
            setCachedCandles(cleanSymbol, {
              candles: formatted,
              observedAt: observedAtStr,
            });

            setIsSimulated(false);
            isSimulatedRef.current = false;
            setCachedLabel(null);
            setNoDataAvailable(false);
            setFreshness({
              status: payload.freshness || 'LIVE',
              source: payload.source || 'ANGEL_ONE_SMARTAPI',
              asOf: payload.observed_at || new Date().toLocaleTimeString(),
              lastPrice: last ? last.close : null,
            });

            if (last && onPriceUpdate) {
              onPriceUpdate(last.close);
            }
            return;
          }
        }
      } catch (err) {
        console.warn(`Historical candles fetch error for ${cleanSymbol}:`, err);
      }

      // Step 1: FIRST try real cached candles (the last successfully fetched historical candles)
      const cached = getCachedCandles(cleanSymbol);
      if (cached && cached.candles && cached.candles.length > 0 && seriesRef.current) {
        seriesRef.current.setData(cached.candles as any);
        chart.timeScale().fitContent();

        const last = cached.candles[cached.candles.length - 1];
        if (last) {
          lastBarRef.current = { ...last };
        }
        setIsSimulated(false);
        isSimulatedRef.current = false;
        setNoDataAvailable(false);
        setCachedLabel(`Last real data: ${cached.observedAt} — market data unavailable, showing last cached candles`);
        setFreshness({
          status: 'FALLBACK_CACHED',
          source: `FinEx Cache (${cached.observedAt})`,
          asOf: cached.observedAt,
          lastPrice: last ? last.close : null,
        });
        if (last && onPriceUpdate) {
          onPriceUpdate(last.close);
        }
        return;
      }

      // Step 2: Use generateFallbackCandles() synthesizer ONLY when VITE_DEMO_SIMULATION is enabled
      if (isDemoSimEnabled && seriesRef.current) {
        const fallback = generateFallbackCandles(cleanSymbol, rangePreset, interval);
        seriesRef.current.setData(fallback as any);
        chart.timeScale().fitContent();

        const last = fallback[fallback.length - 1];
        if (last) {
          lastBarRef.current = { ...last };
          startSimulatedTicks(last);
        }
        setIsSimulated(true);
        isSimulatedRef.current = true;
        setCachedLabel(null);
        setNoDataAvailable(false);
        setFreshness({
          status: 'SIMULATED',
          source: 'FinEx Replay Engine (NSE Baseline)',
          asOf: new Date().toLocaleTimeString(),
          lastPrice: last ? last.close : null,
        });
        if (last && onPriceUpdate) {
          onPriceUpdate(last.close);
        }
        return;
      }

      // Step 3: Flag is OFF and no cached candles exist -> honest empty state, NEVER synthesized bars
      setIsSimulated(false);
      isSimulatedRef.current = false;
      setCachedLabel(null);
      setNoDataAvailable(true);
      if (seriesRef.current) {
        seriesRef.current.setData([]);
      }
      setFreshness({
        status: 'DISCONNECTED',
        source: 'FinEx Market Engine',
        asOf: '--',
        lastPrice: null,
      });
    };

    fetchHistory();

    // 3. Connect to WebSocket Tick Stream (Optional Live Stream)
    let wsHost = window.location.host;
    let wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const envApiUrl = (import.meta as any).env?.VITE_API_BASE_URL;
    if (envApiUrl && envApiUrl.startsWith('http')) {
      try {
        const parsed = new URL(envApiUrl);
        wsHost = parsed.host;
        wsProtocol = parsed.protocol === 'https:' ? 'wss:' : 'ws:';
      } catch {
        // fallback
      }
    } else if (window.location.port === '3000') {
      wsHost = `${window.location.hostname}:8000`;
    }
    const wsUrl = `${wsProtocol}//${wsHost}/api/v1/market/ws/${cleanSymbol}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (simTimerRef.current) clearInterval(simTimerRef.current);
        setFreshness((prev) => ({ ...prev, status: 'STREAMING' }));
      };

      ws.onmessage = (event) => {
        try {
          const tick = JSON.parse(event.data);
          const INTERVAL_SECONDS: Record<string, number> = {
            ONE_MINUTE: 60,
            FIVE_MINUTE: 300,
            FIFTEEN_MINUTE: 900,
            THIRTY_MINUTE: 1800,
            ONE_HOUR: 3600,
            ONE_DAY: 86400,
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '30m': 1800,
            '1h': 3600,
            '1d': 86400,
            '1D': 86400,
          };
          const bucket = INTERVAL_SECONDS[interval] ?? 60;
          const tickTs = Number(tick.CurrentBarUnixTime) || Math.floor(Date.now() / 1000);
          const barTime = Math.floor(tickTs / bucket) * bucket;
          const closePrice = Number(tick.ltp || tick.close);

          if (seriesRef.current && !isNaN(closePrice) && closePrice > 0) {
            const effectiveBarTime = lastBarRef.current && barTime < lastBarRef.current.time
              ? lastBarRef.current.time
              : barTime;

            let updatedBar: { time: number; open: number; high: number; low: number; close: number };

            if (lastBarRef.current && lastBarRef.current.time === effectiveBarTime) {
              updatedBar = {
                time: effectiveBarTime,
                open: lastBarRef.current.open,
                high: Math.max(lastBarRef.current.high, closePrice),
                low: Math.min(lastBarRef.current.low, closePrice),
                close: closePrice,
              };
            } else {
              updatedBar = {
                time: effectiveBarTime,
                open: closePrice,
                high: closePrice,
                low: closePrice,
                close: closePrice,
              };
            }

            lastBarRef.current = updatedBar;
            try {
              seriesRef.current.update(updatedBar as any);
              chartInstanceRef.current?.timeScale().scrollToPosition(3, false);
            } catch (err) {
              console.warn('Series update ignored:', err);
            }
          }

          setFreshness({
            status: tick.freshness || 'LIVE',
            source: tick.source || 'ANGEL_ONE_SMARTAPI',
            asOf: new Date(tick.observed_at || Date.now()).toLocaleTimeString(),
            lastPrice: closePrice,
          });

          if (onPriceUpdate && !isNaN(closePrice)) {
            onPriceUpdate(closePrice);
          }
        } catch (tickErr) {
          console.warn('Error parsing tick message:', tickErr);
        }
      };

      ws.onerror = (e) => {
        console.warn(`WebSocket note for ${cleanSymbol} (using replay mode):`, e);
      };

      ws.onclose = () => {
        const simActive = isSimulatedRef.current;
        setFreshness((prev) => ({
          ...prev,
          status: prev.status === 'STREAMING'
            ? 'REPLAY_SYNC'
            : simActive
            ? 'SIMULATED'
            : (prev.status === 'CONNECTING' ? 'DISCONNECTED' : prev.status),
          source: prev.source || (simActive ? 'FinEx Replay Engine (NSE Baseline)' : 'FinEx Market Engine'),
        }));
        if (isDemoSimEnabled && simActive && lastBarRef.current && !simTimerRef.current) {
          startSimulatedTicks(lastBarRef.current);
        }
      };
    } catch (wsErr) {
      console.warn('WebSocket setup exception:', wsErr);
    }

    return () => {
      if (simTimerRef.current) {
        clearInterval(simTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
      resizeObserver.disconnect();
      chart.remove();
    };
  }, [cleanSymbol, interval, rangePreset, height]);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
        flex: 1,
        minHeight: 0,
        backgroundColor: '#090D14',
        borderRadius: 8,
        border: '1px solid rgba(255, 255, 255, 0.08)',
        overflow: 'hidden',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
      }}
    >
      {/* Option A & B: Persistent Full-Width Simulation Watermark Banner */}
      {isSimulated && (
        <div
          data-testid="simulated-watermark-banner"
          style={{
            width: '100%',
            backgroundColor: '#DC2626',
            color: '#FFFFFF',
            padding: '6px 12px',
            fontSize: 12,
            fontWeight: 700,
            textAlign: 'center',
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
            boxShadow: '0 2px 8px rgba(220, 38, 38, 0.4)',
            zIndex: 10,
            flexShrink: 0,
          }}
        >
          SIMULATED DATA — randomly generated for display only, not market prices
        </div>
      )}

      {/* Option B: Cached Candles Informational Notice */}
      {!isSimulated && cachedLabel && (
        <div
          data-testid="cached-watermark-banner"
          style={{
            width: '100%',
            backgroundColor: 'rgba(245, 158, 11, 0.15)',
            borderBottom: '1px solid rgba(245, 158, 11, 0.3)',
            color: '#FBBF24',
            padding: '4px 12px',
            fontSize: 11,
            fontWeight: 600,
            textAlign: 'center',
            flexShrink: 0,
          }}
        >
          ℹ️ {cachedLabel}
        </div>
      )}

      {/* Top Ticker Status Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '8px',
          padding: '6px 12px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
          backgroundColor: '#0F172A',
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontWeight: 700, fontSize: 13, color: '#F8FAFC' }}>
            NSE:{cleanSymbol}
          </span>
          {freshness.lastPrice !== null && (
            <span style={{ fontSize: 13, fontWeight: 700, color: '#10B981', fontFamily: "'JetBrains Mono', monospace" }}>
              ₹{freshness.lastPrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          )}
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
              padding: '2px 6px',
              borderRadius: 4,
              fontSize: 10,
              fontWeight: 600,
              backgroundColor: freshness.status === 'STREAMING' || freshness.status === 'LIVE'
                ? 'rgba(16, 185, 129, 0.15)'
                : freshness.status === 'FALLBACK_CACHED'
                ? 'rgba(56, 189, 248, 0.15)'
                : freshness.status.includes('REPLAY') || freshness.status.includes('SIMULATED')
                ? 'rgba(239, 68, 68, 0.2)'
                : 'rgba(239, 68, 68, 0.15)',
              color: freshness.status === 'STREAMING' || freshness.status === 'LIVE'
                ? '#34D399'
                : freshness.status === 'FALLBACK_CACHED'
                ? '#38BDF8'
                : freshness.status.includes('REPLAY') || freshness.status.includes('SIMULATED')
                ? '#F87171'
                : '#F87171',
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                backgroundColor: freshness.status === 'STREAMING' || freshness.status === 'LIVE'
                  ? '#10B981'
                  : freshness.status === 'FALLBACK_CACHED'
                  ? '#38BDF8'
                  : freshness.status.includes('REPLAY') || freshness.status.includes('SIMULATED')
                  ? '#EF4444'
                  : '#EF4444',
              }}
            />
            {freshness.status}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 10, color: '#64748B' }}>
          <span className="desktop-only">Source: <strong style={{ color: '#94A3B8' }}>{freshness.source}</strong></span>
          <span style={{ color: '#38BDF8', fontWeight: 500 }}>FinEx Feed</span>
        </div>
      </div>

      {/* Chart Canvas Area */}
      <div
        style={{ width: '100%', flex: 1, minHeight: 0, position: 'relative', overflow: 'hidden' }}
      >
        <div
          ref={chartContainerRef}
          style={{ width: '100%', height: '100%' }}
          aria-label={`Live Chart for ${cleanSymbol}`}
        />
        {noDataAvailable && (
          <div
            data-testid="chart-empty-state"
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'rgba(9, 13, 20, 0.92)',
              backdropFilter: 'blur(3px)',
              zIndex: 5,
              padding: 24,
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: 15, fontWeight: 600, color: '#F1F5F9', marginBottom: 6 }}>
              No market data available for this symbol
            </div>
            <div style={{ fontSize: 12, color: '#94A3B8', maxWidth: 360, lineHeight: 1.5 }}>
              Market data is currently offline. No cached or live candles exist for {cleanSymbol}.
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
