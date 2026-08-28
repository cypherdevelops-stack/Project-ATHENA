from django.test import SimpleTestCase

from .orchestrator import StrategyOrchestrator


class SMCOrchestrationTests(SimpleTestCase):
    def _orchestrator(self, *, execution_allowed=True):
        orchestrator = StrategyOrchestrator()
        orchestrator.set_portfolio_state(
            regime='TRENDING_BULLISH',
            state={
                'risk_allowed': True,
                'market_open': True,
                'news_locked': False,
                'execution_allowed': execution_allowed,
            },
            smc_context={'alignment': 'ALIGNED', 'higherTimeframeBias': 'BUY'},
        )
        return orchestrator

    def _candidate(self):
        return {
            'direction': 'BUY',
            'score': 82,
            'decisionState': 'READY',
            'entryZone': {'lower': 100, 'upper': 101},
            'setup': {'active': True, 'state': 'CANDIDATE', 'missing': []},
            'gates': [],
            'smcEvidence': {
                'alignment': 'ALIGNED',
                'timeframes': {'M1': {'activePois': [{'type': 'OB', 'state': 'REACTED'}]}},
            },
        }

    def test_smc_evidence_is_retained_on_orchestrated_candidate(self):
        orchestrator = self._orchestrator()
        orchestrator.ingest_scalping_candidate(self._candidate())

        result = orchestrator.orchestrate_execution()

        self.assertEqual(result['scalping_engine']['evidence']['smc']['alignment'], 'ALIGNED')
        self.assertEqual(result['smcContext']['higherTimeframeBias'], 'BUY')
        self.assertEqual(result['decision']['action'], 'SCALP_LONG_APPROVED')

    def test_portfolio_block_preserves_smc_evidence(self):
        orchestrator = self._orchestrator(execution_allowed=False)
        orchestrator.ingest_scalping_candidate(self._candidate())

        result = orchestrator.orchestrate_execution()

        self.assertEqual(result['decision']['action'], 'OBSERVE')
        self.assertEqual(result['decision']['reasonCodes'], ['PORTFOLIO_EXECUTION_BLOCKED'])
        self.assertEqual(result['scalping_engine']['evidence']['smc']['alignment'], 'ALIGNED')
