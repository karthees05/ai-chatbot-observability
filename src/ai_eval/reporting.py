"""Allure 2 result files and machine-readable summaries, without a pytest runtime."""
import hashlib
import json
import time
import uuid
from pathlib import Path


# Purpose: write one standard Allure test result per scenario/backend/metric.
def write_result(directory, case, result, attach_evidence=False):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    identity = f"{case['id']}::{result['backend']}::{result['metric']}"
    if result.get("run_name"):
        identity = result["run_name"] + "::" + identity
    uid = str(uuid.uuid4())
    now = int(time.time() * 1000)
    attachments = []
    if attach_evidence:
        source = uid + "-attachment.json"
        (directory / source).write_text(json.dumps({"scenario": case, "evaluation": result}, indent=2, default=str), encoding="utf-8")
        attachments.append({"name": "Actual, expected, and evaluator output", "source": source, "type": "application/json"})
    status = {"passed": "passed", "failed": "failed", "skipped": "skipped", "error": "broken"}[result["status"]]
    document = {"uuid": uid, "historyId": hashlib.sha256(identity.encode()).hexdigest(),
                "testCaseId": hashlib.sha256(identity.encode()).hexdigest(), "name": identity,
                "fullName": identity, "description": case["description"], "status": status,
                "stage": "finished", "start": result.get("started", now), "stop": now,
                "statusDetails": {"message": result.get("reason", "")},
                "labels": [{"name": "parentSuite", "value": result.get("run_name") or "Evaluation"}, {"name": "suite", "value": result["backend"]}, {"name": "feature", "value": result["metric"]}, {"name": "implementation", "value": result.get("implementation", result["backend"])}],
                "parameters": [{"name": "score / 5", "value": str(result.get("score"))}, {"name": "threshold / 5", "value": str(result["threshold"])}],
                "attachments": attachments}
    (directory / (uid + "-result.json")).write_text(json.dumps(document, indent=2), encoding="utf-8")


# Purpose: summarize coverage and scores while excluding unscored evaluations from the mean.
def summarize(results):
    counts = {status: sum(r["status"] == status for r in results) for status in ("passed", "failed", "skipped", "error")}
    scores = [r["score"] for r in results if r.get("score") is not None]
    return {"counts": counts, "evaluated": len(scores), "total": len(results),
            "mean_score_out_of_5": sum(scores) / len(scores) if scores else None, "results": results}
