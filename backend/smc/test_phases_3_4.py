from django.test import SimpleTestCase

from .detector import advance_poi_state, analyze_multi_timeframe
from .scripts.lifecycle import active_pois


class POILifecycleTests(SimpleTestCase):
    def test_price_breach_invalidates_poi_and_records_reason(self):
        poi = {
            'type': 'OB',
            'direction': 'BULLISH',
            'lowerBound': 100,
            'upperBound': 101,
            'time': 100,
            'sourceEvent': 'BOS-100',
        }

        result = advance_poi_state(poi, 99, current_time=110)

        self.assertEqual(result['state'], 'INVALIDATED')
        self.assertEqual(result['invalidationReason'], 'PRICE_CLOSED_BELOW_ZONE')
        self.assertEqual(result['sourceEvent'], 'BOS-100')
        self.assertNotIn(result, active_pois([result]))

    def test_old_active_poi_expires_and_is_not_active(self):
        poi = {
            'direction': 'BEARISH',
            'lowerBound': 100,
            'upperBound': 101,
            'time': 0,
        }

        result = advance_poi_state(poi, 105, current_time=100, max_age_seconds=50)

        self.assertEqual(result['state'], 'EXPIRED')
        self.assertEqual(active_pois([result]), [])


class MultiTimeframeSMCTests(SimpleTestCase):
    def test_conflicting_timeframes_remain_visible(self):
        bullish = [
            {'open': 10, 'close': 10.5, 'high': 11, 'low': 9, 'time': index}
            for index in range(5)
        ]
        bullish[-1] = {'open': 10, 'close': 12, 'high': 12, 'low': 9.5, 'time': 4}
        bearish = [
            {'open': 10, 'close': 9.5, 'high': 11, 'low': 9, 'time': index}
            for index in range(5)
        ]
        bearish[-1] = {'open': 10, 'close': 8, 'high': 10.5, 'low': 8, 'time': 4}

        result = analyze_multi_timeframe({'H1': bullish, 'M5': bearish}, timeframes=('H1', 'M5'))

        self.assertEqual(result['alignment'], 'CONFLICTING')
        self.assertEqual(result['higherTimeframe'], 'H1')
        self.assertEqual(result['timeframes']['H1']['bias'], 'BUY')
        self.assertEqual(result['timeframes']['M5']['bias'], 'SELL')
