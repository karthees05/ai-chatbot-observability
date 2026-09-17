"""Offline contract tests for transport, scoring, adapters, and reporting."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from ai_eval.core import load_cases, get_actual, score_out_of_five, resolve_env
from ai_eval.runner import run, safe_error
from ai_eval.python_lib import PythonBackend, normalize_sdk
from ai_eval.judge_llm import JudgeBackend
from ai_eval.ragas_framework import RagasBackend
from ai_eval.core import NotApplicable

CASE = {"id": "one", "question": "Capital?", "ground_truth": "Paris", "description": "Check capital"}
CONFIG = {"target": {"url": "http://localhost/chat"}, "metrics": ["f1", "string_checker"]}


class FrameworkTests(unittest.TestCase):
    # Purpose: verify CSV and JSON samples both honor the requested column aliases.
    def test_inputs(self):
        for extension in ("csv", "json"):
            cases = load_cases(f"examples/scenarios.{extension}")
            self.assertEqual(cases[0]["id"], "capital")
            self.assertTrue(cases[0]["ground_truth"])

    # Purpose: reject empty datasets and duplicate IDs before endpoint execution.
    def test_invalid_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            for value in ([], [CASE, CASE], [{"question": "only"}]):
                path.write_text(json.dumps(value))
                with self.assertRaises(ValueError):
                    load_cases(path)

    # Purpose: verify bounded normalization, inverse safety scales, and invalid outputs.
    def test_scales(self):
        self.assertEqual(score_out_of_five(0.8), 4)
        self.assertEqual(normalize_sdk("violence", {"violence_score": 7}), 0)
        self.assertEqual(normalize_sdk("coherence", {"coherence": 1}), 1)
        self.assertEqual(normalize_sdk("groundedness_pro", {"groundedness_pro_label": True}), 5)
        self.assertEqual(normalize_sdk("protected_material", {"protected_material_label": True}), 0)
        for value in (float("nan"), float("inf"), -1, 2):
            with self.assertRaises(ValueError):
                score_out_of_five(value)

    # Purpose: prove multiset F1 penalizes repeated unsupported words.
    def test_f1(self):
        score, _ = PythonBackend({}).evaluate("f1", dict(CASE, response="Paris Paris Paris"))
        self.assertEqual(score, 2.5)

    # Purpose: ensure target calls contain questions but never the expected answers.
    def test_target_mapping(self):
        with patch("ai_eval.core.post_json", return_value={"data": {"answer": "Paris", "context": ["Paris"]}}) as post:
            actual = get_actual({"response_path": "data.answer", "evidence_paths": {"contexts": "data.context"}}, CASE)
            self.assertEqual(actual["response"], "Paris")
            self.assertEqual(post.call_args.args[1], {"question": "Capital?"})

    # Purpose: verify one target call feeds all metrics and valid Allure artifacts are written.
    def test_run_report(self):
        with tempfile.TemporaryDirectory() as directory, patch("ai_eval.runner.get_actual", return_value=dict(CASE, response="Paris")) as target:
            summary = run([CASE], CONFIG, directory)
            self.assertEqual(target.call_count, 1)
            self.assertEqual(summary["counts"]["passed"], 2)
            reports = list((Path(directory) / "allure-results").glob("*-result.json"))
            self.assertEqual(len(reports), 2)
            report = json.loads(reports[0].read_text())
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["attachments"], [])

    # Purpose: distinguish missing evidence from endpoint failures in reports.
    def test_skip_and_error(self):
        with tempfile.TemporaryDirectory() as directory, patch("ai_eval.runner.get_actual", return_value=dict(CASE, response="Paris")):
            summary = run([CASE], dict(CONFIG, metrics=["groundedness"]), directory)
            self.assertEqual(summary["counts"]["skipped"], 1)
            self.assertIsNone(summary["mean_score_out_of_5"])
        with tempfile.TemporaryDirectory() as directory, patch("ai_eval.runner.get_actual", side_effect=TimeoutError("expired")):
            summary = run([CASE], CONFIG, directory)
            self.assertEqual(summary["counts"]["error"], 2)

    # Purpose: ensure unknown metrics fail before any billable target request.
    def test_invalid_metric(self):
        with tempfile.TemporaryDirectory() as directory, patch("ai_eval.runner.get_actual") as target:
            with self.assertRaises(ValueError):
                run([CASE], dict(CONFIG, metrics=["typo"]), directory)
            target.assert_not_called()

    # Purpose: validate judge JSON and prevent fabricated deterministic scores.
    def test_judge(self):
        judge = JudgeBackend({"model": "test"})
        with patch("ai_eval.judge_llm.post_json", return_value={"choices": [{"message": {"content": '{"score":4,"reason":"Evidence matches"}'}}]}):
            self.assertEqual(judge.evaluate("relevance", dict(CASE, response="Paris"))[0], 4)
        with patch("ai_eval.judge_llm.post_json", return_value={"choices": [{"message": {"content": '{"score":true,"reason":"bad"}'}}]}):
            with self.assertRaises(ValueError):
                judge.evaluate("relevance", dict(CASE, response="Paris"))
        with patch("ai_eval.judge_llm.post_json") as post:
            self.assertEqual(judge.evaluate("f1", dict(CASE, response="Paris"))[0], 5)
            post.assert_not_called()

    # Purpose: validate SDK invocation and score mapping without cloud credentials.
    def test_sdk_adapter(self):
        sdk = Mock()
        sdk.BleuScoreEvaluator.return_value.return_value = {"bleu_score": 0.6}
        with patch("ai_eval.python_lib.importlib.import_module", return_value=sdk):
            score, _ = PythonBackend({}).evaluate("bleu", dict(CASE, response="Paris"))
            self.assertEqual(score, 3)
            sdk.BleuScoreEvaluator.return_value.assert_called_once_with(response="Paris", ground_truth="Paris")

    # Purpose: prevent unsupported RAGAS metrics from silently using another evaluator.
    def test_ragas_unsupported(self):
        with self.assertRaises(NotApplicable):
            RagasBackend({}).evaluate("not_a_metric", CASE)

    # Purpose: keep configuration secrets out of exception diagnostics.
    def test_secret_redaction(self):
        self.assertNotIn("abc123", safe_error(ValueError("Bearer abc123"), {"target": {"headers": {"Authorization": "Bearer abc123"}}}))
        with patch.dict("os.environ", {"TEST_EVAL_VALUE": "resolved"}):
            self.assertEqual(resolve_env({"key": "${TEST_EVAL_VALUE}"}), {"key": "resolved"})


if __name__ == "__main__":
    unittest.main()
