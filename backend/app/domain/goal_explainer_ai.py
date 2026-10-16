"""Goal Planning Explanation AI Pipeline.

Task ID: S7-AI-01
Author: Shivraj Dhote
Date: 16 October 2026

Coordinates:
1. Explains deterministic goal projections, required monthly savings, and timeline in accessible language.
2. Identifies inflation considerations and realistic saving milestones.
3. Strict prohibition on guaranteed future returns or wealth promises.
4. Preserves all input numbers with 100% mathematical fidelity.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from backend.app.domain.goal_engine import GoalProjectionResult


class GoalExplanationResponse(BaseModel):
    goal_id: str
    headline: str
    timeline_summary: str
    required_savings_narrative: str
    milestone_checkpoints: List[str]
    risk_and_inflation_considerations: List[str]
    disclaimer: str


AI_GOAL_EXPLANATION_DISCLAIMER = (
    "EDUCATIONAL DISCLAIMER: This goal projection commentary is generated solely for personal financial planning literacy. "
    "All figures are calculated using standard compound interest formulas based on user-supplied assumptions. "
    "Actual market returns vary significantly from year to year; investment returns are subject to market risks."
)


def explain_goal_projection(projection: GoalProjectionResult, goal_title: str) -> GoalExplanationResponse:
    """Produces educational commentary based strictly on deterministic calculation outputs."""
    tgt = projection.target_amount
    cur = projection.current_amount
    pmt = projection.required_monthly_savings
    months = projection.months_remaining
    rate = projection.assumed_annual_return_pct
    prog = projection.progress_pct

    years = round(months / 12.0, 1)

    headline = f"Goal Plan: {goal_title} — Target ₹{tgt:,.2f} in {months} months ({years} years)"

    timeline = (
        f"You have currently accumulated ₹{cur:,.2f} ({prog:.1f}% of target). "
        f"With {months} months remaining until your target date, you have an active runway of {years} years."
    )

    if pmt == 0.0:
        savings_text = (
            f"Great progress! Based on your assumed nominal return of {rate:.1f}% p.a., your existing corpus of ₹{cur:,.2f} "
            f"is projected to compound to ₹{projection.projected_future_value_zero_contributions:,.2f}, surpassing your target of ₹{tgt:,.2f}."
        )
    else:
        savings_text = (
            f"To reach ₹{tgt:,.2f} by the target date at an assumed {rate:.1f}% nominal annual return, "
            f"you will need to save approximately ₹{pmt:,.2f} per month systematically."
        )

    # 3 Milestone checkpoints
    m1 = round(tgt * 0.25, 2)
    m2 = round(tgt * 0.50, 2)
    m3 = round(tgt * 0.75, 2)
    milestones = [
        f"25% Quarter Milestone: ₹{m1:,.2f}",
        f"50% Halfway Checkpoint: ₹{m2:,.2f}",
        f"75% Target Horizon: ₹{m3:,.2f}",
    ]

    risks = [
        f"Return Assumption Risk: An assumed return of {rate:.1f}% is an average annualized estimate; equity funds can experience multi-year periods of negative or flat returns.",
        "Inflation Awareness: Consumer inflation in India (typically 5-6% CPI) erodes purchasing power; consider reviewing target values every 12 months.",
        "Emergency Buffer: Ensure an independent 3-6 month emergency fund exists so you do not break long-term goal investments prematurely.",
    ]

    return GoalExplanationResponse(
        goal_id=projection.goal_id,
        headline=headline,
        timeline_summary=timeline,
        required_savings_narrative=savings_text,
        milestone_checkpoints=milestones,
        risk_and_inflation_considerations=risks,
        disclaimer=AI_GOAL_EXPLANATION_DISCLAIMER,
    )
