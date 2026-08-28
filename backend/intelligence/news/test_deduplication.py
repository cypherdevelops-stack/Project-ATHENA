from datetime import datetime, timedelta, timezone

from django.test import SimpleTestCase

from .contracts import NewsEvent
from .deduplication import cluster_events


class DeduplicationTests(SimpleTestCase):
    def test_paraphrased_same_category_events_cluster(self):
        timestamp = datetime(2026, 8, 27, 12, tzinfo=timezone.utc)
        events = [
            NewsEvent('one', timestamp, 'wire-a', 0.9, 'Federal Reserve keeps rates higher for longer', category='CENTRAL_BANK', entities=('USD',)),
            NewsEvent('two', timestamp + timedelta(minutes=5), 'wire-b', 0.8, 'Fed signals interest rates stay higher for longer', category='CENTRAL_BANK', entities=('USD',)),
        ]
        clustered = cluster_events(events)
        self.assertEqual(clustered[0].event_cluster_id, clustered[1].event_cluster_id)

    def test_different_categories_do_not_cluster(self):
        timestamp = datetime(2026, 8, 27, 12, tzinfo=timezone.utc)
        events = [
            NewsEvent('one', timestamp, 'wire', 0.9, 'Oil prices rally', category='ENERGY'),
            NewsEvent('two', timestamp, 'wire', 0.9, 'Oil prices rally', category='COMMODITIES'),
        ]
        clustered = cluster_events(events)
        self.assertNotEqual(clustered[0].event_cluster_id, clustered[1].event_cluster_id)

    def test_old_events_do_not_cluster(self):
        timestamp = datetime(2026, 8, 27, 12, tzinfo=timezone.utc)
        events = [
            NewsEvent('one', timestamp, 'wire', 0.9, 'Fed raises rates', category='CENTRAL_BANK'),
            NewsEvent('two', timestamp + timedelta(days=2), 'wire', 0.9, 'Fed raises rates', category='CENTRAL_BANK'),
        ]
        clustered = cluster_events(events)
        self.assertNotEqual(clustered[0].event_cluster_id, clustered[1].event_cluster_id)