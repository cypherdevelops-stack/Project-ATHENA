from django.test import SimpleTestCase, override_settings

from backend.accounts.models import Account
from backend.backtesting.models import HistoricalCandle
from backend.database_router import AthenaDatabaseRouter
from backend.intelligence.news.models import (
    AdaptiveNewsStatistic,
    NewsIntelligenceSnapshot,
    NewsReactionObservation,
)


@override_settings(
    DATABASES={
        'default': {},
        'market_intelligence': {},
        'backtesting': {},
        'learning_memory': {},
    }
)
class AthenaDatabaseRouterTests(SimpleTestCase):
    def setUp(self):
        self.router = AthenaDatabaseRouter()

    def test_reads_and_writes_route_to_their_data_domains(self):
        self.assertEqual(self.router.db_for_read(Account), 'default')
        self.assertEqual(self.router.db_for_write(HistoricalCandle), 'backtesting')
        self.assertEqual(self.router.db_for_read(NewsIntelligenceSnapshot), 'market_intelligence')
        self.assertEqual(self.router.db_for_write(NewsReactionObservation), 'learning_memory')
        self.assertEqual(self.router.db_for_read(AdaptiveNewsStatistic), 'learning_memory')

    def test_migrations_are_limited_to_their_data_domain(self):
        self.assertTrue(self.router.allow_migrate('default', 'accounts', 'account'))
        self.assertFalse(self.router.allow_migrate('backtesting', 'accounts', 'account'))
        self.assertTrue(self.router.allow_migrate('backtesting', 'backtesting', 'historicalcandle'))
        self.assertTrue(self.router.allow_migrate('market_intelligence', 'news_intelligence', 'newsintelligencesnapshot'))
        self.assertTrue(self.router.allow_migrate('learning_memory', 'news_intelligence', 'adaptivenewsstatistic'))
        self.assertFalse(self.router.allow_migrate('market_intelligence', 'news_intelligence', 'adaptivenewsstatistic'))

    def test_sqlite_development_routes_all_models_to_default(self):
        with override_settings(DATABASES={'default': {}}):
            self.assertEqual(self.router.db_for_read(HistoricalCandle), 'default')
            self.assertTrue(self.router.allow_migrate('default', 'backtesting', 'historicalcandle'))

    def test_cross_database_orm_relations_are_rejected(self):
        account = Account()
        snapshot = NewsIntelligenceSnapshot()
        account._state.db = 'default'
        snapshot._state.db = 'market_intelligence'
        self.assertFalse(self.router.allow_relation(account, snapshot))
