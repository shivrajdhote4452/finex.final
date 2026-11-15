import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

interface MarketQuote {
  symbol: string;
  name: string;
  price: number;
  changeVal: number;
  changePct: number;
  isPositive: boolean;
  high: number;
  low: number;
  volume: string;
  source?: string;
  observedAt?: string;
  isDelayed?: boolean;
  isStale?: boolean;
  isPriceUnavailable?: boolean;
  isChangeUnavailable?: boolean;
  isHighLowUnavailable?: boolean;
}

/**
 * Mirroring the exact quote transformation and UI display logic in ChartWorkspaceScreen.tsx
 */
function processQuoteResponse(
  q: any,
  cleanSelectedSymbol: string,
  prevQuote: MarketQuote | null
): MarketQuote | null {
  const cleanQSymbol = (q.symbol || '').replace('.NS', '').replace('NSE:', '').trim();
  if (cleanQSymbol !== cleanSelectedSymbol) {
    return null; // Discard stale or mismatched symbol response
  }

  const hasPrice = q.price !== undefined && q.price !== null && !isNaN(Number(q.price)) && Number(q.price) > 0;
  const p = hasPrice ? (typeof q.price === 'string' ? parseFloat(q.price) : Number(q.price)) : 0;

  const hasChg = q.change !== undefined && q.change !== null && !isNaN(Number(q.change));
  const hasChgPct = q.change_pct !== undefined && q.change_pct !== null && !isNaN(Number(q.change_pct));
  const isChangeMissing = !hasChg || !hasChgPct;
  const chg = hasChg ? Number(q.change) : 0;
  const chgPct = hasChgPct ? Number(q.change_pct) : 0;

  const hasHigh = q.high_price !== undefined && q.high_price !== null && !isNaN(Number(q.high_price)) && Number(q.high_price) > 0;
  const hasLow = q.low_price !== undefined && q.low_price !== null && !isNaN(Number(q.low_price)) && Number(q.low_price) > 0;
  const isHighLowMissing = !hasHigh || !hasLow;
  const high = hasHigh ? Number(q.high_price) : 0;
  const low = hasLow ? Number(q.low_price) : 0;

  const vol = q.volume !== undefined && q.volume !== null && Number(q.volume) > 0
    ? `${(Number(q.volume) / 1e6).toFixed(1)}M`
    : '—';

  return {
    symbol: cleanQSymbol,
    name: q.canonical_id || q.symbol,
    price: hasPrice ? p : (prevQuote?.price ?? 0),
    changeVal: !isChangeMissing ? chg : (prevQuote?.changeVal ?? 0),
    changePct: !isChangeMissing ? chgPct : (prevQuote?.changePct ?? 0),
    isPositive: !isChangeMissing ? chg >= 0 : (prevQuote?.isPositive ?? false),
    high: hasHigh ? high : (prevQuote?.high ?? 0),
    low: hasLow ? low : (prevQuote?.low ?? 0),
    volume: vol !== '—' ? vol : (prevQuote?.volume || '—'),
    source: q.source || prevQuote?.source,
    observedAt: q.observed_at || prevQuote?.observedAt,
    isDelayed: q.is_delayed ?? prevQuote?.isDelayed,
    isStale: q.is_stale ?? prevQuote?.isStale,
    isPriceUnavailable: !hasPrice && (prevQuote?.isPriceUnavailable ?? true),
    isChangeUnavailable: isChangeMissing && (prevQuote?.isChangeUnavailable ?? true),
    isHighLowUnavailable: isHighLowMissing && (prevQuote?.isHighLowUnavailable ?? true),
  };
}

function renderPriceDisplay(quote: MarketQuote, currency: string = 'INR'): { priceText: string; changeText: string; changeClass: string } {
  const priceText = !quote.isPriceUnavailable && quote.price > 0
    ? `${currency === 'USD' ? '$' : '₹'}${quote.price.toFixed(2)}`
    : '—';

  let changeText = '—';
  let changeClass = 'neutral';

  if (!quote.isChangeUnavailable) {
    if (quote.changeVal === 0) {
      changeText = '0.00 (0.00%)';
      changeClass = 'neutral';
    } else if (quote.changeVal > 0) {
      changeText = `+${quote.changeVal.toFixed(2)} (+${quote.changePct.toFixed(2)}%)`;
      changeClass = 'positive';
    } else {
      changeText = `${quote.changeVal.toFixed(2)} (${quote.changePct.toFixed(2)}%)`;
      changeClass = 'negative';
    }
  }

  return { priceText, changeText, changeClass };
}

