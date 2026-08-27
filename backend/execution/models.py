from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone
from backend.accounts.models import Account


class OrchestrationSnapshot(models.Model):
    """
    Persistent record of orchestration decisions and state at a point in time.
    
    Used for:
    - Audit trail of orchestration decisions
    - Backtesting orchestration logic
    - Performance analysis
    - Debugging strategy interactions
    """
    
    REGIME_CHOICES = [
        ('TRENDING_BULLISH', 'Trending Bullish'),
        ('TRENDING_BEARISH', 'Trending Bearish'),
        ('VOLATILE', 'Volatile'),
        ('RANGING', 'Ranging'),
        ('UNKNOWN', 'Unknown'),
    ]
    
    DECISION_CHOICES = [
        ('SCALP_LONG_APPROVED', 'Scalping Long Approved'),
        ('SCALP_SHORT_APPROVED', 'Scalping Short Approved'),
        ('DAY_BUY_DEVELOPING', 'Day Trading Buy Developing'),
        ('DAY_SELL_DEVELOPING', 'Day Trading Sell Developing'),
        ('OBSERVE', 'Observe'),
        ('BLOCKED', 'Blocked'),
        ('ERROR', 'Error'),
    ]
    
    # Account and timing
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='orchestration_snapshots')
    decision_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    symbol = models.CharField(max_length=20, default='XAUUSD')
    
    # Market state
    regime = models.CharField(max_length=20, choices=REGIME_CHOICES)
    bid_price = models.DecimalField(max_digits=10, decimal_places=5)
    ask_price = models.DecimalField(max_digits=10, decimal_places=5)
    spread = models.DecimalField(max_digits=10, decimal_places=5)
    
    # Scalping engine state
    scalping_status = models.CharField(max_length=20, default='OBSERVE')
    scalping_direction = models.CharField(max_length=10, null=True, blank=True)
    scalping_score = models.IntegerField(default=0)
    scalping_confidence = models.FloatField(default=0.0)
    scalping_evidence = models.JSONField(default=dict)
    
    # Day trading engine state
    day_trading_status = models.CharField(max_length=20, default='OBSERVE')
    day_trading_direction = models.CharField(max_length=10, null=True, blank=True)
    day_trading_score = models.IntegerField(default=0)
    day_trading_confidence = models.FloatField(default=0.0)
    day_trading_evidence = models.JSONField(default=dict)
    
    # Portfolio state
    risk_available = models.BooleanField(default=True)
    daily_drawdown_pct = models.FloatField(default=0.0)
    account_equity = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Orchestrator decision
    decision = models.CharField(max_length=30, choices=DECISION_CHOICES)
    decision_reason = models.TextField()
    reason_codes = models.JSONField(default=list)
    recommended_strategy = models.CharField(max_length=20, null=True, blank=True)  # SCALPING, DAY_TRADING, or None
    
    # ML advisory
    ml_probability = models.FloatField(default=0.0)
    
    # Full payload (for reference and debugging)
    full_payload = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['account', '-timestamp']),
            models.Index(fields=['symbol', '-timestamp']),
            models.Index(fields=['decision', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.symbol} {self.decision} @ {self.timestamp.strftime('%H:%M:%S')}"


class ExecutionIntent(models.Model):
    """Durable command boundary between orchestration and broker execution."""

    STATUS_CHOICES = [
        ('QUEUED', 'Queued'),
        ('SUBMITTING', 'Submitting'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('EXPIRED', 'Expired'),
        ('INVALIDATED', 'Invalidated'),
    ]

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='execution_intents')
    snapshot = models.OneToOneField(OrchestrationSnapshot, on_delete=models.CASCADE, related_name='execution_intent')
    decision_id = models.UUIDField(unique=True, db_index=True)
    strategy = models.CharField(max_length=20)
    direction = models.CharField(max_length=10)
    symbol = models.CharField(max_length=128)
    setup = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='QUEUED')
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    invalidation_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['account', 'status', '-created_at']),
            models.Index(fields=['symbol', 'status', '-created_at']),
        ]

    def __str__(self):
        return f"Intent {self.decision_id} {self.status}"


