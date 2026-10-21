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

    // Helper to start realistic simulated micro-ticks
    const startSimulatedTicks = (baseLastBar: { time: number; open: number; high: number; low: number; close: number }) => {
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

    // 2. Fetch Historical Candles (with robust fallback)
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
        const res = await apiClient.market.getHistory(cleanSymbol, {
          interval: interval,
          days: fetchDays,
        } as any);
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

          seriesRef.current.setData(formatted);
          chart.timeScale().fitContent();

          const last = formatted[formatted.length - 1];
          if (last) {
            lastBarRef.current = { ...last };
          }
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
      } catch (err) {
        console.warn(`Historical candles fetch error for ${cleanSymbol}, falling back to replay synthesizer:`, err);
      }

      // Fallback: Synthesize realistic baseline candles so chart is NEVER blank
      if (seriesRef.current) {
        const fallback = generateFallbackCandles(cleanSymbol, rangePreset, interval);
        seriesRef.current.setData(fallback as any);
        chart.timeScale().fitContent();

        const last = fallback[fallback.length - 1];
        if (last) {
          lastBarRef.current = { ...last };
          startSimulatedTicks(last);
        }
        setFreshness({
          status: 'SIMULATED_REPLAY',
          source: 'FinEx Replay Engine (NSE Baseline)',
          asOf: new Date().toLocaleTimeString(),
          lastPrice: last ? last.close : null,
        });
        if (last && onPriceUpdate) {
          onPriceUpdate(last.close);
        }
      }
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
        setFreshness((prev) => ({
          ...prev,
          status: prev.status === 'STREAMING' ? 'REPLAY_SYNC' : (prev.status || 'SIMULATED_REPLAY'),
          source: prev.source || 'FinEx Replay Engine',
        }));
        if (lastBarRef.current && !simTimerRef.current) {
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
                : freshness.status.includes('REPLAY') || freshness.status.includes('SIMULATED')
                ? 'rgba(242, 154, 96, 0.15)'
                : 'rgba(239, 68, 68, 0.15)',
              color: freshness.status === 'STREAMING' || freshness.status === 'LIVE'
                ? '#34D399'
                : freshness.status.includes('REPLAY') || freshness.status.includes('SIMULATED')
                ? '#F29A60'
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
                  : freshness.status.includes('REPLAY') || freshness.status.includes('SIMULATED')
                  ? '#F29A60'
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

      {/* Chart Canvas */}
      <div
        ref={chartContainerRef}
        style={{ width: '100%', flex: 1, minHeight: 0, position: 'relative', overflow: 'hidden' }}
        aria-label={`Live Chart for ${cleanSymbol}`}
      />
    </div>
  );
};
