from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone


class NewsIntelligenceSnapshot(models.Model):
    """Immutable point-in-time news context attached to an orchestration decision."""

    snapshot_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE, related_name='news_intelligence_snapshots')
    orchestration_snapshot = models.ForeignKey(
        'execution.OrchestrationSnapshot',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='news_snapshots',
    )
    decision_id = models.UUIDField(null=True, blank=True, db_index=True)
    symbol = models.CharField(max_length=32, db_index=True)
    captured_at = models.DateTimeField(default=timezone.now, db_index=True)
    provider_available = models.BooleanField(default=False)
    news_state = models.CharField(max_length=20, default='DEGRADED')
    fundamental_bias = models.CharField(max_length=20, default='UNCERTAIN')
    event_risk = models.CharField(max_length=20, default='CLEAR')
    execution_allowed = models.BooleanField(default=False)
    technical_alignment = models.CharField(max_length=32, default='UNCERTAIN')
    technical_conflict = models.BooleanField(default=False)
    sentiment_score = models.FloatField(default=0.0)
    sentiment_confidence = models.FloatField(default=0.0)
    impact_score = models.FloatField(default=0.0)
    reason_codes = models.JSONField(default=list)
    events = models.JSONField(default=list)
    reaction = models.JSONField(default=dict)
    execution_conditions = models.JSONField(default=dict)
    full_payload = models.JSONField(default=dict)

    class Meta:
        ordering = ['-captured_at']
        indexes = [
            models.Index(fields=['account', '-captured_at']),
            models.Index(fields=['symbol', '-captured_at']),
            models.Index(fields=['event_risk', '-captured_at']),
        ]

    def __str__(self):
        return f'{self.symbol} news {self.news_state} @ {self.captured_at:%H:%M:%S}'


class NewsReactionObservation(models.Model):
    """AMEF-ready expected-versus-actual reaction record."""

    news_snapshot = models.ForeignKey(NewsIntelligenceSnapshot, on_delete=models.CASCADE, related_name='reaction_observations')
    symbol = models.CharField(max_length=32, db_index=True)
    observed_at = models.DateTimeField(default=timezone.now, db_index=True)
    expected_direction = models.CharField(max_length=12, default='UNKNOWN')
    actual_direction = models.CharField(max_length=12, default='UNKNOWN')
    reaction_state = models.CharField(max_length=20, default='UNCONFIRMED')
    price_change = models.FloatField(null=True, blank=True)
    volatility = models.CharField(max_length=20, default='UNKNOWN')
    spread = models.FloatField(null=True, blank=True)
    outcome_context = models.JSONField(default=dict)

    class Meta:
        ordering = ['-observed_at']
        indexes = [models.Index(fields=['symbol', '-observed_at'])]


class NewsMarketSample(models.Model):
    """Point-in-time quote sample used to measure an event's market reaction."""

    news_snapshot = models.ForeignKey(NewsIntelligenceSnapshot, on_delete=models.CASCADE, related_name='market_samples')
    phase = models.CharField(max_length=12, choices=[('PRE', 'Pre-event'), ('POST', 'Post-event')])
    captured_at = models.DateTimeField(default=timezone.now, db_index=True)
    bid = models.FloatField(null=True, blank=True)
    ask = models.FloatField(null=True, blank=True)
    spread = models.FloatField(null=True, blank=True)
    volatility = models.CharField(max_length=20, default='UNKNOWN')
    metadata = models.JSONField(default=dict)

    class Meta:
        ordering = ['captured_at']
        indexes = [models.Index(fields=['news_snapshot', 'phase', '-captured_at'])]


class AdaptiveNewsStatistic(models.Model):
    """Time-ordered, outcome-derived statistics used only for advisory context."""

    symbol = models.CharField(max_length=32)
    category = models.CharField(max_length=32, default='OTHER')
    regime = models.CharField(max_length=32, default='UNKNOWN')
    source_class = models.CharField(max_length=32, default='unknown')
    observations = models.PositiveIntegerField(default=0)
    confirmed_reactions = models.PositiveIntegerField(default=0)
    contrary_reactions = models.PositiveIntegerField(default=0)
    mean_price_change = models.FloatField(default=0.0)
    mean_sentiment_confidence = models.FloatField(default=0.0)
    last_observed_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['symbol', 'category', 'regime', 'source_class'],
                name='unique_adaptive_news_context',
            ),
        ]
        indexes = [models.Index(fields=['symbol', 'category', 'regime'])]


class NewsAMEFRecord(models.Model):
    """Stable point-in-time fundamental context for AMEF and outcome analysis."""

    news_snapshot = models.OneToOneField(NewsIntelligenceSnapshot, on_delete=models.CASCADE, related_name='amef_record')
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    event_context = models.JSONField(default=dict)
    asset_context = models.JSONField(default=dict)
    technical_context = models.JSONField(default=dict)
    reaction_context = models.JSONField(default=dict)
    execution_context = models.JSONField(default=dict)
    trade_outcome = models.JSONField(default=dict)

    class Meta:
        ordering = ['-created_at']
