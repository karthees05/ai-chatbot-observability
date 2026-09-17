"""Run actual model-assisted evaluations against a separately started Ollama instance."""
import argparse
import json
from pathlib import Path
from ai_eval.core import load_cases
from ai_eval.runner import run


# Purpose: verify live target/judge/RAGAS calls complete, without asserting a small model is accurate.
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='examples/ollama-smoke.json')
    parser.add_argument('--data', default='data/common_scenarios.json')
    parser.add_argument('--output', default='reports/ollama-smoke')
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    summary = run(load_cases(args.data), config, args.output)
    print(json.dumps({key:value for key,value in summary.items() if key != 'results'}, indent=2))
    if summary['counts']['error'] or summary['counts']['skipped']:
        raise AssertionError('Live model evaluation had errors or skips; inspect the report')
    for backend in config['backends']:
        results = [result for result in summary['results'] if result['backend'] == backend]
        if not any(result['metric'] == 'coherence' and result['score'] is not None for result in results):
            raise AssertionError(f'{backend} did not produce a live model-assisted score')
    print('Live model integration assertions passed. Quality failures remain visible in the report.')


if __name__ == '__main__':
    main()
