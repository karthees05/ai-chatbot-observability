# Module 3: Judge LLM

## Framework diagram and required inputs

![judge_llm flow](../../../docs/diagrams/judge-llm.svg)

[Open standalone SVG](../../../docs/diagrams/judge-llm.svg) · [New-user setup and every input field](../../../docs/new-user-setup.md)

Fill `target` for the chatbot being tested, then `judge_llm.url`, `model`, and authentication for model-backed judging. These are separate endpoints/settings. Supply `rubric`, `labels` and `passing_labels` for labeling; exact calculations use nested `judge_llm.python_lib` settings.

Every scenario must contain **Questions**, **Ground_Truths**, and **Descriptions**. The framework obtains the actual answer from your endpoint. Copy the [starter scenario](../../../examples/new-user/scenarios.json) and follow the linked guide for field types, sample values, credentials and optional evidence.

A separate model scores the chatbot's actual answer against the question, expected answer and relevant evidence. This is an LLM-as-judge implementation, not a dependency on a package named JudgeLLM.

```sh
python -m pip install -e .
# Export the CHATBOT_* and JUDGE_* variables in examples/judge.json.
ai-eval --data data/common_scenarios.json --config examples/judge.json --output reports/judge
allure serve reports/judge/allure-results
```

## Endpoint configuration

`target` obtains the actual answer; `judge_llm` is configured independently. The judge accepts a chat-completions-compatible URL, headers, model, optional body settings and timeout. `response_path` defaults to `choices.0.message.content`. The expected content is strict JSON:

```json
{"score":4,"reason":"The answer covers the expected facts with a minor omission."}
```

Only finite numeric 0–5 scores and nonempty reasons are accepted. A score of 5 is best, including safety. Invalid JSON, booleans and materially out-of-range scores become errors. Use `body.response_format` if the endpoint supports JSON output. [Ollama configuration](../../../examples/ollama.json) provides an open-weight local model alternative.

## Model labeling and exact calculations

`model_labeler` requires `rubric`, `labels`, and `passing_labels` in the scenario. The judge must also return a valid `label`; the framework assigns 5 for a passing label and 0 otherwise. `model_scorer` requires a rubric and reports the judge's 0–5 score.

F1, BLEU, GLEU, ROUGE, METEOR, exact string checks, document ranking, paired direct-attack comparison and custom Python checks delegate explicitly to `judge_llm.python_lib` (default local engine). The model is never asked to invent mathematical scores. Install `.[local]` for library-backed calculations. Delegation appears in the result's `implementation` field.

## Limits and verification

Quality, safety, agent, groundedness-pro and attack rubrics are assessments by the configured model, not equivalent implementations of Microsoft's hosted detectors. Contexts, tools, instructions and protected reference text are required where relevant. Missing evidence is skipped. Supplied evidence is treated as untrusted data in the judge prompt, but judge models can still be misled.

The ELIZA endpoint integration verifies this module's real deterministic delegation. Structured judge responses and invalid labels are covered by contract tests; those tests do not claim to measure a live LLM's judgment quality. The separate live Ollama integration script executes actual rubric requests with the same shared data; see the verification record for its results.

## Full evaluator run

The [full-catalog guide](../../../docs/full-catalog-run.md) runs every metric with actual local retrieval/tool evidence and separately lists native Azure availability. The ELIZA and Ollama module profiles below are focused integration tests, not complete catalog runs.

## Run this module's tests and Allure reports

All commands below run **from the repository root**, not from this module directory. The module-specific configurations select only `judge_llm`. They reuse the same [common JSON](../../../data/common_scenarios.json) or [CSV](../../../data/common_scenarios.csv) data.

### Sample chatbot sources and endpoint addresses

