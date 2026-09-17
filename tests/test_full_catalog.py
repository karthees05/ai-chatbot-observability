"""Validate the additions needed for honest, complete evaluator reporting."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ai_eval.core import NotApplicable
from ai_eval.python_lib import PythonBackend
from ai_eval.judge_llm import JudgeBackend
from ai_eval.runner import run
from ai_eval.reporting import write_result
from examples.rag_chatbot import answer

CASE={'id':'case','question':'returns policy','ground_truth':'30 days','description':'test','response':'30 days'}


class FullCatalogTests(unittest.TestCase):
    # Purpose: missing Azure project configuration must be an explicit skip before importing cloud packages.
    def test_azure_prerequisite(self):
        with self.assertRaisesRegex(NotApplicable,'Native Azure detector not run'):
            PythonBackend({'engine':'azure'}).evaluate('violence',CASE)

    # Purpose: code-only exclusions must remain visible with a reason rather than disappear from the report.
    def test_explicit_applicability(self):
        case=dict(CASE,not_applicable={'code_vulnerability':'No code requested'})
        with tempfile.TemporaryDirectory() as directory, patch('ai_eval.runner.get_actual',return_value=case):
            result=run([case],{'target':{},'metrics':['code_vulnerability']},directory)
        self.assertEqual(result['counts']['skipped'],1)
        self.assertEqual(result['results'][0]['reason'],'No code requested')

    # Purpose: native and rubric results for the same metric must not be collapsed as Allure retries.
    def test_distinct_report_identity(self):
        base={'backend':'python_lib','metric':'violence','status':'skipped','threshold':3}
        with tempfile.TemporaryDirectory() as directory:
            write_result(directory,CASE,dict(base,run_name='Local'))
            write_result(directory,CASE,dict(base,run_name='Azure native'))
            rows=[json.loads(path.read_text()) for path in Path(directory).glob('*-result.json')]
        self.assertNotEqual(rows[0]['historyId'],rows[1]['historyId'])

    # Purpose: structured labeling requests must permit and require the label without mutating the caller configuration.
    def test_label_schema(self):
        body={'response_format':{'type':'json_schema','json_schema':{'schema':{'type':'object','properties':{'score':{'type':'number'},'reason':{'type':'string'}},'required':['score','reason'],'additionalProperties':False}}}}
        case=dict(CASE,labels=['correct','incorrect'],passing_labels=['correct'],rubric='Classify correctness')
        response={'choices':[{'message':{'content':'{"score":5,"reason":"matches","label":"correct"}'}}]}
        with patch('ai_eval.judge_llm.post_json',return_value=response) as post:
            self.assertEqual(JudgeBackend({'model':'test','body':body}).evaluate('model_labeler',case)[0],5)
            schema=post.call_args.args[1]['response_format']['json_schema']['schema']
            self.assertIn('label',schema['required'])
        self.assertNotIn('label',body['response_format']['json_schema']['schema']['properties'])

    # Purpose: returned retrieval evidence must be the same documents actually passed into the model request.
    def test_actual_retrieval_trace(self):
        with patch('examples.rag_chatbot.post_json',return_value={'message':{'content':'30 days'}}) as post:
            result=answer('What is the returns policy for unused items?')
        self.assertEqual(result['retrieved_documents'][0]['document_id'],'returns')
        prompt=post.call_args.args[1]['messages'][0]['content']
        for context in result['contexts']:
            self.assertIn(context,prompt)
        self.assertEqual(result['tool_calls'][0]['arguments']['query'],'What is the returns policy for unused items?')


if __name__=='__main__':
    unittest.main()
