import React, { useState } from 'react';
import { apiClient, OptionContractData } from '../../api/client';
import { useFinancial } from '../../context/FinancialContext';
import { useToast } from '../../context/ToastContext';

interface OptionTradeModalProps {
  contract: OptionContractData | null;
  underlyingSpot: number;
  onClose: () => void;
  onSuccess?: () => void;
}

export const OptionTradeModal: React.FC<OptionTradeModalProps> = ({
  contract,
  underlyingSpot,
  onClose,
  onSuccess,
}) => {
  const { virtualCash, refreshAccount } = useFinancial();
  const { showToast } = useToast();

  const [lots, setLots] = useState<number>(1);
  const [riskAcknowledged, setRiskAcknowledged] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [receipt, setReceipt] = useState<any | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!contract) return null;

  const lotSize = contract.lot_size || 25;
  const totalUnits = lots * lotSize;
  const premium = contract.ltp;
  const totalCost = Number((premium * totalUnits).toFixed(2));
  const maxLoss = totalCost; // strictly capped for buyer
  const breakeven =
    contract.option_type === 'CE'
      ? Number((contract.strike + premium).toFixed(2))
      : Number((contract.strike - premium).toFixed(2));

  const hasSufficientCash = virtualCash >= totalCost;
  const isCall = contract.option_type === 'CE';

  const handleLotsChange = (delta: number) => {
    setLots((prev) => Math.max(1, Math.min(100, prev + delta)));
  };

  const handleSubmit = async () => {
    if (!riskAcknowledged) {
      setErrorMessage('You must acknowledge the mandatory risk disclosure before placing an options order.');
      return;
    }
    if (!hasSufficientCash) {
      setErrorMessage(`Insufficient virtual cash. Required: ₹${totalCost.toLocaleString('en-IN')}, Available: ₹${virtualCash.toLocaleString('en-IN')}`);
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const res = await apiClient.paperTrading.submitOptionOrder({
        underlying: contract.underlying,
        contract_symbol: contract.contract_symbol,
        option_type: contract.option_type,
        strike: contract.strike,
        expiry: contract.expiry,
        side: 'BUY',
        lots,
        lot_size: lotSize,
        limit_premium: premium,
        risk_acknowledged: true,
      });

      if (res && res.status === 'FILLED') {
        setReceipt(res);
        showToast(
          `Bought ${lots} lot(s) (${totalUnits} units) of ${contract.contract_symbol} @ ₹${premium.toFixed(2)}`,
          'success',
          'Option Order Executed'
        );
        await refreshAccount();
        if (onSuccess) onSuccess();
      } else {
        const msg = res?.rejection_reason || 'Option order was not filled.';
        setErrorMessage(msg);
        showToast(msg, 'error', 'Trade Rejected');
      }
    } catch (err: any) {
      const msg = err?.message || err?.details?.message || 'Failed to submit option order.';
      setErrorMessage(msg);
      showToast(msg, 'error', 'Order Failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content"
        style={{
          maxWidth: '540px',
          width: '90%',
          backgroundColor: '#0A0A0A',
          border: '1px solid var(--border-subtle)',
          borderRadius: '12px',
          padding: '28px',
          boxShadow: '0 20px 40px rgba(0,0,0,0.8)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {receipt ? (
          /* Execution Contract Receipt */
          <div style={{ textAlign: 'center' }}>
            <div
              style={{
                width: '56px',
                height: '56px',
                borderRadius: '50%',
                backgroundColor: 'rgba(16, 185, 129, 0.15)',
                border: '2px solid var(--color-profit)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px auto',
                fontSize: '24px',
                color: 'var(--color-profit)',
              }}
            >
              ✓
            </div>

            <span className="badge badge-profit" style={{ marginBottom: '8px' }}>
              OPTION FILLED • {receipt.order_id}
            </span>
            <h3 style={{ fontSize: '22px', fontWeight: 700, color: '#FFFFFF', marginTop: '4px' }}>
              Long {isCall ? 'Call' : 'Put'} Purchased
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '20px' }}>
              Simulated long position opened with strict risk parameters.
            </p>

            <div
              style={{
                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '16px',
                textAlign: 'left',
                marginBottom: '20px',
                fontSize: '13px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Contract</span>
                <strong style={{ color: '#FFFFFF' }}>{receipt.contract_symbol}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Position Size</span>
                <span style={{ color: '#FFFFFF' }}>
                  {receipt.lots} Lot(s) ({receipt.total_quantity} units)
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Entry Premium</span>
                <span className="tabular-nums" style={{ color: '#FFFFFF' }}>
                  ₹{Number(receipt.fill_premium).toFixed(2)}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Total Premium Paid</span>
                <span className="tabular-nums" style={{ color: 'var(--color-action)', fontWeight: 600 }}>
                  ₹{Number(receipt.total_premium_paid).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Maximum Loss</span>
                <span className="tabular-nums" style={{ color: 'var(--color-loss)', fontWeight: 600 }}>
                  ₹{Number(receipt.max_loss).toLocaleString('en-IN', { minimumFractionDigits: 2 })} (100% capped)
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Breakeven at Expiry</span>
                <span className="tabular-nums" style={{ color: '#FFFFFF', fontWeight: 600 }}>
                  ₹{Number(receipt.breakeven).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '10px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Paper Cash Balance After</span>
                <span className="tabular-nums" style={{ color: 'var(--color-profit)', fontWeight: 700 }}>
                  ₹{Number(receipt.cash_balance_after).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
            </div>

            <button onClick={onClose} className="btn btn-primary" style={{ width: '100%' }}>
              Done
            </button>
          </div>
        ) : (
          /* Option Order Ticket */
          <div>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 700,
                      padding: '3px 8px',
                      borderRadius: '4px',
                      backgroundColor: isCall ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                      color: isCall ? 'var(--color-profit)' : 'var(--color-loss)',
                      letterSpacing: '0.05em',
                    }}
                  >
                    {isCall ? 'CALL (CE)' : 'PUT (PE)'}
                  </span>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    {contract.underlying}
                  </span>
                </div>
                <h3 style={{ fontSize: '20px', fontWeight: 800, color: '#FFFFFF', margin: 0 }}>
                  Strike ₹{contract.strike.toLocaleString('en-IN')} {isCall ? 'CE' : 'PE'}
                </h3>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Expiry: <strong style={{ color: '#FFFFFF' }}>{contract.expiry}</strong> •{' '}
                  <span style={{ color: 'var(--color-action)' }}>{contract.days_to_expiry} days to expiry</span> •{' '}
                  <span>Spot: <strong style={{ color: '#FFFFFF' }}>₹{underlyingSpot.toLocaleString('en-IN')}</strong></span>
                </div>
              </div>

              <button
                onClick={onClose}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  fontSize: '20px',
                  cursor: 'pointer',
                  padding: '4px',
                }}
              >
                ✕
              </button>
            </div>

            {/* Price & Greeks Snapshot */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: '8px',
                backgroundColor: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '12px',
                marginBottom: '20px',
                textAlign: 'center',
              }}
            >
              <div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>LTP Premium</div>
                <div className="tabular-nums" style={{ fontSize: '15px', fontWeight: 700, color: '#FFFFFF' }}>
                  ₹{premium.toFixed(2)}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>IV</div>
                <div className="tabular-nums" style={{ fontSize: '15px', fontWeight: 600, color: '#FFFFFF' }}>
                  {contract.implied_volatility}%
                </div>
              </div>
              <div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Delta (Δ)</div>
                <div className="tabular-nums" style={{ fontSize: '15px', fontWeight: 600, color: '#FFFFFF' }}>
                  {contract.greeks?.delta ?? '—'}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Theta (θ/day)</div>
                <div className="tabular-nums" style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-loss)' }}>
                  {contract.greeks?.theta ? `₹${contract.greeks.theta}` : '—'}
                </div>
              </div>
            </div>

            {/* Order Configuration: Lots & Units */}
            <div style={{ marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <label style={{ fontSize: '13px', fontWeight: 600, color: '#FFFFFF' }}>
                  Order Lots (1 Lot = {lotSize} units)
                </label>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Total: <strong style={{ color: '#FFFFFF' }}>{totalUnits} units</strong>
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button
                  type="button"
                  onClick={() => handleLotsChange(-1)}
                  disabled={lots <= 1}
                  style={{
                    width: '42px',
                    height: '42px',
                    borderRadius: '6px',
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid var(--border-subtle)',
                    color: '#FFFFFF',
                    fontSize: '18px',
                    fontWeight: 700,
                    cursor: lots <= 1 ? 'not-allowed' : 'pointer',
                    opacity: lots <= 1 ? 0.4 : 1,
                  }}
                >
                  −
                </button>
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={lots}
                  onChange={(e) => setLots(Math.max(1, parseInt(e.target.value) || 1))}
                  style={{
                    flex: 1,
                    height: '42px',
                    backgroundColor: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    color: '#FFFFFF',
                    fontSize: '16px',
                    fontWeight: 700,
                    textAlign: 'center',
                  }}
                />
                <button
                  type="button"
                  onClick={() => handleLotsChange(1)}
                  style={{
                    width: '42px',
                    height: '42px',
                    borderRadius: '6px',
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid var(--border-subtle)',
                    color: '#FFFFFF',
                    fontSize: '18px',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  +
                </button>
              </div>
            </div>

            {/* Deterministic Cost Math Box */}
            <div
              style={{
                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '16px',
                marginBottom: '20px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                fontSize: '13px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Calculation</span>
                <span className="tabular-nums" style={{ color: 'var(--text-muted)' }}>
                  ₹{premium.toFixed(2)} × {totalUnits} units
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#FFFFFF', fontWeight: 600 }}>Total Order Cost</span>
                <strong className="tabular-nums" style={{ color: 'var(--color-action)', fontSize: '15px' }}>
                  ₹{totalCost.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Max Loss</span>
                <strong className="tabular-nums" style={{ color: 'var(--color-loss)' }}>
                  ₹{maxLoss.toLocaleString('en-IN', { minimumFractionDigits: 2 })} (Premium Paid)
                </strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Breakeven at Expiry</span>
                <strong className="tabular-nums" style={{ color: '#FFFFFF' }}>
                  ₹{breakeven.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '8px', marginTop: '4px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Available Paper Cash</span>
                <span className="tabular-nums" style={{ color: hasSufficientCash ? 'var(--color-profit)' : 'var(--color-loss)', fontWeight: 600 }}>
                  ₹{virtualCash.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
            </div>

            {/* Mandatory Risk Warning Box */}
            <div
              style={{
                backgroundColor: 'rgba(239, 68, 68, 0.08)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                borderRadius: '8px',
                padding: '14px',
                marginBottom: '20px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginBottom: '10px' }}>
                <span style={{ fontSize: '16px' }}>⚠️</span>
                <div style={{ fontSize: '12px', color: '#FCA5A5', lineHeight: 1.4 }}>
                  <strong>Mandatory Risk Notice:</strong> You can lose the full premium if this expires out of the money.
                  Options positions lose time value daily (theta decay) and expire worthless if spot finishes {isCall ? 'below' : 'above'} strike ₹{contract.strike.toLocaleString('en-IN')}.
                </div>
              </div>

              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  cursor: 'pointer',
                  fontSize: '12px',
                  color: '#FFFFFF',
                  fontWeight: 500,
                  userSelect: 'none',
                }}
              >
                <input
                  type="checkbox"
                  checked={riskAcknowledged}
                  onChange={(e) => setRiskAcknowledged(e.target.checked)}
                  style={{ accentColor: 'var(--color-action)', width: '16px', height: '16px', cursor: 'pointer' }}
                />
                I understand this order risks losing 100% of the ₹{totalCost.toLocaleString('en-IN')} premium.
              </label>
            </div>

            {errorMessage && (
              <div
                style={{
                  backgroundColor: 'rgba(239, 68, 68, 0.1)',
                  color: 'var(--color-loss)',
                  padding: '10px 14px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  marginBottom: '16px',
                  border: '1px solid var(--color-loss)',
                }}
              >
                {errorMessage}
              </div>
            )}

            {/* Order Action Buttons */}
            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                type="button"
                onClick={onClose}
                className="btn btn-secondary"
                style={{ flex: 1 }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={!riskAcknowledged || !hasSufficientCash || isSubmitting}
                className="btn btn-primary"
                style={{
                  flex: 2,
                  backgroundColor: isCall ? 'var(--color-profit)' : 'var(--color-loss)',
                  borderColor: isCall ? 'var(--color-profit)' : 'var(--color-loss)',
                  color: '#000000',
                  fontWeight: 800,
                  opacity: !riskAcknowledged || !hasSufficientCash || isSubmitting ? 0.4 : 1,
                  cursor: !riskAcknowledged || !hasSufficientCash || isSubmitting ? 'not-allowed' : 'pointer',
                }}
              >
                {isSubmitting ? 'Routing Paper Order...' : `Buy ${isCall ? 'Call (CE)' : 'Put (PE)'} • ₹${totalCost.toLocaleString('en-IN')}`}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
