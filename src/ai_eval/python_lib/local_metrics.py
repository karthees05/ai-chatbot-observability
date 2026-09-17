"""Deterministic, local alternatives with explicit algorithms and native outputs."""
import importlib
import math
import re
from difflib import SequenceMatcher
from ai_eval.core import score_out_of_five

LOCAL_METRICS = {"bleu", "gleu", "rouge", "meteor", "document_retrieval", "text_similarity", "direct_attack", "custom"}


# Purpose: tokenize consistently without implicit corpus downloads.
def tokens(text):
    return re.findall(r"\w+", text.casefold())


# Purpose: compute local lexical, retrieval, paired-risk, or registered custom scores.
def evaluate_local(metric, case, config):
    reference, response = tokens(case["ground_truth"]), tokens(case["response"])
    if metric == "bleu":
        from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
        raw = sentence_bleu([reference], response, smoothing_function=SmoothingFunction().method1) if response and reference else 0.0
        details = {"implementation": "nltk sentence_bleu; uniform 1–4 grams; smoothing method1", "native_score": raw}
    elif metric == "gleu":
        from nltk.translate.gleu_score import sentence_gleu
        raw = sentence_gleu([reference], response) if response and reference else 0.0
        details = {"implementation": "nltk sentence_gleu; 1–4 grams", "native_score": raw}
    elif metric == "meteor":
        from nltk.translate.meteor_score import single_meteor_score
        raw = single_meteor_score(reference, response) if response and reference else 0.0
        details = {"implementation": "nltk METEOR with WordNet synonyms and Porter stemming", "native_score": raw}
    elif metric == "rouge":
        from rouge_score.rouge_scorer import RougeScorer
        result = RougeScorer(["rougeL"], use_stemmer=True).score(case["ground_truth"], case["response"])["rougeL"]
        raw = result.fmeasure
        details = {"implementation": "rouge-score ROUGE-L F1", "precision": result.precision, "recall": result.recall, "native_score": raw}
    elif metric == "text_similarity":
        raw = SequenceMatcher(None, case["ground_truth"].casefold(), case["response"].casefold(), autojunk=False).ratio()
        details = {"implementation": "difflib character similarity; not semantic similarity", "native_score": raw}
    elif metric == "document_retrieval":
        raw, details = document_retrieval(case, config.get("top_k", 3))
    elif metric == "direct_attack":
        # Values must come from paired baseline/attack safety runs with the same evaluator.
        baseline, attacked = float(case["baseline_safety_score"]), float(case["attack_safety_score"])
        score_out_of_five(baseline, 0, 5)
        score_out_of_five(attacked, 0, 5)
        raw = 1 - max(0, baseline - attacked) / 5
        details = {"implementation": "paired safety degradation; not standalone harm severity",
                   "baseline_safety_score": baseline, "attack_safety_score": attacked,
                   "degradation": max(0, baseline - attacked), "native_score": raw}
    elif metric == "custom":
        # Configuration is trusted application code; dataset rows cannot select imports.
        specification = config["custom_evaluator"]
        module, function = specification["callable"].split(":", 1)
        result = getattr(importlib.import_module(module), function)(dict(case))
        score = score_out_of_five(result["score"], specification.get("min", 0), specification.get("max", 1), specification.get("higher_is_better", True))
        return score, {"implementation": specification["callable"], "result": result}
    else:
        raise ValueError(f"Unknown local metric: {metric}")
    return score_out_of_five(raw), details


# Purpose: measure ranking against independent relevance labels, preserving retrieval diagnostics.
def document_retrieval(case, top_k):
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    labels = {}
    for item in case["retrieval_ground_truth"]:
        key, relevance = str(item["document_id"]), float(item["query_relevance_label"])
        if key in labels or not math.isfinite(relevance) or relevance < 0:
            raise ValueError("Relevance labels must be finite, nonnegative and have unique IDs")
        labels[key] = relevance
    ids = [str(item["document_id"]) for item in case["retrieved_documents"]]
    if len(set(ids)) != len(ids):
        raise ValueError("Retrieved document IDs must be unique and ordered by rank")
    if not labels or not any(labels.values()):
        raise ValueError("NDCG requires at least one positively labeled document")
    ranked = [labels.get(key, 0) for key in ids[:top_k]]
    ideal = sorted(labels.values(), reverse=True)[:top_k]
    # Purpose: compute linear-gain DCG with logarithmic rank discounting.
    def dcg(values):
        return sum(value / math.log2(rank + 2) for rank, value in enumerate(values))
    ndcg = dcg(ranked) / dcg(ideal)
    relevant = {key for key, value in labels.items() if value > 0}
    hits = len(set(ids[:top_k]) & relevant)
    holes = sum(key not in labels for key in ids[:top_k])
    return ndcg, {"implementation": "linear-gain NDCG; input list order is rank", f"ndcg@{top_k}": ndcg,
                  "precision_at_k": hits / top_k, "recall_at_k": hits / len(relevant),
                  "holes": holes, "holes_ratio": holes / len(ids[:top_k]) if ids else 0.0}
