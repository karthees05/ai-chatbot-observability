"""Keep all module READMEs and the coverage matrix synchronized with executable routes."""
from pathlib import Path
from ai_eval.catalog import RUBRICS, REQUIRES, DETERMINISTIC
from ai_eval.python_lib import CLASSES
from ai_eval.ragas_framework import METRICS

SOURCE = 'https://learn.microsoft.com/en-us/azure/foundry-classic/concepts/evaluation-evaluators/'
CATALOG = 'https://learn.microsoft.com/en-us/azure/foundry-classic/concepts/built-in-evaluators'


# Purpose: describe each backend's real execution route without claiming algorithm equivalence.
def coverage(metric):
    python = CLASSES.get(metric, 'Local computation')
    if metric in {'model_labeler', 'model_scorer'}:
        python = 'Configured judge delegation'
    elif metric in {'bleu','gleu','rouge','meteor','document_retrieval'}:
        python += ' / local library alternative'
    elif metric == 'f1':
        python = 'Local token F1 / F1ScoreEvaluator'
    ragas = METRICS.get(metric, 'SimpleCriteriaScore custom rubric')
    if metric == 'response_completeness':
        ragas += ' (recall mode)'
    if metric in DETERMINISTIC - {'bleu','rouge','string_checker'} or metric == 'model_labeler':
        ragas = 'Explicit Python module delegation'
    judge = 'Explicit Python module delegation' if metric in DETERMINISTIC else 'LLM rubric (not Azure service)'
    if metric == 'model_labeler':
        judge = 'Validated label + passing-label score'
    return python, ragas, judge


# Purpose: generate a full inline evaluator table in each module's README and the shared matrix.
def main():
    header = (f'## Evaluators covered from Microsoft\n\nReference: [evaluator section]({SOURCE}) and '
              f'[built-in catalog]({CATALOG}), reviewed 2026-09-15. The section URL has no readable index; '
              'the catalog and its linked category pages define this list. Direct/indirect attacks and custom evaluators come from the linked pages.\n\n'
              'Every listed category has an execution route. Native algorithms, custom rubrics, and explicit delegation are distinguished below. '
              'A rubric is not an equivalent implementation of a specialized Microsoft detector. Required credentials and evidence still apply.\n\n')
    combined = ['# Evaluator coverage', '', header, '| Metric | Python library | RAGAS | Judge LLM | Additional evidence |', '|---|---|---|---|---|']
    for metric in RUBRICS:
        evidence = ', '.join(REQUIRES.get(metric, [])) or 'Base question / actual / expected'
        combined.append('| `' + metric + '` | ' + ' | '.join(coverage(metric)) + ' | ' + evidence + ' |')
    Path('docs/evaluator-coverage.md').write_text('\n'.join(combined)+'\n')
    for index, module in enumerate(('python_lib','ragas_framework','judge_llm')):
        path = Path(f'src/ai_eval/{module}/README.md')
        content = path.read_text().split('<!-- COVERAGE START -->')[0].rstrip()
        lines = [header, '| Metric ID | Execution in this module | Additional evidence |', '|---|---|---|']
        for metric in RUBRICS:
            evidence = ', '.join(REQUIRES.get(metric, [])) or 'Base question / actual / expected'
            lines.append(f'| `{metric}` | {coverage(metric)[index]} | {evidence} |')
        lines += ['', 'With `python_lib.engine=local`, model-assisted Python evaluations use `python_lib.judge`; they are reported as delegated rubrics. '
                  'Azure protected-material detection does not require a reference; local judge approximations do. '
                  'Empty retrieved-document/tool-call arrays are valid observed outcomes; missing fields are skipped.', '',
                  'The direct-attack metric compares independently obtained baseline and attacked safety scores; it does not generate attacks. '
                  'Custom Python functions come from trusted configuration. Azure grader-service APIs are not invoked: corresponding grader categories use local or judge implementations.', '',
                  'Common data: [JSON](../../../data/common_scenarios.json) / [CSV](../../../data/common_scenarios.csv). '
                  'Run the [open-source endpoint tests](../../../docs/open-source-endpoint-tests.md).']
        path.write_text(content+'\n\n<!-- COVERAGE START -->\n'+'\n'.join(lines)+'\n<!-- COVERAGE END -->\n')


if __name__ == '__main__':
    main()