class PaperExecution(models.Model):
    """Idempotent record connecting an orchestration decision to a paper position."""

    STATUS_CHOICES = [
        ('OPENED', 'Opened'),
        ('SKIPPED', 'Skipped'),
        ('REJECTED', 'Rejected'),
    ]

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='paper_executions')
    decision_id = models.UUIDField(unique=True, editable=False)
    position_id = models.CharField(max_length=64, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    reason = models.TextField(blank=True)
    setup = models.JSONField(default=dict)
    quote = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['account', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"Paper {self.status} {self.decision_id}"


class LiveExecutionAttempt(models.Model):
    """Auditable, idempotent record for a confirmed demo-MT5 submission."""

    STATUS_CHOICES = [
        ('SUBMITTING', 'Submitting'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
    ]

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='live_execution_attempts')
    intent = models.ForeignKey('ExecutionIntent', on_delete=models.SET_NULL, null=True, blank=True, related_name='execution_attempts')
    decision_id = models.UUIDField(unique=True, editable=False)
    idempotency_key = models.CharField(max_length=128, unique=True)
    strategy = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    order_ticket = models.BigIntegerField(null=True, blank=True)
    deal_ticket = models.BigIntegerField(null=True, blank=True)
    reason = models.TextField(blank=True)
    setup = models.JSONField(default=dict)
    broker_response = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    request_payload = models.JSONField(default=dict)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['account', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"Live {self.status} {self.decision_id}"


class ExecutionLifecycleEvent(models.Model):
    """Durable copy of execution events also published to the dashboard bus."""

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='execution_lifecycle_events')
    decision_id = models.UUIDField(db_index=True)
    event_type = models.CharField(max_length=64)
    state = models.CharField(max_length=32)
    symbol = models.CharField(max_length=128)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['account', '-created_at']),
            models.Index(fields=['decision_id', '-created_at']),
            models.Index(fields=['event_type', '-created_at']),
        ]

    def __str__(self):
        return f"{self.event_type} {self.decision_id}"


