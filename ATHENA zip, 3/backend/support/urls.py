from django.urls import path

from . import views


urlpatterns = [
    path('requests', views.create_help_request_view, name='support-help-request'),
]
