"""Shared dataset, configuration, transport, and scoring contracts."""
from __future__ import annotations

import csv
import json
import math
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse


# Purpose: distinguish unavailable evidence/capabilities from evaluation failures.
class NotApplicable(Exception):
    pass


# Purpose: resolve explicit environment placeholders without storing credentials in files.
def resolve_env(value):
    if isinstance(value, dict):
        return {k: resolve_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_env(v) for v in value]
    if isinstance(value, str):
        return re.sub(r"\$\{([A-Z0-9_]+)\}", lambda m: os.environ[m[1]], value)
    return value


# Purpose: load JSON/CSV and normalize the user's column names to a shared schema.
def load_cases(path):
    path = Path(path)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        if path.suffix.lower() == ".csv":
            rows = list(csv.DictReader(stream))
        elif path.suffix.lower() == ".json":
            rows = json.load(stream)
        else:
            raise ValueError("Dataset must be .json or .csv")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Dataset must contain a nonempty array of scenarios")
    aliases = {"questions": "question", "ground_truths": "ground_truth", "descriptions": "description"}
    cases, ids = [], set()
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError(f"Scenario {index} must be an object")
        case = {}
        for key, value in row.items():
            name = str(key).strip().lower().replace(" ", "_")
            name = aliases.get(name, name)
            if name in case:
                raise ValueError(f"Duplicate normalized column: {name}")
            if name in {"contexts", "metrics", "tool_calls", "tool_definitions", "retrieval_ground_truth", "retrieved_documents", "sdk_inputs", "labels", "passing_labels", "not_applicable"} and isinstance(value, str) and value.strip():
                value = json.loads(value)
            case[name] = value
        for required in ("question", "ground_truth", "description"):
            if not isinstance(case.get(required), str) or not case[required].strip():
                raise ValueError(f"Scenario {index}: {required} must be nonempty text")
        case["id"] = str(case.get("id") or index)
        if case["id"] in ids:
            raise ValueError(f"Duplicate scenario id: {case['id']}")
        ids.add(case["id"])
        if "metrics" in case and (not isinstance(case["metrics"], list) or not case["metrics"] or not all(isinstance(x, str) for x in case["metrics"])):
            raise ValueError("metrics must be a nonempty JSON array of names")
        if "contexts" in case and (not isinstance(case["contexts"], list) or not all(isinstance(x, str) for x in case["contexts"])):
            raise ValueError("contexts must be a JSON array of strings")
        cases.append(case)
    return cases


# Purpose: read a nested response value using dotted dictionary keys and list indexes.
def at_path(value, path):
    for part in path.split(".") if path else []:
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


# Purpose: perform one bounded JSON POST without retrying stateful chatbot actions.
def post_json(config, payload):
    url = config["url"]
    parsed = urlparse(url)
    if parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}):
        raise ValueError("Endpoints require HTTPS, except for local development")
    request = Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **config.get("headers", {})}, method="POST")
    with urlopen(request, timeout=float(config.get("timeout", 60))) as response:
        return json.load(response)


# Purpose: query the chatbot once and retain optional retrieval and tool evidence.
def get_actual(config, case):
    payload = dict(config.get("body", {}))
    protocol = config.get("protocol", "json")
    if protocol in {"chat_completions", "ollama"}:
        payload["messages"] = [*payload.get("messages", []), {"role": "user", "content": case["question"]}]
        payload["stream"] = False
    elif protocol == "json":
        payload[config.get("question_field", "question")] = case["question"]
    else:
        raise ValueError("protocol must be json, chat_completions, or ollama")
    result = post_json(config, payload)
    actual = at_path(result, config.get("response_path", "response"))
    if not isinstance(actual, str):
        raise ValueError("Chatbot response_path must resolve to text")
    evidence = dict(case, response=actual)
    for field, path in config.get("evidence_paths", {}).items():
        if field not in {"contexts", "tool_calls", "tool_definitions", "retrieved_documents"}:
            raise ValueError(f"Unsupported endpoint evidence field: {field}")
        evidence[field] = at_path(result, path)
    if "contexts" in evidence and (not isinstance(evidence["contexts"], list) or not all(isinstance(x, str) for x in evidence["contexts"])):
        raise ValueError("Endpoint contexts must be a list of strings")
    return evidence


# Purpose: normalize an explicit native scale to 0–5, where higher always means better.
def score_out_of_five(raw, minimum=0, maximum=1, higher_is_better=True):
    number = float(raw)
    tolerance = 1e-12 * max(1, abs(minimum), abs(maximum))
    if not math.isfinite(number) or maximum <= minimum or not minimum - tolerance <= number <= maximum + tolerance:
        raise ValueError(f"Invalid score {number}; expected [{minimum}, {maximum}]")
    number = min(maximum, max(minimum, number))
    fraction = (number - minimum) / (maximum - minimum)
    return round(5 * (fraction if higher_is_better else 1 - fraction), 6)
