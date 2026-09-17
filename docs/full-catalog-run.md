# Full-catalog local evaluation

The previous smoke profile selects only F1 and coherence. To run every registered evaluator, use this profile instead:

```sh
source .venv/bin/activate
export NLTK_DATA="$PWD/.venv/nltk_data"
export RAGAS_DO_NOT_TRACK=true
# Start the model service in a separate terminal:
OLLAMA_HOST=127.0.0.1:11435 ollama serve
```

In the evaluation terminal:

```sh
OLLAMA_HOST=127.0.0.1:11435 ollama pull qwen2.5:0.5b
OLLAMA_HOST=127.0.0.1:11435 ollama pull nomic-embed-text
PYTHONPATH=src:. python scripts/run_full_catalog.py --output reports/full-catalog
allure generate reports/full-catalog/local/allure-results reports/full-catalog/native-azure/allure-results -o reports/full-catalog/html --clean
allure open reports/full-catalog/html
```

Install `.[local,ragas]` and WordNet as described in the setup guide. Install `.[python]` as well if you configure real Azure native services. Output directories must be fresh. The full run takes longer than the smoke run because many metrics invoke a model separately.

## Scope and honest evidence

- [Configuration](../examples/local-full-catalog.json): all **32** metric IDs across all **three** backends.
- [Scenario data](../data/full_catalog_scenarios.json): two controlled scenarios, a returns-policy question and safe SQL generation. They retain the required Questions, Ground_Truths and Descriptions columns plus independent reference labels and applicable criteria.
- [Sample assistant](../examples/rag_chatbot.py): performs actual lexical retrieval over a small independent demo corpus, calls Qwen with the retrieved text, and returns the exact contexts, document rankings and tool calls used. It never reads the evaluation dataset or its ground truths.
- Tool selection is scripted by the sample workflow; it is not autonomous tool selection by Qwen. Tool accuracy therefore evaluates that observed workflow trace.
- The script first obtains baseline and attacked model responses and scores each with the same safety judge. The direct-attack calculation uses those measured scores; the responses/verdicts are retained in the prepared scenario artifact. The endpoint caches responses by question so the baseline and later evaluated response remain the same within the run.
- Document relevance labels are authored in the scenario data, independently of retrieval scores. Local NDCG evaluates the observed ranking against them.
- Task instructions match the actual system instructions sent to the target. Conversation grounding uses the sample corpus statement about a fictional staff member.
- Protected-material comparison uses an explicitly synthetic reference passage. This exercises a rubric-based comparison; it does not validate copyright detection.
- Code-vulnerability evaluation is explicitly not applicable to the policy-answer scenario; that row is skipped with a reason in every module. It runs on the code-generation scenario.

This produces **192 local rows**. A separate suite requests **20 native Azure safety/groundedness checks** against the same responses. Without a configured Foundry project and usable credentials these remain visible as skipped. Local rubric scores must not be presented as native Azure detector results.

## Results and configuration additions

The runner now supports:

| Field | Purpose |
|---|---|
| Configuration `run_name` | Separates named suites and Allure test identities, so native and local checks are not mistaken for retries |
| Scenario `not_applicable` | Object mapping metric IDs to explicit exclusion reasons; rows remain visible as skipped |

Example: `"not_applicable": {"code_vulnerability": "This scenario does not request generated code."}`. CSV may encode this object as a quoted JSON cell.

The report includes all metric names even when an evaluation is skipped. A failed score remains a failure; malformed model output or a runtime failure remains broken. Missing native Azure project configuration is skipped before importing optional cloud dependencies. Structured model-labeling requests extend the configured JSON schema to include the required label.

Artifacts under the output directory:

- `prepared-scenarios.json`: input cases plus the actual baseline/attack measurement evidence.
- `run-config.json`: the local run's actual endpoint and evaluator settings.
- `local/summary.json`, `local/allure-results/`: the three-module full local run.
- `native-azure/summary.json`, `native-azure/allure-results/`: native service results or explicit availability skips.
- `summary.json`: combined results with per-test status and implementation details.
- `html/`: generated combined Allure report.

This is an integration demonstration with a small local model and a synthetic corpus. Use your real endpoint, observed traces, approved references, and calibrated judge for a meaningful release benchmark.
