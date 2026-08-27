from django.db import models


class PointOfInterest(models.Model):
    account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE, related_name='points_of_interest')
    canonical_asset = models.CharField(max_length=32)
    broker_symbol = models.CharField(max_length=128)
    timeframe = models.CharField(max_length=4)
    source_key = models.CharField(max_length=160)
    poi_type = models.CharField(max_length=12)
    formation_timestamp = models.DateTimeField()
    lower_bound = models.FloatField()
    upper_bound = models.FloatField()
    direction = models.CharField(max_length=12)
    strength = models.FloatField(default=0)
    freshness = models.FloatField(default=1)
    state = models.CharField(max_length=20, default='DETECTED')
    invalidation_reason = models.CharField(max_length=80, blank=True)
    reaction_metrics = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('account', 'timeframe', 'source_key'), name='unique_account_timeframe_poi'),
        ]
