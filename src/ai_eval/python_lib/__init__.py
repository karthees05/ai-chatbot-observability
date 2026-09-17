"""Python standard-library checks and Azure AI Evaluation SDK adapters."""
import importlib
from collections import Counter
import re
from ai_eval.core import NotApplicable, score_out_of_five
from .local_metrics import LOCAL_METRICS, evaluate_local

QUALITY = {name: name.title().replace("_", "") + "Evaluator" for name in (
    "coherence", "fluency", "similarity", "retrieval", "groundedness", "relevance",
    "response_completeness", "intent_resolution", "task_adherence", "tool_call_accuracy")}
CLASSES = {**QUALITY, "f1": "F1ScoreEvaluator", "bleu": "BleuScoreEvaluator",
    "gleu": "GleuScoreEvaluator", "rouge": "RougeScoreEvaluator", "meteor": "MeteorScoreEvaluator",
    "document_retrieval": "DocumentRetrievalEvaluator", "groundedness_pro": "GroundednessProEvaluator",
    "hate_unfairness": "HateUnfairnessEvaluator", "sexual": "SexualEvaluator", "violence": "ViolenceEvaluator",
    "self_harm": "SelfHarmEvaluator", "content_safety": "ContentSafetyEvaluator",
    "protected_material": "ProtectedMaterialEvaluator", "code_vulnerability": "CodeVulnerabilityEvaluator",
    "ungrounded_attributes": "UngroundedAttributesEvaluator", "indirect_attack": "IndirectAttackEvaluator"}
SAFETY = {"hate_unfairness", "sexual", "violence", "self_harm"}
HOSTED = SAFETY | {"content_safety", "protected_material", "code_vulnerability", "ungrounded_attributes", "groundedness_pro", "indirect_attack"}


class PythonBackend:
    # Purpose: retain SDK constructor overrides and reuse evaluator instances.
    def __init__(self, config):
        self.config, self.cache = config, {}

    # Purpose: evaluate exact local checks or invoke the official Python evaluation library.
    def evaluate(self, metric, case):
        if metric in LOCAL_METRICS and (self.config.get("engine", "azure") == "local" or metric in {"text_similarity", "direct_attack", "custom"}):
            return evaluate_local(metric, case, self.config)
        if metric in {"model_labeler", "model_scorer"} or (self.config.get("engine") == "local" and metric in set(QUALITY) | HOSTED):
            from ai_eval.judge_llm import JudgeBackend
            if "judge" not in self.config:
                raise NotApplicable("Configure python_lib.judge for local-engine rubric evaluations")
            score, raw = JudgeBackend(self.config["judge"]).evaluate(metric, case)
            return score, {"implementation": "delegated judge_llm", "result": raw}
        if metric == "string_checker":
            operation = self.config.get("string_operation", "eq")
            actual, expected = case["response"], case["ground_truth"]
            checks = {"eq": actual == expected, "ne": actual != expected,
                      "like": expected in actual, "ilike": expected.casefold() in actual.casefold()}
            if operation not in checks:
                raise ValueError("string_operation must be eq, ne, like, or ilike")
            raw = checks[operation]
            return score_out_of_five(raw), {"match": raw, "operation": operation}
        if metric == "f1" and self.config.get("local_f1", True):
            expected = Counter(re.findall(r"\w+", case["ground_truth"].casefold()))
            actual = Counter(re.findall(r"\w+", case["response"].casefold()))
            total = sum(expected.values()) + sum(actual.values())
            raw = 2 * sum((expected & actual).values()) / total if total else 0.0
            return score_out_of_five(raw), {"f1": raw, "implementation": "casefolded Unicode word tokens; multiset overlap"}
        if metric not in CLASSES:
            raise NotApplicable("Use judge_llm for model_labeler/model_scorer/text_similarity; Azure grader APIs are not wrapped")
        if metric in HOSTED and not self.config.get("azure_ai_project"):
            raise NotApplicable("Native Azure detector not run: azure_ai_project and authenticated Azure credentials are not configured")
        if metric in QUALITY and not self.config.get("model_config"):
            raise NotApplicable("Native Azure quality evaluator not run: model_config is not configured")
        if metric not in self.cache:
            sdk = importlib.import_module("azure.ai.evaluation")
            kwargs = dict(self.config.get("evaluators", {}).get(metric, {}))
            if metric in QUALITY:
                kwargs.setdefault("model_config", self.config["model_config"])
            if metric in HOSTED:
                from azure.identity import DefaultAzureCredential
                kwargs.setdefault("azure_ai_project", self.config["azure_ai_project"])
                kwargs["credential"] = DefaultAzureCredential()
            if metric == "rouge":
                kwargs["rouge_type"] = sdk.RougeType(kwargs.get("rouge_type", "rougeL"))
            self.cache[metric] = getattr(sdk, CLASSES[metric])(**kwargs)
        inputs = {"query": case["question"], "response": case["response"], "ground_truth": case["ground_truth"]}
        if metric in {"f1", "bleu", "gleu", "rouge", "meteor", "response_completeness"}:
            inputs = {k: inputs[k] for k in ("response", "ground_truth")}
        if metric in {"retrieval", "groundedness", "groundedness_pro", "indirect_attack"}:
            inputs["context"] = "\n\n".join(case["contexts"])
        if metric == "document_retrieval":
            inputs = {k: case[k] for k in ("retrieval_ground_truth", "retrieved_documents")}
        if metric == "tool_call_accuracy":
            inputs = {"query": case["question"], "tool_calls": case["tool_calls"], "tool_definitions": case["tool_definitions"]}
        if metric == "task_adherence":
            inputs["query"] = case["instructions"] + "\n\n" + case["question"]
        if metric == "ungrounded_attributes":
            inputs["context"] = str(case["conversation"])
        inputs.update(case.get("sdk_inputs", {}).get(metric, {}))
        result = self.cache[metric](**inputs)
        return normalize_sdk(metric, result, self.config.get("score_mappings", {}).get(metric)), result


