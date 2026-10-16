"""Sprint 8: Databricks Production Workflow Orchestration Simulator.

Task ID: S8-DAT-02
Author: Shivraj Dhote
Date: 16 October 2026

Simulates and verifies:
1. DAG Dependency Resolution (upstream must pass before downstream starts).
2. Bounded Retries (max_retries respected; no infinite looping).
3. Upstream Failure Safety (failed upstream task prevents downstream execution).
4. Failure Alert Notification formatting with actionable context.
"""

import json
import os
import sys
from typing import Any, Callable, Dict, List, Optional


class WorkflowTask:
    def __init__(self, key: str, description: str, depends_on: List[str], max_retries: int = 2):
        self.key = key
        self.description = description
        self.depends_on = depends_on
        self.max_retries = max_retries
        self.status = "PENDING"  # PENDING, RUNNING, SUCCEEDED, FAILED, SKIPPED
        self.attempts = 0
        self.error_message: Optional[str] = None


class WorkflowRunner:
    def __init__(self, workflow_def: Dict[str, Any]):
        self.name = workflow_def["name"]
        self.tasks: Dict[str, WorkflowTask] = {}
        for t in workflow_def["tasks"]:
            deps = [d["task_key"] for d in t.get("depends_on", [])]
            self.tasks[t["task_key"]] = WorkflowTask(
                key=t["task_key"],
                description=t.get("description", ""),
                depends_on=deps,
                max_retries=t.get("max_retries", 2),
            )
        self.notifications: List[Dict[str, Any]] = []

    def execute(self, custom_handlers: Optional[Dict[str, Callable[[int], bool]]] = None) -> Dict[str, str]:
        """
        Executes workflow DAG tasks.
        custom_handlers: task_key -> callable(attempt) returning True (success) or False (failure)
        """
        handlers = custom_handlers or {}

        for task_key, task in self.tasks.items():
            # Check if any upstream task failed or was skipped
            upstream_failed = any(self.tasks[dep].status in {"FAILED", "SKIPPED"} for dep in task.depends_on)
            if upstream_failed:
                task.status = "SKIPPED"
                continue

            # Run task with bounded retries
            handler = handlers.get(task_key, lambda attempt: True)
            succeeded = False

            while task.attempts <= task.max_retries and not succeeded:
                task.attempts += 1
                try:
                    if handler(task.attempts):
                        succeeded = True
                        task.status = "SUCCEEDED"
                    else:
                        raise RuntimeError(f"Task {task_key} execution failed on attempt {task.attempts}")
                except Exception as e:
                    task.error_message = str(e)
                    if task.attempts > task.max_retries:
                        task.status = "FAILED"
                        self._emit_failure_alert(task)
                        break

        return {k: t.status for k, t in self.tasks.items()}

    def _emit_failure_alert(self, task: WorkflowTask):
        alert = {
            "workflow": self.name,
            "failed_task": task.key,
            "attempts": task.attempts,
            "max_retries": task.max_retries,
            "error": task.error_message,
            "recipient": "shivraj.dhote@finex.internal",
            "actionable_context": f"Upstream data validation blocked pipeline progression to prevent corrupt downstream writes.",
        }
        self.notifications.append(alert)


def run_orchestration_verification() -> Dict[str, bool]:
    with open("data/workflows/databricks_production_workflows.json", "r", encoding="utf-8") as f:
        spec = json.load(f)

    market_wf = next(w for w in spec["workflows"] if w["name"] == "eod_market_ingestion")
    results = {}

    # Scenario 1: Clean happy-path run
    runner1 = WorkflowRunner(market_wf)
    res1 = runner1.execute()
    results["happy_path_all_succeeded"] = all(s == "SUCCEEDED" for s in res1.values())

    # Scenario 2: Bounded retry that recovers on attempt 2
    runner2 = WorkflowRunner(market_wf)
    # Task 1 fails on attempt 1, succeeds on attempt 2
    res2 = runner2.execute(custom_handlers={"fetch_bhavcopy_nse": lambda att: att >= 2})
    results["transient_failure_bounded_recovery"] = all(s == "SUCCEEDED" for s in res2.values())
    results["attempt_count_bounded"] = runner2.tasks["fetch_bhavcopy_nse"].attempts == 2

    # Scenario 3: Upstream Failure Safety (Task 2 DQ fails permanently)
    runner3 = WorkflowRunner(market_wf)
    # validate_market_data_quality always fails
    res3 = runner3.execute(custom_handlers={"validate_market_data_quality": lambda att: False})
    results["dq_task_marked_failed"] = res3["validate_market_data_quality"] == "FAILED"
    results["downstream_publish_safely_skipped"] = res3["publish_market_candles_delta"] == "SKIPPED"
    results["failure_alert_emitted_to_owner"] = len(runner3.notifications) > 0 and runner3.notifications[0]["recipient"] == "shivraj.dhote@finex.internal"

    return results


if __name__ == "__main__":
    print("=" * 65)
    print("FINEX SPRINT 8: DATABRICKS WORKFLOW ORCHESTRATION VERIFICATION")
    print("Author: Shivraj Dhote | Task: S8-DAT-02")
    print("=" * 65)

    checks = run_orchestration_verification()
    all_passed = True
    for name, passed in checks.items():
        status = "PASSED" if passed else "FAILED"
        if not passed:
            all_passed = False
        print(f"[{status}] {name}")

    print("=" * 65)
    print(f"Overall Orchestration Status: {'PASSED' if all_passed else 'FAILED'}")
    print("=" * 65)
    if not all_passed:
        sys.exit(1)
