"""Deterministic Risk Profile Evaluation Engine.

Task ID: S2-AI-01, S2-AI-02
Evaluates risk profiles deterministically based on willingness, capacity, and horizon.
Zero hallucinations or speculative recommendations. Cites SEBI Asset Allocation principles.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RiskBand(str, Enum):
    CONSERVATIVE = "CONSERVATIVE"
    MODERATE = "MODERATE"
    AGGRESSIVE = "AGGRESSIVE"


class RiskAnswer(BaseModel):
    question_id: str
    option_id: str
    score: int = Field(..., ge=0, le=100)


class AssessmentSubmission(BaseModel):
    user_id: Optional[str] = None
    questionnaire_version: str = "v1.0"
    horizon_category: str = Field(..., description="<1, 1-3, 3-5, >5")
    answers: List[RiskAnswer]


class RiskAssessmentResult(BaseModel):
    composite_score: int = Field(..., ge=0, le=100)
    risk_band: RiskBand
    willingness_score: int
    capacity_score: int
    horizon_factor: float
    factors: List[Dict[str, Any]]
    explanation: str
    citation: str
    disclaimer: str


# Question catalog v1.0
RISK_QUESTIONNAIRE_V1 = [
    {
        "id": "Q1",
        "dimension": "willingness",
        "prompt": "If your portfolio dropped by 15% in a broad market correction over 3 months, what would you do?",
        "options": [
            {"id": "Q1_A", "text": "Panic and sell all holdings to prevent further loss", "score": 10},
            {"id": "Q1_B", "text": "Sell a portion to hold cash until markets stabilize", "score": 35},
            {"id": "Q1_C", "text": "Do nothing and wait for natural market recovery", "score": 70},
            {"id": "Q1_D", "text": "View it as a discount and buy additional shares", "score": 100},
        ],
    },
    {
        "id": "Q2",
        "dimension": "capacity",
        "prompt": "How many months of basic living expenses do you currently hold in liquid cash/emergency reserves?",
        "options": [
            {"id": "Q2_A", "text": "Less than 1 month (rely on next month's salary)", "score": 15},
            {"id": "Q2_B", "text": "1 to 3 months of basic expenses", "score": 45},
            {"id": "Q2_C", "text": "3 to 6 months in liquid savings/deposits", "score": 75},
            {"id": "Q2_D", "text": "More than 6 months of secure liquid reserves", "score": 100},
        ],
    },
    {
        "id": "Q3",
        "dimension": "willingness",
        "prompt": "Which asset return profile best aligns with your primary investment goal?",
        "options": [
            {"id": "Q3_A", "text": "Capital preservation: 5-7% returns with near-zero downside", "score": 20},
            {"id": "Q3_B", "text": "Balanced growth: 9-11% returns with moderate temporary swings", "score": 60},
            {
                "id": "Q3_C",
                "text": "Wealth maximization: 13-16% returns with substantial market volatility",
                "score": 95,
            },
        ],
    },
    {
        "id": "Q4",
        "dimension": "capacity",
        "prompt": "What proportion of your monthly take-home income is committed to fixed debt payments (EMIs)?",
        "options": [
            {"id": "Q4_A", "text": "Over 50% of monthly income committed to EMIs", "score": 15},
            {"id": "Q4_B", "text": "30% to 50% committed to debt obligations", "score": 40},
            {"id": "Q4_C", "text": "10% to 30% of income committed to debt", "score": 70},
            {"id": "Q4_D", "text": "Zero debt / negligible loan liabilities", "score": 100},
        ],
    },
]


def evaluate_risk_profile(submission: AssessmentSubmission) -> RiskAssessmentResult:
    """Deterministic evaluation of investor risk profile."""
    # Horizon multiplier
    horizon_multipliers = {
        "<1": 0.50,  # Very short: limits equity risk capacity heavily
        "1-3": 0.75,  # Short: modest equity capacity
        "3-5": 1.00,  # Medium: balanced standard baseline
        ">5": 1.15,  # Long: high compounding absorption capacity
    }
    horizon_factor = horizon_multipliers.get(submission.horizon_category, 1.00)

    # Separate willingness vs capacity
    willingness_scores: List[int] = []
    capacity_scores: List[int] = []

    question_map = {q["id"]: q for q in RISK_QUESTIONNAIRE_V1}

    for ans in submission.answers:
        q_meta = question_map.get(ans.question_id)
        if q_meta:
            if q_meta["dimension"] == "willingness":
                willingness_scores.append(ans.score)
            elif q_meta["dimension"] == "capacity":
                capacity_scores.append(ans.score)

    avg_willingness = sum(willingness_scores) / len(willingness_scores) if willingness_scores else 50
    avg_capacity = sum(capacity_scores) / len(capacity_scores) if capacity_scores else 50

    # 40% willingness, 40% capacity, 20% horizon adjustment
    raw_composite = (avg_willingness * 0.45 + avg_capacity * 0.55) * horizon_factor
    composite_score = max(0, min(100, int(round(raw_composite))))

    # Deterministic risk band categorization
    if composite_score < 40:
        band = RiskBand.CONSERVATIVE
        explanation = (
            "Your profile prioritizes capital stability and near-term capital protection. "
            "Your capacity to absorb equity market drawdowns is constrained by investment horizon or liquidity buffers."
        )
    elif composite_score < 70:
        band = RiskBand.MODERATE
        explanation = (
            "Your profile balances equity market growth with downside capital preservation. "
            "A medium investment horizon allows you to absorb temporary market volatility while compounding wealth."
        )
    else:
        band = RiskBand.AGGRESSIVE
        explanation = (
            "Your profile possesses strong psychological willingness and substantial balance-sheet capacity to absorb volatility. "
            "A long investment horizon enables you to pursue aggressive equity asset allocations."
        )

    factors = [
        {
            "name": "Investment Horizon",
            "value": f"{submission.horizon_category} years",
            "impact": "High positive" if horizon_factor >= 1.0 else "Constraining factor",
        },
        {
            "name": "Psychological Willingness",
            "score": int(avg_willingness),
            "band": "High" if avg_willingness >= 70 else "Moderate" if avg_willingness >= 40 else "Conservative",
        },
        {
            "name": "Balance Sheet Capacity",
            "score": int(avg_capacity),
            "band": "Resilient" if avg_capacity >= 70 else "Adequate" if avg_capacity >= 40 else "Vulnerable",
        },
    ]

    return RiskAssessmentResult(
        composite_score=composite_score,
        risk_band=band,
        willingness_score=int(avg_willingness),
        capacity_score=int(avg_capacity),
        horizon_factor=horizon_factor,
        factors=factors,
        explanation=explanation,
        citation="SEBI Guide to Financial Education for Beginners, Chapter 2 & Chapter 3 (Asset Allocation Principles)",
        disclaimer=(
            "This risk assessment is derived by a deterministic scoring formula for educational and simulated trading purposes. "
            "It does not constitute registered financial advisory under SEBI (Investment Advisers) Regulations, 2013."
        ),
    )
