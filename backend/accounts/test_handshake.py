from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from backend.execution.symbol_resolver import discover_symbol_capabilities

from .handshake import HandshakeStage, HandshakeStatus, discover_demo_account, verify_broker_handshake
from .metaapi import MetaApiHandshakeError, verify_metaapi_handshake


class AccountHandshakeTests(SimpleTestCase):
    def test_market_discovery_selects_visible_executable_symbol_from_terminal_metadata(self):
        mt5 = SimpleNamespace(
            symbols_get=lambda *_args: [
                SimpleNamespace(name='XAUUSD.disabled', description='Gold', visible=True, trade_mode=0),
                SimpleNamespace(name='Gold.cash', description='Spot Gold', visible=True, trade_mode=1, digits=2),
            ],
        )

        mt5.symbol_info = lambda name: next(
            symbol for symbol in mt5.symbols_get() if symbol.name == name
        )
        result = discover_symbol_capabilities(mt5)

        self.assertEqual(result['canonicalAsset'], 'XAUUSD')
        self.assertIsNone(result['brokerSymbol'])
        self.assertEqual(result['assetMatches'], ['XAUUSD.disabled', 'Gold.cash'])
        self.assertEqual(result['symbols'][1]['confidence'], 0.45)

    def test_demo_discovery_returns_account_facts_and_next_stage(self):
        result = discover_demo_account(platform='MT5', login='123456', server='Demo-Server')

        self.assertEqual(result.status, HandshakeStatus.DISCOVERED)
        self.assertEqual(result.stage, HandshakeStage.USER_POLICY_CONFIGURATION)
        self.assertEqual(result.discovery['marketData'], 'HEALTHY')
        self.assertEqual(result.discovery['login'], '123456')
        self.assertIn(HandshakeStage.VALIDATE, result.completed_stages)

    def test_handshake_rejects_non_numeric_account_without_loading_mt5(self):
        with patch.dict('sys.modules', {'MetaTrader5': None}):
            result = verify_broker_handshake('not-a-number', 'password', 'Demo-Server')

        self.assertEqual(result['reason_code'], 'INVALID_ACCOUNT_FORMAT')

    def test_handshake_reports_terminal_initialization_failure(self):
        mt5 = SimpleNamespace(
            initialize=lambda **kwargs: False,
            last_error=lambda: (-10005, 'Terminal unavailable'),
            shutdown=lambda: self.fail('shutdown should not run when initialization fails'),
        )
        with patch.dict('sys.modules', {'MetaTrader5': mt5}):
            result = verify_broker_handshake('123456', 'password', 'Demo-Server')

        self.assertEqual(result['reason_code'], 'TERMINAL_INIT_FAILED')

    def test_handshake_casts_account_and_returns_telemetry(self):
        mt5 = SimpleNamespace(
            initialize=lambda **kwargs: True,
            login=lambda **kwargs: kwargs['login'] == 123456,
            account_info=lambda: SimpleNamespace(
                login=123456,
                company='Broker',
                server='Demo-Server',
                balance=1000.0,
                leverage=100,
                currency='USD',
                trade_mode=0,
                trade_allowed=True,
            ),
            shutdown=lambda: None,
        )
        with patch.dict('sys.modules', {'MetaTrader5': mt5}):
            result = verify_broker_handshake('123456', 'password', 'Demo-Server')

        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['account_id'], 123456)
        self.assertTrue(result['trade_allowed'])


class MetaApiHandshakeTests(SimpleTestCase):
    def test_api_handshake_collects_account_validation_facts(self):
        profile = {
            'region': 'london',
            'state': 'DEPLOYED',
            'platform': 'mt5',
            'login': '123456',
            'server': 'Example-Demo',
            'broker': 'Example Broker',
        }
        account_info = {
            'balance': 1000.25,
            'equity': 998.75,
            'leverage': 200,
            'currency': 'USD',
            'tradeAllowed': True,
            'marginMode': 'HEDGED',
        }
        with patch(
            'backend.accounts.metaapi._get_json',
            side_effect=[profile, account_info, [{'symbol': 'XAUUSD.a'}], ['XAUUSD.a', 'EURUSD']],
        ) as get_json:
            result = verify_metaapi_handshake('metaapi-account-id', 'private-token')

        self.assertEqual(result['account_id'], '123456')
        self.assertEqual(result['platform'], 'MT5')
        self.assertEqual(result['balance'], '1000.25')
        self.assertEqual(result['equity'], '998.75')
        self.assertEqual(result['leverage'], 200)
        self.assertTrue(result['trade_allowed'])
        self.assertEqual(result['existing_positions'], 1)
        self.assertEqual(result['market_discovery']['brokerSymbol'], 'XAUUSD.a')
        self.assertEqual(get_json.call_count, 4)

    def test_api_handshake_rejects_accounts_that_are_not_deployed(self):
        with patch('backend.accounts.metaapi._get_json', return_value={'region': 'london', 'state': 'DEPLOYING'}):
            with self.assertRaisesRegex(MetaApiHandshakeError, 'Deploy the MetaAPI account'):
                verify_metaapi_handshake('metaapi-account-id', 'private-token')
