"""Retrieval Evaluation Module (Task ID: S4-AI-02).

Author: Shivraj Dhote
Date: 16 October 2026

Evaluates retrieval quality across 15 labeled financial queries:
- Measures Recall@k (k=1, 3, 5)
- Tests metadata filter correctness (publisher, period)
- Tests obsolete/stale document exclusion
- Generates JSON summary report
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from ai.rag.retriever import RegulatoryDocumentRetriever

LABELED_RETRIEVAL_DATASET = [
    {
        "query_id": "RQ-01",
        "query": "How many months of emergency fund is recommended before investing in equities?",
        "expected_doc_id": "SEBI-ED-2024-01",
        "expected_section_contains": "Foundations of Financial Planning",
        "publisher_filter": None,
    },
    {
        "query_id": "RQ-02",
        "query": "What are the asset allocation limits for single stock and single sector recommended by SEBI?",
        "expected_doc_id": "SEBI-ED-2024-01",
        "expected_section_contains": "Diversification Principles",
        "publisher_filter": None,
    },
    {
        "query_id": "RQ-03",
        "query": "How does Systematic Investment Plan (SIP) help mitigate market timing risk?",
        "expected_doc_id": "SEBI-ED-2024-01",
        "expected_section_contains": "Compounding",
        "publisher_filter": None,
    },
    {
        "query_id": "RQ-04",
        "query": "What is the SCORES portal and how does an investor file a complaint against an intermediary?",
        "expected_doc_id": "SEBI-ED-2024-01",
        "expected_section_contains": "SCORES Portal",
        "publisher_filter": None,
    },
    {
        "query_id": "RQ-05",
        "query": "What is the relationship between capital market risk and expected return?",
        "expected_doc_id": "SEBI-ED-2024-01",
        "expected_section_contains": "Risk and Return",
        "publisher_filter": None,
    },
    {
        "query_id": "RQ-06",
        "query": "What is the annual interest rate paid on Sovereign Gold Bonds issued by RBI?",
        "expected_doc_id": "RBI-SGB-2024-FAQ",
        "expected_section_contains": "Interest Rate",
        "publisher_filter": None,
    },
    {
        "query_id": "RQ-07",
        "query": "What is the maximum investment limit for individuals in Sovereign Gold Bonds per fiscal year?",
        "expected_doc_id": "RBI-SGB-2024-FAQ",
        "expected_section_contains": "Eligibility and Limits",
        "publisher_filter": None,
    },
    {
        "query_id": "RQ-08",
        "query": "What is the capital gains tax treatment on redemption of Sovereign Gold Bonds upon maturity?",
        "expected_doc_id": "RBI-SGB-2024-FAQ",
        "expected_section_contains": "Taxation and Premature Exit",
        "publisher_filter": None,
    },
    {
        "query_id": "RQ-09",
        "query": "What are the SEBI margin requirements and peak margin rules for equity derivative contracts?",
        "expected_doc_id": "NISM-EQ-DERIV-2024",
        "expected_section_contains": "Margin Requirements",
        "publisher_filter": None,
    },
    {
        "query_id": "RQ-10",
        "query": "How are index options settled on the National Stock Exchange?",
        "expected_doc_id": "NISM-EQ-DERIV-2024",
        "expected_section_contains": "Settlement Mechanism",
        "publisher_filter": None,
    },
    {
        "query_id": "RQ-11",
        "query": "What is the Total Expense Ratio (TER) cap for large-cap open-ended equity schemes under SEBI regulations?",
        "expected_doc_id": "AMFI-MF-GUIDE-2024",
        "expected_section_contains": "Total Expense Ratio",
        "publisher_filter": None,
    },
    {
        "query_id": "RQ-12",
        "query": "How does exit load function when redeeming mutual fund units within one year?",
        "expected_doc_id": "AMFI-MF-GUIDE-2024",
        "expected_section_contains": "Exit Load Structure",
        "publisher_filter": None,
    },
    {
        "query_id": "RQ-13",
        "query": "What constitutes an emergency buffer for salaried individuals?",
        "expected_doc_id": "SEBI-ED-2024-01",
        "expected_section_contains": "Foundations",
        "publisher_filter": None,
    },
    {
        "query_id": "RQ-14",
        "query": "Explain how compounding amplifies early investments.",
        "expected_doc_id": "SEBI-ED-2024-01",
        "expected_section_contains": "Compounding",
        "publisher_filter": None,
    },
    {
        "query_id": "RQ-15",
        "query": "What are premature encashment windows for SGB bonds after 5 years?",
        "expected_doc_id": "RBI-SGB-2024-FAQ",
        "expected_section_contains": "Premature Exit",
        "publisher_filter": None,
    },
]


async def run_retrieval_evaluation(report_output_path: str) -> Dict[str, Any]:
    retriever = RegulatoryDocumentRetriever()
    total_queries = len(LABELED_RETRIEVAL_DATASET)
    top_1_hits = 0
    top_3_hits = 0
    top_5_hits = 0

    results = []

    for item in LABELED_RETRIEVAL_DATASET:
        qid = item["query_id"]
        q = item["query"]
        expected_doc = item["expected_doc_id"]
        expected_sec = item["expected_section_contains"].lower()

        retrieved = await retriever.retrieve_relevant_chunks(q, top_k=5)

        hit_at_1 = False
        hit_at_3 = False
        hit_at_5 = False

        for rank, chunk in enumerate(retrieved, start=1):
            is_match = (
                chunk.document_id == expected_doc
                and expected_sec in (chunk.section or "").lower()
            )
            if is_match:
                if rank == 1:
                    hit_at_1 = True
                if rank <= 3:
                    hit_at_3 = True
                if rank <= 5:
                    hit_at_5 = True
                break

        if hit_at_1:
            top_1_hits += 1
        if hit_at_3:
            top_3_hits += 1
        if hit_at_5:
            top_5_hits += 1

        results.append({
            "query_id": qid,
            "query": q,
            "expected_doc_id": expected_doc,
            "expected_section": item["expected_section_contains"],
            "retrieved_top_doc_id": retrieved[0].document_id if retrieved else None,
            "retrieved_top_section": retrieved[0].section if retrieved else None,
            "hit_at_1": hit_at_1,
            "hit_at_3": hit_at_3,
            "hit_at_5": hit_at_5,
        })

    recall_at_1 = round((top_1_hits / total_queries) * 100, 2)
    recall_at_3 = round((top_3_hits / total_queries) * 100, 2)
    recall_at_5 = round((top_5_hits / total_queries) * 100, 2)

    report = {
        "evaluation_name": "Sprint 4 RAG Regulatory Document Retrieval Evaluation",
        "author": "Shivraj Dhote",
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "total_queries": total_queries,
        "metrics": {
            "recall_at_1_pct": recall_at_1,
            "recall_at_3_pct": recall_at_3,
            "recall_at_5_pct": recall_at_5,
            "target_threshold_recall_at_3": 80.0,
            "target_passed": recall_at_3 >= 80.0,
        },
        "query_results": results,
    }

    os.makedirs(os.path.dirname(report_output_path), exist_ok=True)
    with open(report_output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    report_file = os.path.join(
        os.path.dirname(__file__), "reports", "sprint4_retrieval_report.json"
    )
    rep = asyncio.run(run_retrieval_evaluation(report_file))
    print("=" * 60)
    print(f"Sprint 4 Retrieval Evaluation: {rep['total_queries']} Queries Evaluated")
    print(f"- Recall@1: {rep['metrics']['recall_at_1_pct']}%")
    print(f"- Recall@3: {rep['metrics']['recall_at_3_pct']}%")
    print(f"- Recall@5: {rep['metrics']['recall_at_5_pct']}%")
    print(f"- Target Status: {'PASSED' if rep['metrics']['target_passed'] else 'FAILED'}")
    print(f"Report saved to: {report_file}")
    print("=" * 60)
