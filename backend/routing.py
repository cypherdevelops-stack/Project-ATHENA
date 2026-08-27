from django.urls import re_path

from backend.execution.orchestration_ws import OrchestratorConsumer


websocket_urlpatterns = [
    re_path(
        r'^ws/orchestration/(?P<symbol>[A-Z0-9_.-]+)/(?:(?P<account_id>[0-9]+)/)?$',
        OrchestratorConsumer.as_asgi(),
    ),
]
