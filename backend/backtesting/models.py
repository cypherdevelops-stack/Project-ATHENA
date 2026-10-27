from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone as django_timezone


class ExternalOwnership(models.Model):
    user_id = models.BigIntegerField(db_column='user_id', db_index=True)
    account_id = models.BigIntegerField(db_column='account_id', db_index=True)

    @property
    def user(self):
        return get_user_model().objects.using('default').get(pk=self.user_id)

    @property
    def account(self):
        from backend.accounts.models import Account

        return Account.objects.using('default').get(pk=self.account_id)

    class Meta:
        abstract = True


class BacktestingDrawing(ExternalOwnership):
    class DrawingType(models.TextChoices):
        TRENDLINE = 'trendline', 'Trend line'
        HORIZONTAL = 'horizontal', 'Horizontal line'
        VERTICAL = 'vertical', 'Vertical line'
        RAY = 'ray', 'Ray'
        RECTANGLE = 'rectangle', 'Rectangle'
        TRIANGLE = 'triangle', 'Triangle'
        ELLIPSE = 'ellipse', 'Ellipse'
        LONG_POSITION = 'long_position', 'Long position'
        SHORT_POSITION = 'short_position', 'Short position'

    symbol = models.CharField(max_length=128)
    timeframe = models.CharField(max_length=8)
    drawing_type = models.CharField(max_length=16, choices=DrawingType.choices)
    start = models.JSONField()
    end = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class HistoricalCandle(ExternalOwnership):
    symbol = models.CharField(max_length=128)
    timeframe = models.CharField(max_length=8)
    timestamp = models.BigIntegerField()
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.BigIntegerField(default=0)
    dataset = models.ForeignKey('HistoricalDataset', null=True, blank=True, on_delete=models.CASCADE, related_name='candles')

    class Meta:
        constraints = [models.UniqueConstraint(fields=('account', 'symbol', 'timeframe', 'timestamp', 'dataset'), name='unique_historical_candle')]
        ordering = ('timestamp',)

    def as_dict(self):
        return {'time': self.timestamp, 'open': self.open, 'high': self.high, 'low': self.low, 'close': self.close, 'volume': self.volume}


class HistoricalDataset(ExternalOwnership):
    source = models.CharField(max_length=32)
    symbol = models.CharField(max_length=128)
    timezone = models.CharField(max_length=64, default='UTC')
    timeframe = models.CharField(max_length=8)
    start_time = models.BigIntegerField()
    end_time = models.BigIntegerField()
    version = models.CharField(max_length=64, default='1')
    row_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=django_timezone.now)


class ReplaySession(ExternalOwnership):
    class Status(models.TextChoices):
        PAUSED = 'PAUSED', 'Paused'
        PLAYING = 'PLAYING', 'Playing'
        COMPLETE = 'COMPLETE', 'Complete'

    dataset = models.ForeignKey('HistoricalDataset', null=True, blank=True, on_delete=models.SET_NULL, related_name='replays')
    symbol = models.CharField(max_length=128)
    timeframe = models.CharField(max_length=8)
    start_time = models.BigIntegerField(null=True, blank=True)
    end_time = models.BigIntegerField(null=True, blank=True)
    cursor = models.PositiveIntegerField(default=50)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PAUSED)
    speed = models.FloatField(default=1.0)
    slippage = models.FloatField(default=0.0)
    commission = models.FloatField(default=0.0)
    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(auto_now=True)


class ReplayTrade(models.Model):
    session = models.ForeignKey(ReplaySession, on_delete=models.CASCADE, related_name='trades')
    direction = models.CharField(max_length=4)
    entry = models.FloatField()
    stop_loss = models.FloatField(null=True, blank=True)
    take_profit = models.FloatField(null=True, blank=True)
    volume = models.FloatField(default=1.0)
    status = models.CharField(max_length=8, default='OPEN')
    outcome = models.CharField(max_length=9, default='OPEN')
    pnl = models.FloatField(default=0.0)
    opened_at = models.BigIntegerField()
    exit_price = models.FloatField(null=True, blank=True)
    closed_at = models.BigIntegerField(null=True, blank=True)
    close_reason = models.CharField(max_length=24, blank=True, default='')
    costs = models.FloatField(default=0.0)
    created_at = models.DateTimeField(default=django_timezone.now)


class ReplayDecision(models.Model):
    session = models.ForeignKey(ReplaySession, on_delete=models.CASCADE, related_name='decisions')
    cursor = models.PositiveIntegerField()
    candle_time = models.BigIntegerField()
    snapshot = models.JSONField(default=dict)
    regime = models.JSONField(default=dict)
    analysis = models.JSONField(default=dict)
    signal = models.JSONField(default=dict)
    decision_state = models.CharField(max_length=16, default='OBSERVE')
    created_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('session', 'cursor'), name='unique_replay_decision_cursor')]
        ordering = ('cursor',)
