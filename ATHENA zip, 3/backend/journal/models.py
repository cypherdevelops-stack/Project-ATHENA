from django.conf import settings
from django.db import models


class JournalSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='journal_sessions')
    account = models.ForeignKey('accounts.Account', on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_sessions')
    canonical_asset = models.CharField(max_length=32, default='XAUUSD')
    market_session = models.CharField(max_length=20, default='UNKNOWN')
    regime = models.CharField(max_length=32, default='UNKNOWN')
    title = models.CharField(max_length=160, default='Market observation')
    status = models.CharField(max_length=20, default='OPEN')
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class JournalEvent(models.Model):
    session = models.ForeignKey(JournalSession, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=40)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
