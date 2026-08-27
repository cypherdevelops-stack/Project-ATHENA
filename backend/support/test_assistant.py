from django.test import SimpleTestCase

from .assistant import answer_help_request
from .nlp import analyze


class HelpAssistantTests(SimpleTestCase):
    def test_answers_athena_topics(self):
        answer = answer_help_request('How do I use the orchestration decision stream?')
        self.assertEqual(answer.intent, 'orchestration')
        self.assertIn('Orchestration', answer.text)

    def test_refuses_trading_authority_requests(self):
        answer = answer_help_request('Please place a trade for me.')
        self.assertEqual(answer.intent, 'safety_refusal')
        self.assertIn('cannot place orders', answer.text)

    def test_nlp_normalizes_synonyms_and_extracts_entities(self):
        result = analyze('Why is MetaTrader broken on /backtesting with XAUUSD M5?')
        self.assertEqual(result.intent, 'backtesting')
        self.assertIn('mt5', result.tokens)
        self.assertEqual(result.entities['symbols'], ('XAUUSD',))
        self.assertEqual(result.entities['timeframes'], ('M5',))
        self.assertEqual(result.entities['routes'], ('/backtesting',))