describe('Chart Workspace Quotes & Symbol Switching Suite', () => {
  it('1. Missing price, change, and high/low are marked unavailable and display neutral "—"', () => {
    const rawQuote = {
      symbol: 'RELIANCE',
      price: null,
      change: null,
      change_pct: null,
      high_price: null,
      low_price: null,
      volume: null,
    };

    const quote = processQuoteResponse(rawQuote, 'RELIANCE', null);
    assert.ok(quote);
    assert.equal(quote.isPriceUnavailable, true, 'Price must be flagged as unavailable');
    assert.equal(quote.isChangeUnavailable, true, 'Change must be flagged as unavailable');
    assert.equal(quote.isHighLowUnavailable, true, 'High/Low must be flagged as unavailable');

    const display = renderPriceDisplay(quote);
    assert.equal(display.priceText, '—', 'Missing price must render as "—", not 0');
    assert.equal(display.changeText, '—', 'Missing change must render as "—", not 0.00%');
    assert.equal(display.changeClass, 'neutral');
  });

  it('2. Legitimate zero change (0.00 / 0.00%) is preserved and displayed as genuine zero, not unavailable', () => {
    const rawQuote = {
      symbol: 'TCS',
      price: 3500.0,
      change: 0.0,
      change_pct: 0.0,
      high_price: 3520.0,
      low_price: 3480.0,
      volume: 1200000,
    };

    const quote = processQuoteResponse(rawQuote, 'TCS', null);
    assert.ok(quote);
    assert.equal(quote.isPriceUnavailable, false);
    assert.equal(quote.isChangeUnavailable, false, 'Legitimate 0 change must NOT be flagged as unavailable');
    assert.equal(quote.changeVal, 0.0);
    assert.equal(quote.changePct, 0.0);

    const display = renderPriceDisplay(quote);
    assert.equal(display.priceText, '₹3500.00');
    assert.equal(display.changeText, '0.00 (0.00%)', 'Legitimate zero change must render as "0.00 (0.00%)"');
    assert.equal(display.changeClass, 'neutral');
  });

  it('3. Genuine positive and negative changes render with correct sign and color class', () => {
    const positiveQuote = processQuoteResponse(
      { symbol: 'INFY', price: 1600.0, change: 24.5, change_pct: 1.55, high_price: 1610, low_price: 1580, volume: 500000 },
      'INFY',
      null
    );
    assert.ok(positiveQuote);
    const posDisplay = renderPriceDisplay(positiveQuote);
    assert.equal(posDisplay.priceText, '₹1600.00');
    assert.equal(posDisplay.changeText, '+24.50 (+1.55%)');
    assert.equal(posDisplay.changeClass, 'positive');

    const negativeQuote = processQuoteResponse(
      { symbol: 'INFY', price: 1580.0, change: -20.0, change_pct: -1.25, high_price: 1610, low_price: 1575, volume: 600000 },
      'INFY',
      null
    );
    assert.ok(negativeQuote);
    const negDisplay = renderPriceDisplay(negativeQuote);
    assert.equal(negDisplay.priceText, '₹1580.00');
    assert.equal(negDisplay.changeText, '-20.00 (-1.25%)');
    assert.equal(negDisplay.changeClass, 'negative');
  });

  it('4. Switching symbols immediately rejects stale responses from previous symbol', () => {
    // Current symbol in workspace is TCS, but an async response for previous symbol RELIANCE arrives
    const staleResponse = {
      symbol: 'RELIANCE',
      price: 2600.0,
      change: 15.0,
      change_pct: 0.58,
    };

    const quote = processQuoteResponse(staleResponse, 'TCS', null);
    assert.equal(quote, null, 'Response for RELIANCE must be discarded when selectedSymbol is TCS');
  });

  it('5. Switching symbol isolates active quote state and displays placeholder until new quote loads', () => {
    const previousSymbolQuote: MarketQuote = {
      symbol: 'RELIANCE',
      name: 'Reliance Industries',
      price: 2500.0,
      changeVal: 15.0,
      changePct: 0.6,
      isPositive: true,
      high: 2520,
      low: 2480,
      volume: '3.2M',
    };

    // User switches to WIPRO; activeQuote is cleared (null) or symbol checked
    const cleanSelectedSymbol = 'WIPRO';
    const matchingActiveQuote = previousSymbolQuote.symbol === cleanSelectedSymbol ? previousSymbolQuote : null;
    assert.equal(matchingActiveQuote, null, 'Active quote from previous symbol must not match newly selected symbol');

    const defaultQuote: MarketQuote = {
      symbol: cleanSelectedSymbol,
      name: cleanSelectedSymbol,
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

    const display = renderPriceDisplay(defaultQuote);
    assert.equal(display.priceText, '—', 'New symbol must show "—" until quote arrives');
    assert.equal(display.changeText, '—');
  });
});

