"""Tests for expanded coverage, reusable input, exact scoring, and native adapters."""
import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch, Mock, AsyncMock
from ai_eval.core import get_actual, load_cases
from ai_eval.catalog import RUBRICS
from ai_eval.python_lib import PythonBackend, normalize_sdk
from ai_eval.python_lib.local_metrics import document_retrieval
from ai_eval.judge_llm import JudgeBackend
from ai_eval.ragas_framework import RagasBackend

CASE = {"question":"Hello", "ground_truth":"The cat sat on the mat.", "response":"The cat sat on the mat.", "description":"Test"}


class ExtendedTests(unittest.TestCase):
    # Purpose: ensure both common data representations stay semantically identical.
    def test_common_data(self):
        self.assertEqual(load_cases('data/common_scenarios.json'), load_cases('data/common_scenarios.csv'))

    # Purpose: verify messages-based target protocols without leaking expected answers.
    def test_chat_protocol(self):
        for protocol in ('chat_completions', 'ollama'):
            with patch('ai_eval.core.post_json', return_value={'answer':'hello'}) as post:
                get_actual({'protocol':protocol, 'body':{'model':'sample'}, 'response_path':'answer'}, CASE)
                self.assertEqual(post.call_args.args[1], {'model':'sample','stream':False,'messages':[{'role':'user','content':'Hello'}]})

    # Purpose: ensure document ranking penalizes bad order, diagnoses unlabeled results, and rejects duplicates.
    def test_document_ranking(self):
        case=dict(CASE, retrieval_ground_truth=[{'document_id':'a','query_relevance_label':3},{'document_id':'b','query_relevance_label':1}],retrieved_documents=[{'document_id':'a'},{'document_id':'b'}])
        self.assertEqual(document_retrieval(case,2)[0],1)
        case['retrieved_documents'].reverse()
        self.assertLess(document_retrieval(case,2)[0],1)
        case['retrieved_documents']=[{'document_id':'unknown'}]
        self.assertEqual(document_retrieval(case,2)[1]['holes'],1)
        case['retrieved_documents']=[{'document_id':'a'},{'document_id':'a'}]
        with self.assertRaises(ValueError):
            document_retrieval(case,2)

    # Purpose: validate paired attack score direction independently of hosted safety inference.
    def test_attack_scores(self):
        score, raw=PythonBackend({}).evaluate('direct_attack',dict(CASE,baseline_safety_score=5,attack_safety_score=1))
        self.assertEqual(score,1)
        self.assertEqual(raw['degradation'],4)
        self.assertEqual(normalize_sdk('indirect_attack',{'xpia_label':True}),0)
        with self.assertRaises(ValueError):
            normalize_sdk('indirect_attack',{'xpia_label':'true'})

    # Purpose: enforce valid model labels and derive a binary passing-label score.
    def test_labeler(self):
        case=dict(CASE,rubric='Classify whether helpful.',labels=['helpful','unhelpful'],passing_labels=['helpful'])
        with patch('ai_eval.judge_llm.post_json',return_value={'choices':[{'message':{'content':json.dumps({'score':4,'reason':'Does not help','label':'unhelpful'})}}]}):
            self.assertEqual(JudgeBackend({'model':'test'}).evaluate('model_labeler',case)[0],0)

    # Purpose: ensure exact metrics in the judge module never invoke a language model.
    def test_judge_delegation(self):
        with patch('ai_eval.judge_llm.post_json') as post:
            score,raw=JudgeBackend({}).evaluate('f1',CASE)
            self.assertEqual(score,5)
            self.assertIn('delegated',raw['implementation'])
            post.assert_not_called()

    # Purpose: verify real installed NLTK and ROUGE implementations on matching and unrelated text.
    @unittest.skipUnless(importlib.util.find_spec('nltk') and importlib.util.find_spec('rouge_score'), 'Install .[local]')
    def test_local_libraries(self):
        backend=PythonBackend({'engine':'local'})
        for metric in ('bleu','gleu','rouge','meteor','text_similarity'):
            with self.subTest(metric=metric):
                self.assertGreater(backend.evaluate(metric,CASE)[0],4)
                self.assertLess(backend.evaluate(metric,dict(CASE,response='Completely unrelated vocabulary'))[0],2)

    # Purpose: verify the actual RAGAS package can compute native lexical metrics without models.
    @unittest.skipUnless(importlib.util.find_spec('ragas'), 'Install .[ragas]')
    def test_native_ragas(self):
        backend=RagasBackend({})
        for metric in ('bleu','rouge','string_checker'):
            with self.subTest(metric=metric):
                self.assertAlmostEqual(backend.evaluate(metric,CASE)[0],5)
                self.assertLess(backend.evaluate(metric,dict(CASE,response='Unrelated'))[0],2)

    # Purpose: verify trusted custom functions use configured scales and expose provenance.
    def test_custom_callable(self):
        module = Mock()
        module.grade.return_value = {"score": 80, "reason": "custom criterion"}
        with patch("ai_eval.python_lib.local_metrics.importlib.import_module", return_value=module):
            score, raw = PythonBackend({"custom_evaluator": {"callable": "trusted:grade", "max": 100}}).evaluate("custom", CASE)
            self.assertEqual(score, 4)
            self.assertEqual(raw["implementation"], "trusted:grade")
            module.grade.assert_called_once_with(CASE)

    # Purpose: prove score-boundary tolerance fixes roundoff without accepting invalid scores.
    def test_score_roundoff(self):
        from ai_eval.core import score_out_of_five
        self.assertEqual(score_out_of_five(1.0000000000000004), 5)
        with self.assertRaises(ValueError):
            score_out_of_five(1.001)

    # Purpose: verify an observed empty retrieval result scores zero instead of being skipped.
    def test_empty_retrieval(self):
        import tempfile
        from ai_eval.runner import run
        case = dict(CASE, id="empty", retrieval_ground_truth=[{"document_id":"a","query_relevance_label":1}], retrieved_documents=[])
        with tempfile.TemporaryDirectory() as directory, patch("ai_eval.runner.get_actual", return_value=case):
            result = run([case], {"metrics":["document_retrieval"], "python_lib":{"engine":"local"}, "target":{}}, directory)
            self.assertEqual(result["counts"]["failed"], 1)
            self.assertEqual(result["results"][0]["score"], 0)

    # Purpose: verify completeness evaluates actual/reference recall and initializes no embeddings.
    @unittest.skipUnless(importlib.util.find_spec('ragas'), 'Install .[ragas]')
    def test_ragas_completeness_contract(self):
        backend = RagasBackend({})
        backend.llm = object()
        evaluator = Mock()
        evaluator.single_turn_ascore = AsyncMock(return_value=0.8)
        with patch("ragas.metrics.FactualCorrectness", return_value=evaluator) as metric:
            self.assertEqual(backend.evaluate("response_completeness", CASE)[0], 4)
            metric.assert_called_once_with(llm=backend.llm, mode="recall")
            sample = evaluator.single_turn_ascore.call_args.args[0]
            self.assertEqual(sample.response, CASE["response"])
            self.assertEqual(sample.reference, CASE["ground_truth"])
            self.assertIsNone(backend.embeddings)

    # Purpose: require every module guide to contain an explicit coverage row for every registered metric.
    def test_documented_coverage(self):
        for module in ('python_lib','ragas_framework','judge_llm'):
            text=Path(f'src/ai_eval/{module}/README.md').read_text()
            for metric in RUBRICS:
                self.assertIn(f'`{metric}`',text, (module,metric))


if __name__ == '__main__':
    unittest.main()
