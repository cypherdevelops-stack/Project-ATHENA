from django.test import SimpleTestCase

from .execution_gateway import ExecutionGatewayError, normalize_price, normalize_volume, validate_broker_setup


class ExecutionGatewayTests(SimpleTestCase):
    def capability(self):
        return {
            'visible': True,
            'selectable': True,
            'tradeMode': 1,
            'selectedFillingMode': 'IOC',
            'selectedFillingModeValue': 1,
            'digits': 2,
            'point': 0.01,
            'stopsLevel': 10,
            'freezeLevel': 0,
            'tickSize': 0.05,
            'volumeMin': 0.1,
            'volumeMax': 2.0,
            'volumeStep': 0.1,
        }

    def setup(self):
        return {
            'direction': 'BUY',
            'entry': 100,
            'stopLoss': 99,
            'takeProfit2': 102,
            'volume': 0.26,
        }

    def test_setup_is_normalized_to_broker_volume_step_and_filling_mode(self):
        result = validate_broker_setup(setup=self.setup(), capability=self.capability(), market_price=100)

        self.assertEqual(result['volume'], 0.2)
        self.assertEqual(result['fillingMode'], 'IOC')
        self.assertEqual(result['fillingModeValue'], 1)

    def test_setup_rejects_stop_inside_broker_minimum_distance(self):
        with self.assertRaisesRegex(ExecutionGatewayError, 'minimum distance'):
            validate_broker_setup(
                setup={**self.setup(), 'stopLoss': 99.95},
                capability=self.capability(),
                market_price=100,
            )

    def test_volume_below_broker_minimum_is_rejected(self):
        with self.assertRaisesRegex(ExecutionGatewayError, 'below the broker minimum'):
            normalize_volume(0.05, self.capability())

    def test_prices_are_normalized_to_tick_size(self):
        self.assertEqual(normalize_price(100.03, self.capability()), 100.05)

    def test_freeze_level_is_enforced_as_minimum_distance(self):
        capability = {**self.capability(), 'freezeLevel': 200}
        with self.assertRaisesRegex(ExecutionGatewayError, 'minimum distance'):
            validate_broker_setup(setup=self.setup(), capability=capability, market_price=100)

    def test_market_order_mode_is_required(self):
        with self.assertRaisesRegex(ExecutionGatewayError, 'market orders'):
            validate_broker_setup(
                setup=self.setup(),
                capability={**self.capability(), 'orderModes': 2, 'marketOrderMode': 1},
                market_price=100,
            )
