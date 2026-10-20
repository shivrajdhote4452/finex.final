import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi } from 'lightweight-charts';

interface FinExLiveChartProps {
  symbol: string;
  height?: number;
  interval?: string;
  rangePreset?: string;
  onPriceUpdate?: (price: number) => void;
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
      timeScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
        timeVisible: true,
        secondsVisible: false,
        barSpacing: 8,
        minBarSpacing: 4,
        rightOffset: 5,
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

    // 2. Fetch Historical Candles
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
        const response = await fetch(`/api/v1/market/history/${cleanSymbol}?interval=${interval}&days=${fetchDays}`);
        if (!response.ok) return;

        const resJson = await response.json();
        const payload = resJson.data || resJson;
        const candles = payload.candles || payload.bars || [];

        if (candles.length > 0 && seriesRef.current) {
          // Deduplicate and sort by ascending time
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
          setFreshness((prev) => ({
            ...prev,
            status: payload.freshness || 'LIVE',
            source: payload.source || 'ANGEL_ONE_SMARTAPI',
            asOf: payload.observed_at || new Date().toLocaleTimeString(),
            lastPrice: last ? last.close : prev.lastPrice,
          }));

          if (last && onPriceUpdate) {
            onPriceUpdate(last.close);
          }
        }
      } catch (err) {
        console.warn(`Historical candles fetch error for ${cleanSymbol}:`, err);
      }
    };

    fetchHistory();

    // 3. Connect to WebSocket Tick Stream
    let wsHost = window.location.host;
    let wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const envApiUrl = (import.meta as any).env?.VITE_API_URL;
    if (envApiUrl && envApiUrl.startsWith('http')) {
      try {
        const parsed = new URL(envApiUrl);
        wsHost = parsed.host;
        wsProtocol = parsed.protocol === 'https:' ? 'wss:' : 'ws:';
      } catch {
        // fallback to default
      }
    } else if (window.location.port === '3000') {
      wsHost = `${window.location.hostname}:8000`;
    }
    const wsUrl = `${wsProtocol}//${wsHost}/api/v1/market/ws/${cleanSymbol}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
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

          if (seriesRef.current && !isNaN(closePrice)) {
            seriesRef.current.update({
              time: barTime as any,
              open: Number(tick.open || closePrice),
              high: Math.max(Number(tick.high || closePrice), closePrice),
              low: Math.min(Number(tick.low || closePrice), closePrice),
              close: closePrice,
            });
            chartInstanceRef.current?.timeScale().scrollToPosition(3, false);
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
        console.warn(`WebSocket error on ${cleanSymbol}:`, e);
        setFreshness((prev) => ({ ...prev, status: 'FALLBACK_CACHED' }));
      };

      ws.onclose = () => {
        setFreshness((prev) => ({ ...prev, status: 'DISCONNECTED' }));
      };
    } catch (wsErr) {
      console.warn('WebSocket setup exception:', wsErr);
    }

    return () => {
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
          padding: '8px 16px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
          backgroundColor: '#0F172A',
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontWeight: 700, fontSize: 14, color: '#F8FAFC' }}>
            NSE:{cleanSymbol}
          </span>
          {freshness.lastPrice !== null && (
            <span style={{ fontSize: 14, fontWeight: 600, color: '#10B981' }}>
              ₹{freshness.lastPrice.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </span>
          )}
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
              padding: '2px 8px',
              borderRadius: 4,
              fontSize: 11,
              fontWeight: 600,
              backgroundColor: freshness.status === 'STREAMING' || freshness.status === 'LIVE' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
              color: freshness.status === 'STREAMING' || freshness.status === 'LIVE' ? '#34D399' : '#F87171',
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                backgroundColor: freshness.status === 'STREAMING' || freshness.status === 'LIVE' ? '#10B981' : '#EF4444',
              }}
            />
            {freshness.status}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 14, fontSize: 11, color: '#64748B' }}>
          <span>Source: <strong style={{ color: '#94A3B8' }}>{freshness.source}</strong></span>
          {freshness.asOf && <span>As of: {freshness.asOf}</span>}
          <span style={{ color: '#38BDF8', fontWeight: 500 }}>FinEx Live Feed (2s Poll)</span>
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
