"""Sprint 8: API Load, Concurrency, and Reliability Test Runner.

Task ID: S8-API-03
Author: Shivraj Dhote
Date: 16 October 2026

Simulates concurrent multi-tenant workload against all critical API routes:
- Health & Liveness
- Identity & User Profile
- Market Data Real Quote (RELIANCE)
- Portfolio Holdings & Valuations
- Paper Trading Practice Account
- Smart Alerts Rules
- Financial Goals & Planning
- Spending Trend Summaries

Outputs JSON benchmark report with p50, p90, p95, p99 latency percentiles and throughput.
"""

import concurrent.futures
import json
import os
import statistics
import sys
import time
from typing import Any, Dict, List

sys.path.insert(0, os.path.abspath("."))

from backend.app.factory import create_app
from fastapi.testclient import TestClient


def execute_request_batch(
    client: TestClient,
    auth_header: Dict[str, str],
    endpoints: List[str],
) -> List[Dict[str, Any]]:
    results = []
    for endpoint in endpoints:
        start = time.perf_counter()
        resp = client.get(endpoint, headers=auth_header)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        results.append(
            {
                "endpoint": endpoint,
                "status_code": resp.status_code,
                "latency_ms": elapsed_ms,
                "success": resp.status_code == 200,
            }
        )
    return results


def run_benchmark(concurrency: int = 10, iterations_per_worker: int = 5) -> Dict[str, Any]:
    app = create_app()
    client = TestClient(app)

    endpoints = [
        "/api/v1/health/live",
        "/api/v1/health/ready",
        "/api/v1/users/me",
        "/api/v1/market/quotes/RELIANCE",
        "/api/v1/portfolios/me",
        "/api/v1/paper-trading/account",
        "/api/v1/alerts/rules",
        "/api/v1/goals",
        "/api/v1/spending/summary",
    ]

    all_records: List[Dict[str, Any]] = []
    start_total = time.perf_counter()

    from backend.app.routers.auth import create_access_token

    def worker_job(worker_id: int) -> List[Dict[str, Any]]:
        token = create_access_token(
            f"usr-worker-{worker_id:03d}", f"worker{worker_id}@finex.internal", f"Worker {worker_id}"
        )
        auth_header = {"Authorization": f"Bearer {token}"}
        worker_records = []
        for _ in range(iterations_per_worker):
            batch = execute_request_batch(client, auth_header, endpoints)
            worker_records.extend(batch)
        return worker_records

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker_job, i) for i in range(concurrency)]
        for f in concurrent.futures.as_completed(futures):
            all_records.extend(f.result())

    total_time_sec = time.perf_counter() - start_total
    total_requests = len(all_records)
    successful_requests = sum(1 for r in all_records if r["success"])
    failed_requests = total_requests - successful_requests

    latencies = sorted([r["latency_ms"] for r in all_records])

    def percentile(data: List[float], pct: float) -> float:
        if not data:
            return 0.0
        idx = int(len(data) * pct)
        return data[min(idx, len(data) - 1)]

    p50 = statistics.median(latencies) if latencies else 0.0
    p90 = percentile(latencies, 0.90)
    p95 = percentile(latencies, 0.95)
    p99 = percentile(latencies, 0.99)
    min_lat = min(latencies) if latencies else 0.0
    max_lat = max(latencies) if latencies else 0.0
    avg_lat = statistics.mean(latencies) if latencies else 0.0
    rps = total_requests / total_time_sec if total_time_sec > 0 else 0.0

    report = {
        "author": "Shivraj Dhote",
        "task_id": "S8-API-03",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "workload_profile": {
            "concurrency": concurrency,
            "iterations_per_worker": iterations_per_worker,
            "endpoints_tested": len(endpoints),
            "total_requests": total_requests,
            "total_time_sec": round(total_time_sec, 3),
            "throughput_rps": round(rps, 2),
        },
        "reliability_metrics": {
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate_pct": round((successful_requests / total_requests) * 100, 2) if total_requests else 0,
        },
        "latency_percentiles_ms": {
            "min": round(min_lat, 2),
            "avg": round(avg_lat, 2),
            "p50": round(p50, 2),
            "p90": round(p90, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
            "max": round(max_lat, 2),
        },
        "sla_assessment": {
            "p95_under_500ms": p95 < 500.0,
            "zero_http_500_errors": failed_requests == 0,
            "status": "PASSED" if (failed_requests == 0 and p95 < 500.0) else "FAILED",
        },
    }

    os.makedirs("backend/reports", exist_ok=True)
    out_path = "backend/reports/load_and_reliability_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    print("=" * 65)
    print("FINEX SPRINT 8: API LOAD & RELIABILITY BENCHMARK RUNNER")
    print("Author: Shivraj Dhote | Task: S8-API-03")
    print("=" * 65)
    res = run_benchmark(concurrency=10, iterations_per_worker=4)
    print(f"Total Requests: {res['workload_profile']['total_requests']}")
    print(f"Throughput: {res['workload_profile']['throughput_rps']} req/s")
    print(f"Success Rate: {res['reliability_metrics']['success_rate_pct']}%")
    print(f"Latency P50: {res['latency_percentiles_ms']['p50']} ms")
    print(f"Latency P95: {res['latency_percentiles_ms']['p95']} ms")
    print(f"Latency P99: {res['latency_percentiles_ms']['p99']} ms")
    print(f"SLA Status: {res['sla_assessment']['status']}")
    print("=" * 65)
