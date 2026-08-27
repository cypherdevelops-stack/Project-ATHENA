from django.urls import path

from . import views

urlpatterns = [
    path('sessions', views.sessions_view, name='journal-sessions'),
    path('sessions/create', views.create_session_view, name='journal-session-create'),
    path('sessions/<int:session_id>/events', views.create_event_view, name='journal-event-create'),
]
