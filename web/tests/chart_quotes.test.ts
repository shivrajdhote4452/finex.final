import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  cleanSymbol,
  createDefaultQuote,
  parseRawQuote,
  formatQuotePrice,
  formatQuoteChange,
  formatQuoteHighLow,
  calculateRangeSliderWidth,
  getFeedStatusBadge,
} from '../src/domain/chartQuoteProcessing.ts';
import type { MarketQuote } from '../src/context/FinancialContext.ts';

/**
 * Chart Workspace Quotes & Market Data Processing Suite.
 *
 * This test suite directly exercises the production quote handling functions in
 * `web/src/domain/chartQuoteProcessing.ts` (used by `web/src/pages/ChartWorkspaceScreen.tsx`).
 */

describe('Chart Workspace Quotes (Actual Production Logic)', () => {
  it('1. Missing price, change, and high/low are marked unavailable and display neutral "—"', () => {
    // Backend returns raw quote with missing change and missing high/low
    const rawQuoteMissing = {
      symbol: 'RELIANCE',
      price: null,
      change: undefined,
      change_pct: null,
      high_price: null,
      low_price: null,
      volume: null,
    };

    const parsed = parseRawQuote(rawQuoteMissing, 'RELIANCE');
    assert.ok(parsed, 'Quote for matching symbol must be parsed');
    assert.equal(parsed.isPriceUnavailable, true, 'Price must be flagged as unavailable');
    assert.equal(parsed.isChangeUnavailable, true, 'Change must be flagged as unavailable');
    assert.equal(parsed.isHighLowUnavailable, true, 'High/low must be flagged as unavailable');

    // Display formatting
    const priceText = formatQuotePrice(parsed);
    assert.equal(priceText, '—', 'Missing price must render as neutral "—", NOT 0 or ₹0.00');

    const changeFormatted = formatQuoteChange(parsed);
    assert.equal(changeFormatted.text, '—', 'Missing change must render as neutral "—"');
    assert.equal(changeFormatted.isUnavailable, true);
    assert.equal(changeFormatted.color, '#8E8E93', 'Must use neutral grey color');

    const highText = formatQuoteHighLow(parsed.high, parsed.isHighLowUnavailable);
    assert.equal(highText, '—', 'Missing high must render as "—"');

    const lowText = formatQuoteHighLow(parsed.low, parsed.isHighLowUnavailable);
    assert.equal(lowText, '—', 'Missing low must render as "—"');

    const sliderWidth = calculateRangeSliderWidth(
      parsed.price,
      parsed.high,
      parsed.low,
      parsed.isPriceUnavailable,
      parsed.isHighLowUnavailable
    );
    assert.equal(sliderWidth, '0%', 'Slider width must be 0% when range is unavailable');
  });

  it('2. Legitimate zero change (0.00 / 0.00%) is preserved and displayed as genuine zero, not unavailable', () => {
    // Valid unchanged trading session (0.00 change)
    const rawUnchanged = {
      symbol: 'TCS',
      price: 3450.5,
      change: 0.0,
      change_pct: 0.0,
      high_price: 3460.0,
      low_price: 3440.0,
      volume: 1200000,
    };

    const parsed = parseRawQuote(rawUnchanged, 'TCS');
    assert.ok(parsed);
    assert.equal(parsed.price, 3450.5);
    assert.equal(parsed.isPriceUnavailable, false);
    assert.equal(parsed.isChangeUnavailable, false, 'Genuine zero change must NOT be flagged as unavailable');
    assert.equal(parsed.changeVal, 0);
    assert.equal(parsed.changePct, 0);

    const changeFormatted = formatQuoteChange(parsed);
    assert.equal(changeFormatted.isZero, true);
    assert.equal(changeFormatted.isUnavailable, false);
    assert.equal(changeFormatted.text, '0.00 (0.00%)', 'Must display exact 0.00 (0.00%) format');
    assert.equal(changeFormatted.color, '#8E8E93', 'Zero change must use neutral grey (#8E8E93), not green or red');
  });

  it('3. Genuine positive and negative changes render with correct sign and color class', () => {
    // Positive change
    const positiveQuote: MarketQuote = {
      symbol: 'INFY',
      name: 'Infosys Limited',
      price: 1520.0,
      changeVal: 15.25,
      changePct: 1.01,
      isPositive: true,
      high: 1530.0,
      low: 1500.0,
      volume: '2.5M',
      isPriceUnavailable: false,
      isChangeUnavailable: false,
      isHighLowUnavailable: false,
    };

    const posFormatted = formatQuoteChange(positiveQuote);
    assert.equal(posFormatted.valFormatted, '+15.25');
    assert.equal(posFormatted.pctFormatted, '+1.01%');
    assert.equal(posFormatted.text, '+15.25 (+1.01%)');
    assert.equal(posFormatted.color, '#26A69A', 'Positive change must use green (#26A69A)');

    // Negative change
    const negativeQuote: MarketQuote = {
      symbol: 'HDFCBANK',
      name: 'HDFC Bank Limited',
      price: 1650.0,
      changeVal: -22.5,
      changePct: -1.35,
      isPositive: false,
      high: 1680.0,
      low: 1640.0,
      volume: '4.1M',
      isPriceUnavailable: false,
      isChangeUnavailable: false,
      isHighLowUnavailable: false,
    };

    const negFormatted = formatQuoteChange(negativeQuote);
    assert.equal(negFormatted.valFormatted, '-22.50');
    assert.equal(negFormatted.pctFormatted, '-1.35%');
    assert.equal(negFormatted.text, '-22.50 (-1.35%)');
    assert.equal(negFormatted.color, '#EF5350', 'Negative change must use red (#EF5350)');
  });

  it('4. Switching symbols immediately rejects stale responses from previous symbol', () => {
    // Current selected symbol is TCS, but an async response for previous symbol RELIANCE arrives
    const staleResponse = {
      symbol: 'RELIANCE',
      price: 2600.0,
      change: 12.0,
      change_pct: 0.46,
    };

    const targetSymbol = 'TCS';
    const result = parseRawQuote(staleResponse, targetSymbol);

    assert.equal(result, null, 'Must return null and discard response for non-selected symbol');

    // Now test response for active symbol TCS with .NS suffix
    const validResponse = {
      symbol: 'TCS.NS',
      price: 3450.0,
      change: -10.0,
      change_pct: -0.29,
    };
    const validResult = parseRawQuote(validResponse, targetSymbol);
    assert.ok(validResult, 'Must accept matching symbol regardless of .NS suffix');
    assert.equal(validResult?.symbol, 'TCS');
    assert.equal(validResult?.price, 3450.0);
  });

  it('5. Switching symbol isolates active quote state and displays placeholder until new quote loads', () => {
    const defaultPlaceholder = createDefaultQuote('INFY');

    assert.equal(defaultPlaceholder.symbol, 'INFY');
    assert.equal(defaultPlaceholder.price, 0);
    assert.equal(defaultPlaceholder.isPriceUnavailable, true);
    assert.equal(defaultPlaceholder.isChangeUnavailable, true);
    assert.equal(defaultPlaceholder.isHighLowUnavailable, true);
    assert.equal(formatQuotePrice(defaultPlaceholder), '—');
    assert.equal(formatQuoteChange(defaultPlaceholder).text, '—');
  });

  it('6. Feed status badge accurately reflects stale cache, delayed feed, live NSE, and replay modes', () => {
    const baseQuote: MarketQuote = {
      symbol: 'RELIANCE',
      name: 'Reliance',
      price: 2500,
      changeVal: 10,
      changePct: 0.4,
      isPositive: true,
      high: 2520,
      low: 2480,
      volume: '1.2M',
    };

    // Stale offline cache
    const staleBadge = getFeedStatusBadge({ ...baseQuote, isStale: true });
    assert.equal(staleBadge.label, 'Market Offline (Stale Cache)');
    assert.equal(staleBadge.dotColor, '#8E8E93');

    // Delayed feed
    const delayedBadge = getFeedStatusBadge({ ...baseQuote, isDelayed: true });
    assert.equal(delayedBadge.label, 'Delayed Feed');
    assert.equal(delayedBadge.dotColor, '#F29A60');

    // Indian live data
    const liveBadge = getFeedStatusBadge(baseQuote, { mode: 'INDIAN_LIVE_DATA', feed_label: 'Angel One SmartAPI (Live NSE Feed)' });
    assert.equal(liveBadge.label, 'Angel One SmartAPI (Live NSE Feed)');
    assert.equal(liveBadge.dotColor, '#26A69A');

    // Replay mode with educational lag
    const replayBadge = getFeedStatusBadge(baseQuote, { mode: 'INDIAN_OFFLINE_EDUCATIONAL', sebi_educational_lag_days: 45 });
    assert.equal(replayBadge.label, 'NSE Historical Replay (45D Lag)');
    assert.equal(replayBadge.dotColor, '#F29A60');
  });

  it('7. Today\'s range slider width calculation conforms to boundaries', () => {
    // Normal range
    const widthMid = calculateRangeSliderWidth(2500, 2600, 2400, false, false);
    assert.equal(widthMid, '50%');

    // At low boundary (clamps to min 5%)
    const widthLow = calculateRangeSliderWidth(2400, 2600, 2400, false, false);
    assert.equal(widthLow, '5%');

    // At high boundary (clamps to max 100%)
    const widthHigh = calculateRangeSliderWidth(2600, 2600, 2400, false, false);
    assert.equal(widthHigh, '100%');

    // Inverted or invalid high/low
    const widthInvalid = calculateRangeSliderWidth(2500, 2400, 2600, false, false);
    assert.equal(widthInvalid, '0%');
  });
});
