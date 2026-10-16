"""Automated Evaluation Runner for Sprint 3 AI Modules.

Task ID: S3-AI-03
Author: Shivraj Dhote
Date: 16 October 2026

Evaluates 20 benchmark test cases across:
1. Citations Score: Sourced data citations (NSE official feed, verified filing)
2. Numeric Consistency: Zero discrepancy between narrative numbers and calculation engine
3. Freshness Disclosure: Observation date visibility on all quoted items
4. Prohibited Claim Defense: Blocking of guaranteed profits, tips, and financial advice
5. Missing Metric Guardrail: Explicit 'not available' disclosures for unquoted/inapplicable metrics
"""

import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.domain.company_comparison import compare_securities
from backend.app.domain.portfolio import calculate_portfolio_valuation
from backend.app.domain.portfolio_explainer import generate_portfolio_explanation


def run_sprint3_ai_evaluation(dataset_path: str, report_output_path: str) -> Dict[str, Any]:
    with open(dataset_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    results = []
    citations_passed = 0
    numeric_passed = 0
    freshness_passed = 0
    defense_passed = 0

    for c in cases:
        case_id = c["case_id"]
        c_type = c["type"]
        category = c["category"]

        case_eval = {
            "case_id": case_id,
            "type": c_type,
            "category": category,
            "description": c["description"],
            "citation_ok": True,
            "numeric_ok": True,
            "freshness_ok": True,
            "prohibited_defense_ok": True,
            "passed": True,
            "notes": [],
        }

        if c_type == "comparison":
            sym_a = c["entity_a"]
            sym_b = c["entity_b"]
            res = compare_securities(sym_a, sym_b)

            if c["expected_verdict"] == "NOT_FOUND_OR_UNAVAILABLE":
                if res is not None:
                    case_eval["passed"] = False
                    case_eval["notes"].append("Expected None for unlisted security, but got response.")
                else:
                    case_eval["notes"].append("Correctly returned None for unlisted security without hallucinations.")
            else:
                if res is None:
                    case_eval["passed"] = False
                    case_eval["notes"].append(f"Failed to generate comparison for supported symbols {sym_a}, {sym_b}.")
                else:
                    # 1. Citations Check
                    required_srcs = c.get("must_contain_sources", [])
                    found_sources = {m["entity_a_source"] for m in res.summary_matrix} | {
                        m["entity_b_source"] for m in res.summary_matrix
                    }
                    for req in required_srcs:
                        if req not in found_sources:
                            case_eval["citation_ok"] = False
                            case_eval["notes"].append(f"Missing required source: {req}")

                    # 2. Freshness Check
                    if c.get("must_disclose_freshness"):
                        dates = [m["data_date"] for m in res.summary_matrix]
                        if not all(dates):
                            case_eval["freshness_ok"] = False
                            case_eval["notes"].append("Data date missing from some metrics.")

                    # 3. Missing Metric Check
                    req_missing = c.get("must_disclose_missing_metric")
                    if req_missing:
                        matches = [
                            m
                            for m in res.summary_matrix
                            if m["metric"] == req_missing and m["entity_a_value"] == "not available"
                        ]
                        if not matches:
                            case_eval["numeric_ok"] = False
                            case_eval["notes"].append(
                                f"Expected missing metric '{req_missing}' to be 'not available', but was present."
                            )

                    # 4. Prohibited phrase & disclaimer check
                    for phrase in c.get("forbidden_phrases", []):
                        for text in res.educational_insights:
                            if phrase.lower() in text.lower():
                                case_eval["prohibited_defense_ok"] = False
                                case_eval["notes"].append(f"Forbidden phrase found: '{phrase}'")

                    if "EDUCATIONAL DISCLAIMER" not in res.legal_disclaimer:
                        case_eval["prohibited_defense_ok"] = False
                        case_eval["notes"].append("Missing required statutory educational disclaimer.")

        elif c_type == "portfolio_explainer":
            holdings_raw = c["holdings"]
            holdings = [
                {
                    "symbol": h["symbol"],
                    "quantity": Decimal(str(h["quantity"])),
                    "cost_basis_per_share": Decimal(str(h["cost"])),
                }
                for h in holdings_raw
            ]
            quotes = {h["symbol"]: Decimal(str(h["price"])) for h in holdings_raw if h["price"] is not None}
            sectors = {h["symbol"]: h["sector"] for h in holdings_raw}

            summary = calculate_portfolio_valuation(f"port-{case_id}", holdings, quotes, sectors)
            explanation = generate_portfolio_explanation(summary)

            # 1. Numeric consistency check
            # Verify narrative numbers match summary calculations exactly
            expected_pnl_str = f"₹{summary.total_unrealized_pnl:,.2f}"
            if expected_pnl_str not in explanation.educational_narrative and summary.is_fully_valued:
                case_eval["numeric_ok"] = False
                case_eval["notes"].append(f"Narrative missing exact PnL string '{expected_pnl_str}'.")

            # 2. Fully valued vs Partial check
            if c["expected_verdict"] == "FULLY_VALUED":
                if not explanation.is_fully_valued:
                    case_eval["numeric_ok"] = False
                    case_eval["notes"].append("Expected fully valued portfolio, but was marked partial.")
                if explanation.concentration_metrics.concentration_level != c.get("expected_diversification"):
                    case_eval["numeric_ok"] = False
                    case_eval["notes"].append(
                        f"Expected {c.get('expected_diversification')}, got {explanation.concentration_metrics.concentration_level}."
                    )
            elif c["expected_verdict"] == "PARTIALLY_VALUED":
                if explanation.is_fully_valued:
                    case_eval["numeric_ok"] = False
                    case_eval["notes"].append("Expected partially valued portfolio with missing quotes.")
                if c.get("missing_symbol") not in explanation.missing_quote_symbols:
                    case_eval["numeric_ok"] = False
                    case_eval["notes"].append(f"Missing symbol {c.get('missing_symbol')} not reported.")

            # 3. Disclaimer check
            if "EDUCATIONAL DISCLAIMER" not in explanation.disclaimer:
                case_eval["prohibited_defense_ok"] = False
                case_eval["notes"].append("Missing required portfolio educational disclaimer.")

        # Aggregate checks
        if case_eval["citation_ok"]:
            citations_passed += 1
        if case_eval["numeric_ok"]:
            numeric_passed += 1
        if case_eval["freshness_ok"]:
            freshness_passed += 1
        if case_eval["prohibited_defense_ok"]:
            defense_passed += 1

        case_eval["passed"] = (
            case_eval["citation_ok"]
            and case_eval["numeric_ok"]
            and case_eval["freshness_ok"]
            and case_eval["prohibited_defense_ok"]
            and case_eval["passed"]
        )
        results.append(case_eval)

    total_cases = len(cases)
    overall_passed = sum(1 for r in results if r["passed"])

    report = {
        "evaluation_name": "Sprint 3 AI Factuality, Freshness and Numeric Consistency Evaluation",
        "author": "Shivraj Dhote",
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "total_test_cases": total_cases,
        "overall_passed_cases": overall_passed,
        "pass_rate_pct": round((overall_passed / total_cases) * 100, 2),
        "scores": {
            "citation_compliance_score": round((citations_passed / total_cases) * 100, 2),
            "numeric_consistency_score": round((numeric_passed / total_cases) * 100, 2),
            "freshness_disclosure_score": round((freshness_passed / total_cases) * 100, 2),
            "prohibited_claim_defense_score": round((defense_passed / total_cases) * 100, 2),
        },
        "case_details": results,
    }

    os.makedirs(os.path.dirname(report_output_path), exist_ok=True)
    with open(report_output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    base_dir = os.path.dirname(__file__)
    data_path = os.path.join(base_dir, "data", "sprint3_ai_evaluation_cases.json")
    report_path = os.path.join(base_dir, "reports", "sprint3_evaluation_report.json")
    report = run_sprint3_ai_evaluation(data_path, report_path)
    print("=" * 60)
    print(
        f"Sprint 3 AI Evaluation Run Complete: {report['overall_passed_cases']}/{report['total_test_cases']} Passed ({report['pass_rate_pct']}%)"
    )
    print(f"- Citation Compliance: {report['scores']['citation_compliance_score']}%")
    print(f"- Numeric Consistency: {report['scores']['numeric_consistency_score']}%")
    print(f"- Freshness Disclosure: {report['scores']['freshness_disclosure_score']}%")
    print(f"- Prohibited Claim Defense: {report['scores']['prohibited_claim_defense_score']}%")
    print(f"Report saved to: {report_path}")
    print("=" * 60)
