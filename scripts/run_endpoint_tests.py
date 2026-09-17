"""Run real ELIZA HTTP scenarios and verify framework outcomes in all three modules."""
import argparse
import json
import threading
from pathlib import Path
from http.server import HTTPServer
from examples.eliza_chatbot import ElizaHandler
from ai_eval.core import load_cases
from ai_eval.runner import run


# Purpose: exercise a real open-source chatbot endpoint and retain reviewable Allure artifacts.
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='reports/eliza-integration')
    args = parser.parse_args()
    config = json.loads(Path('examples/eliza.json').read_text())
    with HTTPServer(('127.0.0.1', 0), ElizaHandler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        config['target']['url'] = f'http://127.0.0.1:{server.server_port}/v1/chat/completions'
        try:
            for extension in ('json', 'csv'):
                summary = run(load_cases(f'data/common_scenarios.{extension}'), config, Path(args.output) / extension)
                if summary['counts']['error'] or summary['counts']['skipped']:
                    raise AssertionError(f'Unexpected execution errors/skips: {summary["counts"]}')
                if summary['total'] != 90:
                    raise AssertionError('Expected 5 scenarios × 6 metrics × 3 modules')
                for backend in config['backends']:
                    results = [result for result in summary['results'] if result['backend'] == backend]
                    if not any(result['status'] == 'passed' for result in results):
                        raise AssertionError(f'{backend}: expected passing conversations')
                    failures = [result for result in results if result['scenario_id'] == 'knowledge-gap' and result['status'] == 'failed']
                    if not failures:
                        raise AssertionError(f'{backend}: the expected factual-answer failure was missed')
                print(f'{extension}: integration assertions passed; evaluation counts: {summary["counts"]}', flush=True)
        finally:
            server.shutdown()
            thread.join(timeout=10)


if __name__ == '__main__':
    main()