# Purpose: interpret explicit SDK result keys and native score directions without guessing.
def normalize_sdk(metric, result, override=None):
    if override:
        return score_out_of_five(result[override["key"]], override.get("min", 0), override.get("max", 1), override.get("higher_is_better", True))
    if metric in QUALITY:
        if metric == "task_adherence" and metric not in result:
            verdict = result["task_adherence_result"]
            if verdict not in {"pass", "fail"}:
                raise ValueError("Unknown task adherence verdict")
            return 5.0 if verdict == "pass" else 0.0
        # Preserve native 1–5 quality scores rather than rescaling their lower bound.
        score_out_of_five(result[metric], 1, 5)
        return float(result[metric])
    if metric in SAFETY:
        return score_out_of_five(result[metric + "_score"], 0, 7, False)
    if metric == "content_safety":
        return min(normalize_sdk(name, result) for name in SAFETY)
    if metric == "groundedness_pro":
        value = result["groundedness_pro_label"]
        if not isinstance(value, bool):
            raise ValueError("Expected a boolean groundedness label")
        return score_out_of_five(value)
    if metric == "indirect_attack":
        value = result["xpia_label"]
        if not isinstance(value, bool):
            raise ValueError("Expected boolean indirect attack label")
        return score_out_of_five(value, higher_is_better=False)
    if metric in {"protected_material", "code_vulnerability", "ungrounded_attributes"}:
        key = {"protected_material": "protected_material", "code_vulnerability": "code_vulnerability", "ungrounded_attributes": "ungrounded_attributes"}[metric]
        value = result[key + "_label"]
        if not isinstance(value, bool):
            raise ValueError("Expected a boolean risk label; configure score_mappings for this SDK version")
        return score_out_of_five(value, higher_is_better=False)
    key = {"f1": "f1_score", "bleu": "bleu_score", "gleu": "gleu_score", "meteor": "meteor_score", "rouge": "rouge_f1_score", "document_retrieval": "ndcg@3"}[metric]
    return score_out_of_five(result[key])
