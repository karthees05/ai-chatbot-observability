# Evaluator coverage

## Evaluators covered from Microsoft

Reference: [evaluator section](https://learn.microsoft.com/en-us/azure/foundry-classic/concepts/evaluation-evaluators/) and [built-in catalog](https://learn.microsoft.com/en-us/azure/foundry-classic/concepts/built-in-evaluators), reviewed 2026-09-15. The section URL has no readable index; the catalog and its linked category pages define this list. Direct/indirect attacks and custom evaluators come from the linked pages.

Every listed category has an execution route. Native algorithms, custom rubrics, and explicit delegation are distinguished below. A rubric is not an equivalent implementation of a specialized Microsoft detector. Required credentials and evidence still apply.


| Metric | Python library | RAGAS | Judge LLM | Additional evidence |
|---|---|---|---|---|
| `coherence` | CoherenceEvaluator | SimpleCriteriaScore custom rubric | LLM rubric (not Azure service) | Base question / actual / expected |
| `fluency` | FluencyEvaluator | SimpleCriteriaScore custom rubric | LLM rubric (not Azure service) | Base question / actual / expected |
| `similarity` | SimilarityEvaluator | SemanticSimilarity | LLM rubric (not Azure service) | Base question / actual / expected |
| `f1` | Local token F1 / F1ScoreEvaluator | Explicit Python module delegation | Explicit Python module delegation | Base question / actual / expected |
| `bleu` | BleuScoreEvaluator / local library alternative | BleuScore | Explicit Python module delegation | Base question / actual / expected |
| `gleu` | GleuScoreEvaluator / local library alternative | Explicit Python module delegation | Explicit Python module delegation | Base question / actual / expected |
| `rouge` | RougeScoreEvaluator / local library alternative | RougeScore | Explicit Python module delegation | Base question / actual / expected |
| `meteor` | MeteorScoreEvaluator / local library alternative | Explicit Python module delegation | Explicit Python module delegation | Base question / actual / expected |
| `retrieval` | RetrievalEvaluator | LLMContextPrecisionWithReference | LLM rubric (not Azure service) | contexts |
| `document_retrieval` | DocumentRetrievalEvaluator / local library alternative | Explicit Python module delegation | Explicit Python module delegation | retrieval_ground_truth, retrieved_documents |
| `groundedness` | GroundednessEvaluator | Faithfulness | LLM rubric (not Azure service) | contexts |
| `groundedness_pro` | GroundednessProEvaluator | SimpleCriteriaScore custom rubric | LLM rubric (not Azure service) | contexts |
| `relevance` | RelevanceEvaluator | ResponseRelevancy | LLM rubric (not Azure service) | Base question / actual / expected |
| `response_completeness` | ResponseCompletenessEvaluator | FactualCorrectness (recall mode) | LLM rubric (not Azure service) | Base question / actual / expected |
| `hate_unfairness` | HateUnfairnessEvaluator | SimpleCriteriaScore custom rubric | LLM rubric (not Azure service) | Base question / actual / expected |
| `sexual` | SexualEvaluator | SimpleCriteriaScore custom rubric | LLM rubric (not Azure service) | Base question / actual / expected |
| `violence` | ViolenceEvaluator | SimpleCriteriaScore custom rubric | LLM rubric (not Azure service) | Base question / actual / expected |
| `self_harm` | SelfHarmEvaluator | SimpleCriteriaScore custom rubric | LLM rubric (not Azure service) | Base question / actual / expected |
| `content_safety` | ContentSafetyEvaluator | SimpleCriteriaScore custom rubric | LLM rubric (not Azure service) | Base question / actual / expected |
| `protected_material` | ProtectedMaterialEvaluator | SimpleCriteriaScore custom rubric | LLM rubric (not Azure service) | protected_reference |
| `code_vulnerability` | CodeVulnerabilityEvaluator | SimpleCriteriaScore custom rubric | LLM rubric (not Azure service) | Base question / actual / expected |
| `ungrounded_attributes` | UngroundedAttributesEvaluator | SimpleCriteriaScore custom rubric | LLM rubric (not Azure service) | conversation |
| `intent_resolution` | IntentResolutionEvaluator | SimpleCriteriaScore custom rubric | LLM rubric (not Azure service) | Base question / actual / expected |
| `task_adherence` | TaskAdherenceEvaluator | SimpleCriteriaScore custom rubric | LLM rubric (not Azure service) | instructions |
| `tool_call_accuracy` | ToolCallAccuracyEvaluator | SimpleCriteriaScore custom rubric | LLM rubric (not Azure service) | tool_calls, tool_definitions |
| `model_labeler` | Configured judge delegation | Explicit Python module delegation | Validated label + passing-label score | rubric, labels, passing_labels |
| `string_checker` | Local computation | ExactMatch | Explicit Python module delegation | Base question / actual / expected |
| `text_similarity` | Local computation | SimpleCriteriaScore custom rubric | LLM rubric (not Azure service) | Base question / actual / expected |
| `indirect_attack` | IndirectAttackEvaluator | SimpleCriteriaScore custom rubric | LLM rubric (not Azure service) | contexts |
| `direct_attack` | Local computation | Explicit Python module delegation | Explicit Python module delegation | baseline_safety_score, attack_safety_score |
| `custom` | Local computation | Explicit Python module delegation | Explicit Python module delegation | Base question / actual / expected |
| `model_scorer` | Configured judge delegation | SimpleCriteriaScore custom rubric | LLM rubric (not Azure service) | rubric |
