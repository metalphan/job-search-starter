import copy
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import job_search as app


class JobSearchTests(unittest.TestCase):
    def setUp(self):
        self.c = app.load_config(app.ROOT / 'config.example.json')
        self.result = {'title': 'Software Engineer at Example', 'url': 'https://example.com/jobs/1',
                       'content': 'Hybrid software engineer based in New York.'}

    def test_location_and_role(self):
        self.assertIsNotNone(app.assess(self.result, self.c))
        self.result['content'] = 'Hybrid job based in Boston.'
        self.assertIsNone(app.assess(self.result, self.c))
        self.result['content'] = 'Hybrid based in New York.'
        self.result['title'] = 'Marketing Director'
        self.assertIsNone(app.assess(self.result, self.c))

    def test_remote_jurisdiction(self):
        self.result['content'] = 'Remote software engineer, Canada only.'
        self.assertIsNone(app.assess(self.result, self.c))
        self.result['content'] = 'Remote software engineer, United States.'
        self.assertIsNotNone(app.assess(self.result, self.c))

    def test_unknown_salary(self):
        self.c['minimum_annual_salary'] = 100000
        self.assertIsNotNone(app.assess(self.result, self.c))
        self.c['include_unknown_salary'] = False
        self.assertIsNone(app.assess(self.result, self.c))

    def test_ai_salary_and_currency(self):
        self.c.update(minimum_annual_salary=100000, include_unknown_salary=False)
        d = dict(title='Software Engineer', firm='Example', location='New York', arrangement='Hybrid',
                 salary='$90,000–$120,000', fit_notes='Match', eligible=True, is_job_posting=True,
                 is_open=True, annual_salary_max=120000, salary_currency='USD')
        ai = lambda provider, model, prompt: json.dumps(d)
        self.assertIsNotNone(app.assess(self.result, self.c, ai))
        d['annual_salary_max'] = 90000
        self.assertIsNone(app.assess(self.result, self.c, ai))
        d.update(annual_salary_max=120000, salary_currency='CAD')
        self.assertIsNone(app.assess(self.result, self.c, ai))
        d.update(salary_currency='USD', is_open=False)
        self.assertIsNone(app.assess(self.result, self.c, ai))

    def test_provider_requests_and_credentials(self):
        self.c['ai_provider'] = 'openai'
        with patch.dict(app.os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                app.ai_response('openai', 'gpt-4o-mini', 'JSON only')
        with patch.dict(app.os.environ, {'OPENAI_API_KEY': 'test', 'XAI_API_KEY': 'test', 'GEMINI_API_KEY': 'test'}), patch.object(app, 'post_json', return_value={'choices': [{'message': {'content': '{}'}}]}) as post:
            self.assertEqual(app.ai_response('openai', 'gpt-4o-mini', 'JSON only'), '{}')
            self.assertIn('api.openai.com', post.call_args.args[0])
            self.assertEqual(app.ai_response('xai', 'grok-4.7', 'JSON only'), '{}')
            self.assertIn('api.x.ai', post.call_args.args[0])
            post.return_value = {'candidates': [{'content': {'parts': [{'text': '{}'}]}}]}
            self.assertEqual(app.ai_response('gemini', 'gemini-2.5-flash', 'JSON only'), '{}')
            self.assertIn('generativelanguage.googleapis.com', post.call_args.args[0])

    def test_exclusions_and_boundaries(self):
        self.c['exclude_terms'] = ['contract']
        self.result['content'] += ' Contract position.'
        self.assertIsNone(app.assess(self.result, self.c))
        self.assertFalse(app.contains('MySQL', 'SQL'))

    def test_exports_formula_safety(self):
        from openpyxl import load_workbook
        job = dict(title='=HYPERLINK("bad")', url='https://example.com')
        with tempfile.TemporaryDirectory() as directory:
            csv = Path(directory) / 'jobs.csv'
            xlsx = Path(directory) / 'jobs.xlsx'
            app.export([job], csv)
            app.export([job], xlsx)
            self.assertIn("'=HYPERLINK", csv.read_text(encoding='utf-8-sig'))
            wb = load_workbook(xlsx)
            self.assertEqual(wb.active['A2'].data_type, 's')
            self.assertEqual(wb.active.freeze_panes, 'A2')
            wb.close()

    def test_preview_delivery_failure_and_dedup(self):
        fake = types.SimpleNamespace(TavilyClient=lambda **kwargs: types.SimpleNamespace(search=lambda **kwargs: {'results': [self.result, self.result]}))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cpath = root / 'config.json'
            cpath.write_text(json.dumps(self.c))
            with patch.object(app, 'ROOT', root), patch.dict(sys.modules, {'tavily': fake}), patch.dict(app.os.environ, {'TAVILY_API_KEY': 'test', 'ANTHROPIC_API_KEY': ''}), patch.object(app, 'deliver') as delivery:
                app.main(['--config', str(cpath), '--preview'])
                delivery.assert_not_called()
                self.assertFalse((root / 'state/history.json').exists())
                delivery.side_effect = RuntimeError('delivery failed')
                with self.assertRaises(RuntimeError):
                    app.main(['--config', str(cpath)])
                self.assertFalse((root / 'state/history.json').exists())
                delivery.side_effect = None
                app.main(['--config', str(cpath)])
                state = json.loads((root / 'state/history.json').read_text())
                self.assertEqual(len(state['jobs']), 1)
                app.main(['--config', str(cpath)])
                self.assertEqual(delivery.call_args.args[1], 0)
                self.c['output_format'] = 'csv'
                cpath.write_text(json.dumps(self.c))
                app.main(['--config', str(cpath)])
                self.assertEqual(delivery.call_args.args[1], 0)
                self.assertTrue((root / 'results/master.csv').exists())

    def test_query_limit(self):
        self.c['max_queries'] = 1
        self.c['queries'] = ['explicit query']
        self.assertEqual(app.queries(self.c), ['explicit query'])

    def test_company_domain_query(self):
        self.c['company_domains'] = ['careers.example.com']
        self.c['max_queries'] = 12
        self.assertIn('site:careers.example.com "software engineer" careers jobs', app.queries(self.c))


if __name__ == '__main__':
    unittest.main()