| Sample | Upstream implementation/model | Endpoint used here |
|---|---|---|
| ELIZA | [NLTK ELIZA](https://www.nltk.org/api/nltk.chat.eliza.html), exposed by our [HTTP adapter](../../../examples/eliza_chatbot.py) | `http://127.0.0.1:8766/v1/chat/completions` (also supports `/chat`) |
| Qwen via Ollama | [Qwen2.5-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct), hosted locally with [Ollama](https://docs.ollama.com/api/chat) | Target: `http://127.0.0.1:11435/api/chat`; judge: `http://127.0.0.1:11435/v1/chat/completions` |

These are local services you start, not public chatbot URLs copied from a website. ELIZA generates responses through its upstream rule-based implementation; Qwen generates responses using actual open model weights. Both were exercised in the [verification runs](../../../docs/verification.md). The older `mock_chatbot.py` is only a fixed-answer fixture and is not the open-source chatbot integration.

### A. Install and run the module's unit/library tests

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[local]'
python -m nltk.downloader -d .venv/nltk_data wordnet
export NLTK_DATA="$PWD/.venv/nltk_data"
export RAGAS_DO_NOT_TRACK=true
PYTHONPATH=src:tests python -m unittest \
  test_framework.FrameworkTests.test_judge \
  test_extended.ExtendedTests.test_labeler \
  test_extended.ExtendedTests.test_judge_delegation -v
```

These tests report to the terminal. The scenario runs below create Allure results. To run all shared tests, use `PYTHONPATH=src python -m unittest discover -s tests -v`; install `.[local,ragas]` to execute all optional library tests without skips. Native Azure use additionally requires `.[python]` and your service credentials.

### B. Run this module against ELIZA

Terminal 1, from the repository root:

```sh
source .venv/bin/activate
python examples/eliza_chatbot.py --port 8766
```

Terminal 2, also from the repository root:

```sh
source .venv/bin/activate
export NLTK_DATA="$PWD/.venv/nltk_data"
export RAGAS_DO_NOT_TRACK=true
ai-eval --data data/common_scenarios.json --config examples/modules/judge_llm-eliza.json --output reports/judge_llm-eliza
```

This runs 5 scenarios × 6 metrics = **30 evaluations for this module**. ELIZA cannot answer the factual geography question, so its quality failures and CLI exit code 1 are expected. Do not treat those scores as execution errors. The report is still generated. Use `.csv` instead of `.json` for the common CSV file and choose a different output directory.

The ELIZA profile exercises exact calculations; it does not use ELIZA as an LLM judge. For model-backed evaluations, use the next profile.

### C. Run this module's real LLM integration test

Install Ollama using its official instructions. Terminal 1:

```sh
OLLAMA_HOST=127.0.0.1:11435 ollama serve
```

Terminal 2, from the repository root:

```sh
source .venv/bin/activate
export RAGAS_DO_NOT_TRACK=true
OLLAMA_HOST=127.0.0.1:11435 ollama pull qwen2.5:0.5b
PYTHONPATH=src python scripts/run_llm_tests.py --config examples/modules/judge_llm-ollama.json --data data/common_scenarios.json --output reports/judge_llm-ollama
```

This runs 5 scenarios × 2 metrics = **10 evaluations for this module**. Coherence sends actual model-judge HTTP requests to Qwen. F1 is calculated by the shared Python route rather than guessed by the model.

The integration script exits successfully when the requests and scoring contracts work, even if quality scores fail. It raises an error for execution errors or skips. The small model and ELIZA-oriented expected phrases make this a connectivity/contract test, not a production quality benchmark. Stop servers with Ctrl+C when finished.

### D. Generate and view Allure

Install **Allure 2 CLI and Java** using the [Allure installation guide](https://allurereport.org/docs/install/). For an npm installation, `npm install --global allure-commandline@2` makes `allure` available on your PATH. The framework writes Allure result files directly; `allure-pytest` is not needed for these scenario commands.

View results directly in a temporary report:

```sh
allure serve reports/judge_llm-eliza/allure-results
```

Generate a persistent HTML report and open it through Allure's local server:

```sh
allure generate reports/judge_llm-eliza/allure-results -o reports/judge_llm-eliza/html --clean
allure open reports/judge_llm-eliza/html
```

For the real model run:

```sh
allure generate reports/judge_llm-ollama/allure-results -o reports/judge_llm-ollama/html --clean
allure open reports/judge_llm-ollama/html
```

Artifacts are `summary.json`, `allure-results/`, and (after generation) `html/` under the chosen run directory. Each test shows the score out of 5, threshold, status and implementation. These profiles enable attachments containing actual/expected responses and evaluator details. Serve HTML with `allure open`; directly opening `index.html` can prevent report data from loading.

Use a **fresh evaluation output directory** on every rerun. Allure's `--clean` only rebuilds its HTML directory; it does not make an existing evaluation output directory reusable.

<!-- COVERAGE START -->
## Evaluators covered from Microsoft

Reference: [evaluator section](https://learn.microsoft.com/en-us/azure/foundry-classic/concepts/evaluation-evaluators/) and [built-in catalog](https://learn.microsoft.com/en-us/azure/foundry-classic/concepts/built-in-evaluators), reviewed 2026-09-15. The section URL has no readable index; the catalog and its linked category pages define this list. Direct/indirect attacks and custom evaluators come from the linked pages.

Every listed category has an execution route. Native algorithms, custom rubrics, and explicit delegation are distinguished below. A rubric is not an equivalent implementation of a specialized Microsoft detector. Required credentials and evidence still apply.


| Metric ID | Execution in this module | Additional evidence |
|---|---|---|
| `coherence` | LLM rubric (not Azure service) | Base question / actual / expected |
| `fluency` | LLM rubric (not Azure service) | Base question / actual / expected |
| `similarity` | LLM rubric (not Azure service) | Base question / actual / expected |
| `f1` | Explicit Python module delegation | Base question / actual / expected |
| `bleu` | Explicit Python module delegation | Base question / actual / expected |
| `gleu` | Explicit Python module delegation | Base question / actual / expected |
| `rouge` | Explicit Python module delegation | Base question / actual / expected |
| `meteor` | Explicit Python module delegation | Base question / actual / expected |
| `retrieval` | LLM rubric (not Azure service) | contexts |
| `document_retrieval` | Explicit Python module delegation | retrieval_ground_truth, retrieved_documents |
| `groundedness` | LLM rubric (not Azure service) | contexts |
| `groundedness_pro` | LLM rubric (not Azure service) | contexts |
| `relevance` | LLM rubric (not Azure service) | Base question / actual / expected |
| `response_completeness` | LLM rubric (not Azure service) | Base question / actual / expected |
| `hate_unfairness` | LLM rubric (not Azure service) | Base question / actual / expected |
| `sexual` | LLM rubric (not Azure service) | Base question / actual / expected |
| `violence` | LLM rubric (not Azure service) | Base question / actual / expected |
| `self_harm` | LLM rubric (not Azure service) | Base question / actual / expected |
| `content_safety` | LLM rubric (not Azure service) | Base question / actual / expected |
| `protected_material` | LLM rubric (not Azure service) | protected_reference |
| `code_vulnerability` | LLM rubric (not Azure service) | Base question / actual / expected |
| `ungrounded_attributes` | LLM rubric (not Azure service) | conversation |
| `intent_resolution` | LLM rubric (not Azure service) | Base question / actual / expected |
| `task_adherence` | LLM rubric (not Azure service) | instructions |
| `tool_call_accuracy` | LLM rubric (not Azure service) | tool_calls, tool_definitions |
| `model_labeler` | Validated label + passing-label score | rubric, labels, passing_labels |
| `string_checker` | Explicit Python module delegation | Base question / actual / expected |
| `text_similarity` | LLM rubric (not Azure service) | Base question / actual / expected |
| `indirect_attack` | LLM rubric (not Azure service) | contexts |
| `direct_attack` | Explicit Python module delegation | baseline_safety_score, attack_safety_score |
| `custom` | Explicit Python module delegation | Base question / actual / expected |
| `model_scorer` | LLM rubric (not Azure service) | rubric |

With `python_lib.engine=local`, model-assisted Python evaluations use `python_lib.judge`; they are reported as delegated rubrics. Azure protected-material detection does not require a reference; local judge approximations do. Empty retrieved-document/tool-call arrays are valid observed outcomes; missing fields are skipped.

The direct-attack metric compares independently obtained baseline and attacked safety scores; it does not generate attacks. Custom Python functions come from trusted configuration. Azure grader-service APIs are not invoked: corresponding grader categories use local or judge implementations.

Common data: [JSON](../../../data/common_scenarios.json) / [CSV](../../../data/common_scenarios.csv). Run the [open-source endpoint tests](../../../docs/open-source-endpoint-tests.md).
<!-- COVERAGE END -->
