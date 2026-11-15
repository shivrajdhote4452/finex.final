import type { MarketQuote } from '../context/FinancialContext.ts';

/**
 * Normalizes symbols by removing NSE exchange prefixes/suffixes.
 */
export function cleanSymbol(symbol: string): string {
  if (!symbol) return '';
  return symbol.replace('.NS', '').replace('NSE:', '').trim();
}

/**
 * Creates a neutral initial placeholder quote for a given symbol.
 * Does not fabricate non-zero prices, fake changes, or artificial high/lows.
 */
export function createDefaultQuote(symbol: string): MarketQuote {
  const clean = cleanSymbol(symbol);
  return {
    symbol: clean,
    name: clean,
    price: 0,
    changeVal: 0,
    changePct: 0,
    isPositive: false,
    high: 0,
    low: 0,
    volume: '—',
    isPriceUnavailable: true,
    isChangeUnavailable: true,
    isHighLowUnavailable: true,
  };
}

/**
 * Processes a raw market quote response from the backend.
 * Returns null if the response belongs to a stale or mismatched symbol.
 */
export function parseRawQuote(
  raw: any,
  targetSymbol: string,
  prevQuote?: MarketQuote | null
): MarketQuote | null {
  if (!raw) return null;

  const targetClean = cleanSymbol(targetSymbol);
  const rawClean = cleanSymbol(raw.symbol || '');

  // Strict symbol isolation: discard responses for any symbol other than the currently active symbol
  if (rawClean !== targetClean) {
    return null;
  }

  const hasPrice = raw.price !== undefined && raw.price !== null && !isNaN(Number(raw.price)) && Number(raw.price) > 0;
  const p = hasPrice ? (typeof raw.price === 'string' ? parseFloat(raw.price) : Number(raw.price)) : 0;

  const hasChg = raw.change !== undefined && raw.change !== null && !isNaN(Number(raw.change));
  const hasChgPct = raw.change_pct !== undefined && raw.change_pct !== null && !isNaN(Number(raw.change_pct));
  const isChangeMissing = !hasChg || !hasChgPct;
  const chg = hasChg ? Number(raw.change) : 0;
  const chgPct = hasChgPct ? Number(raw.change_pct) : 0;

  const hasHigh = raw.high_price !== undefined && raw.high_price !== null && !isNaN(Number(raw.high_price)) && Number(raw.high_price) > 0;
  const hasLow = raw.low_price !== undefined && raw.low_price !== null && !isNaN(Number(raw.low_price)) && Number(raw.low_price) > 0;
  const isHighLowMissing = !hasHigh || !hasLow;
  const high = hasHigh ? Number(raw.high_price) : 0;
  const low = hasLow ? Number(raw.low_price) : 0;

  const vol = raw.volume !== undefined && raw.volume !== null && Number(raw.volume) > 0
    ? `${(Number(raw.volume) / 1e6).toFixed(1)}M`
    : '—';

  return {
    symbol: targetClean,
    name: raw.canonical_id || raw.symbol || targetClean,
    price: hasPrice ? p : (prevQuote?.price ?? 0),
    changeVal: !isChangeMissing ? chg : (prevQuote?.changeVal ?? 0),
    changePct: !isChangeMissing ? chgPct : (prevQuote?.changePct ?? 0),
    isPositive: !isChangeMissing ? chg >= 0 : (prevQuote?.isPositive ?? false),
    high: hasHigh ? high : (prevQuote?.high ?? 0),
    low: hasLow ? low : (prevQuote?.low ?? 0),
    volume: vol !== '—' ? vol : (prevQuote?.volume || '—'),
    source: raw.source || prevQuote?.source,
    observedAt: raw.observed_at || prevQuote?.observedAt,
    isDelayed: raw.is_delayed ?? prevQuote?.isDelayed,
    isStale: raw.is_stale ?? prevQuote?.isStale,
    isPriceUnavailable: !hasPrice && (prevQuote?.isPriceUnavailable ?? true),
    isChangeUnavailable: isChangeMissing && (prevQuote?.isChangeUnavailable ?? true),
    isHighLowUnavailable: isHighLowMissing && (prevQuote?.isHighLowUnavailable ?? true),
  };
}

