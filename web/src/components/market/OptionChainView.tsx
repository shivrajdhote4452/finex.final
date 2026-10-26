import React, { useState, useEffect } from 'react';
import { apiClient, OptionChainData, OptionContractData, StrikeRowData } from '../../api/client';
import { TableSkeleton } from '../common/Skeleton';

interface OptionChainViewProps {
  onOpenTrade: (contract: OptionContractData, spot: number) => void;
  defaultUnderlying?: string;
}

export const OptionChainView: React.FC<OptionChainViewProps> = ({
  onOpenTrade,
  defaultUnderlying = 'NIFTY 50',
}) => {
  const [underlyings, setUnderlyings] = useState<string[]>([
    'NIFTY 50',
    'NIFTY BANK',
    'FINNIFTY',
    'RELIANCE',
    'TCS',
    'INFY',
    'HDFCBANK',
    'ICICIBANK',
    'TATAMOTORS',
    'SBIN',
    'BHARTIARTL',
  ]);
  const [selectedUnderlying, setSelectedUnderlying] = useState<string>(defaultUnderlying);
  const [selectedExpiry, setSelectedExpiry] = useState<string>('');
  const [chainData, setChainData] = useState<OptionChainData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [strikeFilter, setStrikeFilter] = useState<'ALL' | 'NEAR_ATM'>('NEAR_ATM');

  // Load supported F&O underlyings from API
  useEffect(() => {
    let active = true;
    apiClient.market
      .getOptionUnderlyings()
      .then((res) => {
        if (active && res?.underlyings && res.underlyings.length > 0) {
          setUnderlyings(res.underlyings.map((u) => u.symbol));
        }
      })
      .catch((err) => {
        console.warn('Failed to fetch option underlyings, using verified defaults:', err);
      });
    return () => {
      active = false;
    };
  }, []);

  // Fetch option chain whenever underlying or expiry changes
  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setErrorMessage(null);

    apiClient.market
      .getOptionChain(selectedUnderlying, selectedExpiry || undefined)
      .then((data) => {
        if (!active) return;
        setChainData(data);
        if (!selectedExpiry && data.selected_expiry) {
          setSelectedExpiry(data.selected_expiry);
        }
      })
      .catch((err: any) => {
        if (!active) return;
        console.error('Option chain fetch error:', err);
        const msg =
          err?.details?.message ||
          err?.message ||
          `Option chain unavailable for ${selectedUnderlying}. FinEx only serves verified NSE F&O contracts.`;
        setErrorMessage(msg);
        setChainData(null);
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [selectedUnderlying, selectedExpiry]);

  // Handle underlying change
  const handleUnderlyingChange = (und: string) => {
    setSelectedUnderlying(und);
    setSelectedExpiry(''); // Reset expiry to fetch default near expiry
  };

  const spot = chainData?.spot_price || 0;
  const atm = chainData?.atm_strike || 0;

  // Filter strikes if NEAR_ATM is selected (e.g. 10 strikes above and below ATM)
  const displayStrikes: StrikeRowData[] = React.useMemo(() => {
    if (!chainData?.strikes) return [];
    if (strikeFilter === 'ALL') return chainData.strikes;

    const strikes = chainData.strikes;
    const atmIndex = strikes.findIndex((s) => s.strike_price >= atm);
    const startIdx = Math.max(0, atmIndex - 8);
    const endIdx = Math.min(strikes.length, atmIndex + 9);
    return strikes.slice(startIdx, endIdx);
  }, [chainData, strikeFilter, atm]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', width: '100%' }}>
      {/* Top Header & Underlyings Selector */}
      <div
        className="glass-card"
        style={{
          padding: '20px 24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 700,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  color: 'var(--color-action)',
                }}
              >
                NSE Derivatives Trading Floor
              </span>
              <span className="badge badge-neutral" style={{ fontSize: '10px' }}>
                Long-Only Paper Options
              </span>
              {chainData?.served_from_cache && (
                <span className="badge badge-neutral" style={{ fontSize: '10px', color: '#F59E0B', borderColor: 'rgba(245, 158, 11, 0.3)' }}>
                  CACHED REPLAY
                </span>
              )}
            </div>
            <h2 style={{ fontSize: '24px', fontWeight: 700, color: '#FFFFFF', margin: 0 }}>
              Option Chain — {selectedUnderlying}
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
              Real Angel One derivatives chain with deterministic Black-Scholes Greeks. Click any contract to open the pre-filled paper trade ticket.
            </p>
          </div>

          {/* Underlyings Dropdown / Quick Select */}
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Underlying:</label>
            <select
              value={selectedUnderlying}
              onChange={(e) => handleUnderlyingChange(e.target.value)}
              style={{
                backgroundColor: 'var(--bg-input)',
                border: '1px solid var(--border-medium)',
                color: '#FFFFFF',
                borderRadius: 'var(--radius-sm)',
                padding: '8px 12px',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <optgroup label="Index Derivatives">
                {underlyings.filter((u) => u.startsWith('NIFTY') || u.includes('FIN')).map((u) => (
                  <option key={u} value={u}>
                    {u}
                  </option>
                ))}
              </optgroup>
              <optgroup label="Stock Derivatives">
                {underlyings.filter((u) => !u.startsWith('NIFTY') && !u.includes('FIN')).map((u) => (
                  <option key={u} value={u}>
                    {u}
                  </option>
                ))}
              </optgroup>
            </select>
          </div>
        </div>

        {/* Quick Underlying Pill Buttons */}
        <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '4px' }}>
          {['NIFTY 50', 'NIFTY BANK', 'FINNIFTY', 'RELIANCE', 'TCS', 'HDFCBANK'].map((u) => (
            <button
              key={u}
              onClick={() => handleUnderlyingChange(u)}
              style={{
                padding: '6px 12px',
                borderRadius: 'var(--radius-xs)',
                fontSize: '12px',
                fontWeight: selectedUnderlying === u ? 700 : 500,
                backgroundColor: selectedUnderlying === u ? 'rgba(242, 154, 96, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                border: selectedUnderlying === u ? '1px solid var(--color-action)' : '1px solid var(--border-subtle)',
                color: selectedUnderlying === u ? '#FFFFFF' : 'var(--text-muted)',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              {u}
            </button>
          ))}
        </div>
      </div>

      {/* Error or Honest Unavailable State */}
      {errorMessage && (
        <div
          className="glass-card"
          style={{
            padding: '24px',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            backgroundColor: 'rgba(239, 68, 68, 0.05)',
            display: 'flex',
            alignItems: 'center',
            gap: '14px',
          }}
        >
          <span style={{ fontSize: '24px' }}>🛡️</span>
          <div>
            <h4 style={{ margin: '0 0 4px 0', color: '#FFFFFF', fontSize: '15px' }}>
              Option Chain Data Unavailable
            </h4>
            <p style={{ margin: 0, fontSize: '13px', color: '#FCA5A5' }}>
              {errorMessage}
            </p>
          </div>
        </div>
      )}

      {/* KPI Summary Strip */}
      {chainData && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
            gap: '12px',
          }}
        >
          {/* Underlying Spot */}
          <div className="glass-card" style={{ padding: '14px 18px' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Underlying Spot
            </span>
            <div className="tabular-nums" style={{ fontSize: '20px', fontWeight: 800, color: '#FFFFFF', marginTop: '2px' }}>
              ₹{chainData.spot_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
            <span style={{ fontSize: '11px', color: 'var(--color-profit)' }}>
              Live NSE EOD Spot
            </span>
          </div>

          {/* ATM Strike */}
          <div className="glass-card" style={{ padding: '14px 18px' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              ATM Strike
            </span>
            <div className="tabular-nums" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-action)', marginTop: '2px' }}>
              ₹{chainData.atm_strike.toLocaleString('en-IN')}
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Nearest Step: {chainData.strike_step ? `${chainData.strike_step} pts` : 'Standard Grid'}
            </span>
          </div>

          {/* Expiry Selector Card */}
          <div className="glass-card" style={{ padding: '14px 18px' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Contract Expiry
            </span>
            <select
              value={selectedExpiry}
              onChange={(e) => setSelectedExpiry(e.target.value)}
              style={{
                width: '100%',
                marginTop: '4px',
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid var(--border-medium)',
                color: '#FFFFFF',
                borderRadius: '4px',
                padding: '4px 8px',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              {chainData.expiries.map((exp) => (
                <option key={exp} value={exp}>
                  {exp}
                </option>
              ))}
            </select>
            <span style={{ fontSize: '11px', color: 'var(--color-primary)', display: 'block', marginTop: '4px' }}>
              {chainData.days_to_expiry} days to expiry
            </span>
          </div>

          {/* Put-Call Ratio (PCR) */}
          <div className="glass-card" style={{ padding: '14px 18px' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Put-Call Ratio (PCR)
            </span>
            <div className="tabular-nums" style={{ fontSize: '20px', fontWeight: 800, color: '#FFFFFF', marginTop: '2px' }}>
              {chainData.pcr}
            </div>
            <span style={{ fontSize: '11px', color: chainData.pcr >= 1 ? 'var(--color-profit)' : 'var(--color-loss)' }}>
              {chainData.pcr >= 1.2 ? 'Bullish Sentiment' : chainData.pcr <= 0.8 ? 'Bearish Sentiment' : 'Neutral Range'}
            </span>
          </div>

          {/* Lot Size */}
          <div className="glass-card" style={{ padding: '14px 18px' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              F&O Lot Size
            </span>
            <div className="tabular-nums" style={{ fontSize: '20px', fontWeight: 800, color: '#FFFFFF', marginTop: '2px' }}>
              {chainData.lot_size} units
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              1 Lot Minimum Contract
            </span>
          </div>

          {/* Max Pain */}
          <div className="glass-card" style={{ padding: '14px 18px' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Max Pain Strike
            </span>
            <div className="tabular-nums" style={{ fontSize: '20px', fontWeight: 800, color: '#FFFFFF', marginTop: '2px' }}>
              ₹{chainData.max_pain.toLocaleString('en-IN')}
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-faint)' }}>
              Least loss expiry level
            </span>
          </div>
        </div>
      )}

      {/* Main Option Chain Strike Table */}
      <div className="glass-card" style={{ padding: '20px', width: '100%', boxSizing: 'border-box' }}>
        {/* Table Control Ribbon */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '16px',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#FFFFFF', margin: 0 }}>
              Strikes Ledger
            </h3>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Showing {displayStrikes.length} strikes around spot (₹{spot.toFixed(2)})
            </span>
          </div>

          {/* Strike Filter (Near ATM vs All) */}
          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              onClick={() => setStrikeFilter('NEAR_ATM')}
              style={{
                padding: '4px 10px',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: 600,
                backgroundColor: strikeFilter === 'NEAR_ATM' ? 'var(--color-primary)' : 'rgba(255, 255, 255, 0.05)',
                color: strikeFilter === 'NEAR_ATM' ? '#FFFFFF' : 'var(--text-muted)',
                border: 'none',
                cursor: 'pointer',
              }}
            >
              Near ATM (±8 Strikes)
            </button>
            <button
              onClick={() => setStrikeFilter('ALL')}
              style={{
                padding: '4px 10px',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: 600,
                backgroundColor: strikeFilter === 'ALL' ? 'var(--color-primary)' : 'rgba(255, 255, 255, 0.05)',
                color: strikeFilter === 'ALL' ? '#FFFFFF' : 'var(--text-muted)',
                border: 'none',
                cursor: 'pointer',
              }}
            >
              All Strikes ({chainData?.strikes.length || 0})
            </button>
          </div>
        </div>

        {/* Swipe Hint for Mobile */}
        <div className="table-swipe-hint">← Swipe horizontally to view full Call / Strike / Put matrix →</div>

        {isLoading ? (
          <div style={{ padding: '24px' }}>
            <TableSkeleton rows={8} columns={9} />
          </div>
        ) : !chainData || displayStrikes.length === 0 ? (
          <div style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>
            No active option chain data available for the selected contract.
          </div>
        ) : (
          <div className="table-scroll-wrapper">
            <table
              style={{
                width: '100%',
                minWidth: '940px',
                borderCollapse: 'collapse',
                textAlign: 'center',
                fontSize: '13px',
              }}
            >
              <thead>
                {/* Top Section Header: CALLS vs PUTS */}
                <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <th
                    colSpan={4}
                    style={{
                      padding: '10px',
                      backgroundColor: 'rgba(16, 185, 129, 0.08)',
                      color: 'var(--color-profit)',
                      fontSize: '12px',
                      fontWeight: 700,
                      letterSpacing: '0.05em',
                      borderRight: '1px solid var(--border-subtle)',
                    }}
                  >
                    CALL OPTIONS (CE) — BUY LONG
                  </th>
                  <th
                    style={{
                      padding: '10px',
                      backgroundColor: 'rgba(255, 255, 255, 0.04)',
                      color: '#FFFFFF',
                      fontSize: '12px',
                      fontWeight: 800,
                      letterSpacing: '0.05em',
                      borderRight: '1px solid var(--border-subtle)',
                      borderLeft: '1px solid var(--border-subtle)',
                    }}
                  >
                    STRIKE
                  </th>
                  <th
                    colSpan={4}
                    style={{
                      padding: '10px',
                      backgroundColor: 'rgba(239, 68, 68, 0.08)',
                      color: 'var(--color-loss)',
                      fontSize: '12px',
                      fontWeight: 700,
                      letterSpacing: '0.05em',
                      borderLeft: '1px solid var(--border-subtle)',
                    }}
                  >
                    PUT OPTIONS (PE) — BUY LONG
                  </th>
                </tr>

                {/* Sub-column Headers */}
                <tr
                  style={{
                    borderBottom: '1px solid var(--border-subtle)',
                    color: 'var(--text-faint)',
                    fontSize: '11px',
                    textTransform: 'uppercase',
                  }}
                >
                  {/* Call Columns */}
                  <th style={{ padding: '10px', textAlign: 'left' }}>OI</th>
                  <th style={{ padding: '10px' }}>IV %</th>
                  <th style={{ padding: '10px' }}>LTP Premium</th>
                  <th style={{ padding: '10px', borderRight: '1px solid var(--border-subtle)' }}>Action</th>

                  {/* Center Strike Column */}
                  <th
                    style={{
                      padding: '10px',
                      borderRight: '1px solid var(--border-subtle)',
                      borderLeft: '1px solid var(--border-subtle)',
                      backgroundColor: 'rgba(255, 255, 255, 0.02)',
                    }}
                  >
                    Price (₹)
                  </th>

                  {/* Put Columns */}
                  <th style={{ padding: '10px', borderLeft: '1px solid var(--border-subtle)' }}>Action</th>
                  <th style={{ padding: '10px' }}>LTP Premium</th>
                  <th style={{ padding: '10px' }}>IV %</th>
                  <th style={{ padding: '10px', textAlign: 'right' }}>OI</th>
                </tr>
              </thead>
              <tbody>
                {displayStrikes.map((row) => {
                  const isAtm = row.strike_price === atm;
                  const isCallItm = row.strike_price < spot;
                  const isPutItm = row.strike_price > spot;

                  return (
                    <tr
                      key={row.strike_price}
                      style={{
                        borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                        backgroundColor: isAtm ? 'rgba(242, 154, 96, 0.08)' : 'transparent',
                        transition: 'background-color var(--transition-fast)',
                      }}
                      onMouseEnter={(e) => {
                        if (!isAtm) e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.02)';
                      }}
                      onMouseLeave={(e) => {
                        if (!isAtm) e.currentTarget.style.backgroundColor = 'transparent';
                      }}
                    >
                      {/* CALL SIDE */}
                      {/* Call OI */}
                      <td
                        style={{
                          padding: '12px 10px',
                          textAlign: 'left',
                          backgroundColor: isCallItm ? 'rgba(16, 185, 129, 0.04)' : 'transparent',
                        }}
                        className="tabular-nums"
                      >
                        <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                          {row.call.open_interest.toLocaleString('en-IN')}
                        </span>
                      </td>

                      {/* Call IV */}
                      <td
                        style={{
                          padding: '12px 10px',
                          backgroundColor: isCallItm ? 'rgba(16, 185, 129, 0.04)' : 'transparent',
                        }}
                        className="tabular-nums"
                      >
                        <span style={{ color: 'var(--text-faint)', fontSize: '12px' }}>
                          {row.call.implied_volatility}%
                        </span>
                      </td>

                      {/* Call LTP */}
                      <td
                        style={{
                          padding: '12px 10px',
                          backgroundColor: isCallItm ? 'rgba(16, 185, 129, 0.04)' : 'transparent',
                        }}
                      >
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                          <span
                            className="tabular-nums"
                            style={{
                              color: isCallItm ? 'var(--color-profit)' : '#FFFFFF',
                              fontWeight: 700,
                              fontSize: '14px',
                            }}
                          >
                            ₹{row.call.ltp.toFixed(2)}
                          </span>
                          <span
                            className="tabular-nums"
                            style={{
                              fontSize: '10px',
                              color: row.call.change >= 0 ? 'var(--color-profit)' : 'var(--color-loss)',
                            }}
                          >
                            {row.call.change >= 0 ? '+' : ''}
                            {row.call.change.toFixed(2)} ({row.call.change_pct}%)
                          </span>
                        </div>
                      </td>

                      {/* Call Action Button */}
                      <td
                        style={{
                          padding: '12px 10px',
                          borderRight: '1px solid var(--border-subtle)',
                          backgroundColor: isCallItm ? 'rgba(16, 185, 129, 0.04)' : 'transparent',
                        }}
                      >
                        <button
                          type="button"
                          onClick={() => onOpenTrade(row.call, spot)}
                          style={{
                            padding: '4px 10px',
                            borderRadius: '4px',
                            backgroundColor: 'rgba(16, 185, 129, 0.15)',
                            border: '1px solid var(--color-profit)',
                            color: 'var(--color-profit)',
                            fontSize: '11px',
                            fontWeight: 700,
                            cursor: 'pointer',
                          }}
                        >
                          BUY CE
                        </button>
                      </td>

                      {/* CENTER STRIKE */}
                      <td
                        style={{
                          padding: '12px 14px',
                          borderRight: '1px solid var(--border-subtle)',
                          borderLeft: '1px solid var(--border-subtle)',
                          backgroundColor: isAtm ? 'rgba(242, 154, 96, 0.18)' : 'rgba(255, 255, 255, 0.02)',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
                          <span
                            className="tabular-nums"
                            style={{
                              fontWeight: 800,
                              fontSize: isAtm ? '15px' : '13px',
                              color: isAtm ? '#FFFFFF' : 'var(--text-muted)',
                            }}
                          >
                            {row.strike_price.toLocaleString('en-IN')}
                          </span>
                          {isAtm && (
                            <span
                              style={{
                                fontSize: '9px',
                                fontWeight: 800,
                                backgroundColor: 'var(--color-action)',
                                color: '#000000',
                                padding: '1px 4px',
                                borderRadius: '3px',
                              }}
                            >
                              ATM
                            </span>
                          )}
                        </div>
                      </td>

                      {/* PUT SIDE */}
                      {/* Put Action Button */}
                      <td
                        style={{
                          padding: '12px 10px',
                          borderLeft: '1px solid var(--border-subtle)',
                          backgroundColor: isPutItm ? 'rgba(239, 68, 68, 0.04)' : 'transparent',
                        }}
                      >
                        <button
                          type="button"
                          onClick={() => onOpenTrade(row.put, spot)}
                          style={{
                            padding: '4px 10px',
                            borderRadius: '4px',
                            backgroundColor: 'rgba(239, 68, 68, 0.15)',
                            border: '1px solid var(--color-loss)',
                            color: 'var(--color-loss)',
                            fontSize: '11px',
                            fontWeight: 700,
                            cursor: 'pointer',
                          }}
                        >
                          BUY PE
                        </button>
                      </td>

                      {/* Put LTP */}
                      <td
                        style={{
                          padding: '12px 10px',
                          backgroundColor: isPutItm ? 'rgba(239, 68, 68, 0.04)' : 'transparent',
                        }}
                      >
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                          <span
                            className="tabular-nums"
                            style={{
                              color: isPutItm ? 'var(--color-loss)' : '#FFFFFF',
                              fontWeight: 700,
                              fontSize: '14px',
                            }}
                          >
                            ₹{row.put.ltp.toFixed(2)}
                          </span>
                          <span
                            className="tabular-nums"
                            style={{
                              fontSize: '10px',
                              color: row.put.change >= 0 ? 'var(--color-profit)' : 'var(--color-loss)',
                            }}
                          >
                            {row.put.change >= 0 ? '+' : ''}
                            {row.put.change.toFixed(2)} ({row.put.change_pct}%)
                          </span>
                        </div>
                      </td>

                      {/* Put IV */}
                      <td
                        style={{
                          padding: '12px 10px',
                          backgroundColor: isPutItm ? 'rgba(239, 68, 68, 0.04)' : 'transparent',
                        }}
                        className="tabular-nums"
                      >
                        <span style={{ color: 'var(--text-faint)', fontSize: '12px' }}>
                          {row.put.implied_volatility}%
                        </span>
                      </td>

                      {/* Put OI */}
                      <td
                        style={{
                          padding: '12px 10px',
                          textAlign: 'right',
                          backgroundColor: isPutItm ? 'rgba(239, 68, 68, 0.04)' : 'transparent',
                        }}
                        className="tabular-nums"
                      >
                        <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                          {row.put.open_interest.toLocaleString('en-IN')}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Provenance Footer */}
        {chainData && (
          <div
            style={{
              marginTop: '16px',
              padding: '10px 14px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid var(--border-subtle)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontSize: '11px',
              color: 'var(--text-muted)',
              flexWrap: 'wrap',
              gap: '8px',
            }}
          >
            <span>
              Source: <strong style={{ color: '#FFFFFF' }}>{chainData.source}</strong> • Observed at:{' '}
              {chainData.observed_at ? new Date(chainData.observed_at).toLocaleString('en-IN') : 'Live'}
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-faint)' }}>
              Hash: {chainData.evidence_hash.slice(0, 16)}...
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
