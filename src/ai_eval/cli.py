"""Command-line entry point for reusable evaluation runs."""
import argparse
import json
from datetime import datetime, timezone
from ai_eval.core import load_cases, resolve_env
from ai_eval.runner import run


# Purpose: load a configured run, publish Allure files, and return a CI-friendly exit code.
def main():
    parser = argparse.ArgumentParser(description="Evaluate chatbot scenarios with scores out of five")
    parser.add_argument("--data", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", default="reports/" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    args = parser.parse_args()
    try:
        with open(args.config, encoding="utf-8") as stream:
            config = resolve_env(json.load(stream))
        summary = run(load_cases(args.data), config, args.output)
    except (ValueError, KeyError, OSError) as error:
        print(f"Configuration/input error ({type(error).__name__}). Check the dataset, paths, environment variables, and config.")
        return 2
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, indent=2))
    print("Report files: " + args.output)
    counts = summary["counts"]
    return 1 if counts["failed"] or counts["error"] or not summary["evaluated"] or (config.get("fail_on_skip", False) and counts["skipped"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
