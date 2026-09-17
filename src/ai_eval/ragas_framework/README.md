# Module 1: RAGAS framework

## Framework diagram and required inputs

![ragas_framework flow](../../../docs/diagrams/ragas-framework.svg)

[Open standalone SVG](../../../docs/diagrams/ragas-framework.svg) · [New-user setup and every input field](../../../docs/new-user-setup.md)

Choose metrics first. Fill `target` and run settings for every run. Add `ragas_framework.llm` for model-backed metrics; add `embeddings` for similarity/relevance. Supply contexts when required. Delegated settings live in `ragas_framework.python_lib`.

Every scenario must contain **Questions**, **Ground_Truths**, and **Descriptions**. The framework obtains the actual answer from your endpoint. Copy the [starter scenario](../../../examples/new-user/scenarios.json) and follow the linked guide for field types, sample values, credentials and optional evidence.

Run native RAGAS metrics, RAGAS custom rubrics, and explicitly delegated exact computations against the actual chatbot response.

```sh
python -m pip install -e '.[local,ragas]'
# Set variables in examples/ragas.json for model-assisted RAGAS evaluations.
ai-eval --data data/common_scenarios.json --config examples/ragas.json --output reports/ragas
allure serve reports/ragas/allure-results
```

## Behavior and configuration

- Native lexical BLEU, ROUGE-L F1, and exact string match require no model. The ELIZA integration suite executes these real RAGAS classes.
- Groundedness, retrieval precision, response relevance and semantic similarity use native RAGAS metrics. Completeness uses `FactualCorrectness(mode="recall")` against the actual and expected responses, not context recall.
- Other model-assisted criteria use `SimpleCriteriaScore` with separate rubrics and 0–5 score anchors. This expands coverage without claiming to reproduce Azure's specialized detectors.
- F1, GLEU, METEOR, document retrieval, paired attack comparison and custom Python functions delegate to `ragas_framework.python_lib`. Model labeling also delegates; configure that section's `judge` to obtain validated labels.
- `llm` contains `ChatOpenAI` constructor settings; `embeddings` contains `OpenAIEmbeddings` settings. Models are initialized only when needed. `timeout` defaults to 120 seconds per evaluation.
- Native 0–1 outputs are multiplied by 5; custom 0–5 rubric outputs are retained. Tiny floating-point roundoff at score boundaries is tolerated; materially out-of-range and nonfinite values remain errors.

RAGAS `string_checker` is exact-match only. Python's checker supports additional operations. Delegated routes are visible in every result's `implementation` field, even when evidence attachments are disabled.

