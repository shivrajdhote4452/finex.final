/**
 * Risk Profile Evaluation Domain Model and Questionnaire Catalog.
 *
 * Grounded in server-authoritative scoring rules defined in `backend/app/domain/risk.py`.
 * Provides deterministic evaluation, step metadata, and option catalogs.
 */

export interface OptionItem {
  id: string;
  text: string;
  desc?: string;
  score: number;
}

export interface QuestionItem {
  id: string;
  dimension: 'willingness' | 'capacity';
  numberLabel: string;
  title: string;
  prompt: string;
  options: OptionItem[];
}

export interface HorizonOptionItem {
  id: string;
  title: string;
  desc: string;
  multiplier: number;
}

export const HORIZON_OPTIONS: HorizonOptionItem[] = [
  { id: '<1', title: 'Less than 1 year', desc: 'Short-term needs, lower tolerance for volatility', multiplier: 0.50 },
  { id: '1-3', title: '1-3 years', desc: 'Near-term capital protection priority', multiplier: 0.75 },
  { id: '3-5', title: '3-5 years', desc: 'Balanced window navigating market cycles', multiplier: 1.00 },
  { id: '>5', title: 'More than 5 years', desc: 'Long-term equity compounding timeframe', multiplier: 1.15 },
];

export const RISK_QUESTIONS: Record<string, QuestionItem> = {
  Q1: {
    id: 'Q1',
    dimension: 'willingness',
    numberLabel: '1',
    title: 'Market correction reaction',
    prompt: 'If your portfolio dropped by 15% in a broad market correction over 3 months, what would you do?',
    options: [
      { id: 'Q1_A', text: 'Panic and sell all holdings to prevent further loss', score: 10 },
      { id: 'Q1_B', text: 'Sell a portion to hold cash until markets stabilize', score: 35 },
      { id: 'Q1_C', text: 'Do nothing and wait for natural market recovery', score: 70 },
      { id: 'Q1_D', text: 'View it as a discount and buy additional shares', score: 100 },
    ],
  },
  Q3: {
    id: 'Q3',
    dimension: 'willingness',
    numberLabel: '2',
    title: 'Target return profile',
    prompt: 'Which asset return profile best aligns with your primary investment goal?',
    options: [
      { id: 'Q3_A', text: 'Capital preservation: 5-7% returns with near-zero downside', score: 20 },
      { id: 'Q3_B', text: 'Balanced growth: 9-11% returns with moderate temporary swings', score: 60 },
      { id: 'Q3_C', text: 'Wealth maximization: 13-16% returns with substantial market volatility', score: 95 },
    ],
  },
  Q2: {
    id: 'Q2',
    dimension: 'capacity',
    numberLabel: '4',
    title: 'Emergency cash reserves',
    prompt: 'How many months of basic living expenses do you currently hold in liquid cash/emergency reserves?',
    options: [
      { id: 'Q2_A', text: "Less than 1 month (rely on next month's salary)", score: 15 },
      { id: 'Q2_B', text: '1 to 3 months of basic expenses', score: 45 },
      { id: 'Q2_C', text: '3 to 6 months in liquid savings/deposits', score: 75 },
      { id: 'Q2_D', text: 'More than 6 months of secure liquid reserves', score: 100 },
    ],
  },
  Q4: {
    id: 'Q4',
    dimension: 'capacity',
    numberLabel: '5',
    title: 'Fixed debt obligations (EMIs)',
    prompt: 'What proportion of your monthly take-home income is committed to fixed debt payments (EMIs)?',
    options: [
      { id: 'Q4_A', text: 'Over 50% of monthly income committed to EMIs', score: 15 },
      { id: 'Q4_B', text: '30% to 50% committed to debt obligations', score: 40 },
      { id: 'Q4_C', text: '10% to 30% of income committed to debt', score: 70 },
      { id: 'Q4_D', text: 'Zero debt / negligible loan liabilities', score: 100 },
    ],
  },
};

