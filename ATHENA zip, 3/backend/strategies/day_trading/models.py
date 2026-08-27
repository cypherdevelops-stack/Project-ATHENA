from django.db import models


class DayTradingRiskState(models.Model):
    account = models.OneToOneField('accounts.Account', on_delete=models.CASCADE, related_name='day_trading_risk_state')
    state = models.CharField(max_length=24, default='NORMAL')
    consecutive_losses = models.PositiveIntegerField(default=0)
    daily_risk_used = models.DecimalField(max_digits=8, decimal_places=3, default=0)
    cooldown_until = models.DateTimeField(null=True, blank=True)
    session_locked = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
