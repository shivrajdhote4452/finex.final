export interface AssistantAllocationItem {
  symbol: string;
  side?: string;
  quantity: number;
  estimated_price?: number;
  estimated_total?: number;
  estimated_subtotal?: number;
  currency?: string;
}

export interface AssistantProposalCardData {
  proposal_id?: string;
  status?: string;
  total_budget?: number;
  estimated_allocation_total?: number;
  expires_in_minutes?: number;
  currency?: string;
  requires_approval?: boolean;
  allocations?: AssistantAllocationItem[];
}

export function isExecutableProposal(proposal: AssistantProposalCardData | null | undefined): boolean {
  if (!proposal || !proposal.proposal_id) return false;
  if (proposal.requires_approval === false) return false;
  return proposal.status === 'PROPOSED' || proposal.status === 'PARTIALLY_EXECUTED';
}

export function shouldRenderProposalCard(proposal: AssistantProposalCardData | null | undefined): boolean {
  if (!proposal || !proposal.proposal_id) return false;
  return Array.isArray(proposal.allocations) && proposal.allocations.length > 0;
}

export function formatAllocationSubtotal(alloc: AssistantAllocationItem): string {
  const raw = alloc.estimated_total ?? alloc.estimated_subtotal;
  if (typeof raw !== 'number' || !Number.isFinite(raw)) {
    return 'Unavailable';
  }
  return `₹${raw.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatCashBalanceAfter(cashAfter: number | null | undefined): string {
  if (typeof cashAfter !== 'number' || !Number.isFinite(cashAfter)) {
    return 'Unavailable';
  }
  return `₹${cashAfter.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