RAGAS model and embedding configurations are in [examples/ragas.json](../../../examples/ragas.json). An Ollama example is in [examples/ollama.json](../../../examples/ollama.json). The [RAGAS API](https://docs.ragas.io/en/v0.3.2/references/metrics/) documents the pinned 0.3.2 version.

## Full evaluator run

The [full-catalog guide](../../../docs/full-catalog-run.md) runs every metric with actual local retrieval/tool evidence and separately lists native Azure availability. The ELIZA and Ollama module profiles below are focused integration tests, not complete catalog runs.

## Run this module's tests and Allure reports

All commands below run **from the repository root**, not from this module directory. The module-specific configurations select only `ragas_framework`. They reuse the same [common JSON](../../../data/common_scenarios.json) or [CSV](../../../data/common_scenarios.csv) data.

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
python -m pip install -e '.[local,ragas]'
python -m nltk.downloader -d .venv/nltk_data wordnet
export NLTK_DATA="$PWD/.venv/nltk_data"
export RAGAS_DO_NOT_TRACK=true
PYTHONPATH=src:tests python -m unittest \
  test_extended.ExtendedTests.test_native_ragas \
  test_extended.ExtendedTests.test_ragas_completeness_contract \
  test_framework.FrameworkTests.test_ragas_unsupported -v
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
ai-eval --data data/common_scenarios.json --config examples/modules/ragas_framework-eliza.json --output reports/ragas_framework-eliza
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
PYTHONPATH=src python scripts/run_llm_tests.py --config examples/modules/ragas_framework-ollama.json --data data/common_scenarios.json --output reports/ragas_framework-ollama
```

This runs 5 scenarios × 2 metrics = **10 evaluations for this module**. F1 delegates to the shared Python calculation; coherence executes the real RAGAS SimpleCriteriaScore against Qwen. No embedding model is needed for these two metrics.

The integration script exits successfully when the requests and scoring contracts work, even if quality scores fail. It raises an error for execution errors or skips. The small model and ELIZA-oriented expected phrases make this a connectivity/contract test, not a production quality benchmark. Stop servers with Ctrl+C when finished.

### D. Generate and view Allure

Install **Allure 2 CLI and Java** using the [Allure installation guide](https://allurereport.org/docs/install/). For an npm installation, `npm install --global allure-commandline@2` makes `allure` available on your PATH. The framework writes Allure result files directly; `allure-pytest` is not needed for these scenario commands.

View results directly in a temporary report:

```sh
allure serve reports/ragas_framework-eliza/allure-results
```

Generate a persistent HTML report and open it through Allure's local server:

```sh
allure generate reports/ragas_framework-eliza/allure-results -o reports/ragas_framework-eliza/html --clean
allure open reports/ragas_framework-eliza/html
```

For the real model run:

```sh
allure generate reports/ragas_framework-ollama/allure-results -o reports/ragas_framework-ollama/html --clean
allure open reports/ragas_framework-ollama/html
```

Artifacts are `summary.json`, `allure-results/`, and (after generation) `html/` under the chosen run directory. Each test shows the score out of 5, threshold, status and implementation. These profiles enable attachments containing actual/expected responses and evaluator details. Serve HTML with `allure open`; directly opening `index.html` can prevent report data from loading.

Use a **fresh evaluation output directory** on every rerun. Allure's `--clean` only rebuilds its HTML directory; it does not make an existing evaluation output directory reusable.

<!-- COVERAGE START -->
## Evaluators covered from Microsoft

Reference: [evaluator section](https://learn.microsoft.com/en-us/azure/foundry-classic/concepts/evaluation-evaluators/) and [built-in catalog](https://learn.microsoft.com/en-us/azure/foundry-classic/concepts/built-in-evaluators), reviewed 2026-09-15. The section URL has no readable index; the catalog and its linked category pages define this list. Direct/indirect attacks and custom evaluators come from the linked pages.

Every listed category has an execution route. Native algorithms, custom rubrics, and explicit delegation are distinguished below. A rubric is not an equivalent implementation of a specialized Microsoft detector. Required credentials and evidence still apply.


| Metric ID | Execution in this module | Additional evidence |
|---|---|---|
| `coherence` | SimpleCriteriaScore custom rubric | Base question / actual / expected |
| `fluency` | SimpleCriteriaScore custom rubric | Base question / actual / expected |
| `similarity` | SemanticSimilarity | Base question / actual / expected |
| `f1` | Explicit Python module delegation | Base question / actual / expected |
| `bleu` | BleuScore | Base question / actual / expected |
| `gleu` | Explicit Python module delegation | Base question / actual / expected |
| `rouge` | RougeScore | Base question / actual / expected |
| `meteor` | Explicit Python module delegation | Base question / actual / expected |
| `retrieval` | LLMContextPrecisionWithReference | contexts |
| `document_retrieval` | Explicit Python module delegation | retrieval_ground_truth, retrieved_documents |
| `groundedness` | Faithfulness | contexts |
| `groundedness_pro` | SimpleCriteriaScore custom rubric | contexts |
| `relevance` | ResponseRelevancy | Base question / actual / expected |
| `response_completeness` | FactualCorrectness (recall mode) | Base question / actual / expected |
| `hate_unfairness` | SimpleCriteriaScore custom rubric | Base question / actual / expected |
| `sexual` | SimpleCriteriaScore custom rubric | Base question / actual / expected |
| `violence` | SimpleCriteriaScore custom rubric | Base question / actual / expected |
| `self_harm` | SimpleCriteriaScore custom rubric | Base question / actual / expected |
| `content_safety` | SimpleCriteriaScore custom rubric | Base question / actual / expected |
| `protected_material` | SimpleCriteriaScore custom rubric | protected_reference |
| `code_vulnerability` | SimpleCriteriaScore custom rubric | Base question / actual / expected |
| `ungrounded_attributes` | SimpleCriteriaScore custom rubric | conversation |
| `intent_resolution` | SimpleCriteriaScore custom rubric | Base question / actual / expected |
| `task_adherence` | SimpleCriteriaScore custom rubric | instructions |
| `tool_call_accuracy` | SimpleCriteriaScore custom rubric | tool_calls, tool_definitions |
| `model_labeler` | Explicit Python module delegation | rubric, labels, passing_labels |
| `string_checker` | ExactMatch | Base question / actual / expected |
| `text_similarity` | SimpleCriteriaScore custom rubric | Base question / actual / expected |
| `indirect_attack` | SimpleCriteriaScore custom rubric | contexts |
| `direct_attack` | Explicit Python module delegation | baseline_safety_score, attack_safety_score |
| `custom` | Explicit Python module delegation | Base question / actual / expected |
| `model_scorer` | SimpleCriteriaScore custom rubric | rubric |

With `python_lib.engine=local`, model-assisted Python evaluations use `python_lib.judge`; they are reported as delegated rubrics. Azure protected-material detection does not require a reference; local judge approximations do. Empty retrieved-document/tool-call arrays are valid observed outcomes; missing fields are skipped.

The direct-attack metric compares independently obtained baseline and attacked safety scores; it does not generate attacks. Custom Python functions come from trusted configuration. Azure grader-service APIs are not invoked: corresponding grader categories use local or judge implementations.

Common data: [JSON](../../../data/common_scenarios.json) / [CSV](../../../data/common_scenarios.csv). Run the [open-source endpoint tests](../../../docs/open-source-endpoint-tests.md).
<!-- COVERAGE END -->
