"""Run each scenario once against its target, then apply all selected evaluators."""
import json
import math
import time
from pathlib import Path
from ai_eval.catalog import REQUIRES, validate_metrics
from ai_eval.core import NotApplicable, get_actual
from ai_eval.reporting import summarize, write_result
from ai_eval.python_lib import PythonBackend
from ai_eval.ragas_framework import RagasBackend
from ai_eval.judge_llm import JudgeBackend

BACKENDS = {"python_lib": PythonBackend, "ragas_framework": RagasBackend, "judge_llm": JudgeBackend}


# Purpose: validate run selection and thresholds before contacting any external endpoint.
def validate_run(cases, config):
    selected = config.get("backends", ["python_lib"])
    if not isinstance(selected, list) or not selected or len(set(selected)) != len(selected) or set(selected) - BACKENDS.keys():
        raise ValueError("backends must be a nonempty unique list of registered backend names")
    for case in cases:
        metrics = case.get("metrics", config.get("metrics", ["f1", "string_checker"]))
        if not isinstance(metrics, list) or not metrics or not all(isinstance(x, str) for x in metrics) or len(set(metrics)) != len(metrics):
            raise ValueError("metrics must be a nonempty unique list")
        validate_metrics(metrics)
    for case in cases:
        exclusions = case.get("not_applicable", {})
        if not isinstance(exclusions, dict) or not all(isinstance(reason, str) and reason.strip() for reason in exclusions.values()):
            raise ValueError("not_applicable must map metric IDs to nonempty reasons")
        validate_metrics(exclusions)
    for threshold in [config.get("threshold", 3), *config.get("thresholds", {}).values()]:
        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not math.isfinite(threshold) or not 0 <= threshold <= 5:
            raise ValueError("Thresholds must be finite numbers in [0, 5]")


# Purpose: redact configured secret values and endpoint URLs from diagnostic messages.
def safe_error(error, config):
    message = f"{type(error).__name__}: {error}"
    # Purpose: recursively remove secret configuration values from an exception string.
    def redact(value):
        nonlocal message
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"headers", "api_key", "url"}:
                    for secret in (item.values() if isinstance(item, dict) else [item]):
                        if isinstance(secret, str) and secret:
                            message = message.replace(secret, "[redacted]")
                else:
                    redact(item)
        elif isinstance(value, list):
            for item in value:
                redact(item)
    redact(config)
    return message


# Purpose: produce durable per-evaluation results while isolating target and evaluator failures.
def run(cases, config, output):
    validate_run(cases, config)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError("Output directory must be empty; choose a new directory for each run")
    backends = {name: BACKENDS[name](config.get(name, {})) for name in config.get("backends", ["python_lib"])}
    results = []
    for case in cases:
        target_error = None
        try:
            evidence = get_actual(config["target"], case)
        except Exception as error:
            evidence, target_error = case, safe_error(error, config)
        for name, backend in backends.items():
            for metric in case.get("metrics", config.get("metrics", ["f1", "string_checker"])):
                threshold = config.get("thresholds", {}).get(metric, config.get("threshold", 3))
                result = {"scenario_id": case["id"], "backend": name, "metric": metric,
                          "score": None, "threshold": threshold, "run_name": config.get("run_name", ""), "started": int(time.time() * 1000)}
                try:
                    if target_error:
                        raise RuntimeError("Target request failed: " + target_error)
                    if metric in case.get("not_applicable", {}):
                        raise NotApplicable(case["not_applicable"][metric])
                    requirements = REQUIRES.get(metric, [])
                    if name == "python_lib" and metric == "protected_material" and config.get(name, {}).get("engine", "azure") == "azure":
                        requirements = []
                    missing = [field for field in requirements if field not in evidence or evidence[field] in (None, "") or (evidence[field] == [] and field not in {"tool_calls", "retrieved_documents"})]
                    if missing:
                        raise NotApplicable("Missing evidence: " + ", ".join(missing))
                    score, raw = backend.evaluate(metric, evidence)
                    if not math.isfinite(score) or not 0 <= score <= 5:
                        raise ValueError("Backend score must be finite and between 0 and 5")
                    result.update(score=score, status="passed" if score >= threshold else "failed",
                                  reason=f"Score {score:.3f}/5; required {threshold}/5",
                                  implementation=raw.get("implementation", raw.get("native_metric", name)))
                    if config.get("attach_evidence", False):
                        result["raw"] = raw
                except NotApplicable as error:
                    result.update(status="skipped", reason=str(error))
                except Exception as error:
                    result.update(status="error", reason=safe_error(error, config))
                results.append(result)
                write_result(output / "allure-results", evidence, result, config.get("attach_evidence", False))
    summary = summarize(results)
    (output / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return summary
