import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  formatAllocationSubtotal,
  formatCashBalanceAfter,
  isExecutableProposal,
  shouldRenderProposalCard,
} from '../src/domain/chartAssistantHelpers.ts';

describe('Chart Assistant Proposal Card & Formatting Helpers', () => {
  it('only enables execution for valid PROPOSED/PARTIALLY_EXECUTED proposals', () => {
    const validProposal = {
      proposal_id: 'prop-abc123',
      status: 'PROPOSED',
      requires_approval: true,
      total_budget: 2500,
      expires_in_minutes: 10,
      allocations: [{ symbol: 'RELIANCE', side: 'BUY', quantity: 1, estimated_total: 2500 }],
    };
    assert.equal(shouldRenderProposalCard(validProposal), true);
    assert.equal(isExecutableProposal(validProposal), true);

    assert.equal(isExecutableProposal({ ...validProposal, status: 'EXECUTED' }), false);
    assert.equal(isExecutableProposal({ ...validProposal, status: 'CANCELLED' }), false);
    assert.equal(isExecutableProposal({ ...validProposal, status: 'EXPIRED' }), false);
    assert.equal(isExecutableProposal({ status: 'INSUFFICIENT_BUDGET', requires_approval: false, allocations: [] }), false);
    assert.equal(shouldRenderProposalCard({ status: 'INSUFFICIENT_BUDGET', allocations: [] }), false);
  });

  it('formats backend estimated_total cleanly and labels unavailable subtotals', () => {
    assert.equal(
      formatAllocationSubtotal({ symbol: 'RELIANCE', side: 'BUY', quantity: 1, estimated_total: 2450.5 }),
      '₹2,450.50'
    );
    assert.equal(
      formatAllocationSubtotal({ symbol: 'TCS', quantity: 2, estimated_subtotal: 7000 }),
      '₹7,000.00'
    );
    assert.equal(
      formatAllocationSubtotal({ symbol: 'RELIANCE', quantity: 1 }),
      'Unavailable'
    );
  });

  it('preserves genuine zero cash and labels missing cash_balance_after as Unavailable', () => {
    assert.equal(formatCashBalanceAfter(97500), '₹97,500.00');
    assert.equal(formatCashBalanceAfter(0), '₹0.00');
    assert.equal(formatCashBalanceAfter(null), 'Unavailable');
    assert.equal(formatCashBalanceAfter(undefined), 'Unavailable');
    assert.equal(formatCashBalanceAfter(Number.NaN), 'Unavailable');
  });
});
