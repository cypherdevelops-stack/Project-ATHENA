from django.conf import settings
from django.db import models


class HelpRequest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='help_requests')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class HelpAttachment(models.Model):
    request = models.ForeignKey(HelpRequest, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='help/attachments/')
    original_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
