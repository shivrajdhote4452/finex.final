"""Sprint 8: API Load, Reliability, and SLA Verification Suite.

Task ID: S8-API-03
Author: Shivraj Dhote
"""

import pytest
from backend.scripts.run_load_test import run_benchmark


def test_api_concurrency_and_reliability_sla():
    """Execute multi-tenant concurrency benchmark and verify zero failures and SLA bounds."""
    # Run bounded load test: 6 concurrent workers × 3 iterations = 162 total requests
    report = run_benchmark(concurrency=6, iterations_per_worker=3)

    assert report["reliability_metrics"]["failed_requests"] == 0
    assert report["reliability_metrics"]["success_rate_pct"] == 100.0
    assert report["latency_percentiles_ms"]["p95"] < 500.0
    assert report["sla_assessment"]["status"] == "PASSED"