export interface RiskEvaluationResult {
  composite_score: number;
  risk_band: 'Conservative' | 'Moderate' | 'Aggressive';
  willingness_score: number;
  capacity_score: number;
  horizon_factor: number;
  summary: string;
  explanation: string;
  citation: string;
  disclaimer: string;
  suggested_allocation: { Equity: number; Debt: number; Gold: number };
  factors: Array<{
    name: string;
    value?: string;
    score?: number;
    band?: string;
    impact?: string;
  }>;
}

export function evaluateDeterministicRisk(
  horizonCategory: string,
  answers: {
    Q1: string;
    Q2: string;
    Q3: string;
    Q4: string;
  }
): RiskEvaluationResult {
  const horizonItem = HORIZON_OPTIONS.find((h) => h.id === horizonCategory) || HORIZON_OPTIONS[2];
  const horizonFactor = horizonItem.multiplier;

  const q1 = RISK_QUESTIONS.Q1.options.find((o) => o.id === answers.Q1)?.score ?? 70;
  const q3 = RISK_QUESTIONS.Q3.options.find((o) => o.id === answers.Q3)?.score ?? 60;
  const q2 = RISK_QUESTIONS.Q2.options.find((o) => o.id === answers.Q2)?.score ?? 75;
  const q4 = RISK_QUESTIONS.Q4.options.find((o) => o.id === answers.Q4)?.score ?? 70;

  const avgWillingness = (q1 + q3) / 2;
  const avgCapacity = (q2 + q4) / 2;

  const rawComposite = (avgWillingness * 0.45 + avgCapacity * 0.55) * horizonFactor;
  const compositeScore = Math.max(0, Math.min(100, Math.round(rawComposite)));

  let band: 'Conservative' | 'Moderate' | 'Aggressive';
  let summary: string;
  let explanation: string;
  let allocation: { Equity: number; Debt: number; Gold: number };

  if (compositeScore < 40) {
    band = 'Conservative';
    summary = 'Capital preservation priority with high allocation to fixed income and short-term debt instruments.';
    explanation =
      'Your profile prioritizes capital stability and near-term capital protection. Your capacity to absorb equity market drawdowns is constrained by investment horizon or liquidity buffers.';
    allocation = { Equity: 25, Debt: 65, Gold: 10 };
  } else if (compositeScore < 70) {
    band = 'Moderate';
    summary = 'Balanced exposure between steady income assets and capital appreciation equities.';
    explanation =
      'Your profile balances equity market growth with downside capital preservation. A medium investment horizon allows you to absorb temporary market volatility while compounding wealth.';
    allocation = { Equity: 50, Debt: 40, Gold: 10 };
  } else {
    band = 'Aggressive';
    summary = 'Growth-oriented portfolio targeting long-term capital compounding through diversified equities.';
    explanation =
      'Your profile possesses strong psychological willingness and substantial balance-sheet capacity to absorb volatility. A long investment horizon enables you to pursue aggressive equity asset allocations.';
    allocation = { Equity: 75, Debt: 15, Gold: 10 };
  }

  const factors = [
    {
      name: 'Investment Horizon',
      value: `${horizonCategory} years`,
      impact: horizonFactor >= 1.0 ? 'High positive' : 'Constraining factor',
    },
    {
      name: 'Psychological Willingness',
      score: Math.round(avgWillingness),
      band: avgWillingness >= 70 ? 'High' : avgWillingness >= 40 ? 'Moderate' : 'Conservative',
    },
    {
      name: 'Balance Sheet Capacity',
      score: Math.round(avgCapacity),
      band: avgCapacity >= 70 ? 'Resilient' : avgCapacity >= 40 ? 'Adequate' : 'Vulnerable',
    },
  ];

  return {
    composite_score: compositeScore,
    risk_band: band,
    willingness_score: Math.round(avgWillingness),
    capacity_score: Math.round(avgCapacity),
    horizon_factor: horizonFactor,
    summary,
    explanation,
    citation:
      'FinEx Educational Summary: Guide to Financial Planning & Regulatory Principles, Chapter 2 & Chapter 3 (Asset Allocation Principles)',
    disclaimer:
      'This risk assessment is derived by a deterministic scoring formula for educational and simulated trading purposes. It does not constitute registered financial advisory under SEBI (Investment Advisers) Regulations, 2013.',
    suggested_allocation: allocation,
    factors,
  };
}