class BrokerPositionSnapshot(models.Model):
    """Latest durable broker-side state for one account position ticket."""

    STATE_CHOICES = [
        ('ACTIVE', 'Active'),
        ('PARTIALLY_FILLED', 'Partially filled'),
        ('CLOSED', 'Closed'),
        ('MODIFIED', 'Modified'),
        ('RECONCILIATION_REQUIRED', 'Reconciliation required'),
    ]

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='broker_position_snapshots')
    decision_id = models.UUIDField(null=True, blank=True, db_index=True)
    ticket = models.BigIntegerField()
    symbol = models.CharField(max_length=128)
    direction = models.CharField(max_length=10)
    volume = models.DecimalField(max_digits=20, decimal_places=8)
    price_open = models.DecimalField(max_digits=20, decimal_places=8)
    stop_loss = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    take_profit = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    state = models.CharField(max_length=32, choices=STATE_CHOICES, default='ACTIVE')
    observed_at = models.DateTimeField(default=timezone.now, db_index=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-observed_at']
        constraints = [
            models.UniqueConstraint(fields=('account', 'ticket'), name='unique_broker_position_ticket'),
        ]
        indexes = [
            models.Index(fields=['account', 'state', '-observed_at']),
            models.Index(fields=['symbol', 'state', '-observed_at']),
        ]

    def __str__(self):
        return f"{self.symbol} {self.ticket} {self.state}"


class StrategyRiskLog(models.Model):
    """
    Track risk state changes for each strategy independently.
    
    Records when strategies enter/exit risk states (cooldowns, locks, etc.)
    """
    
    STRATEGY_CHOICES = [
        ('SCALPING', 'Scalping'),
        ('DAY_TRADING', 'Day Trading'),
    ]
    
    STATE_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('LOSS_STREAK_COOLDOWN', 'Loss Streak Cooldown'),
        ('DAILY_LOSS_LOCK', 'Daily Loss Lock'),
        ('SESSION_LOCKED', 'Session Locked'),
        ('BLOCKED', 'Blocked'),
    ]
    
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='strategy_risk_logs')
    strategy = models.CharField(max_length=20, choices=STRATEGY_CHOICES)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    # State transition
    previous_state = models.CharField(max_length=30, choices=STATE_CHOICES)
    new_state = models.CharField(max_length=30, choices=STATE_CHOICES)
    reason = models.TextField()
    
    # Risk metrics at time of change
    daily_loss_pct = models.FloatField()
    loss_streak = models.IntegerField()
    consecutive_wins = models.IntegerField()
    cooldown_until = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['account', 'strategy', '-timestamp']),
            models.Index(fields=['new_state', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.strategy} {self.previous_state} → {self.new_state} @ {self.timestamp.strftime('%H:%M:%S')}"


class PositionConflictLog(models.Model):
    """
    Log of position conflicts detected and resolved by portfolio governor.
    
    Useful for analyzing when strategies have conflicting signals.
    """
    
    RESOLUTION_CHOICES = [
        ('SCALPING_PRIORITY', 'Scalping Prioritized'),
        ('DAY_TRADING_PRIORITY', 'Day Trading Prioritized'),
        ('BOTH_BLOCKED', 'Both Strategies Blocked'),
        ('COEXIST', 'Strategies Can Coexist'),
    ]
    
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='position_conflict_logs')
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    symbol = models.CharField(max_length=20, default='XAUUSD')
    
    # Conflicting directions
    scalping_direction = models.CharField(max_length=10)
    day_trading_direction = models.CharField(max_length=10)
    
    # Conflict details
    scalping_score = models.IntegerField()
    day_trading_score = models.IntegerField()
    scalping_setup_active = models.BooleanField()
    day_trading_status = models.CharField(max_length=20)
    
    # Resolution
    resolution = models.CharField(max_length=30, choices=RESOLUTION_CHOICES)
    resolution_reason = models.TextField()
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['account', '-timestamp']),
            models.Index(fields=['resolution', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.symbol} conflict → {self.resolution} @ {self.timestamp.strftime('%H:%M:%S')}"


class OrchestratorAlert(models.Model):
    """
    Alerts and notifications from orchestrator.
    
    Used for:
    - Real-time notifications
    - Alert history
    - Debugging
    - User notifications
    """
    
    SEVERITY_CHOICES = [
        ('INFO', 'Information'),
        ('WARNING', 'Warning'),
        ('CRITICAL', 'Critical'),
    ]
    
    ALERT_TYPE_CHOICES = [
        ('DECISION_CHANGED', 'Decision Changed'),
        ('RISK_THRESHOLD_BREACHED', 'Risk Threshold Breached'),
        ('STRATEGY_LOCKED', 'Strategy Locked'),
        ('PORTFOLIO_BLOCKED', 'Portfolio Blocked'),
        ('CONFLICT_DETECTED', 'Conflict Detected'),
        ('REGIME_CHANGED', 'Regime Changed'),
        ('SETUP_CONFIRMED', 'Setup Confirmed'),
        ('SETUP_INVALIDATED', 'Setup Invalidated'),
    ]
    
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='orchestrator_alerts')
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Context
    symbol = models.CharField(max_length=20, default='XAUUSD')
    related_snapshot = models.ForeignKey(
        OrchestrationSnapshot, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='alerts'
    )
    
    # Metadata
    data = models.JSONField(default=dict)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['account', '-timestamp']),
            models.Index(fields=['severity', '-timestamp']),
            models.Index(fields=['is_read', '-timestamp']),
        ]
    
    def __str__(self):
        return f"[{self.severity}] {self.alert_type}: {self.title}"


class OrchestratorSessionLog(models.Model):
    """
    High-level session logs for orchestrator monitoring/backtesting.
    
    Records when monitoring sessions start/stop and summary statistics.
    """
    
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='orchestrator_sessions')
    symbol = models.CharField(max_length=20, default='XAUUSD')
    
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    # Summary statistics
    snapshots_count = models.IntegerField(default=0)
    scalping_approvals = models.IntegerField(default=0)
    day_trading_develops = models.IntegerField(default=0)
    conflicts_detected = models.IntegerField(default=0)
    alerts_raised = models.IntegerField(default=0)
    
    # Performance
    avg_decision_latency_ms = models.FloatField(default=0.0)
    
    # Metadata
    notes = models.TextField(blank=True)
    data = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['account', '-started_at']),
        ]
    
    def __str__(self):
        return f"{self.symbol} session {self.started_at.strftime('%Y-%m-%d %H:%M:%S')}"
    
    @property
    def duration_seconds(self):
        """Duration of session in seconds."""
        end = self.ended_at or timezone.now()
        return (end - self.started_at).total_seconds()
    
    @property
    def duration_str(self):
        """Human-readable duration."""
        seconds = self.duration_seconds
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}h {minutes}m {secs}s"
