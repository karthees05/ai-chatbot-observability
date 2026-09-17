# Open-source endpoints and common test data

## Reproducible ELIZA integration

The endpoint wraps [NLTK's ELIZA chatbot](https://www.nltk.org/api/nltk.chat.eliza.html). It uses the upstream conversational rules and reflections to generate responses. It never reads the test dataset or expected answers. A fixed seed makes its choice among rule responses reproducible. ELIZA is a rule-based chatbot, not an LLM or a general knowledge assistant.

The same five scenarios are available in [JSON](../data/common_scenarios.json) and [CSV](../data/common_scenarios.csv), both with `Questions`, `Ground_Truths`, `Descriptions` and stable IDs. Four cases check established conversational behavior; one factual question intentionally exposes ELIZA's knowledge limitation. These are illustrative regression expectations, not a universal quality benchmark.

From the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[local,ragas]'
python -m nltk.downloader -d .venv/nltk_data wordnet
export NLTK_DATA="$PWD/.venv/nltk_data"
export RAGAS_DO_NOT_TRACK=true
PYTHONPATH=src:. python scripts/run_endpoint_tests.py --output reports/eliza-integration
```

The script starts a real HTTP server on a free local port, runs JSON and CSV datasets through all three modules, validates expected successes/failures, writes Allure artifacts and stops the server. It raises an error for unexpected skips or execution errors. Use a fresh report directory for each run.

Each format runs 5 scenarios × 6 metrics × 3 modules = 90 evaluations. Python computes F1/BLEU/GLEU/ROUGE/METEOR/string checks. RAGAS executes native BLEU/ROUGE/exact match and delegates the other exact calculations. Judge LLM delegates mathematical metrics without making a model call. This test does not claim that ELIZA can act as an LLM judge.

For manual endpoint testing:

```sh
python examples/eliza_chatbot.py --port 8766
# Another terminal, with the same environment:
ai-eval --data data/common_scenarios.json --config examples/eliza.json --output reports/eliza-manual
allure generate reports/eliza-manual/allure-results -o reports/eliza-manual/html --clean
```

The CLI deliberately exits 1 for the knowledge-gap evaluation failures. The integration script exits 0 when those failures are correctly detected. Its target configuration uses the `/v1/chat/completions` route; the sample also exposes `/chat` for a top-level question payload.

## Open-weight assistant with Ollama

[Ollama](https://docs.ollama.com/api/chat) can host a real open-weight assistant locally. The example uses [Qwen2.5-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct), a small Apache-2.0 model suitable for connectivity checks. It is too small to serve as a reliable quality judge for production decisions.

After installing Ollama using its official instructions:

```sh
ollama serve
# Another terminal:
ollama pull qwen2.5:0.5b
ollama pull nomic-embed-text
ai-eval --data data/common_scenarios.json --config examples/ollama.json --output reports/ollama
```

This configuration uses Ollama's native chat target and compatible model/embedding endpoints for evaluations. The target's expected response is never included in its request. Relevance uses embeddings in RAGAS; coherence and factual completeness do not require embeddings. Replace the target and judge model names independently for meaningful benchmarks. Using the same small model for both is only an integration smoke test.

For all catalog metrics, select names from any module README and supply their documented evidence fields. Questions/expected answers alone cannot establish retrieval relevance labels, actual tool calls, conversation grounding or paired attack effects. Missing prerequisites remain explicit skips.

## Add richer scenarios

Use the same base schema and add the evidence required by your evaluator:

```json
{
  "Questions": "What is the returns window?",
  "Ground_Truths": "30 days",
  "Descriptions": "Check the published returns policy.",
  "contexts": ["Returns are accepted within 30 days."],
  "instructions": "Answer from the published policy.",
  "rubric": "A passing answer identifies the 30-day window without inventing exceptions.",
  "labels": ["correct", "incorrect"],
  "passing_labels": ["correct"],
  "metrics": ["groundedness", "response_completeness", "model_labeler"]
}
```

The context should come from an actual retrieval trace, or be a controlled input known to have been available to the target. Agent tools and ranked documents must be observed evidence rather than expected traces copied into the actual result. For direct attacks, first collect baseline and attack safety scores with the same evaluator and configuration; the paired metric then measures degradation.

## Select every catalog route

[examples/all-evaluators.json](../examples/all-evaluators.json) explicitly lists all 32 evaluator IDs across all three modules. Supply the environment variables from the individual backend examples, install the optional libraries, and add evidence fields required by the module tables. It uses `fail_on_skip: true`, so absent evidence fails the coverage gate. It also enables result attachments. This is a cloud-enabled configuration, not a claim that the small ELIZA dataset supports every criterion.

```sh
python -m pip install -e '.[local,python,ragas]'
PYTHONPATH=src:. python -m ai_eval.cli --data data/common_scenarios.json --config examples/all-evaluators.json --output reports/full-catalog
```

The sample `custom` criterion in `examples/custom_evaluator.py` checks a configurable word limit. Change the trusted callable configuration to your own domain-specific evaluation. Agent observations, protected reference material, custom labeling criteria and paired attack scores must come from your real scenarios. Do not replace missing evidence with invented traces merely to make a report pass.

## Live LLM integration smoke test

The dedicated [Ollama smoke configuration](../examples/ollama-smoke.json) uses coherence and F1, so it needs no embedding model. It runs the same common JSON scenarios through all three modules: Python uses its configured judge, Judge LLM sends its own rubric requests, and RAGAS runs `SimpleCriteriaScore`. Judge output is constrained to a JSON schema. This profile expects a local Ollama service on port 11435:

```sh
OLLAMA_HOST=127.0.0.1:11435 ollama serve
# Another terminal:
OLLAMA_HOST=127.0.0.1:11435 ollama pull qwen2.5:0.5b
RAGAS_DO_NOT_TRACK=true PYTHONPATH=src python scripts/run_llm_tests.py --output reports/ollama-smoke
allure generate reports/ollama-smoke/allure-results -o reports/ollama-smoke/html --clean
```

The integration assertion checks that each module produces a live coherence score and that no calls error or skip. It does not require every quality score to pass. ELIZA-specific expected phrases will often have low F1 against a generative assistant; retain those failures when reviewing the report. This sample caps target generation at 64 tokens and evaluator generation at 512 tokens; raise the target limit for a substantive quality benchmark.
