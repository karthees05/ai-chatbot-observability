# Verification record

Run on 2026-09-15. The five common scenarios were reused from `data/common_scenarios.json` and its equivalent CSV. Test scripts and results distinguish integration success from model-quality pass/fail.

| Verification | Result |
|---|---|
| Unit/library/contract tests | 25 passed, no skips |
| Actual NLTK ELIZA HTTP endpoint, JSON | 90 evaluations: 72 passed, 18 failed, 0 skipped, 0 errors |
| Actual NLTK ELIZA HTTP endpoint, CSV | 90 evaluations: 72 passed, 18 failed, 0 skipped, 0 errors |
| Actual Qwen2.5:0.5b through Ollama, JSON | 30 evaluations: 16 passed, 14 failed, 0 skipped, 0 errors |
| Allure HTML | Generated for ELIZA JSON and verified Qwen runs |
| Input/doc consistency | JSON/CSV equivalence, full coverage tables, SVG XML, function-purpose comments checked |

**210 endpoint evaluations completed in the final verified runs.** All integration assertions passed. Evaluation failures remain failures in Allure; they are not rewritten to make a suite green.

## What actually ran

- ELIZA: the real NLTK conversational algorithm behind a local HTTP server, not the earlier fixed-answer mock. Its sample adapter does not read test data. All 18 failures per format are six metrics × three modules for the factual question ELIZA cannot answer.
- Python: actual NLTK BLEU/GLEU/METEOR, rouge-score, token F1 and string matching. METEOR ran with downloaded WordNet.
- RAGAS: real `BleuScore`, `RougeScore`, `ExactMatch` during ELIZA evaluation. Real `SimpleCriteriaScore` with actual Qwen model calls during the LLM test. Completeness recall and cloud call boundaries also have contract tests.
- Judge LLM: exact calculations delegated to the Python module during ELIZA tests. Actual HTTP rubric requests to Qwen during the live LLM test; the Python module's configured local judge route was exercised too.
- Ollama: official v0.34.0 macOS runtime, archive checked against its published SHA256 manifest. Qwen2.5:0.5b was downloaded through Ollama. Runtime/models were staged under `/private/tmp/ai-eval-ollama`; no system application installation was required. The local server was stopped after verification.

The Qwen smoke run uses the same small model as target and judge. That verifies connectivity and contracts, not impartial or expert grading. The target output cap is 64 tokens. ELIZA regression phrases are not ideal ground truths for Qwen, so low lexical scores are expected. Do not interpret the aggregate mean as a benchmark of assistant quality.

## Errors caught and corrected

The first Qwen attempt produced one truncated judge JSON result, correctly reported as broken. The final sample uses a JSON schema and a larger evaluator output limit; the rerun had no errors. The initial attempt is retained in `reports/ollama-smoke` for transparency. Native RAGAS BLEU also exposed floating-point roundoff just above 1; the normalizer now tolerates only tiny boundary roundoff, with a regression test rejecting larger violations.

## Artifacts

Generated reports are ignored by Git but available in the workspace:

- `reports/unit-tests.log`
- `reports/eliza-integration/json/summary.json` and `html/`
- `reports/eliza-integration/csv/summary.json` and `allure-results/`
- `reports/ollama-verified/summary.json` and `html/`
- [Tested Python dependency snapshot](tested-dependencies.txt)

To serve the final results with Allure:

```sh
allure serve reports/eliza-integration/json/allure-results
allure serve reports/ollama-verified/allure-results
```

See [reproduction commands](open-source-endpoint-tests.md) for both endpoint test suites. Use a fresh output directory on each run.

## Not live-verified

Azure project-backed safety services, native Azure quality evaluators, embedding-backed RAGAS relevance/similarity, and every individual rubric were not all exercised against live services. Coverage tables document available routes and requirements, not a claim that all 32 categories received live validation. Agent, retrieval-label and attack-pair evaluations require scenario-specific observed evidence. The all-evaluators configuration intentionally fails its coverage gate if that evidence is absent.
