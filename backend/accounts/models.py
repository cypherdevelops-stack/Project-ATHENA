from django.conf import settings
from django.db import models


class Account(models.Model):
    class AccountType(models.TextChoices):
        PERSONAL = 'PERSONAL', 'Personal'
        DEMO = 'DEMO', 'Demo'
        FUNDED = 'FUNDED', 'Funded'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trading_accounts')
    display_name = models.CharField(max_length=120, default='Primary account')
    platform = models.CharField(max_length=20, default='MT5')
    connection_method = models.CharField(
        max_length=16,
        choices=[('BROKER', 'Broker login'), ('METAAPI', 'MetaAPI')],
        default='BROKER',
    )
    external_account_id = models.CharField(max_length=120, blank=True)
    login = models.CharField(max_length=120, blank=True)
    broker = models.CharField(max_length=120, blank=True)
    server = models.CharField(max_length=120, blank=True)
    terminal_path = models.CharField(max_length=512, blank=True)
    password_encrypted = models.TextField(blank=True)
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    equity = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    account_mode = models.CharField(max_length=32, blank=True)
    trade_allowed = models.BooleanField(default=False)
    terminal_connected = models.BooleanField(default=False)
    last_handshake_at = models.DateTimeField(null=True, blank=True)
    handshake_status = models.CharField(max_length=32, blank=True)
    account_type = models.CharField(max_length=20, choices=AccountType.choices, default=AccountType.DEMO)
    base_currency = models.CharField(max_length=3, default='USD')
    leverage = models.PositiveIntegerField(default=100)
    enabled = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    allowed_instruments = models.JSONField(default=list)
    canonical_asset = models.CharField(max_length=32, blank=True)
    broker_symbol = models.CharField(max_length=128, blank=True)
    market_discovery = models.JSONField(default=dict)
    risk_per_trade = models.DecimalField(max_digits=6, decimal_places=3, default=0.250)
    max_daily_drawdown = models.DecimalField(max_digits=6, decimal_places=2, default=5.00)
    athena_safety_drawdown = models.DecimalField(max_digits=6, decimal_places=2, default=3.00)
    max_overall_drawdown = models.DecimalField(max_digits=6, decimal_places=2, default=10.00)
    max_concurrent_positions = models.PositiveIntegerField(default=1)
    current_daily_drawdown = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    current_overall_drawdown = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    emergency_stop = models.BooleanField(default=False)
    live_execution_enabled = models.BooleanField(default=False)
    live_execution_mode = models.CharField(
        max_length=24,
        choices=[
            ('DISABLED', 'Disabled'),
            ('PAPER', 'Paper'),
            ('CONFIRMATION_REQUIRED', 'Confirmation required'),
            ('AUTOMATIC', 'Automatic'),
        ],
        default='DISABLED',
    )
    allowed_strategies = models.JSONField(default=list)
    max_live_orders_per_day = models.PositiveIntegerField(default=0)
    max_live_risk_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_order_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    require_fresh_decision_seconds = models.PositiveIntegerField(default=60)
    reconciliation_safe = models.BooleanField(default=True)
    last_reconciliation_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def guardian_state(self):
        if self.emergency_stop:
            return 'HALT'
        if self.current_overall_drawdown >= self.max_overall_drawdown:
            return 'ACCOUNT_LOCK'
        if self.current_daily_drawdown >= self.athena_safety_drawdown:
            return 'DAILY_LOCK'
        if not self.enabled:
            return 'DISABLED'
        return 'NORMAL'


class AccountInstrumentCapability(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='instrument_capabilities')
    canonical_asset = models.CharField(max_length=32)
    broker_symbol = models.CharField(max_length=128)
    symbol_visible = models.BooleanField(default=False)
    symbol_selected = models.BooleanField(default=False)
    trade_mode = models.IntegerField(null=True, blank=True)
    execution_mode = models.IntegerField(null=True, blank=True)
    filling_modes = models.JSONField(default=list)
    order_modes = models.JSONField(default=list)
    digits = models.IntegerField(null=True, blank=True)
    point = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    tick_size = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    volume_min = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    volume_max = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    volume_step = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    stops_level = models.IntegerField(null=True, blank=True)
    freeze_level = models.IntegerField(null=True, blank=True)
    contract_size = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    last_discovered_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('account', 'canonical_asset', 'broker_symbol'), name='unique_account_asset_symbol'),
        ]