/**
 * Formats the live price for display, rendering '—' when price is missing or unavailable.
 */
export function formatQuotePrice(quote: MarketQuote, currencySymbol: string = '₹'): string {
  if (quote.isPriceUnavailable || quote.price <= 0) {
    return '—';
  }
  return `${currencySymbol}${quote.price.toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

/**
 * Formats price change and percentage change.
 * Distinguishes genuine zero changes from missing values.
 */
export function formatQuoteChange(quote: MarketQuote): {
  text: string;
  fullText: string;
  isZero: boolean;
  isUnavailable: boolean;
  color: string;
  valFormatted: string;
  pctFormatted: string;
} {
  if (quote.isChangeUnavailable) {
    return {
      text: '—',
      fullText: '—',
      isZero: false,
      isUnavailable: true,
      color: '#8E8E93',
      valFormatted: '—',
      pctFormatted: '—',
    };
  }

  if (quote.changeVal === 0) {
    return {
      text: '0.00 (0.00%)',
      fullText: '0.00 (0.00%)',
      isZero: true,
      isUnavailable: false,
      color: '#8E8E93',
      valFormatted: '0.00',
      pctFormatted: '0.00%',
    };
  }

  const isPos = quote.changeVal > 0;
  const sign = isPos ? '+' : '';
  const valFormatted = `${sign}${quote.changeVal.toFixed(2)}`;
  const pctFormatted = `${sign}${quote.changePct.toFixed(2)}%`;
  const color = isPos ? '#26A69A' : '#EF5350';

  return {
    text: `${valFormatted} (${pctFormatted})`,
    fullText: `${valFormatted} (${pctFormatted})`,
    isZero: false,
    isUnavailable: false,
    color,
    valFormatted,
    pctFormatted,
  };
}

/**
 * Formats today's high or low price, rendering '—' when unavailable.
 */
export function formatQuoteHighLow(val: number, isUnavailable?: boolean, currencySymbol: string = '₹'): string {
  if (isUnavailable || val <= 0) {
    return '—';
  }
  return `${currencySymbol}${val.toFixed(2)}`;
}

/**
 * Calculates the width percentage of the day's range slider.
 */
export function calculateRangeSliderWidth(
  price: number,
  high: number,
  low: number,
  isPriceUnavailable?: boolean,
  isHighLowUnavailable?: boolean
): string {
  if (isPriceUnavailable || isHighLowUnavailable || high <= low || low <= 0) {
    return '0%';
  }
  const pct = Math.min(100, Math.max(5, ((price - low) / (high - low)) * 100));
  return `${pct}%`;
}

/**
 * Generates badge label and color information for live/feed status.
 */
export function getFeedStatusBadge(
  quote: MarketQuote,
  marketMode?: any
): { label: string; dotColor: string; textColor: string } {
  if (quote.isStale) {
    return {
      label: 'Market Offline (Stale Cache)',
      dotColor: '#8E8E93',
      textColor: '#8E8E93',
    };
  }

  if (quote.isDelayed) {
    return {
      label: 'Delayed Feed',
      dotColor: '#F29A60',
      textColor: '#F29A60',
    };
  }

  const mode = marketMode?.mode;
  if (mode === 'INDIAN_LIVE_DATA') {
    return {
      label: marketMode?.feed_label || 'Angel One SmartAPI (Live NSE Feed)',
      dotColor: '#26A69A',
      textColor: '#26A69A',
    };
  }

  if (mode && typeof mode === 'string' && mode.includes('US')) {
    return {
      label: 'Live IEX (USD Paper)',
      dotColor: '#26A69A',
      textColor: '#26A69A',
    };
  }

  const lagDays = marketMode?.sebi_educational_lag_days || marketMode?.lag_days || 30;
  return {
    label: `NSE Historical Replay (${lagDays}D Lag)`,
    dotColor: '#F29A60',
    textColor: '#8E8E93',
  };
}
